# AllStructureMods

A planned Fabric 26.4 Snapshot 4 mega-collection of **licensed, vanilla-block structure packs**.

## Non-negotiable merge rules

- Preserve every included structure template, placement spacing/separation/salt, biome selection, terrain adaptation, and generation mechanics unchanged unless a Minecraft-version migration requires a technical adjustment. Document any migration.
- **Only gameplay change: unique loot tables for each distinct structure**. Preserve loot containers and their positions; change loot table references / loot JSON only. Do not invent custom blocks, items, or mobs.
- Retain original source credits and license notices. A project being free to download or source-visible is not necessarily redistributable.
- Avoid namespace collisions and duplicate registrations; if a pack requires altered generation behavior, exclude it pending review.
- Run structural comparisons and Minecraft loading tests before publishing an installable release.

## Status

**Research and integration preparation in progress.** No merged structures, converted snapshot data, or tested JAR are claimed yet. Candidate projects and compatibility status: [docs/candidates.md](docs/candidates.md).

## Integration steps

1. Download the source release of each candidate and verify its actual license and dependencies.
2. Inspect all structure NBT palettes for modded block IDs, including buried processors/pools and loot container references.
3. Port datapack registries to Snapshot 4 only as necessary, checking each change against source behavior.
4. Merge original worldgen data with original settings; namespace safely.
5. Create one custom loot table per distinct structure, with appropriate vanilla-only loot. Rewire table references in container NBT when required.
6. Package as Fabric mod built against actual 26.4 Snapshot 4 and test generation, loot, and startup.

This is a work-in-progress integration project, not a released mod.
