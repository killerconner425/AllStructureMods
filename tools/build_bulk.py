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
common=["bread","iron_ingot","gold_ingot","emerald","lapis_lazuli","coal","arrow","leather","torch",
        "cooked_beef","amethyst_shard","string","bone","paper","redstone","compass","map","diamond"]
gear=["iron_sword","iron_axe","iron_pickaxe","bow","crossbow","shield","iron_helmet","iron_chestplate",
      "iron_leggings","iron_boots","diamond_sword","diamond_pickaxe","enchanted_book","golden_apple"]
def item(name,weight,maximum=1):
 e={"type":"minecraft:item","name":"minecraft:"+name,"weight":weight}
 functions=[]
 if maximum>1:functions.append({"function":"minecraft:set_count","count":{"type":"minecraft:uniform","min":1,"max":maximum}})
 if name=="enchanted_book":functions.append({"function":"minecraft:enchant_randomly"})
 if name in gear and name not in ("enchanted_book","golden_apple"):
  functions.append({"function":"minecraft:set_damage","damage":{"type":"minecraft:uniform","min":0.15,"max":0.9}})
 if functions:e["functions"]=functions
 return e
def table(seed):
 # Stable hash supplies per-structure variation without nondeterministic builds.
 h=int(hashlib.sha256(seed.encode()).hexdigest()[:12],16)
 materials=[common[(h//(i+1)+i*7)%len(common)] for i in range(10)]
 equipment=[gear[(h//(i+3)+i*5)%len(gear)] for i in range(9)]
 return {"type":"minecraft:chest","pools":[
  {"rolls":{"type":"minecraft:uniform","min":3,"max":7},
   "entries":[item(v,12-i,2+(i%9)) for i,v in enumerate(materials)]},
  {"rolls":{"type":"minecraft:uniform","min":2,"max":4},
   "entries":[item(v,10-i) for i,v in enumerate(equipment)]},
  {"rolls":{"type":"minecraft:uniform","min":1,"max":3},
   "entries":[item("enchanted_book",4),item("diamond",3,3),item("emerald",9,6),
              item("golden_apple",2),item("experience_bottle",8,7),
              item("gold_ingot",12,8),item("iron_ingot",15,9)]}]}
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

metadata={"schemaVersion":1,"id":"allstructuremods","version":"0.2.3",
"name":"All Structure Mods (Bulk TEST)","environment":"*",
"description":"Bulk structure integration preview. Generated loot only; original worldgen preserved.",
"authors":["ConnersaysXD"],"depends":{"fabricloader":">=0.19.5","minecraft":"26.4-alpha.4","java":">=25"}}
files["fabric.mod.json"]=json.dumps(metadata,indent=2).encode()
files["META-INF/BUILD-NOTICE.txt"]=b"UNTESTED bulk structure pack. Generated loot tables and block entity LootTable tags modified; worldgen files left unchanged. See audit JSON. Licensing review required before public redistribution.\n"
with zipfile.ZipFile(dest,"w",zipfile.ZIP_DEFLATED) as z:
 for name,content in sorted(files.items()):z.writestr(name,content)
(dest.parent/"bulk-loot-report.json").write_text(json.dumps({"structures":report,"altered_templates":altered,"total_chests":sum(r["containers"] for r in report)},indent=2))
print(f"Packaged {len(report)} templates, modified {len(altered)}, total loot containers: {sum(x['containers'] for x in report)}")
