# Netsu VS — Core game systems (v2, Oct 19 2026 evening; assists Oct 24; online, presentation, movement Oct 24 night; throws, input leniency, sounds, CPU Oct 24 late; EX / super pause, crouch exit, group lobbies Oct 25; blockstun, sky supers, stalls, loading emblem, frame data sheets Oct 25 evening; UNI2 damage scaling, BBCF Burst gain, UNI2 Attacklevel Oct 27)

Status: **built** in engine code and data (Cecilia, Flan, Leticia, Noah). The C# changes need a **Build** in Godot before testing. Numbers are first-pass, meant to be tuned in play.

## The team's list (v2)
- **Offense:** Overdrive (offensive burst), EX moves (2 bars), Supers / S-Crafts (3 bars).
- **Defense:** Burst (defensive burst), Pushblock (1 bar).
- **Meter:** 6 bars, carries over between rounds, focus on meter gain.
- **Assists (Oct 24):** Mary, Adin, Eren, Harie on S / 6 + S (below; full doc `claude/assists.md`).

Removed in v2: Brave Cancel (the roman-cancel move), Breakthrough (guard cancel) and the automatic low-health Overdrive.

## The two gauges
| Gauge | Max | Fills from | Spent on |
| --- | --- | --- | --- |
| **Craft Gauge** (meter) | 4 bars (8000, 2000 per bar; 6 bars before Oct 27 night) | BBCF Heat Gain: damage you deal / take, blocking (see Meter gain) | EX Crafts 2 bars, S-Crafts 3 bars, Assist Cancel 1 bar (2 before Oct 26), Pushblock 1 bar (9C 1 bar) |
| **Burst gauge** (engine "Will") | 6000 | starts every match full; BBCF style since Oct 27: 6 / 9 / 12 per frame by health, + on every hit taken (see "Damage scaling... Oct 27") | Burst **or** Overdrive (each needs it full) |

Both gauges carry over between rounds. An Overdrive still running ends when the round ends. (The assist gauge is a third, separate one: see Assists.)

## Burst (defensive) — A+C
Uses the full Burst gauge. **Only while being hit** (hitstun, launched, knocked down); knocks the opponent away. Can't be used while Overdrive runs.
**Oct 26 late:** the same A+C press anywhere else (neutral, blocking, or cancelling one of your own moves that hit or
was blocked) is **Overdrive** instead; A+B+C still works for Overdrive too. Engine: `StanceManager.NetsuIsBurst /
NetsuIsOverdrive / NetsuBurstOrOverdriveState / NetsuAllowedStateType / NetsuInputDone / NetsuOverdriveCancel`.
(Before this, Burst also worked in neutral and is checked before Overdrive, so A+B+C came out as a Burst.)

## Overdrive (offensive) — A+B+C
- Needs a full Burst gauge. Usable in neutral, and as a cancel from normals on hit/block (where Brave Cancel used to be). Short activation pose with a super flash.
- While it runs: **deal 120% damage** and **gain 130% Craft Gauge** (since Oct 24 this includes the fighter's projectiles and assist hits).
- The Burst gauge drains while it runs; Overdrive ends when it is empty, and you then have no Burst until it refills.
  (Oct 26 evening: it lasts 4 s at full health up to 10 s near zero health, BlazBlue Central Fiction style; opponents it
  hits can't Burst until that combo ends; activation pauses the fight for a win pose.)
- HUD: "OVERDRIVE" pulses under the health bar and the BURST bar flashes orange while it drains.
- Engine: `SakugaParameters.StartOverdrive / InOverdrive / OverdriveDamage`, drain in `WillGauge.Tick`. Running = the Burst gauge's state is `WillState.LOCKED` (saved for rollback). The move is recognised by its name "Overdrive" (`StanceManager.ExecuteMove`). Move file: `Moves/50_<TAG>_ExcelCancel.tres` (kept its file name), state `86_<TAG>_XCancelState` (no longer resets damage scaling).

## Pushblock — A+B while blocking, 1 bar
Built from the old Breakthrough move (`Moves/<TAG>_Breakthrough.tres`, kept its file name): no damage, no meter, pushes the attacker far away (150000 knockback) with only 8 frames of hitstun, so neither side can follow up. Startup is still invincible; remove that if it feels too strong.

## Counter hits (Oct 20)
Hitting a move during its startup or active frames (counter) or its recovery (punish counter) now adds **12 frames of hitstun** on top of the move's own, for every fighter. Before this, counter hits only showed the notification. Lets slow moves combo only on counter hit (Cecilia's 214B: 22-frame startup vs max 21 hitstun from her normals). Engine: `SakugaActor.NetsuCounterHitstun` (12) set on the target before `HitDamage`, added to `finalHitstun`. Backup `_backup_stage_select/pre_counterhit/`. **Needs a Build.**

Counter MOVES (a COUNTER box, e.g. Cecilia's Counter · Thunderclap, Adin's 5S): since Oct 24 the counter is settled before any other hit in that frame, and the countered attack can't hit anyone else for the rest of that move (`PhysicsWorld.HitQueries`). A move that follows a counter must reset its hits on its first active frame (`ResetHitAction`), because the attacker counts as already hit; Cecilia's S1 and Leticia's S2 follow-ups got that fix the same day.

## EX Crafts and S-Crafts
EX Crafts cost **2 bars** (4000), S-Crafts **3 bars** (6000), for every fighter (Cecilia's prototype kit, Oct 24: EX 236C / 214C / 623C, supers 236236 / 214214; the prototype's own 3-bar gauge charges 1 and 2). The CPU's S-Craft check is 6000.

**The flash (Oct 24).** When an EX move or a super starts, its flash freezes the opponent (the move's `SuperFlash` frames, 15 for EX, 20 for supers) and the fight shows the spending: the stage goes dark for the freeze (then fades), the frozen opponent and its assist/projectiles turn darker, and a burst of light (spinning rays, a glow in the player's colour, a ring opening out) goes off at her chest. Files: `game/ui/battle_hud/netsu_super_flash.gd` (dark stage + burst; added by `netsu_hud.gd`; sizes, colours and darkness are exports), engine `SakugaActor.NetsuSuperFlashLook` (tints, worked out from `SuperFlashing` every frame, nothing saved) → `MatchSetup.netsu_super_flash`. The fighter shaders multiply the sprite's modulate now (`sprite_color_swap`, `sprite_hue_shift`, `color_palette`) so the alt colours darken too.

**EX / S-Craft presentation (Oct 24 night, after Under Night In-Birth and Melty Blood).** Every fighter has a colour for
it: `FighterProfile.NetsuAuraColor` (Cecilia crimson, Flan gold, Leticia cyan, Noah violet; transparent = the side's blue / red).
- **EX Craft:** a slanted band opens across her side of the screen, **behind the fighters**, with a big close-up of her
  (`actors/<fighter>/Artwork/CutIn_EX.png`), speed lines and a white flash as it opens, "EX CRAFT" + the move's name; a
  line of light shoots through her, sparks drift off her and the **EX sound** plays (`assets/audio/sfx/netsu_ex_flash.wav`).
- **S-Craft:** the stage turns to dark **smoke in her colour** (`assets/shaders/netsu_super_backdrop.gdshader`), a huge
  picture of her (`CutIn_Super.png`) sweeps in behind the fighters, the **S-Craft sound** plays
  (`netsu_super_flash.wav`) and the name comes up big. The smoke stays until she is out of the super.
- **Aura:** a glowing outline around the fighter in her colour, during an EX flash and for a whole super
  (`AnimationViewer.SetAura`: eight flat-colour copies of her sprite behind her, `assets/shaders/netsu_aura.gdshader`).
- Files: `game/ui/battle_hud/netsu_cut_in.gd` (band, close-up, smoke, big picture, names, sounds; it puts its two
  picture layers under the fighters' layer; face positions per fighter in its `ART` table), `netsu_super_flash.gd`
  (streak + sparks), engine `SakugaActor.NetsuSuperFlashLook` (aura, and `MatchSetup.netsu_super_hold` while a super
  runs), `StanceManager` records each flash's cost (`SakugaActor.NetsuFlashCost`). Sounds are synthesized:
  `tools/fx/make_cutin_sfx.py`. All presentation: nothing in the match state depends on it.
- **Counter supers** (Cecilia's Sakura Morning Moon) show nothing while she waits: the move has `NetsuFlashOnHit`, and
  the flash, cut-in and aura start from the counter state (`NetsuSuperFlashAction` in its OnEnterEvents).

**The pause (Oct 25).** An EX move or a super now **stops the whole fight** for a moment as it starts, so everyone sees
it happen and who did it: nothing moves, the clock stops, the camera **zooms in on her** (a little toward her side of the
screen), the stage goes darker than for the flash and the opponent (and its assist, projectiles) turn dark; then the
camera eases back out and the flash, cut-in and freeze carry on as before. EX: 30 frames (half a second), super: 60
(a second, since Oct 25 evening: a super's start lands harder). A move can set its own length
(`MoveSettings.NetsuPauseFrames`) and play one of its states while the fight is held (`MoveSettings.NetsuPauseState`:
only the picture moves): Flan's Big Bang Crash holds 90 frames while she twirls, charging the punch.
- Engine: `GameManager.NetsuPause` (frames left), `NetsuPauseSide`, `NetsuPauseTotal`, saved with the match
  (`GameManagerState` keys 6-8: rollback-safe, sync test clean). `GameManager.GameLoop` only counts frames while it
  runs. Started by `StanceManager` when a move costing 2+ bars starts (`NetsuStartPause(side, cost)`; a counter super
  starts it from its counter state, like its flash). Lengths: `NetsuPauseExFrames` / `NetsuPauseSuperFrames`
  (exports on the GameManager node in `scenes/battle/battle.tscn`).
- Look (Oct 25 evening, after Under Night In-Birth): the camera moves in a little about the fighter who did it — she
  stays where she is on the screen and everything grows around her, the opponent still in view — then eases back.
  `FighterCamera` exports on the Camera3D node: `NetsuZoomFactor` 1.18 (EX), `NetsuZoomFactorSuper` 1.3,
  `NetsuZoomHeight` (the point that stays put, about her waist), `NetsuZoomIn` / `NetsuZoomOut`. Also
  `netsu_super_flash.gd` (`pause_ex_dim` / `pause_super_dim` / `pause_out`), `SakugaActor.NetsuPauseTint` (the
  opponent while paused). Presentation reads `GameManager.NetsuPauseInfo()`.
- No stall the first time (Oct 25 evening): the cut-in pictures and flash sounds load with the fight
  (`MatchSetup.match_paths`), and the smoke shader, the flash's additive material and the big name sizes are drawn
  once, invisibly, on the fight's first black frames (`netsu_cut_in.gd` `_warm`, `netsu_super_flash.gd`).

**Supers that use the whole stage (Oct 25 evening).** Flan's Big Bang Crash carries her opponent high into the sky,
Leticia's Crimson Waltz circles hers on the hoverboard. Pieces anyone can reuse in a state's events:
- `NetsuHoldOpponentAction`: holds the opponent (only while they're in a hit reaction) at a point seen from this
  fighter (Offset.X along her facing, Y above her feet; her speed this frame counted in), or lifts them in place
  (`LiftRate` per mille of the way to Offset.Y each frame). Their own speed is cleared. Walls and floor respected.
- `NetsuSkyRiseAction`: a climb (Velocity once, Gravity each frame) scaled down on stages whose camera can't go as high
  (`StageElement.NetsuCameraTop`, metres, in `data/stage_list.tres`: Thors Hall 8, outdoors up to 20), so it takes as
  long everywhere but tops out where the camera still shows it.
- `NetsuOrbitAction`: puts her on the next point of a path around the opponent and turns her to face them; the side
  she started on is saved with the match (`SakugaActor.NetsuOrbitSide`).
- `FighterState.NetsuShowStage`: the super's dark smoke backdrop clears while she's in that state, so the stage shows.
- `FighterCamera` sky settings: when both fighters are high it pulls back and frames them both (`NetsuSkyFrom`,
  `NetsuSkyFull`, `NetsuSkyPullback`, `NetsuSkyAim`, `NetsuSkyFollow`, `NetsuSkyHead` / `NetsuSkyFeet` keep both in
  view; in a NetsuShowStage state it widens to fit both: `NetsuCineOut` / `NetsuCineIn`), never above the stage's
  `NetsuCameraTop`.

**Supers stop momentum (Oct 24).** A super (3 bars) cancels the fighter's velocity and knockback as it starts (`StanceManager.ExecuteMove`): a dash, a jump arc or a push doesn't carry into it; the super's own states move her from there.

**Super cinematics only on a real hit (Oct 24).** Flan's Radiant Breaker and Big Bang Crash and Leticia's Crimson Waltz went into their cinematic follow-up when blocked too (the engine runs hit-confirm events on block). Their follow-ups now check for a hit (`CheckHitCondition` HIT); Cecilia's EX Dash Slash rush is built the same way.

**Wall bounce (Oct 24).** A hit with `BounceTime` and `BounceXIntensity` (Cecilia's 236B) bounces the opponent off a wall. The stage walls are 24 m apart, so mid-screen the bounce happens at the edge of the screen: once they are 8.8 m from the attacker and still flying away (`OnWallsCondition.NetsuScreenWallDistance` = 88000; the fighters can't get more than 10 m apart). Measured from the opposing fighter, so it's meant for a fighter's own hits.
Since Oct 24 night the bounce **pops them up** off the wall (every fighter's `34_<TAG>_Hit_Bounce_Wall` state:
`NetsuWallPopAction`, at least 9 m/s up, at most 0.8 m/s back out, so they fall by the wall instead of floating back over her),
so a wall bounce can be followed with 5B into an air combo (tested: 236B in the corner → 5B → jump → j.B → j.C; the 5B
window is about 12 frames after 236B recovers). Numbers: `WALL_POP` / `WALL_BACK` in `tools/sprite_port/tune_movement.py`.

## Blockstun (Oct 25 evening)
A blocked attack now holds the defender for its full blockstun (`GroundBlockstun` / `AirBlockstun`). Before, the stun
timer was stopped every frame in the blocking states, so blocking only lasted the hitstop and every move was about -10
to -15 on block whatever its numbers said (`SakugaActor`, "Netsu (Oct 25)"). On block = blockstun - the frames left in
the move when it hits, as Training shows it (the frame data sheets' On block column).

## Freeze lock, pushback, Special > EX, OTG (Oct 26 afternoon, TamaDeez branch)
Full notes: `docs/handoff_2026-10-26_tama.md`. **Needs a Build.**
- **No inputs during an EX / super flash freeze** (both players; pause still works): each side's last input is held,
  nothing new is pressed (`GameManager.GameLoop`). No kara (B+C replacing a move) out of an EX or super.
- **Normals push back less:** 60% of their hitboxes' pushback on hit and block (`GameManager.NetsuNormalPushbackPercent`,
  Inspector on the GameManager node of `scenes/battle/battle.tscn`).
- **Special > EX cancel** on hit or block, every fighter (`StanceManager.NetsuSpecialToEx`).
- **Assist Cancel: 1 bar** (was 2).
- **OTG:** a lying opponent can be hit for `NetsuOtgWindowFrames` (40) after landing, shorter the more the combo is
  scaled; they stay down (no pick-up, no new hit reaction). After that, and while getting up or tech-rolling on the
  ground, they can't be hit or thrown (supers still connect on a lying opponent). `SakugaActor.NetsuOtgHit` /
  `NetsuWakeInvincible`, `NetsuDownFrames` saved for rollback.

## OTG, knockdowns, techs, Overdrive, throws, assists (Oct 26 evening, TamaDeez branch)
Full notes: `docs/handoff_2026-10-26_systems.md`. **Needs a Build.**
- **OTG** window 45 frames, full down to 50% damage scaling, then shorter (none at 15%). **Supers can't OTG** (they
  never hit a lying fighter). **Knockdowns** keep them down at most `NetsuDownTotalFrames` (50; was 76), then they get
  up (invincible). Both on the GameManager node of `scenes/battle/battle.tscn`.
- **Techs flash white** (any `Recovery_` state, first 10 frames: `SakugaActor.NetsuTechFlash`).
- **Assist Cancel only after a real hit** (the attack has done damage; not on whiff or block).
- **Throws cancel** into EX moves, supers and Overdrive once the throw has hit (`StanceManager.NetsuThrowCancel`).
- **Overdrive (BlazBlue Central Fiction style)**: still the same gauge as Burst (use one or the other). Lasts 4 s at
  full health up to 10 s near zero (`SakugaParameters.StartOverdrive`). Anyone hit by a fighter in Overdrive can't
  Burst until that combo ends (`SakugaActor.NetsuNoBurst`). Activation: the fight stops 45 frames
  (`NetsuOverdrivePauseFrames`) while she strikes her win pose and glows; nobody can input. While it runs: a timer next
  to her Burst gauge and the stage a little darker (`overdrive_dim` in `netsu_super_flash.gd`).
- **Mary's 6S** faces the way her caller faces (`NetsuAssistMove.NetsuFaceCaller`).
- (later that evening) **Overdrive works in neutral** too (A+B+C with a full Burst gauge; its Move files had
  `SkipCheck` on, so it only came out as a cancel). **Assists can be called from blockstun** (1 bar, no pose).

## Damage scaling, minimum damage, Burst gain, Attacklevel (Oct 27 2026, TamaDeez)
**C# changed: Build.** Backup of every touched file: `_backup_stage_select/pre_uni_scaling/`.

**Combo damage — Under Night In-Birth II** (mizuumi.wiki, UNI2 Damage and Combo System). Replaces the old flat
"take X off a running percentage, floor 15%" and the 120% corner bonus.
- Damage = base × (72% Combo Rate × Distance Penalty) × (proration of every earlier hit) × Same Move Proration.
- First hit: 100%. **Combo Rate 72%** from the 2nd hit on (flat). A multi-hit move that **starts** a combo counts as one hit:
  none of its hits get the 72%.
- **Proration** stacks multiplicatively, hit by hit: each hit multiplies it by `100 - Scaling` (the hitbox's
  `DamageScalingSubtract`, the sheets' "Scaling" column: 10 → ×90%). `HitboxElement.NetsuStarterProration` gives a
  different value when the hit starts the combo (UNI's X(P1)/Y(P2)); -1 = same.
- **Distance Penalty**: 2nd hit on, past `GameManager.NetsuDistancePenaltyStart` (27300 units ≈ UNI's 350 of 1280 px),
  −8% per `NetsuDistancePenaltyStep` (19500), never below 92%.
- **Same Move Proration**: 5A > 5A ×98%, 2A > 2A ×97%, stacking for each repeat.
- Every step truncates; at least 1 damage. Example (Cecilia 5A 5B 5C 2C 236B, EX, 6-hit super): 3240 → 2879.
- Training's "Scaling" readout = what the next move would be scaled by. The OTG window reads the same number.

**Minimum damage — UNI2**, for EX moves (2 bars) and supers (3 bars). A hit never does less than
`raw × min% × penalty`: min% = `GameManager.NetsuExMinDamagePercent` (30) / `NetsuSuperMinDamagePercent` (50), or a
hitbox's `NetsuMinDamagePercent` (-1 = default, 0 = none; defaults 90 / 45 since the retune below). Penalty (lowest wins, all ×80%): default 100%;
2+ EX moves in the combo 50% (60% at ≤30% health); 2nd super 30% (40%); throw starter 80%; invincible starter 60%;
Overdrive started mid-combo (UNI's Veil-Off) 80%. A super after 2 EX moves ×1.2. Worked out after scaling, before bonus
damage (Overdrive 120%, Mary's Encore). The 3-bar super 150% counts as base damage.

**Burst gauge — BlazBlue Central Fiction** (dustloop BBCF Frame Data, "Burst Gauge"), scaled from BB's 10,000 to our 6000:
- Passive: 6 / 9 / 12 points a frame at health ≥55% / 41–54% / ≤40% (167 / 111 / 83 s from empty). Was 1 a frame.
- Getting hit: `(1 − current proration) × damage × 10 + 100` per hit. Taken literally that refilled ~160% of the gauge
  in one long combo, so `GameManager.NetsuBurstHitPercent` = 30 (≈ the old "damage taken" rate). Chip no longer fills it.

**Attacklevel — UNI2** (`NetsuAttackLevel` on each hitbox). Blockstun, ground and air: Light 11, Medium 14, High Medium 15,
Heavy 16. AUTO (default): normals A light / B medium / C heavy; specials A medium / B high medium / C heavy; EX, supers
and Overdrive heavy; assists and unknown high medium. CUSTOM keeps the box's own numbers (typing a Blockstun in the sheet
sets it). **Replaces** the Oct 26 fixed block advantage (A −4 / B −5 / C −8, specials −4 / −6): block advantage now
comes from each move's recovery, so re-check it in Training. The sheets' Blockstun column shows the old numbers until
they are remade (`tools/frame_data/make_sheets.py`).

Rollback: new saved values in `ProrationsState` (keys 10–17) and `StanceManagerState` key 6 (`NetsuMoveSerial`); the
StanceManager formatter now also writes keys 4–5 (`NetsuHeldSpecial`), which it was missing.

### Retune (Oct 27 night, TamaDeez)
- **Harsher scaling:** every hit also takes `GameManager.NetsuScalingExtraPerHit` (4) off the hits after it, on top of its
  Scaling (10 works as 14). **Min damage** defaults: EX 90 (×80% = 72% of its damage), supers 45 (36%). Target, checked
  with `tools/frame_data/combo_sim.py` on real routes: no meter ~1.7–2K, 1 bar ~2K, 2 bars ~2.4–3.6K, 3 bars ~3.2–4.2K,
  4 bars ~3.3–4.4K; long combos level off. Leticia's and Noah's EX moves come out lower (less damage on the moves).
- **Burst refill fixed:** BBCF's gauge is 100,000 points inside (the fill times prove it); the first version used 10,000,
  so Burst came back ~10× too fast (about 17 s). Now: ~167 s from empty at high health (83 s at ≤40%) plus ~10–15% of
  the gauge per combo taken: roughly one Burst a round, a second if the first was used early. `NetsuBurstHitPercent` 100.
- **Craft Gauge 400% max** (4 bars) and the BBCF Heat Gain table (see Meter gain).
- Backup: `_backup_stage_select/pre_scaling_tune/`.

## Frame data spreadsheets (Oct 25 evening)
`data/frame_data/<Fighter>.xlsx` and `Assists.xlsx`: every move's frames, damage, stun, guard, knockdown, pushback,
launch, meter, cost and pause, editable; the game applies the changed cells at the start of every match (Training: the
moment the file is saved). Full doc: `docs/frame_data.md`.

## Movement and momentum (Oct 24 night)
- **Specials don't carry momentum.** A dash into a special used to slide the special along (Cecilia's "random
  momentum"), and DPs / supers had no invincibility, assists didn't dash: the kit wrote bare actions into the states'
  event lists, which the engine expects as `FrameDataEvent`s; Godot dropped the whole list when loading the state (an
  InvalidCastException in the output). `tools/sprite_port/fix_event_lists.py` wrapped them (every fighter and assist,
  ~120 files); `fdk.py` writes them right now. A special now stops where it starts, like the dash would have stopped.
- **Less flying:** the dash jump goes 4.8 m/s instead of 7.4 (1.5× a jump), the air dash 6.4 (up / down 5.6), and after
  an air dash she falls on at about jump speed instead of keeping the dash speed (`tools/sprite_port/tune_movement.py`,
  numbers at its top, run again after changing them).

**Standing up from a crouch (Oct 25).** Letting go of down used to play the jump **landing** (state 11: landing pose,
dust, sound), so mashing down looked and sounded like landing from jumps. Each fighter now has its own `Crouch_Exit`
state (`States/<TAG>_CrouchExit.tres`, its `8_<TAG>_CrouchExit` animation; no dust, no sound) used by the Uncrouch move
and the crouch's exit; states 11-13 are the landings again. Made by `tools/sprite_port/crouch_exit.py`.

## Cancels (Oct 24 night)
- **2B chains into 5B, 5C, 2C and jump** for every fighter (Flan and Leticia had Cecilia's old problem: only specials).
- **Crouching normals in chains work:** a move's `CanCancelTo` list is checked from the top and the first match wins;
  5A / 5B / 5C accept any direction, so with 5C listed before 2C, 2B > 2C came out as 2B > 5C (and 5A > 2B as 5A > 5B).
  The normals' lists are now in the engine's own order, highest move index first (2C before 5C), like neutral
  (`tools/sprite_port/sort_cancels.py`; `fdk.add_cancels` keeps that order). Specials keep their own order: a
  follow-up has to be checked before the 66 dash.
- Leticia's Crossfire shots can be cancelled into her supers on hit (the 6X follow-up also matched 236 + B + C).

## Meter gain (2000 = 1 bar = 100%; gauge 4 bars = 8000 since Oct 27 night)
BlazBlue Central Fiction's Heat Gain table (dustloop BBCF Frame Data), BB's whole 10,000-point Heat gauge = our whole
gauge (x0.8). Before Oct 27 night: fixed per-move numbers (the sheets' Meter column, no longer used), 6 bars, +2 a
frame walking forward (removed), half after the 6th hit (removed).
| Situation | BBCF | Ours (Craft Gauge points) |
| --- | --- | --- |
| Your hit lands | scaled damage x 0.72 | x 0.576 (a 2K combo ≈ 1150 = 58% of a bar) |
| You get hit | scaled damage x 0.4 | x 0.32 |
| Your attack is blocked | base damage x 0.18 | x 0.144 |
| You block | base damage x 0.1 | x 0.08 |
| You block the first hit of a string ("instant" block in the engine) | base x 0.2 + 100 | x 0.16 + 80 |
- EX moves, supers and Overdrive give the attacker nothing (BB: moves that cost Heat). Assists still build it.
- Overdrive x1.3 and Mary's Encore x1.25 still apply. One knob: `GameManager.NetsuMeterGainPercent` (100).
- Training's Craft Gauge setting: 0-4 bars.

## Assists (Oct 24) — S / 6 + S
Climax-style support characters: **Mary** (5S Encore: 115% damage + 125% Craft Gauge for 8 s; 6S Fermata Note: a floating note bomb),
**Adin** (5S Shield Counter: absorbs an attack and bashes the attacker into the air; 6S Rush Return: runs off-screen and charges back from behind),
**Eren** (5S Low Double Slash: dashing low cuts, pop-up then hard knockdown; 6S Falling Spin: jump-over spinning slash, then the low cuts back the other way),
**Harie** (5S Puddle Trap: hides in a puddle, uppercut when the opponent steps near it or after 4 s; 6S Swimming Wave: a 4-hit wave from behind you that carries and launches).
- Picked on the character select (after the colour, from a grid of every assist since Oct 24 night); everyone has one (no "none"). Calling from neutral on the ground
  makes the fighter **pose** for 30 frames (14 before Oct 24 night); in the air it's free; during her own attack it's an **Assist Cancel**
  (no pose, 1 bar since Oct 26; was 2). Not during her own super, or while her EX / super flash has the opponent frozen.
- One assist gauge per player (HUD, above the Craft Gauge): empty when you call, refills 9–14 s after the assist leaves
  (per move), full each round, instant in training (Training Menu > Gauges > Assist Gauge). Not while hit, blocking, grabbed, frozen by a super, or before the round starts.
- Assists can't be hit; their hits combo with the fighter's; blocked by holding away from the assist (cross-ups).
- Engine `NetsuAssist.cs`; data `data/assist_list.tres`; made by `tools/sprite_port/assists.py`. **Needs a Build.**

## Training mode (Oct 24 evening)
The dummy's behaviour (stand / crouch / jump / CPU / playback, guard all / after first hit / random, counter hit,
air recovery, wake-up rolls, wake-up reversal actions, recording and playback) and the health / gauge settings run
in the engine: `engine/sakuga/Game/NetsuTraining.cs`, made by `GameManager` in the "Training" mode and called from
`GameLoop` (the dummy's input is written before it goes into the input history; the gauges after the frame). The
Training Menu (pause) stores its settings in GameSettings' "training" section. Full map: `docs/training.md`.
**Needs a Build.**

## Online (Oct 24 night; group lobbies Oct 25)
Main menu → ONLINE: lobbies with a 5-digit join code for up to 8 players, **king of the hill** (the winner stays, the
loser goes to the back of the line), everyone else watches the fight live; rollback fights over direct connections
(LiteNetLib + PleaseResync). Full doc: `docs/online.md`. Rollback saves everything the fight uses: a sync test over 40,000+
frames of random play found no difference (Mahou saved the wall-bounce strengths wrong: fixed in `SakugaActorState`).

## Loading (Oct 24 evening; emblem and stalls Oct 25 evening)
- Between screens (outside the title) the screen fades to black and the Netsu emblem lights up while the next scene
  loads (`game/ui/netsu/netsu_emblem.gd`, `SceneRouter.use_emblem`). The VS screen → fight is a plain fade.
- Hitches in the fight: the .NET garbage collector's pauses. About a tenth of the garbage per frame now, a collection
  whenever the screen is black anyway (fight start, between rounds) and none during a round
  (`engine/sakuga/Game/NetsuGc.cs`).
- `data/roster.tres` and `data/stage_list.tres` now name each fighter colour / stage scene (**ScenePath**) instead of
  holding the scene itself, so loading the lists no longer loads every fighter and every stage (the stages alone were
  ~340 MB of textures, kept in memory for the whole game). The engine loads the one it needs
  (`ColorPaletteElement.GetScene()`, `StageElement.GetScene()`; an `Instance` set in the Inspector still wins).
  A new fighter colour or stage: fill in **ScenePath** (the file picker in the Inspector), not Instance.
- The VS screen loads the battle scene, the stage and both fighters on other threads while it plays
  (`MatchSetup.preload_match`, `bg_load`), and the character select loads every fighter in the background as it opens.
- The engine's per-hit / per-move console messages ("Fighter: Hit!", "You executed 5A!", "Buffer Cleaned!") are left
  out of the build (`engine/sakuga/Globals/NetsuLog.cs`); add `NETSU_VERBOSE` to the csproj's DefineConstants to see them.

## Throws (Oct 24 2026, late)
- **B + C** close (no down: 2 + B + C is still 2C; with a motion it's a super): a grab that comes out on frame 5
  (active 3 frames, 0.1 - 0.9 m in front). It connects → the opponent is held (frozen) for 12 frames → the throw.
  **4 + B + C** is a back throw: the opponent is put 0.65 m behind you and thrown the other way (into the corner if
  your back is to it). Damage: Cecilia 1100 (a slash), Flan 350 (knee) + 750, Leticia 1100 (both guns); knockdown.
  A whiffed throw lasts 28 frames (punishable).
- **Throw break**: the grabbed fighter presses **B + C** during those 12 frames → both are pushed apart (0.5 m each),
  nobody takes damage ("Escaped").
- You can't be thrown while in block stun or hit stun, nor for 5 frames after (no throw the instant blockstun ends,
  no throw on a wake-up that's still in hit reaction), nor while KO'd.
- B + C pressed in the first 2 frames of a normal replaces it (kara throw); B + C pressed during a normal's recovery
  comes out as a throw after it (not as a 5C cancel).
- Made by `tools/sprite_port/throws.py` (tables at the top: frames, boxes, damage, which drawings) → each fighter's
  `States/<TAG>_Throw*.tres`, `Moves/<TAG>_Throw.tres`, `Hitboxes/<TAG>_Hitbox_Throw*.tres`; inputs
  `actors/_shared/sakuga/Inputs/51_Input_Throw.tres` (B+C), `52_Input_ThrowBreak.tres`, `53_Input_HoldBack.tres`.
  Engine: `SakugaActor` (ThrowEscape while grabbed, NetsuThrowable / NetsuThrowProtect, a Mahou bug fixed: the
  throw's victim was told it had thrown itself), `NetsuMoveOpponentAction` (back throw), `MoveSettings.NetsuCheckOrder`
  (the throw is checked after the specials and supers, before the normals). **Needs a Build.**

## Input leniency (Oct 24 2026, late)
Mahou wanted a motion's directions exactly, one after the other, and both buttons of a pair on the same frame.
Now (`InputManager`, `StanceManager`, `GameManager.ReadInputs`; numbers at the top of `InputManager.cs`):
- **Two buttons together** (B+C, A+B, A+C, A+B+C): pressed up to 2 frames apart still count as together.
- **Motions** (236, 623, 214, 236236...): up to 6 frames of other input between two directions; a direction (or the
  last one before the button) may be held up to 12 frames; the button may come up to 6 frames after the last direction;
  an extra direction in between is ignored (2369 + B is 236B); the first direction can be held as long as you like
  (crouch, then 36 + B is 236B). Walking forward then 23 6 + B stays a 236 (the 6 of 623 must be a short tap).
- **Kara**: a two-button move (throw, super) pressed in the first 2 frames of a normal replaces it.
- **Stun buffer**: a normal, special or super pressed in the last 4 frames of block stun or hit stun comes out on the
  first free frame.
- Up + down at once = up; left + right = neutral.

## Fight sounds (Oct 24 2026, late)
Every attack, special, super, throw and assist move has a (placeholder) sound; replace any of them by saving your own
.wav over it. Fight sounds now follow the SFX volume, and don't double up after an online rollback. Full doc:
`docs/sounds.md` (`tools/sprite_port/sounds.py` = which move plays which sound on which frame).

## CPU (Oct 24 2026, late)
The CPU guards what it sees coming (assists, projectiles, full-screen beams, jump-ins, rushing supers) after a reaction
time that depends on the level, anti-airs from your jump, punishes recoveries, breaks throws and throws you, presses
cancels on time and rolls its own dice (its combos used to drop at the same link every time). Full doc: `docs/cpu_ai.md`.

## Launchers, bigger EX moves, wall and ground bounces (Oct 25 night)
- **6C launches** for every fighter (about 2.4 m up); on hit it jump-cancels (8 / 9 / 7) into an air combo. Cecilia and
  Leticia got a new 6C move (they keep 4A); the new move is checked after the normals and before the specials
  (`MoveSettings.NetsuCheckOrder` = 32.5), so 236C still comes out. `tools/sprite_port/launchers.py`.
- **(Oct 26) Every ground normal cancels into 6C** on hit or block. Whether it combos is the frame data's call (6C startup
  15 for Cecilia / Leticia, 17 for Flan / Noah, against the normal's hitstun; counter hit +12): lights only on counter
  hit, mediums and heavies combo. 6C's attack box now covers the body in front (about 1 m). Table:
  `docs/handoff_2026-10-26.md`.
- **EX moves hit harder:** sky-high launches, wall bounces, Leticia's Comet Burst board slam (see
  `docs/handoff_2026-10-25_ex.md` for the list).
- **Wall bounce anywhere in the flight:** the wall check was only in 30 Hit_LaunchAway; it is now also in 35 Hit_UpToDown
  and 36 Hit_Falling. The screen edge counts as a wall 7 m from the attacker while a bounce is pending
  (`OnWallsCondition.NetsuScreenWallDistance` 70000, was 88000).
- **Ground bounce:** a hit with `BounceTime` + `BounceYIntensity` makes them bounce back up off the floor (32
  Hit_LaunchDown → 31 Hit_LaunchUp). Both: `tools/sprite_port/wall_bounce_air.py`.
- **`NetsuOwnerVariableAction`** (new engine action): a spawned object sets a custom variable of the fighter who owns it
  (Noah's holes clear his HoleTimer when they burst on contact). **Needs a Build.**

## Backups
`_backup_stage_select/pre_overdrive_v2/` (engine files, both fighters' system moves, hitboxes, CPU files, command lists, notifications).
`_backup_stage_select/pre_assists/` (every file the assist work changed, Oct 24).
`_backup_stage_select/pre_cecilia_movelist/` (Cecilia's whole data before her prototype kit, the engine / UI / shader files of the call pose, flash and momentum work, Oct 24 afternoon).
`_backup_stage_select/pre_oct24_night/` (every file the Oct 24 night batch changed: movement, cancels, presentation, online, beams, Flan fixes).
`_backup_stage_select/pre_optimize_oct24/` (the loading / log changes), `pre_vs_screen_oct24/` (VS screen: MatchSetup, SceneRouter, character select, docs), `pre_training_oct24/` (training mode: the five engine files, GameSettings, Controls, MatchSetup, pause menu, icons, `battle.tscn`), Oct 24 evening.
`_backup_stage_select/pre_oct24_late/` (every file the throws / input leniency / sounds / CPU batch replaced, Oct 24 late; `push_manifest.tsv` lists them).
`_backup_stage_select/pre_push_oct25/` (every file the Oct 25 batch replaced: crouch exit, EX / super pause, Leticia's beams, sprite sizes, group lobbies, Cecilia's render; the list: `_backup_stage_select/push_oct25/push_manifest.tsv`).
`_backup_stage_select/pre_push_oct25_evening/` (every file the Oct 25 evening batch replaced: loading emblem, EX camera, stalls, the new moves and supers, text, blockstun, frame data sheets; plus the hitbox files and pictures it no longer uses; the list: `_backup_stage_select/push_oct25_evening/push_manifest.tsv` and `orphans.txt`).
`_backup_stage_select/pre_push_oct25_noah/` (every file the Oct 25 night batch replaced: Noah, Leticia's new portrait, the seven-element emblem, character-select music timing, frame data sheets; the list: `_backup_stage_select/push_oct25_noah/push_manifest.tsv`).

## Buttons (decided Oct 20; S Oct 24)
| Button | Normals | With a special-move motion | Alone |
| --- | --- | --- | --- |
| A | light | light version | |
| B | medium | heavy version | |
| C | heavy | EX version (2 bars); **without 2 bars it comes out as the B version** | |
| S | **assist**: S = 5S, 6 + S = 6S (see `claude/assists.md`). Dash is 66 / 44 only | | |
| A+B | | | while blocking: Pushblock (1 bar) |
| B+C | | Supers (236+B+C S-Craft, 3 bars; 214+B+C for a second super). Cecilia: 236236 / 214214 + any button (her B+C versions still work) | **Throw** (close; 4+B+C back throw); when grabbed: **throw break** |
| A+C | | | Burst |
| A+B+C | | | Overdrive |
Rule: two-button presses are only for supers and system mechanics. "C falls back to B" works in data, no engine change: the B move's input accepts B or C, the EX move (needs 4000) is checked first (every fighter's specials do this). Since Oct 24 all three fighters' specials use this scheme (Flan's were rebuilt from her new drawings). Throws: B+C since Oct 24 late (above).
`_backup_stage_select/pre_push_oct25_ex/` (every file the Oct 25 night batch replaced: 6C launchers, bigger EX moves, wall / ground bounces, Comet Burst slam, Noah's holes and Release; the list: `_backup_stage_select/push_oct25_ex/push_manifest.tsv`).
`_backup_stage_select/pre_push_oct26_6c/` (normals into 6C, Oct 26 morning; the list: `_backup_stage_select/push_oct26_6c/push_manifest.tsv`).
`_backup_stage_select/pre_push_oct26_tama/` (freeze lock, pushback, Special > EX, assist cost, OTG; Oct 26 afternoon, TamaDeez).
`_backup_stage_select/pre_push_oct26_noah/` (Noah fixes, Oct 26 late afternoon). `_backup_stage_select/pre_push_oct26_systems/` (this evening's systems batch).
