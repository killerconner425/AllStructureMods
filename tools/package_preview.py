#!/usr/bin/env python3
"""Package the staged Thun datapack as an explicitly UNTESTED Fabric integration JAR.
This does not alter any worldgen registry or other staged datapack bytes.
"""
import io, sys, json, zipfile, pathlib
source=pathlib.Path(sys.argv[1]);out=pathlib.Path(sys.argv[2]);out.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(source) as z:
    entries={x:z.read(x) for x in z.namelist() if not x.endswith('/')}
assert len([x for x in entries if '/worldgen/' in x])==60
assert len([x for x in entries if x.endswith('.nbt')])==20
assert len([x for x in entries if x.startswith('data/allstructuremods/loot_table/chests/') and x.endswith('.json')])==18
meta={"schemaVersion":1,"id":"allstructuremods","version":"0.1.0","name":"All Structure Mods (Thun Preview)","environment":"*",
"description":"UNTESTED integration preview: original Thun structure generation and unique loot tables.",
"authors":["ConnersaysXD"],"contact":{"sources":"https://github.com/killerconner425/AllStructureMods"},
"depends":{"fabricloader":">=0.19.5","minecraft":"26.4-alpha.4","java":">=25"}}
entries["fabric.mod.json"]=json.dumps(meta,indent=2).encode()
entries["META-INF/ASM-TEST-NOTICE.txt"]=b"UNTESTED 26.4 Snapshot 4 data registry and gameplay integration. Do not treat this as a released or fully verified mod.\n"
entries["META-INF/THUNS-PROVENANCE.txt"]=b"Thun's Structures 1.3.4. Original upstream Modrinth project ZLL4Dkxb. Listed license: MIT. Only original container loot references changed and new structure loot tables added. Confirm original copyright and license text before public redistribution.\n"
with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
    for name,blob in sorted(entries.items()):z.writestr(name,blob)
print(f"Created {out}: {out.stat().st_size} bytes")
