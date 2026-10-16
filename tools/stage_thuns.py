#!/usr/bin/env python3
"""Fetch a pinned MIT-licensed structure datapack and build a Fabric mod JAR.
Only modifies loot tables; preserves original structure and worldgen files exactly.
Fails closed when upstream release/version or pack layout is incompatible.
"""
import io,json,hashlib,os,pathlib,urllib.request,zipfile,shutil
PROJECT="ZLL4Dkxb"
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/"dist"; OUT.mkdir(exist_ok=True)
def get(url):
  req=urllib.request.Request(url,headers={"User-Agent":"AllStructureMods/0.1 (github integration)"})
  with urllib.request.urlopen(req,timeout=90) as r:return r.read()
def stop(reason): raise SystemExit("AUDIT STOP: "+reason)
p=json.loads(get("https://api.modrinth.com/v2/project/"+PROJECT))
if p.get("license",{}).get("id")!="MIT":stop("Source license not MIT")
vlist=json.loads(get("https://api.modrinth.com/v2/project/"+PROJECT+"/version"))
vs=[v for v in vlist if "26.3" in v.get("game_versions",[]) and "datapack" in v.get("loaders",[])]
if not vs:stop("No 26.3 datapack release found")
v=sorted(vs,key=lambda x:x["date_published"],reverse=True)[0]
f=next((x for x in v["files"] if x.get("primary")),v["files"][0])
raw=get(f["url"])
if hashlib.sha512(raw).hexdigest()!=f["hashes"]["sha512"]:stop("SHA512 mismatch")
z=zipfile.ZipFile(io.BytesIO(raw))
entries={}
for i in z.infolist():
  if i.is_dir():continue
  path=pathlib.PurePosixPath(i.filename)
  if path.is_absolute() or ".." in path.parts:stop("Unsafe zip entry")
  if i.file_size>24_000_000:stop("Archive entry unreasonably large: "+i.filename)
  entries[str(path)]=z.read(i)
if sum(len(x) for x in entries.values())>140_000_000:stop("Archive exceeds 140 MB")
# Some distributions wrap the datapack in a single outer directory.
packs=[n for n in entries if n.endswith("pack.mcmeta")]
if len(packs)!=1:stop("Expected one pack.mcmeta, found "+str(packs))
prefix=packs[0][:-len("pack.mcmeta")]
entries={k[len(prefix):]:v for k,v in entries.items() if k.startswith(prefix)}
if not any(n.startswith("data/") and "/worldgen/" in n for n in entries):stop("No datapack worldgen found")
if not any(n.endswith(".nbt") for n in entries):stop("No structure NBT found")
# Prevent binary rewriting of generation or structure files in this initial phase.
# First export exact source (only pack assets) as a Fabric jar for compatibility testing.
mod={"schemaVersion":1,"id":"allstructuremods","version":"0.1.0","name":"All Structure Mods (Thun integration preview)","environment":"*",
"authors":["ConnersaysXD"],"description":"Preserves original Thun's Structures world generation; compatibility preview.",
"license":"MIT","depends":{"fabricloader":">=0.19.5","minecraft":"26.4-snapshot-4"}}
# Override the source data pack's metadata with the Snapshot 4 compatible Fabric pack.
# Mod loader will supply its own resource metadata as necessary.
entries.pop("pack.mcmeta",None)
entries["fabric.mod.json"]=json.dumps(mod,indent=2).encode()
entries["META-INF/LICENSE-THUNS-NOTICE.txt"]=("Thun's Structures by its original author. MIT licensed according to Modrinth project "+PROJECT+
"\nUpstream release ID: "+v["id"]+"\nUpstream SHA512: "+hashlib.sha512(raw).hexdigest()+
"\nOriginal LICENSE text must be included before public redistribution when available.\n").encode()
report={"upstream_project":p["slug"],"upstream_version":v["version_number"],"version_id":v["id"],
"upstream_sha512":hashlib.sha512(raw).hexdigest(),"structures":[n for n in entries if n.endswith(".nbt")],
"worldgen":[n for n in entries if "/worldgen/" in n],"loot_tables":[n for n in entries if "/loot_table/" in n or "/loot_tables/" in n],
"status":"PREVIEW ONLY: snapshot format and vanilla palette not yet validated; UNIQUE LOOT NOT IMPLEMENTED",
"packaging":"Original datapack files bundled byte for byte, except pack.mcmeta removed."}
(OUT/"integration-audit.json").write_text(json.dumps(report,indent=2))
# Fail closed: don't publish as a playable mod without byte-level palette inspection and loot conversion.
if os.environ.get("PUBLISH_UNVERIFIED","false").lower()!="true":
  print("Wrote inventory report. Distribution intentionally gated pending validation.")
  print("Structure templates",len(report["structures"]),"worldgen",len(report["worldgen"]))
  raise SystemExit(0)
with zipfile.ZipFile(OUT/"AllStructureMods-0.1.0-UNVERIFIED.jar","w",zipfile.ZIP_DEFLATED) as out:
  for name,blob in sorted(entries.items()):out.writestr(name,blob)
