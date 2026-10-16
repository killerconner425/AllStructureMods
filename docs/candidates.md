# Structure pack candidate audit (16 Oct 2026)

These entries are **research leads, not bundled content**. Licensing is from project pages; source release/license files and NBT content still require inspection.

| Project | Page | Listed license | Listed versions | Next action |
|---|---|---|---|---|
| Thun's Structures | https://modrinth.com/datapack/thuns-structures | MIT | 26.3 | High priority: inspect current source, convert to Snapshot 4 if necessary; ~20 structures. |
| CF Structures | https://modrinth.com/datapack/cf-structures | MIT | 26.2 | Inspect templates and version conversion. |
| Expanded Structures | https://modrinth.com/datapack/vanilla-expanded-structures | MIT | 26.2 / 26.1.2 | Inspect source, version conversion. |
| Likely Structures | https://modrinth.com/datapack/likely-structures | MIT | 1.21.11 | Review 4 structures and conversion. |
| Vanilla+ Structures | https://modrinth.com/datapack/vanilla%2B_structures | MIT | 1.21.x | Review 7 structures and conversion. |
| Anlidan Vanilla Structures | https://modrinth.com/datapack/anlidan-vanilla-structures | MIT | 1.20.x | Review files and extensive conversion. |
| Structures Addition | https://modrinth.com/datapack/structures-addition | MIT | 1.20–1.20.4 | Review older format. |
| NewStructures | https://modrinth.com/datapack/newstructures | MIT | 1.19.4 | Review older format. |
| Mysterious Structures | https://modrinth.com/datapack/mysterious-structures | CC0-1.0 | 1.21.5–1.21.6 | Review contents and conversion. |
| Immersive Structures | https://modrinth.com/datapack/immersive-structures | CC-BY-NC-SA-4.0 | 1.21.x | Legal review required (noncommercial and share-alike obligations). Do not automatically import. |
| Structures | https://modrinth.com/datapack/structures-mod | GaraKrrals Project License 2.0 | 26.4 Snapshot 4 | **Hold**: not a standard permissive license; assess redistribution terms first. |
| Simple Structures | https://modrinth.com/datapack/simple-structures | ARR | 1.21.x | **Exclude** absent specific permission. |
| StructurePack | https://modrinth.com/datapack/structurepack | ARR | 1.21.x | **Exclude** absent specific permission. |

## Exclusion examples

- Structures Everywhere and omgStructures primarily change existing vanilla structure frequency/placement, violating the rule to preserve generation settings; excluded.
- [Let's Do Addon] Structures has MIT licensing but includes integration with another mod family; only vanilla-independent structures could be considered after template/dependency audit.

## Per-source implementation checklist

- [ ] Actual distribution license and required attribution captured
- [ ] Exact upstream release/version/hash pinned
- [ ] All source blocks and entities vanilla-only
- [ ] Original structure sets and biome tags verified
- [ ] Snapshot 4 data migration verified
- [ ] Per-structure loot table mapped without touching generation settings
- [ ] Worldgen and loot tested in a clean instance
