#!/usr/bin/env python3
"""Patch only LootTable NBT strings; emit a per-structure loot table.
Input: upstream datapack ZIP path. Output: transformed ZIP and change report.
Never touch worldgen configuration. Requires nbtlib 2.0.4.
"""
import sys,json,zipfile,io,gzip,hashlib,pathlib,random
import nbtlib
IN=pathlib.Path(sys.argv[1]); OUT=pathlib.Path(sys.argv[2]); OUT.parent.mkdir(parents=True,exist_ok=True)
THEMES={
"acacia_treehouse":["acacia_sapling","bread","leather","gold_nugget","spyglass"],
"badlands_temple":["gold_ingot","emerald","bone","iron_ingot","diamond"],
"bell_tower":["iron_ingot","bell","bread","emerald","clock"],
"campsite":["cooked_beef","coal","leather","flint","iron_nugget"],
"castle":["iron_ingot","crossbow","emerald","diamond","golden_apple"],
"copper_mine":["raw_copper","copper_ingot","iron_pickaxe","coal","raw_iron"],
"gazebo":["flower_pot","honey_bottle","bread","emerald","dandelion"],
"graveyard":["bone","rotten_flesh","iron_ingot","gold_ingot","enchanted_book"],
"hobbit_hole":["bread","baked_potato","apple","emerald","honey_bottle"],
"ice_castle":["blue_ice","snowball","iron_ingot","diamond","gold_ingot"],
"ice_igloo":["leather","rabbit_hide","snowball","cooked_salmon","emerald"],
"jungle_treehouse":["bamboo","cocoa_beans","melon_seeds","emerald","gold_ingot"],
"lighthouse":["cod","cooked_salmon","prismarine_shard","spyglass","compass"],
"oasis":["water_bucket","bread","gold_nugget","emerald","melon_slice"],
"observatory":["amethyst_shard","spyglass","compass","clock","ender_pearl"],
"ship":["iron_ingot","paper","emerald","gold_ingot","compass"],
"windmill":["wheat","bread","wheat_seeds","hay_block","emerald"],
"witch_hut":["redstone","glowstone_dust","spider_eye","glass_bottle","gunpowder"]
}
def loot(name):
 """More varied loot, using official loot functions rather than 1-item entries.
 Enchantments use the loot API to select random enchantments.
 """
 items=THEMES[name]
 def entry(item,weight=5,lo=1,hi=1,bonus=None):
  e={"type":"minecraft:item","name":"minecraft:"+item,"weight":weight}
  fn=[]
  if hi>1:fn.append({"function":"minecraft:set_count","count":{"type":"minecraft:uniform","min":lo,"max":hi}})
  if item in ["iron_sword","iron_axe","iron_pickaxe","iron_chestplate","iron_helmet","bow","crossbow","shield","diamond_sword","diamond_pickaxe","trident","leather_chestplate"]:
   fn.append({"function":"minecraft:set_damage","damage":{"type":"minecraft:uniform","min":0.25,"max":0.9}})
  if item=="enchanted_book":
   fn.append({"function":"minecraft:enchant_randomly"})
  if bonus:fn.extend(bonus)
  if fn:e["functions"]=fn
  return e
 supply=[entry(x,11 if i<2 else 7,2 if x not in ["spyglass","clock","compass","water_bucket","iron_pickaxe","crossbow"] else 1,
               9 if x in ["wheat","bone","paper","coal","redstone","raw_copper","iron_ingot","gold_ingot","bread","snowball","amethyst_shard"] else 4 if x in ["emerald","prismarine_shard","gold_nugget","leather","wheat_seeds"] else 2 if x in ["cooked_salmon","baked_potato","apple"] else 1)
         for i,x in enumerate(items)]
 equipment=[entry(x,w) for x,w in [("iron_sword",7),("iron_axe",6),("iron_pickaxe",7),
   ("iron_helmet",5),("iron_chestplate",4),("bow",5),("crossbow",3),("shield",4),("leather_chestplate",5),
   ("enchanted_book",5),("diamond_sword",1),("diamond_pickaxe",1)]]
 reward=[entry(x,w,lo,hi) for x,w,lo,hi in [("iron_ingot",12,2,7),("gold_ingot",10,2,6),
  ("emerald",9,1,5),("lapis_lazuli",10,3,12),("redstone",10,3,10),("diamond",3,1,3),
  ("golden_apple",2,1,2),("ender_pearl",4,1,3),("experience_bottle",5,2,6)]]
 return {"type":"minecraft:chest","pools":[
  {"rolls":{"type":"minecraft:uniform","min":3,"max":6},"entries":supply},
  {"rolls":{"type":"minecraft:uniform","min":2,"max":4},"entries":equipment},
  {"rolls":{"type":"minecraft:uniform","min":2,"max":4},"entries":reward}]}
changes=[]; output={}
with zipfile.ZipFile(IN) as source:
 names=source.namelist()
 prefixes=[s[:-len("pack.mcmeta")] for s in names if s.endswith("pack.mcmeta")]
 if len(prefixes)!=1:raise SystemExit("Expected exactly one upstream datapack")
 prefix=prefixes[0]
 for n in names:
  if n.endswith("/"):continue
  if not n.startswith(prefix):continue
  rel=n[len(prefix):]; data=source.read(n)
  if rel.endswith(".nbt") and "/structure/" in rel:
   base=pathlib.PurePosixPath(rel).stem
   if base in THEMES:
    compressed=data[:2]==bytes((31,139))
    root=nbtlib.File.parse(io.BytesIO(gzip.decompress(data) if compressed else data))
    count=0; previous=[]
    for block in root.get("blocks",[]):
     meta=block.get("nbt")
     if meta is not None and "LootTable" in meta:
      previous.append(str(meta["LootTable"]))
      meta["LootTable"]=nbtlib.String("allstructuremods:chests/"+base)
      count+=1
    if count:
     buf=io.BytesIO();root.write(buf)
     changed=buf.getvalue()
     data=gzip.compress(changed,mtime=0) if compressed else changed
     changes.append({"structure":base,"original_tables":sorted(set(previous)),"containers_modified":count,"source":rel})
     table="data/allstructuremods/loot_table/chests/"+base+".json"
     output[table]=json.dumps(loot(base),indent=2).encode()
  output[rel]=data
with zipfile.ZipFile(OUT,"w",zipfile.ZIP_DEFLATED) as dest:
 for name,bytes_ in sorted(output.items()):dest.writestr(name,bytes_)
report={"original_zip_sha256":hashlib.sha256(IN.read_bytes()).hexdigest(),"output_zip_sha256":hashlib.sha256(OUT.read_bytes()).hexdigest(),"changes":changes,"note":"Only container LootTable NBT references and additional loot tables changed; 2 containerless structures unchanged."}
OUT.with_suffix(".report.json").write_text(json.dumps(report,indent=2))
print(json.dumps({"structures_with_loot":len(changes),"containers_modified":sum(x["containers_modified"] for x in changes)},indent=2))
assert len(changes)==18,"Expected 18 structures with built-in loot containers; inspect changed upstream release"
assert sum(x["containers_modified"] for x in changes)==63,"Expected 63 loot references; inspect changed release"
