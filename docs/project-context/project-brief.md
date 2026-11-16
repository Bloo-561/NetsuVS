# Netsu VS — Project Brief

Fighting game based on the Netsu No Kiseki DnD campaign (campaign is based on Trails of Cold Steel). Model: Dengeki Bunko Fighting Climax (A/B/C + S support, macros, assist characters with cooldowns). Title/menu look inspired by Persona 4 Arena.

## Goals
- Buildable at a junior-programmer pace with friends; easy to add/edit characters and stages without a full day of wiring.
- 2D sprites (hand-made + AI-assisted), rollback netcode, polished enough for a public feedback release.
- New systems easy to bolt on and tune in-game.

## Base decision
- **Base: Mahou Project (SakugaEngine, C#).** Deterministic fixed-point physics (10000 units = 1 m, ints), PleaseResync rollback, MessagePack save/load state, replays, hitbox viewer (F10 in training), input history, frame advantage display.
- **Reference: Blue Archive FG (GDScript).** Borrow design, not code: assist system, guard meter/crush, juggle/combo scaling, stat templates, menu polish.
- Epic Online Services removed. Online play uses LiteNetLib direct IP connection (no UI yet).

## Project setup
- Project: `E:\Netsu Projects\Netsu Fighter\Godot\netsu-vs`, Godot 4.7.2 mono. C# project: `NetsuVS.csproj` (Godot.NET.Sdk/4.7.2, net8.0, MessagePack 3.1.4).
- 1920×1080 base (window 1280×720 for dev), Compatibility renderer, max 60 fps.
- Folders: actors/ (silverwing, caramello, _shared/sakuga, _template, assists), stages/ (training_stage, mahou/), scenes/<screen>/, engine/ (sakuga, netcode/PleaseResync + LiteNetLib, messagepack, autoloads, ui, assemblies), game/ (autoloads, systems, ui), data/ (roster, stage_list, game_modes, match_settings, soundtrack...), assets/, tools/ (port_mahou record, move_preview), docs/.
- Language split: GDScript for menus/UI glue; C# for engine and fight systems.
- Autoloads: `Controls` (p1_/p2_ actions a,b,c,s,ab,bc,abc,start + "pause"), `SceneRouter` (fades; TITLE/MAIN_MENU/CHARACTER_SELECT/BATTLE), `MatchSetup` (fills data/match_settings.tres, starts battle), engine `LoadingScreenManager`, `AudioManager`.
- Engine edits from Mahou: EOS removed (PleaseResyncManager, GameManager); input prefix p1/p2 (GlobalFunctions); ReadInputs maps A/B/C→FACE_A/B/C, S→FACE_D (Mahou's dash button, placeholder until assists), macros AB/BC/ABC.
- Battle HUD is Mahou's 1280×720 layout; `scenes/battle/battle_resolution.gd` switches content scale to 1280×720 during battles.
- Branding: NETSU VS logo, VS icon, boot splash; fonts Megapunch Italic / Dragonlands / Maximum Impact (Hawtpixel license: in-game OK, don't redistribute files, keep repo private).

## Screens
- Title → Main menu (P4A-style, approved; user removed streak lines) → Training / Versus → Character select → Battle.
- Character select (Cold Steel theme): navy/gold, rotating ARCUS-ring shader (7 Class VII quartz rings), Class VII "VII" emblem, hexagonal quartz roster slots (8, extra = "?"), big renders + name plates, P2 joins with a pick button else P1 picks the CPU/training dummy.
- Placeholder fighters: Silverwing, Caramello (Mahou guests). Stages: Training Grounds (training default), Avenue (versus default).

## Docs
- `docs/fighter_editing_guide.md`: hitboxes, frame data, air dash, damage, speed, cancels, inputs, adding moves.
- `docs/controls.md`, `docs/folder_structure.md`.

## Next / known gaps
- First C# build on 4.7 not yet verified by the user.
- Assist system (Climax-style), guard meter / guard crush, redo battle HUD at 1080p in Netsu style.
- Netsu roster design; replace Trista screenshot with original art before public release.
