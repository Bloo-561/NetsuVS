# Fighter Editing Guide (SakugaEngine)

How to change hitboxes, frame data, air dashes, damage, speed, and more, without writing code.
Examples use **Cecilia** (`actors/cecilia/`, tag `CEC`). Every fighter is set up the same way (Flan: `actors/flan/`,
`FLN`; Leticia: `actors/leticia/`, `LET`).

> Everything here is a `.tres` file you edit in Godot's **Inspector**.
> Double-click a file in the FileSystem dock and its settings appear on the right.
> Change a number, press **Ctrl+S**, and run Training Mode to test.

> **Since Oct 24** most fighter files are made by the scripts in `tools/sprite_port/` from tables (guide:
> `tools/sprite_port/README.md`; per fighter: `docs/characters/<fighter>.md` → "Where to change things").
> Editing in Godot as below still works, and the scripts keep what you changed (they print SKIPPED), except the
> timelines: which picture shows on which frame (and, for specials, when each hitbox file switches on) is
> rewritten from the scripts' tables when they run on that animation. The numbers below are Cecilia's on Oct 24.

---

## 1. How a fighter fits together

```
Button press ──► MOVE ──► STATE ──► ANIMATION DATA ──► sprites for each frame
 (Inputs/)      (Moves/)  (States/)  (AnimationData/)   └► HITBOX SETS (Hitboxes/)
                                                            └► hurtboxes, hitboxes, damage
```

| Folder / file | What it is | You edit it to change... |
|---|---|---|
| `0_CEC_Data.tres` | The fighter's master file. Lists every **state**, the **stances**, health and meter. | Health, meter size, adding new states |
| `0_CEC_Profile.tres` | Name, portraits, art used in menus | Name, select-screen art |
| `Stances/CEC_Stance_Main.tres` | The **move list**: every move the fighter can do | Adding/removing moves |
| `Moves/` | One file per move: which **input** does it, which **state** it plays, what it can cancel into | Inputs, cancels, air-only/ground-only, meter cost |
| `States/` | What happens while the move plays: movement, gravity, sounds, effects, what comes next | Speed, jump height, air dash distance, invincibility |
| `AnimationData/` | Frame-by-frame timeline: which sprite shows when, and **when hitboxes turn on** | Startup / active / recovery frames |
| `Hitboxes/` | The boxes themselves (size, position) **and** all hit properties | Hitbox size, damage, hitstun, blockstun, knockback |
| `Instances/CEC_Fighter_Skin00.tscn` | The fighter scene (sprites, sounds, counters such as air dash limit). `Skin01`–`Skin03` are the other colours. | Air dash / air jump count |
| `actors/_shared/sakuga/Inputs/` | Shared input patterns (`236C`, `66`, `5A`...) used by every fighter | Motion inputs |
| `actors/_shared/sakuga/AttackLevels/` | Shared presets (light/medium/heavy) | Reference values |

### The two rules that trip everyone up

1. **Numbers are positions in a list.** A state's number is its position in the `States` list of
   `0_CEC_Data.tres` (counting from 0). A move's number is its position in the `Moves` list of the stance.
   Moves point to states by that number (`MoveState = 19`), and cancels point to moves by number (`MoveIndex = 8`).
   The number at the start of a file name *usually* matches, but not always: in Cecilia's list the intro /
   victory / defeat states (`1000_...`–`1002_...`) sit at 89–91 and `CEC_Breakthrough` at 96.
   **When in doubt, count the position in the list.**
   **Always add new states and moves at the END of their list**, or every number after it shifts and moves break.
2. **Copying inside the Inspector shares data.** If you copy and paste a sub-resource, both copies are
   the *same* object, so editing one edits both. Right-click the field and choose **Make Unique**
   before changing it. Duplicating a whole file in the FileSystem dock (right-click → Duplicate) is safe.

---

## 2. Units

| Thing | Unit |
|---|---|
| Time | **Frames**. The game runs at 60 frames per second, so 60 frames = 1 second. |
| Distance | **10,000 = 1 meter** (1 Godot unit). A standing fighter is about 13,500–14,300 tall (sprites: 27.5 units per sprite pixel; Flan 490 px, Cecilia 500, Leticia 520). |
| Hitbox `Center` | `(x, y)` measured from the fighter's feet. **+x = in front of them**, +y = up. |
| Hitbox `Size` | Full width and height (`Vector2i(4200, 2000)` = 0.42 m wide, 0.2 m tall). |
| Velocity | Units **per second**: the fighter moves Velocity ÷ 60 every frame (walk 32,000 = 3.2 m/s; air dash 74,000). Gravity takes force ÷ 60 off the vertical speed every frame (default 260,000). |
| Stage walls | ±120,000 from the center. |

All values are whole numbers on purpose. Rollback netcode needs both players' games to compute
*exactly* the same thing, and decimals can differ between PCs. Never change these fields to decimals.

---

## 3. Recipes

### Change startup / active / recovery frames
Open the move's **AnimationData**, for example `AnimationData/48_CEC_5A_AnimData.tres` (Cecilia's 5A):

```
Duration  = 23                       ← total length of the move in frames
Hitboxes  = [ HitboxState AtFrame 0                   → 5_Hitbox_5A_0 (hurtboxes only)
              HitboxState AtFrame 3                   → 5_Hitbox_5A_1 (hurtboxes + proximity box)
              HitboxState AtFrame 5   stage ACTIVE    → 5_Hitbox_5A_2 (has the attack box)
              HitboxState AtFrame 7   stage RECOVERY  → 5_Hitbox_5A_3 (hurtboxes only)
              HitboxState AtFrame 12  stage RECOVERY  → 5_Hitbox_5A_4 ]
Animations = [ sprite 5a_1 at frame 0, 5a_2 at 5, 5a_3 at 11 ]     (pictures in Sprites/v2/)
```

So 5A is **5 frames of startup** (0–4), **active frames 5–6** (2 frames), and **recovery from 7 to 22**.

- **Faster startup:** lower the ACTIVE entry's `AtFrame` (5 → 4). Usually also lower the matching sprite's `AtFrame` so the art lines up.
  For animations the scripts made, change the sprite timing in `tools/sprite_port/manifests/<fighter>.json` (and a
  special's box timing in its `moves_<fighter>.py` table) instead, or the next script run puts it back.
- **More active frames:** raise the RECOVERY entry's `AtFrame` (9 → 11).
- **Less recovery:** lower `Duration` (17 → 15).
- Keep the entries in order (`AtFrame` must increase down the list).

Frame advantage is roughly **blockstun minus the frames left in the move after it connects**.
The exact number shows in **Training Mode** (frame advantage display), so check it there.

### Change a hitbox's size or position
1. Find the hitbox set for the active frames. For 5A it's `Hitboxes/5_Hitbox_5A_2.tres`.
2. It holds a `Pushbox` (the body that pushes the other fighter) and a list of `Hitboxes`.
   Each entry has a **HitboxType** (in the file: no line = HURTBOX, 1 = HITBOX, 2 = PROXIMITY_BLOCK):
   - `HURTBOX` (green): where *you* can be hit
   - `HITBOX` (red): your attack
   - `PROXIMITY_BLOCK` (purple): makes the opponent start blocking early
   - `THROW`, `PROJECTILE`, `COUNTER`, `DEFLECT`: special types
3. Change `Center` and `Size` on the red one. 5A's attack box is `Center (3300, 9400)`, `Size (4400, 2600)`.
   To reach further, raise `Center.x` and/or `Size.x`.
4. See the result:
   - **In the editor:** open `tools/move_preview/move_preview.tscn`, select **HitboxPreviewer**, set **Data** to the AnimationData you're editing, and drag **Frame** to scrub through the move. Turn on **AutoRun** to loop it.
   - **In game:** Training Mode, then press **F10** to show hitboxes.
   - **Refit to the drawings:** `python tools/sprite_port/hitfit.py cecilia 48_CEC_5A --write` (the picture of the
     fit is in `tools/sprite_port/checks/cecilia/`; files you changed in Godot are skipped).

### Change damage, hitstun, blockstun, knockback, hitstop
These live on the **red HITBOX entry** inside the hitbox set (same file as above). Expand its groups:

| Group | Fields | What they do |
|---|---|---|
| Damage Settings | `BaseDamage` (5A = 250), `ChipDamage`, `GuardCrush`, `GuardCrushDamage`, `DamageScalingSubtract` | How much it hurts, chip on block, guard break, combo scaling |
| | `SelfHitStopDuration` / `OpponentHitStopDuration` / `BlockStopDuration` | The freeze on impact |
| | `SelfSuperGaugeGain` / `OpponentSuperGaugeGain` | Meter built |
| Ground Hit Settings | `GroundHitstun` (14), `GroundBlockstun` (10), `GroundHitKnockback` (-30000, 0), `GroundHitReaction` | Stun length, pushback, which hit animation plays |
| Air Hit Settings | `AirHitstun`, `AirHitKnockback` (x, y), `AirHitKnockbackGravity` | Juggles: how high and far they fly, how fast they fall |
| Throw / Bounce / Corner Pushback | `GroundThrow`, `BounceTime`, `SelfPushbackForce` | Throws, wall/ground bounces |

> AnimationData also has an **AttackProfiles** list, and hitboxes have a `Profile` number. In this
> version of the engine the hit uses the values on the **hitbox entry itself**, so edit those.

### Change the air dash
The air dash is split across three files:

1. **The move** (`Moves/7_CEC_AirDashForward.tres`) decides when you're *allowed* to air dash:
   - `Inputs` = `actors/_shared/sakuga/Inputs/9_Input_66.tres` (tap forward twice)
   - `UseOnAir = true` (air only)
   - `VariablesRequirement` checks you still have an air dash left
   - `CanCancelTo` lets you steer it up or down (moves 8 and 9) between frames 3 and 6
2. **The state** (`States/19_CEC_ForwardAirDashState.tres`) decides *how it moves*:
   - `OnEnterEvents`: stops your momentum and locks other moves (`SetFrameProperties` with LOCK_MOVE)
   - `OnTickEvents` **at frame 4**: `MoveXAction Velocity = 64000` (74000 before Oct 24 night). **This is the air dash speed.** Raise it for a faster/longer dash.
   - When it ends (`TransitionEvents`) a `MoveXAction` sets the speed she falls on with (32000). For all fighters at once:
	 `tools/sprite_port/tune_movement.py` (numbers at its top).
   - `TransitionEvents`: when the state ends, plays state **10** (falling)
3. **The length** is the `Duration` of `AnimationData/12_CEC_AirDashFw_AnimData.tres` (22 frames). A longer duration travels further.

**Number of air dashes:** open `Instances/CEC_Fighter_Skin00.tscn`, select
`Parameters/Variables/AirDashLimit`, and change `MaxValue` (1 → 2 for a double air dash).
Do the same in `Skin01`–`Skin03.tscn` (one per colour). `AirJumpLimit` works the same way for double jumps.

### Walk speed, jump height, gravity
- **Walk speed:** `States/1_CEC_MoveForwardState.tres` → `MoveXAction Velocity = 32000`. Backward walk is state 2. (Flan walks slower: 26,000 / back 19,000.)
- **Jump height:** `States/3`, `4`, `5` (neutral / forward / back jump) → `MoveYAction Velocity = 85000`. Forward jump distance is the `MoveXAction` in the same file.
- **Gravity:** jump states use `AddGravityAction` with `UseDefault = true` (the engine default, 260,000). Turn off `UseDefault` and set `Force` for a floatier or heavier character.
- **Dashes:** `States/16_CEC_ForwardDashState.tres` and `18_CEC_BackwardsDashState.tres`.

### Health and meter
`0_CEC_Data.tres`: `MaxHealth` (10,000 by default; Flan has 11,000), `MaxSuperGauge`, `SuperGaugeChargeRate`,
`BaseAttack` / `BaseDefense` (100 = normal).

### Change which button does a move
Open the move (`Moves/23_CEC_5A.tres`) and change `Inputs` to another file from
`actors/_shared/sakuga/Inputs/`. File names read like fighting-game notation: `5A`, `2B`, `236C`, `623C`, `66`.

| NetsuVS button | Engine name |
|---|---|
| A | FACE_A |
| B | FACE_B |
| C | FACE_C |
| S | FACE_D: the assist button (S = the assist's neutral move, 6 + S its forward move; `docs/assists.md`). Dashes are 66 / 44. |
| AB / BC / ABC macros | press those buttons together |

To make a new input, duplicate a similar file in the FileSystem dock and edit its `Directional` / `Buttons` values.

### Cancels (what a move can chain into)
In the move file, `CanCancelTo` is a list. Each entry has:
- `MoveIndex`: which move (its number in the stance's move list)
- `Conditions`: add these numbers together: **1** = on whiff, **2** = on hit, **4** = on block, **8** = kara cancel.
  5A uses **6** (hit + block).
- `FrameThreshold (from, to)`: the frame window where the cancel is allowed.
- **Order matters** (Oct 24 night): the engine checks the list from the top and takes the first entry whose input matches.
  5A / 5B / 5C accept any direction, so they must come after 2A / 2B / 2C or the crouching versions never come out of a
  cancel. Keep normals' lists from the highest move index to the lowest (`python tools/sprite_port/sort_cancels.py` does it).
- **Event lists** (`OnEnterEvents`, `OnTickEvents`, `TransitionEvents`...) hold **FrameDataEvent** entries with the
  actions inside them, never bare actions (Godot drops the whole list: the move loses its momentum stop, invincibility...).
  `python tools/sprite_port/fix_event_lists.py --check` finds any.

### Invincibility, armor, and other frame properties
Two ways to make a move invincible:
- **Simplest:** in the hitbox set used during those frames, delete (or zero the `Size` of) the green
  `HURTBOX` entries. With no hurtbox, nothing can hit you.
- **With events:** in the state, add a `SetFramePropertiesAction` with an `AtFrameRangeCondition` for the frames you want.
  `Properties` is a sum: **1** = immune to strikes, **2** = immune to throws, **4** = immune to projectiles,
  **16** = can't start other moves. `ChangeMode` is SET (replace), ADD, or SUBTRACT (remove). Most of Cecilia's states use **16** (move lock),
  for example the air dash.

`SetArmorAction` (absorb hits) and `SetDefenseAction` (take less damage) work the same way.
`States/88_CEC_LastWishBurstState.tres` has an example to copy. Flan's `States/74_FLN_236B.tres` (Twirling Star
Fist) turns armor on at frame 4 (`SetArmorAction Value = 1`) and off at 24 (`Value = -1`; 0 does nothing); an
armored hit still deals half damage.

### Multi-hit moves
A move hits each opponent once per state: after it connects (hit or block), no other attack box in the same state
can hit them until a **`ResetHitAction`** runs. For a second hit, add an event to the state's `OnTickEvents` with an
`AtFrameCondition` on the frame the next attack box starts and a `ResetHitAction` (Flan's `States/76_FLN_623A.tres`
has two: its uppercut hits three times). In the scripts' tables it is `(frame, reset_hit())` in `tick`; `python tools/sprite_port/check_multihit.py`
lists the moves that are missing one. A new state (a follow-up, a landing) starts clean.

### Add a new move (copy an existing normal)
Specials and supers are quicker to add as a new entry in the fighter's `tools/sprite_port/moves_<fighter>.py`
table (it makes all the files below and registers them). By hand:
1. In the FileSystem dock, **Duplicate** the move, state, animation data and hitbox files of a similar move.
   Give the copies the next free numbers.
2. In the new AnimationData, point `Hitboxes` at your new hitbox files and `Animations` at your sprites.
3. In the new state, set `AnimationData` to your new AnimationData.
4. Add the new state to the **end** of `States` in `0_CEC_Data.tres`, and note its number.
5. In the new move, set `MoveState` to that number and pick its `Inputs`.
6. Add the new move to the **end** of `Moves` in `Stances/CEC_Stance_Main.tres`.

---

## 4. Testing loop
1. Edit, then **Ctrl+S**.
2. **F5**, then Main Menu → Training Mode → pick the fighter.
3. In the match:
   - **F10** shows hitboxes.
   - **Start / Enter** pauses (retry, character select, main menu).
   - The training display shows **frame advantage** and **input history**.
4. Too slow to restart each time? Use `tools/move_preview/move_preview.tscn` to check hitboxes frame by frame without running the game.

## 5. Where the engine lives (for when you want to read code)
| Path | What |
|---|---|
| `engine/sakuga/` | SakugaEngine (C#). Fighters, physics, hit detection, HUD. |
| `engine/sakuga/Resources/FrameDataEvents/Actions/` and `/Conditions/` | Every event you can add to a state, one file each (`MoveXAction`, `AtFrameCondition`...). The file names are the menu names in the Inspector. |
| `engine/sakuga/Globals/GlobalVariables.cs` | Engine-wide numbers (default gravity, wall distance, hitstop...) |
| `engine/netcode/` | PleaseResync rollback + LiteNetLib networking |
| `scenes/battle/battle.tscn` | The match scene |
| `data/` | Roster, stage list, game modes, match settings, soundtrack |
| `tools/port_mahou/` | Record of how files were copied from the Mahou project |
| `tools/sprite_port/` | Scripts that build the fighters and assists from the drawings (sprites, animations, boxes, specials): `README.md` |
| `tools/ai/` | CPU opponent builders, `build_<fighter>_ai.py` → `actors/<fighter>/AI/` |
