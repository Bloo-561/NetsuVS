# Handoff Nov 4 2026 (afternoon): the six picked items

TamaDeez picked six items from the playtest list: Mary's notes, Noah's 22, CPU Burst + tech, ground tech, the lobby,
DPs + wake-up. **C# changed: Build in Godot before testing.** There's no C# compiler here, so every edited .cs file was
checked with a real C# parser (tree-sitter-c-sharp, 0 errors) and every new member reference was checked against its
declaration by hand, but it hasn't been compiled or played. If the build reports an error, it's from this batch.

Backups of every file touched (same folders as the project): `_backup_stage_select/pre_six_nov04/` (38 game files +
3 docs). The lobby has its own backup (see 5).

## 1. Mary's notes (6S Fermata Note)
- **Faster:** the notes chase at up to 5.4 m/s (was 2.4) and steer harder (aim over 6 frames, was 20), and they go off
  within 0.25 m of the opponent (was 0.11 m, so they slowed down to a crawl at the end). From 3 m: about 32 frames to
  reach them (was about 95). `actors/assists/mary/States/1_MRYN_Float.tres` (chase_a, trigger s2).
- **They go away when the character gets hit:** every note still out vanishes the moment Mary's partner (your fighter)
  is in a hit reaction, grabbed or K.O.'d, whether Mary is still on screen or has left; also when Mary herself is hit
  out of her move. Blocking doesn't remove them. `NetsuAssist.Tick` → `ObjectPool.NetsuClearSpawns`;
  `SakugaActor.NetsuAssistStruck` (BaseDamage / HitTrade). Only Mary has assist projectiles today, so it's a general
  rule: any future assist projectile (Adin's shuriken idea) behaves the same.
- Description on the select screen updated (`data/assist_list.tres`).

## 2. Noah's 22 (Event Horizon) holes
- Every black hole Noah has out (near, far, or one sucking after a snap) **bursts at once** when Noah is hit, blocks an
  attack (blockstun), or is thrown. The burst is the hole's normal pop (no hitbox), and the HoleTimer (variable 4) is
  cleared when the last waiting hole goes, so his next 22 makes a new hole instead of a snap with nothing to snap.
- Engine: `FighterState.NetsuPopWhenOwnerStruck` + `NetsuPopState` (hole states 1 / 2 → 5, 3 / 4 → 6),
  `ObjectPool.NetsuPopOnOwnerStruck`, called from `SakugaActor.PreTick` (works during hitstop). Pop states 5 / 6 got the
  owner-variable reset (`NetsuOwnerVariableAction`, the same one the hit-confirm pop uses). Command list text updated.

## 3. CPU: hold-to-tech and Burst (`AIBrain`)
- **Techs:** each time it's knocked into the air, and each time it lands lying after a soft knockdown, it rolls its
  TechingRate (Beginner 0 … Pro 8 in 10). On a yes it holds A (forward / back / neither) so it techs on the first
  frame allowed, exactly like a player holding a button. Sometimes it waits a little before a ground tech. The old
  "recovery press" actions are gone, and whatever plan it was running when hit is dropped (its presses could tech by
  accident or come out on recovery).
- **Burst:** once per combo it rolls Beginner 0, Easy 1, Medium 3, Hard 5, Very Hard 7, Pro 8 in 10; on a yes it
  Bursts when the combo reaches 99 / 8 / 6 / 5 / 4 / 4 hits (+0-2 random; 3 hits at low health), if the gauge is full
  and the combo allows Burst (A+C, a fresh press every other frame until it comes out). Not in Training: the Auto Burst
  setting decides there. Tables: `NetsuBurstRate`, `NetsuBurstHits`, `NetsuBurstHitsLow`.
- `NetsuHitPlan` (every frame) / `NetsuHitInput` (first thing in `UpdateCommand`).

## 4. Ground tech (BlazBlue style)
- **Rule:** lying after a **soft** knockdown (anything but `HARD_KNOCKDOWN`), from **20 ticks after the first ground
  impact** until the usual get-up (tick 50), A / B / C held or pressed gets up at once:
  - forward held = **roll forward** (`Recovery_Ground_Forward`, 20 frames, ~1 m),
  - back held = **roll back** (`Recovery_Ground_Back`),
  - no direction (or up / down) = **tech in place** (`Recovery_OTG`, 20 frames).
  All three are invincible on the ground, flash white like air techs, and keep the throw protection a normal get-up has.
  Holding a button from the air techs on the first allowed tick. Not pressing anything = the full knockdown as before
  (impact 28 + lying 22 + get-up 22 = 72). Hard knockdowns, a super / hold keeping them down, hitstop and K.O. can't.
- **What it means for combos:** OTG follow-ups are only guaranteed in the first 20 ticks after a soft knockdown (or on
  someone who doesn't tech). Hard knockdowns keep the old full OTG window and 72-tick knockdown, so they are now the OTG
  / okizeme tools. Tune the 20 on the GameManager node of `scenes/battle/battle.tscn`: `NetsuGroundTechFromFrames`.
- **Animations:** tech in place used a hop pose that rose into the air (and wasn't invincible up there); it now stays on
  the floor and uses each fighter's get-up frames (crouch_2 → crouch_1). The rolls use the existing recovery animations,
  which borrow air-dash / jump poses (Flan's ball roll and Leticia's flip read best): there are no roll sprites yet.
- **Not copied from BlazBlue (say if wanted):** BBCF's rolls aren't invincible all the way and it has a "quick tech"
  (stands up faster, no invincibility). Ours are fully invincible, three options.
- Code: `SakugaActor.NetsuGroundTechOpen / NetsuGroundTechNow / NetsuInGroundTech`, `StanceManager.NetsuGroundTech /
  NetsuGroundTechMove` (the move found by its state's name, like air techs), the early return in `CheckMoves`.
- **Training:** the Wake-up setting works again: Stay Down, Tech in Place (was "Quick Rise"), Roll Forward, Roll Back,
  Random. Docs: `claude/training.md`.

## 5. Lobby overhaul
Files: `scenes/online/online_lobby.gd` (rewritten), `game/autoloads/online_room.gd`, `game/autoloads/controls.gd`
(key names for the legend), `game/autoloads/game_settings.gd` (`online.spectate` default, so Spectate only is
remembered). Backup: `_backup_stage_select/pre_lobby_nov04/`. Online version bumped to `netsu-vs-online-4`
(`NetsuOnline.ProtocolVersion`), so older builds are told they're a different version; room protocol 3.
- **Keyboard code bug:** the game puts K, L, Backspace, Numpad 5 / 6 on `ui_cancel`, and since Godot 4.4 a LineEdit stops
  editing on `ui_cancel` before it handles Backspace. Backspace (or K / L in backup codes) ended editing; Numpad 5 / 6
  left the join page. The lobby's boxes now read keys themselves.
- **Join page:** five digit boxes; type (numpad too), or Up / Down + Left / Right (pad, WASD, arrows); A / Enter joins,
  B / Esc back, Ctrl+V pastes, Tab / S opens a box for a backup code or address.
- **Pass** (U / Numpad 7 / RB): while picking or next in line, swap with the next player waiting (they get a fresh 60 s
  clock, the other picker keeps their pick). Nobody waiting = nothing (greyed out, the INFORMATION bar says why). The
  king passing ends the streak.
- **Spectate only** (online menu row, or S in the room when not picking) replaces sit-out: never queued until turned
  off, can join a lobby just to watch, remembered between sessions.
- **Look:** first built like P4AU's PLAYER MATCH, then (TamaDeez: "keep the theming of the game") redrawn with the
  Netsu UI kit like the original lobby and main menu: menu_bg, "ONLINE" header, room bar (room name + code), a 1P / 2P
  panel (blue left, crimson right, VS, picks and the clock), a PLAYERS panel on the right (place, avatar, name, status:
  PICKING / READY / NOW PLAYING / NEXT UP / WAITING / SPECTATING, wins, ping; your row lit), a MESSAGES panel (room log),
  the kit footer with real key prompts. The P4-style version is in `_backup_stage_select/pre_lobby_nov04/p4_style/`.
- **SETUP quick menu (later Nov 4, TamaDeez: "easier to switch things... so you can't mess something up"):** the room view
  no longer changes picks with directions / S. A opens SETUP (over the dimmed room): Fighter, Colour, Assist (anyone,
  any time: your saved setup, used when your turn comes), Stage and Music (host only; read-only for the others), and
  Ready during your pick phase. Up / Down row, Left / Right change, A keeps the changes, B closes without them; while it's
  open no room key works. Room keys now: A setup, C watch, S spectate, AB pass, Start invite, B not ready / leave
  (C = stage is gone). Music is a room setting: Auto (player 1's theme), Random (rolled once by the host per match) or a
  song; `MatchSetup.start_online_room` reads `p.music`. Room protocol 4 (`setup` message, also inside `hi`). The room
  bar shows your setup; the VS panel shows stage and music. Backup: `_backup_stage_select/pre_lobby_setup_nov04/`.
  Not checked: Japanese song titles in the lobby font; the setup isn't saved across restarts.
- Changed: Esc in the room starts "leave" for everyone (Start still opens the invite screen for the host).
- Tested in a GDScript harness with stand-ins for networking (117 checks): not yet over a real connection, on Godot 4.7,
  with real controllers or the Windows clipboard. Backup codes still need a keyboard.

## 6. DPs unsafe on block + easier wake-up DP
- **Blocked B and EX DPs land with 30 frames of recovery** (Cecilia Teleport Slash B / EX: 10 → 30; Flan Rising Star B /
  Spiral Star: 16 → 30; Leticia Rising Comet B / Comet Burst: 14 → 30). The landing pose is held; she can't block or act.
  Only when one of the move's hits was blocked; on hit or whiff nothing changes; A versions unchanged.
  These DPs were already committed until landing, so the only punish window was their 10-16 frame landing after a long
  fall: now walking under the landing spot and punishing is easy.
  Engine: `MoveSettings.NetsuBlockedRecovery` (the extra frames, on the B / EX moves), `FighterState.NetsuBlockedRecoveryHere`
  (the shared landing states `CEC_DP2_Land`, `80_FLN_DPLAND`, `98_LET_DPLAND`), `SakugaActor.NetsuBlockedExtra` (set in
  `BlockHit`, cleared on a new move or a hit; rollback key 68), `StateManager.NetsuDuration` (used by `StateEnded` and
  `StateEndedCondition`). Noah has no DP (his reversals are EX moves with their own recovery), so nothing changed for him.
- **Wake-up reversals are easier:** an attack / special / super input in the **last 8 frames of getting up** (or of a
  ground tech) is buffered and comes out on the first free frame (`StanceManager.NetsuWakeBuffer`,
  `NetsuWakeBufferFrames`). Before, CheckMoves ignored everything until the get-up was over, so a DP had to be input on
  the exact frame.
- The frame data sheets still show the old landing numbers (they're computed from the animation, not from this rule).

## How to test (Training)
1. Mary 6S near the dummy, get hit while the notes fly (dummy on CPU or Playback): they vanish. Notes reach the dummy fast.
2. Noah 22A / 22B, then block or get hit: the holes burst; 22 again makes a new hole.
3. Dummy = CPU Hard / Pro: juggle it, it techs out of air combos (Pro ~8/10 times), techs on the ground after soft
   knockdowns, and Bursts out of longer combos in Versus (not in Training).
4. Recovery → Wake-up: Roll Forward / Back / Tech in Place after a sweep: it gets up at tick 20 instead of 72. Try an
   OTG follow-up after 20 ticks: it should whiff on a teching dummy. A hard-knockdown move: it stays down.
5. Block Cecilia / Flan / Leticia 623B and 623C (Recording on the dummy): walk under the landing and punish.
6. Wake-up DP: input 623 + A a few frames before the get-up ends: it comes out on the first free frame.
