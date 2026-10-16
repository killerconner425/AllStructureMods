#!/usr/bin/env python3
"""Audit original source NBT palettes and container loot pointers.
This script DOES NOT alter original structures or world generation.
"""
import io, os, pathlib, json, urllib.request, hashlib, zipfile, collections
import nbtlib
OUT=pathlib.Path("audit-output");OUT.mkdir(exist_ok=True)
PROJECT="ZLL4Dkxb"; V_ID="23Gin9af"
def get(url):
  with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"AllStructureMods-audit/0.2"}),timeout=120) as r:return r.read()
v=json.loads(get(f"https://api.modrinth.com/v2/version/{V_ID}"))
assert v["project_id"]==PROJECT, "Unexpected upstream project"
f=next((f for f in v["files"] if f.get("primary")),v["files"][0])
blob=get(f["url"])
assert hashlib.sha512(blob).hexdigest()==f["hashes"]["sha512"]
archive=zipfile.ZipFile(io.BytesIO(blob))
results=[]; errors=[]
for name in sorted(x for x in archive.namelist() if x.endswith(".nbt") and "/structure/" in x):
  try:
    root=nbtlib.File.parse(io.BytesIO(archive.read(name)))
    palette=root.get("palette",[])
    blocks=[str(p.get("Name","")) for p in palette]
    nonvanilla=sorted(set(b for b in blocks if not b.startswith("minecraft:")))
    containers=[]
    for block in root.get("blocks",[]):
      nbt=block.get("nbt")
      if nbt is None:continue
      loot=nbt.get("LootTable")
      if loot is not None:
        containers.append({"pos":[int(x) for x in block["pos"]],"loot_table":str(loot)})
    results.append({"file":name,"palette_size":len(blocks),"non_vanilla_blocks":nonvanilla,"loot_containers":containers})
  except Exception as ex:errors.append({"file":name,"error":str(ex)})
report={"upstream_version_id":V_ID,"source_sha512":hashlib.sha512(blob).hexdigest(),
"structure_count":len(results),"structures":results,"errors":errors,
"status":"NBTS and loot pointer inventory only; Snapshot 4 generation compatibility not yet tested"}
(OUT/"thuns-nbt-report.json").write_text(json.dumps(report,indent=2))
for x in results:
  print(x["file"],"palette",x["palette_size"],"nonvanilla",x["non_vanilla_blocks"],"chests",len(x["loot_containers"]))
print("ERRORS:",errors)
if errors or any(x["non_vanilla_blocks"] for x in results):raise SystemExit("Vanilla NBT validation failed")
