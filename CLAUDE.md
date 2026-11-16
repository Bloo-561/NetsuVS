# Netsu VS

2D anime fighting game based on the Netsu No Kiseki D&D campaign (Trails of Cold Steel inspired). Godot 4.7.2 mono
(C#) on the Mahou SakugaEngine, rollback netcode.

Full project context (design docs, systems, characters, stages, every handoff) is in `docs/project-context/`.
Start with `docs/project-context/README.md`, then the newest handoff it lists.

Working rules (details in `docs/project-context/sprites-start-here.md`):
- Repo stays private; never use the Mahou EOS credentials.
- Don't delete files: move them to `_backup_stage_select/pre_<name>/` (`.tres.bak` / `.tscn.bak`).
- Never leave a copy of a scene/resource elsewhere in the project (uid clash). New `[ext_resource]` lines go at the top.
- C# changes need a Build in Godot before testing.
