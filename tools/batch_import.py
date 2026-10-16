#!/usr/bin/env python3
"""Stage licensed vanilla structure datapacks, preserving worldgen bytes exactly."""
import io,json,zipfile,urllib.request,urllib.parse,hashlib,pathlib,gzip
import nbtlib
CANDIDATES=["ZLL4Dkxb","cf-structures","vanilla-expanded-structures","likely-structures","vanilla+_structures","anlidan-vanilla-structures","structures-addition","newstructures","mysterious-structures"]
VERSIONS=["26.4-snapshot-4","26.3","26.2","26.1.2","1.21.11","1.21.10","1.21.8","1.21.5"]
OUT=pathlib.Path("dist");OUT.mkdir(exist_ok=True)
def get(url):
 with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"AllStructureMods/0.3"}),timeout=120) as r:return r.read()
def js(url):return json.loads(get(url))
merged={};manifest=[]
for slug in CANDIDATES:
 row={"candidate":slug,"included":False}
 try:
  p=js("https://api.modrinth.com/v2/project/"+urllib.parse.quote(slug,safe=""))
  row["name"]=p["title"];row["license"]=p.get("license",{}).get("id")
  if row["license"] not in ("MIT","CC0-1.0","Apache-2.0"):raise ValueError("License not permissive")
  releases=js("https://api.modrinth.com/v2/project/"+p["id"]+"/version")
  choices=[(VERSIONS.index(g),v) for v in releases for g in v.get("game_versions",[]) if g in VERSIONS and "datapack" in v.get("loaders",[])]
  if not choices:raise ValueError("No recent release available")
  v=min(choices,key=lambda x:x[0])[1]
  f=next((x for x in v["files"] if x.get("primary")),v["files"][0]);blob=get(f["url"])
  if hashlib.sha512(blob).hexdigest()!=f["hashes"]["sha512"]:raise ValueError("Hash mismatch")
  with zipfile.ZipFile(io.BytesIO(blob)) as z:
   names=[n for n in z.namelist() if not n.endswith("/")]
   roots=[n[:-len("pack.mcmeta")] for n in names if n.endswith("pack.mcmeta")]
   if len(roots)!=1:raise ValueError("Expected one datapack per release")
   prefix=roots[0];items={n[len(prefix):]:z.read(n) for n in names if n.startswith(prefix)}
  if sum(map(len,items.values()))>120_000_000:raise ValueError("Too large")
  templates=[n for n in items if n.endswith(".nbt") and "/structure/" in n]
  if not templates:raise ValueError("No structure NBT templates")
  for name in templates:
   raw=items[name];root=nbtlib.File.parse(io.BytesIO(gzip.decompress(raw) if raw[:2]==bytes((31,139)) else raw))
   if any(not str(x["Name"]).startswith("minecraft:") for x in root.get("palette",[])):raise ValueError("Nonvanilla block palette")
  data={n:b for n,b in items.items() if n.startswith("data/")}
  duplicates=set(data)&set(merged)
  if duplicates:raise ValueError("Namespace path conflict: "+next(iter(duplicates)))
  if not any("/worldgen/" in n for n in data):raise ValueError("No worldgen files")
  merged.update(data)
  row.update({"included":True,"version":v["version_number"],"templates":len(templates),"sha512":hashlib.sha512(blob).hexdigest(),"loot_customized":False})
 except Exception as ex:row["reason"]=str(ex)
 manifest.append(row);print(row,flush=True)
(OUT/"bulk-report.json").write_text(json.dumps(manifest,indent=2))
if merged:
 with zipfile.ZipFile(OUT/"bulk-stage.zip","w",zipfile.ZIP_DEFLATED) as z:
  for n,b in sorted(merged.items()):z.writestr(n,b)
