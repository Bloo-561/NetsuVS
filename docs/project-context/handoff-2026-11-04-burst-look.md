# Handoff Nov 4 2026: the Burst's look, after Persona 4 Arena Ultimax

**C# changed (SakugaActor.cs): Build in Godot before testing.** Backups of every file touched: `_backup_stage_select/pre_burst_p4fx_nov04/` (the folder has a `.gdignore` again, so Godot doesn't import the old Celdic copy in there).

Reference: "Persona 4 Arena Ultimax: Tutorial #2: Basic Moves", 0:58–1:01. Frame by frame, the one bursting there is Akihiko (P2) breaking out of Yu's combo; Yu is the one launched (and wrapped in static). The look is P4AU's standard Burst: blue whirlwind → gold flash on the sprite → spiky gold blast → breaks into blue static. The static is put on the Burster's fall here (TamaDeez's timeline).

The timeline itself is unchanged (see handoff-2026-11-03-burst.md): rise 0–11, Burst 15–39, invincible 0–40, fall / punish window 41–66.

## What you see, frame by frame
| Frames | Look |
|---|---|
| 0–4 | her sprite flashes pale blue; a pale blue flash at her chest |
| 0–14 | a big see-through blue whirlwind (8 crescent ribbons on tilted ellipses) wraps her as she lifts, thin blue streaks shoot off it, then two thin rings settle round her waist and legs. Aura: pale blue |
| 13–21 | her sprite flashes gold (brightest on 15). Aura: gold until frame 40 |
| 15– | the blast: white-hot core, 16 gold spikes, 12 flame tongues (gold → orange → red), 7 long white streaks; blue-violet streaks whip round it (0.3 s) |
| ~23–45 | it breaks into blue static (blocky noise) and pixels round her as she comes down, a tall blue whirl, and a ragged patch of static on the floor under where it went off (gone ~0.85 s after it went off) |

Everything follows her (cost -5 every frame). Stage dim 0.25, white flash 0.16.

## Each fighter's own touch
| Fighter | Overlay (`bb_styles`, by ShortName) | Her own burst sprites (AnimationData) |
|---|---|---|
| Cecilia | yellow lightning crackling in the whirlwind, bolts out of the blast | lightning swirl `cs_boom1` 0–14, `cs_boom2` 15–32, `cs_boom3` 33–45. **Always shown now** (was only on contact) |
| Flan | glints drawn in, then 14 spinning gold stars and twinkles | `6c_2` + star flare `fx_burst` from 15 (was 19) to 34 |
| Leticia | cyan sparks drawn in, then embers (falling) and cyan tracers | fire burst `burst_boom` 15–33 (was 0–33) |
| Noah | violet wisps drawn in, then violet crystal shards; every third flame violet | crystal arm `6c_act` from 15 (was 19) |

A new fighter: add `"shortname": "lightning" / "stars" / "embers" / "shards"` to `bb_styles`, or nothing (just the Burst).

## Files
- `game/ui/battle_hud/netsu_super_flash.gd`: section "THE BURST'S LOOK". Three layers so the colours hold on bright stages: light under (the node itself, additive), `BurstPaint` (normal blend: whirlwind, flames, static, stars, crystals), `BurstLight` (additive: core, spikes, lightning, glints). Tuning: the `bb_*` exports. The dead PUNISH ring / dome code is gone.
- `engine/sakuga/Components/SakugaActor.cs`: `NetsuBurstBegin` sends cost -6; `NetsuBurstTick` sends -3 on frame 15 and -5 on every other frame; `NetsuBurstLook` (sprite flashes); aura pale blue → gold.
- `actors/_shared/sakuga/VFX/VFX_20.tscn` (the shared "Burst" VFX): its teal ring and star are hidden; it still plays `Burst.wav`.
- The four `1001_<TAG>_Burst_AnimData.tres`: re-timed as above.

## Engine cues (MatchSetup.netsu_super_flash cost)
-6 Burst starts (frame 0) · -3 it goes off (frame 15, frames = 25) · -5 where she is now (every other frame) · -4 ignored.
