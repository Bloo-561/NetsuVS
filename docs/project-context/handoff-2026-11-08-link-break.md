# Handoff Nov 8 2026 (updated Nov 9): Link Break (prototype, Cecilia + the 4 partners)

Replaces the Link Gauge and Link Chase (both backed up and removed). **C# changed: Build in Godot before testing.**
Not compiled or played: no C# compiler or GDScript parser was available, checked by hand only.
Online version now `netsu-vs-online-10`.

Backups: `_backup_stage_select/pre_link_break_nov08/` (Link Gauge / Link Chase versions), and
`_backup_stage_select/pre_link_triggers_nov08/` (the first Link Break design: "next D / S1 / S2 is the Break", D normals
as crest moves). Everything older is git HEAD ("Before Rework").

## Nov 9 changes (after the test video)
- **No tech till they land, fixed again.** On the video the dummy still recovered: the Break's 16-frame hitstop happens
  while the opponent is still on the floor, and that counted as "landed 4 frames", so the lock ended before they were
  ever thrown. Now the floor only counts **after they have been airborne** (`NoTechAirborne`), and frames where the
  opponent is in hitstop are skipped. `NoTechWait` is 90 frames (a grounded opponent who never leaves the floor).
  New rollback key 14 (`NoTechAirborne`).
- **Adin no longer floats.** The Link hit landed as an air counter, and the counter lift boosted it sky-high. All Link
  versions now set `NetsuCounterLiftPercent = 100`. Adin has his own version, **Wall Splat** (`VersionWallSplat`):
  hard push to the wall (-130000, 38000), gravity 200000, wall bounce time 120, **no floor bounce**, hitstun 40, so they
  hit the wall, slide down and must touch the ground. Eren / Harie keep the wall bounce.
- **Unbalance cut-in, second look** (frame-by-frame problems on the video and what replaced them):
  | Problem | Now |
  |---|---|
  | Full-screen white wash for several frames (looked like a glitch) | 0.06 s pop flash only, then rings |
  | Black brush streak behind the kanji read as a censor bar | thin tapered ink stroke |
  | Kanji shown twice (stamp + band) | one kanji: it slams on the opponent, then flies into the middle band |
  | Bands didn't reach the screen edges; HUD drew on top | full-width bands, cut-in added deferred so it draws over the HUD |
  | Text level while bands were tilted | all labels and the kanji follow the band angle (-6°) |
  | Dark middle band hid the black kanji | grey middle band (0.29, 0.30, 0.33) with blue edge lines |
  | Flat red bands | red gradient fill, white edge lines, speed lines in the middle band, bands sweep out over the last 0.13 s |
  Top band: the leader (partner card art / fighter S-Craft art) slides in from the left; bottom band: the fighter's EX
  art from the right. Middle: **LINK BREAK!** (Exo2 BoldItalic 100), leader name, "UNBALANCED · input".
- **Device bridge note:** `device_commit_files` caches by staged file path: give each commit a new staged filename
  (`_v2`, `_v3`) and check with `md5sum`, otherwise the old content is written again.

## The design (current, second pass)
1. **Each party member places one crest.**
   - **You:** a **D special** that hits (a special whose input uses D; Cecilia: **214D Thunder Pierce**, placeholder), or
     your **Air Throw** (now a hit-grab, below). The air throw places your crest but can **never** be a Break.
   - **Fighting partner** (Eren, Adin, Harie): its move hits (one crest per call). **Support** (Mary): by acting.
   - Crests stay until a Break uses them or the round ends.
2. **A partner hit while acting is OUT for the round.** The other partner fills its slot (it may place two crests).
   Both out: no Breaks this round.
3. **Three crests = LINK READY** (both partners' cooldowns refresh). **You pick the Link Break:**
   - **C+D**: your own Break. Cecilia: **Moonlit Stillness** (a short freeze, then a lightning slash-through that leaves
     them standing in a 60-frame stagger; she ends behind them, **hold back as it ends to land in front**).
   - **D+S1 / D+S2**: that partner leads (it comes at once, free; you do a quick 10-frame call pose). Eren / Harie:
     wall bounce; Adin: wall splat to the ground; all three: **no air tech until they land** (an extended combo). A
     Break always uses the partner's combo move when it has one (Adin: Shield Rush, never his counter). **Support
     (Mary): no startup**: the Unbalance and her buff (twice as long) happen the moment you press D+S; she still comes
     in and plays, but her own buff later does nothing. A free opponent is staggered 50 frames.
   - The Link moves only exist while Ready; otherwise the buttons do what they always do (C+D = C or D, D+S1 = D and a
     normal call). They cancel from any normal or special that hit or was blocked, **before the move's own cancels**.
   - On hit the opponent is **Unbalanced**: no Burst until the combo ends (`NetsuNoBurst`), and the fight stops for the
     Unbalance cut-in.
- **D normals (5D / 2D / j.D)** are plain normals now (placeholders); they will become Cecilia's own BlazBlue-style
  Drive normals (design pending).

## Unbalance cut-in
When a Break connects, `NetsuLink.Break` stops the fight for `BreakPauseFrames` (48) with `GameManager.NetsuStartPause`
(deterministic, rollback-safe) and `NetsuLink.Render` calls `MatchSetup.netsu_link_break(side, opponent chest, leader)`
once per Break. `game/ui/battle_hud/netsu_link_fx.gd` (added by netsu_hud.gd as "LinkBreakFx", deferred so it is above
the HUD) draws the look described in Nov 9 above. Kanji: `assets/ui/link/kanji_kuzushi.png` (崩, Noto Serif CJK Bold,
OFL). Knobs are exports at the top of the script (times, band angle / size / colours, dim 0.72).

## No tech till they land (partner wall Breaks)
When the leading partner's Link version is a wall type (Eren / Harie wall bounce, Adin wall splat),
`NetsuLink.NoTechTillGround` is set. While it's on, the opponent (`SakugaActor.NetsuLinkNoTech()`):
- can't run out of hitstun in the air (PreTick restarts it);
- never gets the forced air tech (`NetsuForcedAirTech`) and can't start a tech move (`StanceManager.CheckMoveConditions`);
- shows the purple juggle meter while airborne.
It ends when they've been **on the floor 4 frames in a row after having been airborne** (hitstop frames don't count),
leave hit reaction or are KO'd; or after `NoTechWait` (90) if they never leave the floor. Saved: NetsuLinkState keys 11-14.

## Training Menu: Unbalance (Link Break)
Gauges page, **"Unbalance (Link Break)": Normal / Always Ready** (`link_ready`; `NetsuTraining.LinkReady`). Always Ready
lights every crest a partner still in can give whenever no Break is running (`NetsuLink.TrainingFill`), for both sides.

## Universal hit-grab Air Throw
Every fighter's move named **"Air Throw"**: an air normal that hits can cancel into it (`StanceManager.NetsuAirThrowCancel`),
and it grabs an opponent in hitstun in the air (`SakugaActor.ThrowDamage`). A hit-grab can't be broken (`NetsuHitGrab`,
SakugaActorState key 72). Crest: `NetsuLink.OnAirThrow`. Landing / knockdown is still each fighter's throw data.

## Cecilia's moves (stance indices)
| # | Move | Input | State | Notes |
|---|---|---|---|---|
| 64 | 5D | D | 79 (Iaido) | placeholder normal |
| 65 | 2D | 2D | 68 (2C) | placeholder normal |
| 66 | j.D | j.D | 71 (j.5C) | placeholder normal (Thunder Strike states 132-134 stay in the data, unused) |
| 67 | 214D Thunder Pierce | 214D | 75 | D special: crest on hit |
| 68 | Link Break: Moonlit Stillness | C+D | 135 | SuperFlash 20 |
| 69 / 70 | Link Call S1 / S2 | D+S1 / D+S2 | 136 "Link Call" (10 frames) | the partner's Break |
Inputs: `_shared/sakuga/Inputs/72_Input_214D`, `73_Input_CD`, `74_Input_DS1`, `75_Input_DS2`. Moves `74`-`80_CEC_*.tres`.

## Adin
- His counter bash (`2_ADN_5S_hit`) can't be hit.
- Called while the opponent is in hitstun he does **Shield Rush** (assist move `Direction = 3`, state 7, own anim data,
  hit from frame 2); **as a Break he always does Shield Rush**. `assists.py` doesn't know this move: re-running it drops it.
- Break: Wall Splat (Nov 9 above) + no tech till they land.

## Mary (support Break)
`NetsuAssist.BreakCall`: a support applies the buff found in its move's state (`FindBuff`) at once, through `StartBuff`
→ `NetsuLink.OnPartnerActed` (Unbalance + doubled buff). `StartBuff` then ignores the buff her state gives later.

## Buttons (6): A B C D + S1 S2
| | Pad (Xbox) | Keyboard P1 | Keyboard P2 |
|---|---|---|---|
| A / B / C | X / Y / B | J / K / L | Num 4 / 5 / 6 |
| **D** (engine FACE_E) | **A** | **;** | **Num 3** |
| **S1** (FACE_D) | **LB** | I | Num 8 |
| **S2** (FACE_F) | **RB** | **O** | **Num 9** |
| AB / BC / ABC macros | LT / RT / none | U / P / [ | Num 7 / Num - / Num + |

## HUD
Two partner cards (S1 / S2, OUT when knocked out). Diamonds **YOU, S1, S2**. LINK READY pulses gold with
"C+D · D+S1 · D+S2". Popups: LINK READY, "S1 OUT".

## Files
| What | Where |
|---|---|
| Rules, crests, Ready, triggers, Link versions, side choice, pause, no-tech, training fill, HUD push | `engine/sakuga/Components/NetsuLink.cs` |
| Rollback | `NetsuLinkState.cs` (keys 0-14), `NetsuAssistState.cs` keys 18-21, `SakugaActorState.cs` key 72 |
| Partners | `NetsuAssist.cs` |
| Link moves / cancels / air throw cancel / no tech | `StanceManager.cs` |
| Hooks | `SakugaActor.cs`, `SakugaParameters.cs`, `NetsuAssistBuffAction.cs`, `GameManager.cs` |
| Training option | `NetsuTraining.cs`, `netsu_training_menu.gd`, `game_settings.gd` |
| Unbalance cut-in | `netsu_link_fx.gd`, `kanji_kuzushi.png`, `match_setup.gd`, `netsu_hud.gd` (deferred add) |
| UI | `controls.gd`, `options_menu.gd`, `character_select.gd`, `match_setup.gd`, `netsu_hud.gd`, command list |

## Test plan (Training, Cecilia)
1. Build. Cecilia → partner 1 Mary → partner 2 Adin (then Eren).
2. Training Menu → Gauges → Unbalance: Always Ready. Dummy: air recovery ON.
3. 5B > C+D: pop, 崩 slams on the dummy and flies into the band, bands over the HUD, slash-through stagger.
4. 5B > 5C > D+(Adin): Shield Rush → hard to the wall → slides down, no floor bounce, **no tech until it's on the floor**,
   no sky-high float. Follow up off the wall.
5. Eren: wall bounce, same no-tech. Mary: cut-in and aura at once.
6. Back to Normal: build Ready by playing (214D, call both).

## Knobs / known gaps
- `NetsuLink.BreakPauseFrames` (48) and `total_time` in netsu_link_fx.gd (0.8 s) should match.
- Face framing in the bands: ART table in netsu_link_fx.gd.
- Wall arcs: `NetsuLink.Variant` (`VersionWallBounce`, `VersionWallSplat`).
- No-tech lasts the whole juggle until they land: if loops appear, limit it.
- No damage-scaling reset on Break; hit-grab air throws have no soft knockdown yet.
- Placeholders: 5D / 2D / j.D, 214D. Not done: Doris, Rumi, CPU Breaks, online second picks, other fighters' D moves.
