# NetsuVS folder guide

| Folder | What goes here |
|---|---|
| `actors/` | Characters. One folder per fighter with its sprites, portraits, palettes, voice, moves/states/hitboxes and its `.tscn`. |
| `actors/_shared/` | Things every fighter uses (hit sparks, common states). |
| `actors/_template/` | Blank fighter. Copy it to start a new character. |
| `actors/assists/` | Climax-style assist characters. |
| `stages/` | One folder per stage (scene, background layers, preview). `_template/` is a blank stage. |
| `scenes/` | One folder per screen (boot, title, menus, battle, results...). Each scene sits next to its script. |
| `engine/` | Borrowed code we rarely edit: SakugaEngine, rollback netcode, MessagePack. |
| `game/` | Code WE write: autoloads, new systems (assists, guard crush), reusable UI. |
| `data/` | Game-wide settings resources: roster, stage list, game modes, match rules. |
| `assets/` | Shared media not owned by one character/stage: music, sfx, announcer, fonts, UI art, VFX, shaders. |
| `addons/` | Third-party Godot plugins (name required by Godot). |
| `tools/` | Editor helpers and debug tools. |
| `docs/` | Notes like this one. |

**Naming:** `snake_case` for folders and files. C# scripts are `PascalCase` and must match their class name (`AssistManager.cs`).

`.gdkeep` files are empty placeholders so Git keeps empty folders. Delete one once its folder has real files.
