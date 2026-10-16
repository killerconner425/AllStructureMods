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
 items=THEMES[name]
 return {"type":"minecraft:chest","pools":[{"rolls":{"type":"minecraft:uniform","min":2,"max":5},"entries":[{"type":"minecraft:item","name":"minecraft:"+it,"weight":w} for w,it in zip((10,8,7,4,1),items)]}]}
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
