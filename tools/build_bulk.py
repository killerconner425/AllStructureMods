#!/usr/bin/env python3
"""Convert batch-staged vanilla datapack into one Fabric test JAR.
Preserves worldgen and templates except replacing LootTable NBT fields.
Creates distinctive loot for all containers, including shared upstream loot references.
"""
import io,gzip,sys,zipfile,json,pathlib,hashlib,re
import nbtlib
from importlib.machinery import SourceFileLoader
source=pathlib.Path(sys.argv[1]);dest=pathlib.Path(sys.argv[2]);dest.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(source) as z:
 files={n:z.read(n) for n in z.namelist() if not n.endswith("/")}
assert files and any("/worldgen/" in n for n in files)
# Distinct per-structure loot; independent across differing mods/namespaces.
# Balanced loot: themed materials, equipment, and rare treasures.
# Explicit components are used because Snapshot 4 did not apply legacy
# enchant_randomly/set_damage functions reliably in the previous test.
import random
THEMES={
 "castle":(["bread","arrow","iron_ingot","leather","shield"],["iron_sword","iron_chestplate","crossbow"]),
 "ship":(["paper","string","cod","gold_nugget","compass"],["bow","iron_sword","leather_boots"]),
 "mine":(["coal","raw_iron","raw_copper","torch","flint"],["iron_pickaxe","iron_axe","iron_helmet"]),
 "grave":(["bone","rotten_flesh","coal","gold_nugget","string"],["iron_sword","iron_helmet","bow"]),
 "tower":(["arrow","bread","iron_nugget","string","torch"],["bow","crossbow","iron_boots"]),
 "temple":(["bone","gold_nugget","lapis_lazuli","rotten_flesh","clay_ball"],["iron_sword","golden_helmet","bow"]),
 "farm":(["wheat","bread","wheat_seeds","carrot","apple"],["iron_hoe","leather_boots","iron_axe"]),
 "hut":(["bread","stick","leather","coal","mushroom_stew"],["stone_axe","leather_chestplate","iron_helmet"]),
}
GENERAL=["bread","coal","stick","torch","leather","string","bone","paper","arrow","flint","copper_ingot","potato","wheat","apple","iron_nugget","gold_nugget"]
GEAR=["iron_sword","iron_pickaxe","iron_axe","bow","crossbow","iron_helmet","iron_chestplate","iron_boots","leather_chestplate"]
MAX_DAMAGE={"iron_sword":250,"iron_pickaxe":250,"iron_axe":250,"iron_helmet":165,"iron_chestplate":240,"iron_leggings":225,"iron_boots":195,"bow":384,"crossbow":465,"shield":336,
"diamond_sword":1561,"diamond_pickaxe":1561,"leather_chestplate":80,"leather_boots":65,"stone_axe":131,"iron_hoe":250,"golden_helmet":77}
ENCHANTS={
 "sword":[("sharpness",1,3),("unbreaking",1,2),("knockback",1,1)],
 "pickaxe":[("efficiency",1,3),("unbreaking",1,2),("fortune",1,1)],
 "axe":[("efficiency",1,3),("unbreaking",1,2)],
 "bow":[("power",1,3),("unbreaking",1,2),("punch",1,1)],
 "crossbow":[("quick_charge",1,2),("piercing",1,2)],
 "armor":[("protection",1,3),("unbreaking",1,2)],
 "book":[("efficiency",1,4),("sharpness",1,3),("protection",1,4),("unbreaking",1,3),("power",1,4),("fortune",1,2),("mending",1,1)]
}
def compatible_kind(item):
 if item=="enchanted_book":return "book"
 if "sword" in item:return "sword"
 if "pickaxe" in item:return "pickaxe"
 if "axe" in item:return "axe"
 if item in ("bow","crossbow"):return item
 return "armor"
def item(name,weight=8,minimum=1,maximum=1,variant=0,enchanted=False,damaged=False):
 e={"type":"minecraft:item","name":"minecraft:"+name,"weight":weight}
 functions=[]
 if maximum>1:functions.append({"function":"minecraft:set_count","count":{"type":"minecraft:uniform","min":minimum,"max":maximum}})
 components={}
 if name in MAX_DAMAGE and damaged:
  damage=int(MAX_DAMAGE[name]*(0.18+((variant*7)%48)/100))
  components["minecraft:damage"]=max(1,damage)
 if enchanted:
  candidates=ENCHANTS[compatible_kind(name)]
  enchant,lo,hi=candidates[variant%len(candidates)]
  level=lo+(variant//3)%(hi-lo+1)
  component="minecraft:stored_enchantments" if name=="enchanted_book" else "minecraft:enchantments"
  components[component]={"minecraft:"+enchant:level}
 if components:functions.append({"function":"minecraft:set_components","components":components})
 if functions:e["functions"]=functions
 return e
def table(seed):
 h=int(hashlib.sha256(seed.encode()).hexdigest()[:16],16)
 rng=random.Random(h)
 theme=next((v for k,v in THEMES.items() if k in seed),None)
 supplies=list(theme[0]) if theme else rng.sample(GENERAL,7)
 equipment=list(theme[1]) if theme else rng.sample(GEAR,3)
 # Each structure has stable curated selections, but chest rolls are random.
 supplies=list(dict.fromkeys(supplies+rng.sample(GENERAL,4)))
 equip=list(dict.fromkeys(equipment+rng.sample(GEAR,2)))
 pool1=[item(n,10 if n not in ("iron_ingot","gold_ingot") else 4,1,
             2 if n in ("bread","apple","potato") else 5 if n in ("iron_ingot","gold_ingot") else 9,
             i) for i,n in enumerate(supplies)]
 pool2=[]
 for i,n in enumerate(equip):
  pool2.append(item(n,9,variant=h%97+i,damaged=(i%2==0)))
  pool2.append(item(n,2,variant=h%101+i,enchanted=True,damaged=(i%3==0)))
 pool2.append(item("enchanted_book",2,variant=h%17,enchanted=True))
 pool3=[item("emerald",8,1,2),item("iron_ingot",9,1,3),item("gold_ingot",6,1,3),
        item("diamond",2,1,1),item("golden_apple",1),item("experience_bottle",3,1,3)]
 return {"type":"minecraft:chest","pools":[
  {"rolls":{"type":"minecraft:uniform","min":1,"max":4},"entries":pool1},
  {"rolls":{"type":"minecraft:uniform","min":0,"max":2},"entries":pool2},
  {"rolls":{"type":"minecraft:uniform","min":0,"max":2},"entries":pool3}]}
report=[]; altered=[]
for path,blob in list(files.items()):
 if not (path.endswith(".nbt") and "/structure/" in path):continue
 prefix=path.split("/structure/")[0].replace("data/","").replace("/worldgen","")
 name=pathlib.PurePosixPath(path).stem
 key=re.sub(r"[^a-z0-9_/-]","_",prefix+"/"+name)
 packed=blob[:2]==bytes((31,139))
 try:root=nbtlib.File.parse(io.BytesIO(gzip.decompress(blob) if packed else blob))
 except Exception as e:raise RuntimeError("Cannot inspect structure "+path) from e
 palette=root.get("palette",[])
 if any(not str(x["Name"]).startswith("minecraft:") for x in palette):raise RuntimeError("Nonvanilla block in "+path)
 count=0
 for b in root.get("blocks",[]):
  tag=b.get("nbt")
  if tag is not None and "LootTable" in tag:
   tag["LootTable"]=nbtlib.String("allstructuremods:chests/"+key)
   count+=1
 if count:
  out=io.BytesIO();root.write(out)
  files[path]=gzip.compress(out.getvalue(),mtime=0) if packed else out.getvalue()
  tablepath="data/allstructuremods/loot_table/chests/"+key+".json"
  files[tablepath]=json.dumps(table(key),indent=2).encode()
  altered.append(path)
 report.append({"structure":path,"containers":count,"loot_table":"allstructuremods:chests/"+key if count else None})
# Snapshot 4 workaround: three CF processor lists fail registry parsing with append_loot.
# Preserve predicates, output states and placement odds, changing only how loot is attached.
for processor_file in (
 "data/cf_structures/worldgen/processor_list/grog_archaeology.json",
 "data/cf_structures/worldgen/processor_list/mill_loot.json",
 "data/cf_structures/worldgen/processor_list/spawner_fix.json"
):
 if processor_file not in files:continue
 document=json.loads(files[processor_file])
 modified=0
 for processor in document.get("processors",[]):
  for rule in processor.get("rules",[]):
   m=rule.get("block_entity_modifier",{})
   if m.get("type")=="minecraft:append_loot":
    rule["block_entity_modifier"]={"type":"minecraft:append_static","data":{"LootTable":m["loot_table"]}}
    modified+=1
 # 26.4 uses block-state codec id instead of legacy NBT Name in processor rules.
 for processor in document.get("processors",[]):
  for rule in processor.get("rules",[]):
   state=rule.get("output_state")
   if isinstance(state,dict) and "Name" in state:
    modern={"id":state.pop("Name")}
    if "Properties" in state:modern["properties"]=state.pop("Properties")
    modern.update(state)
    rule["output_state"]=modern
    modified+=1
 if modified:
  files[processor_file]=json.dumps(document,indent=2).encode()
  print("CF Snapshot 4 processor loot compatibility:",processor_file,modified)

# Convert old random-number syntax in ALL bundled loot tables, not only
# those mentioned in a crash report. Modern codec requires explicit type.
def update_loot_providers(node,field=None):
 if isinstance(node,list):
  return [update_loot_providers(v) for v in node]
 if not isinstance(node,dict):return node
 result={k:update_loot_providers(v,k) for k,v in node.items()}
 if field in ("rolls","count","damage") and "min" in result and "max" in result and "type" not in result:
  return {"type":"minecraft:uniform",**result}
 return result
for path,blob in list(files.items()):
 if "/loot_table/" in path and path.endswith(".json"):
  obj=json.loads(blob)
  fixed=update_loot_providers(obj)
  if fixed!=obj:
   files[path]=json.dumps(fixed,indent=2).encode()
   print("Modernized legacy loot distributions:",path)

# Replace old source chest loot tables too; some upstream tables generated
# entire double chests of one-piece precious metals. Leave non-chest tables intact.
for path,blob in list(files.items()):
 if "/loot_table/" not in path or not path.endswith(".json"):continue
 obj=json.loads(blob)
 if obj.get("type")=="minecraft:chest" and not path.startswith("data/allstructuremods/"):
  files[path]=json.dumps(table(path),indent=2).encode()
  print("Rebalanced inherited chest loot:",path)

metadata={"schemaVersion":1,"id":"allstructuremods","version":"0.2.4",
"name":"All Structure Mods (Bulk TEST)","environment":"*",
"description":"Bulk structure integration preview. Generated loot only; original worldgen preserved.",
"authors":["ConnersaysXD"],"depends":{"fabricloader":">=0.19.5","minecraft":"26.4-alpha.4","java":">=25"}}
files["fabric.mod.json"]=json.dumps(metadata,indent=2).encode()
files["META-INF/BUILD-NOTICE.txt"]=b"UNTESTED bulk structure pack. Generated loot tables and block entity LootTable tags modified; worldgen files left unchanged. See audit JSON. Licensing review required before public redistribution.\n"
with zipfile.ZipFile(dest,"w",zipfile.ZIP_DEFLATED) as z:
 for name,content in sorted(files.items()):z.writestr(name,content)
(dest.parent/"bulk-loot-report.json").write_text(json.dumps({"structures":report,"altered_templates":altered,"total_chests":sum(r["containers"] for r in report)},indent=2))
print(f"Packaged {len(report)} templates, modified {len(altered)}, total loot containers: {sum(x['containers'] for x in report)}")
