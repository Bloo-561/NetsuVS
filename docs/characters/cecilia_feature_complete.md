# Cecilia: road to feature complete (Oct 19 2026)

Goal: every move Cecilia has in game uses real art, and the new systems (Craft Gauge, EX Crafts, Breakthrough, Brave Burst, Overdrive) each have something to look at. Frame wording for moves already in the brief is in `cecilia-sprite-brief.md`; the new system frames are at the bottom of this doc.

## What she has now
- **Real art (done):** idle, walks, crouch, jumps, landing, run, backdash, air dashes, blocks, all hit reactions, 5A/5B/5C, 2A/2B/2C, j.A/j.B/j.C, 4A.
- **Placeholder:** 4B, 4C, 6C, 9C, j.2C (+ landing), j.3C, all 6 Crafts, the S-Craft, intro/victory, knockdown roll.
- **Missing completely:** a throw (the engine supports throws; she has none), Breakthrough and Brave Burst poses (they borrow 5B and the old burst).

## Batches, in order
Each batch is playable on its own when it lands.

| # | Batch | Frames | Why this order |
| --- | --- | --- | --- |
| 1 | **Crafts:** Opening Edge, Fujin, Raijin, Morning Moon, Thunder Strike, Luminous Divider | ~23 | Every combo ends in one, and the EX Crafts reuse these frames, so this one batch gives art to 9 moves. |
| 2 | **System poses:** Breakthrough, Brave Burst, throw + throw whiff, being thrown | ~13 | The new mechanics need their own silhouettes so both players can read them. |
| 3 | **Command normals:** 6C, 4B, 9C, 4C | ~20 | 6C (overhead) and 9C matter most for her game plan. |
| 4 | **Air specials:** j.2C (+ landing), j.3C | ~10 | |
| 5 | **S-Craft:** Sakura Morning Moon (+ cut-in) | 7–8 | Biggest payoff, but it's the hardest to keep on-model; do it once the smaller sheets are reliable. |
| 6 | **Intro / victory / knockdown roll** | ~11 | Presentation polish. |

About 85 frames in total.

## Art that is NOT needed (handled in engine)
- **EX Crafts** reuse the Craft frames with a bright outline/glow and a flash when they start, so EX moves read as "powered up" without new drawings.
- **Brave Cancel:** a full-screen flash and a colored afterimage, no sprite.
- **Overdrive:** a red heat aura around her while it's on, no sprite.
- **Craft Gauge / Burst ready:** HUD only.
These effects get built once and work for every fighter.

## Moves from her campaign kit that aren't in the game yet
Already written in the brief: **Swordwind Slash** (236A projectile), **Defensive Stance** (214A counter), **Focused Mind** (22B, builds meter), **Brilliant Spin** (214BC, 1 bar). Recommendation:
- Add **Swordwind Slash** and **Defensive Stance** after batch 4. A projectile and a counter round out a rushdown character.
- Hold **Focused Mind** (meter-building is a big lever with the new Craft Gauge; better tested after the gauge numbers settle) and **Brilliant Spin** (a 1-bar move now competes with the EX Crafts).

## Decide before drawing
- **Red scarf** (only the 5C art has it). Every new sheet should agree: either add "red scarf" to the master prompt and touch up the old frames, or add "no scarf" and redraw/trim 5C.

---

## New frame wording (batch 2: system poses)
Paste after the master prompt in the brief, one frame per image.

### Breakthrough (6+A+B while blocking): guard-cancel sheath shove
She breaks out of blockstun by shoving the opponent away with the sheathed sword. Fast and defensive, not a big attack. Sword stays SHEATHED.
| File | Pose |
| --- | --- |
| `sys_breakthrough_1.png` | Still in her guard pose, sheathed tachi held crosswise in both hands, a bright white-gold flash at the sheath where it blocked. |
| `sys_breakthrough_2.png` | **Hit**: both arms thrust forward, the sheathed tachi held level and slammed forward like a bar, front leg stepping in, a white-gold shockwave ring at the point of contact. |
| `sys_breakthrough_3.png` | Arms still forward, weight on the front leg, the shockwave fading. |
| `sys_breakthrough_4.png` | Stepping back into her fighting stance. |

### Brave Burst (A+C): defensive burst
A sudden flare of power that blows the opponent away. She doesn't attack; the energy does.
| File | Pose |
| --- | --- |
| `sys_burst_1.png` | Curled tight, knees bent, arms crossed over her chest holding the sheathed tachi, eyes shut, a small gold spark at her core. |
| `sys_burst_2.png` | Exploding open: arms and tachi flung out to her sides, head thrown back, hair and skirt blown outward, a big gold-crimson energy sphere bursting around her. |
| `sys_burst_3.png` | Settling: arms lowering, the energy sphere breaking into gold sparks around her. |
Ask for each frame both standing on the ground and floating in the air (bursts can happen mid-combo): name the air ones `sys_burst_air_1-3.png`. If that's too many, the ground set is enough.

### Throw (forward or back + B+C, input to be decided)
Iai-style throw: she catches the opponent with the sheath and throws them past her.
| File | Pose |
| --- | --- |
| `throw_1.png` | Throw attempt: steps in, left hand reaching forward open-palmed at chest height, right hand on the sheathed hilt. |
| `throw_2.png` | Whiff: hand closing on nothing, leaning forward off-balance. |
| `throw_3.png` | Caught: left hand gripping (the opponent is not drawn), sheath angled across her body. |
| `throw_4.png` | Hooking the sheath and spinning a half-turn, pulling the (undrawn) opponent around. |
| `throw_5.png` | **Hit**: releasing, arm swept forward, hair whipping, small white impact burst where her hand lets go. |
| `throw_6.png` | Recovering into stance. |

### Being thrown (used when the opponent throws her)
| File | Pose |
| --- | --- |
| `hurt_grabbed.png` | Grabbed by the collar: upright, arms flailing slightly, shocked face, feet on the ground. |
| `hurt_thrown.png` | Thrown: body horizontal in the air, back arched, arms trailing, sword still on her hip. |
