#!/usr/bin/env python3
"""Fetch and audit a pinned upstream Modrinth datapack release.
Never republishes structure assets until the audit has been reviewed."""
import json, os, pathlib, urllib.request, zipfile, hashlib, re, io
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/"audit-output"
OUT.mkdir(exist_ok=True)
PROJECT=os.environ.get("UPSTREAM_PROJECT","ZLL4Dkxb")
VERSION=os.environ.get("UPSTREAM_GAME_VERSION","26.3")
headers={"User-Agent":"AllStructureMods/0.1 (structure provenance audit)"}
def get(url):
    return json.load(urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=50))
versions=get(f"https://api.modrinth.com/v2/project/{PROJECT}/version")
candidate=[v for v in versions if VERSION in v.get("game_versions",[]) and "datapack" in v.get("loaders",[])]
if not candidate: raise SystemExit(f"No released datapack for {PROJECT} supporting {VERSION}")
candidate.sort(key=lambda v:v.get("date_published",""),reverse=True)
v=candidate[0]; f=next((f for f in v["files"] if f.get("primary")),v["files"][0])
blob=urllib.request.urlopen(urllib.request.Request(f["url"],headers=headers),timeout=90).read()
actual=hashlib.sha512(blob).hexdigest()
assert actual==f["hashes"]["sha512"],"Upstream SHA512 mismatch"
z=zipfile.ZipFile(io.BytesIO(blob))
names=z.namelist()
files={x for x in names if not x.endswith("/")}
if sum(z.getinfo(n).file_size for n in files)>250_000_000: raise SystemExit("Archive unexpectedly large")
worldgen=[n for n in names if "/worldgen/" in n]
nbt=[n for n in names if n.endswith(".nbt")]
loot=[n for n in names if "/loot_table/" in n or "/loot_tables/" in n]
structure_names=[n for n in worldgen if re.search(r"/structure/[^/]+\\.json$",n)]
issues=[]
for n in files:
    if n.startswith("/") or ".." in pathlib.PurePosixPath(n).parts: issues.append("Unsafe path: "+n)
    if n.endswith(".json"):
        try: json.loads(z.read(n))
        except Exception: issues.append("Invalid JSON: "+n)
data={"project":PROJECT,"project_title":"Thun's Structures","requested_game_version":VERSION,
      "version_id":v["id"],"version_number":v["version_number"],"url":f["url"],
      "sha512":actual,"file_count":len(files),"structure_templates":nbt,
      "worldgen_files":worldgen,"structure_definitions":structure_names,
      "loot_table_files":loot,"issues":issues,
      "block_palette_validation":"PENDING: structure NBT palette scan and processor/jigsaw review",
      "snapshot4_compatibility":"UNVERIFIED; source targets "+VERSION,
      "import_status":"AUDIT ONLY; no untested worldgen installed"}
(OUT/"thuns-report.json").write_text(json.dumps(data,indent=2))
lines=["# Thun's Structures upstream archive audit","",f"- Release: {v['version_number']} ({v['id']})",f"- Minecraft release targeted: {VERSION}",
       f"- SHA-512 verified: {actual}",f"- Structure NBT templates: {len(nbt)}",f"- Worldgen registry files: {len(worldgen)}",f"- Loot table files: {len(loot)}",
       f"- Problems: {len(issues)}","","This is inspection only. Source world generation and vanilla-block status must be checked before merging.",
       "","## Registered structure definitions",*["- "+x for x in structure_names],"","## Issues",*["- "+x for x in issues]]
(OUT/"thuns-report.md").write_text("\n".join(lines)+"\n")
print("\n".join(lines[:10]))
