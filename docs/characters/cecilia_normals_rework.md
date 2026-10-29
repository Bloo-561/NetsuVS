# Cecilia – Normals rework brief (v4)

Oct 19, 2026. Reworks 2B, 2C, j.B and j.C from playtest notes, using Narmaya (GBVS) and Yuuki (DFCI) as references. These replace the matching blocks in `cecilia-sprite-brief.md`. Idle needed no new art; it was retimed in the engine (each frame now 12 game frames, 1.6 s per breath).

**Status:** 2B, 5B and 2C done. 5C redo done Oct 20. Waiting on j.B, j.C charge frames, and the in-between frames listed at the bottom (smoothness pass).

**Slash trails:** her element is lightning, so ask for trails in gold-yellow ("gold-yellow lightning slash trail"). Keep drawing them into the frames as usual; Claude cuts them onto a separate layer that only shows when the move connects (hit or block).

## How to use this with ChatGPT

1. New ChatGPT chat. Attach:
   - her in-game sprite `actors/cecilia/Sprites/idle1.png` (size, angle, pixel style);
   - her full-body render (design);
   - the **pose reference** listed for the move (the Narmaya screenshots).
2. Paste the master prompt below once, then one move block, then ask for one frame per image ("Draw frame 1 only", and so on).
3. Save each frame with the file name in the table and drop them in `actors/cecilia/_incoming/`. Claude cuts, scales, lines them up, fits the hitboxes and swaps them in; the old frames are backed up first.

When you attach a Narmaya reference, add this line every time, or ChatGPT will start drawing horns and pink hair:

```
The extra image is a POSE REFERENCE ONLY. Copy the body angle, how low she is, the blade length and the shape of the slash. Do NOT copy that character's face, hair, horns, outfit, colors or sword design. The character is still Cecilia.
```

**Master prompt (corrected to match her finished sprites):**

```
You are drawing animation frames for a 2D fighting game sprite. The attached images are the character, Cecilia Richter. Keep her design EXACTLY the same in every frame:
- Slim build, average to slightly tall height.
- Black bob haircut fading to purple at the tips, with an ahoge, and a red headband.
- Red eyes.
- Cropped black jacket with rolled sleeves and a tan band on one upper sleeve, white shirt collar, yellow neckerchief.
- Red pinafore dress with a pleated skirt and white frills. NO scarf.
- Back leg: black thigh-high sock crossed with red straps. Front leg: plain black knee-high sock.
- Brown shoes with red bows, black fingerless gloves.
Her weapon is a TACHI (a long curved Japanese sword): red hilt wrapped with gold diamonds and a gold cap, white sheath with a red-and-gold end, worn on her LEFT hip. She fights in the Eight Leaves One Blade style: precise iai draw-slashes and clean cuts. Every pose looks controlled and deliberate. In battle her expression is calm and focused, not angry.

Style: the same crisp high-resolution anime pixel art as the reference sprite, with clean dark outlines, the same colors and the same proportions.

Rules for EVERY frame:
- Full body visible, head to toe, nothing cropped (include the whole blade), with empty space on every side.
- She faces RIGHT, in a side-on fighting-game view, the same size as the reference sprite.
- Feet planted on one flat, invisible ground line (unless the frame is in the air).
- Plain transparent background. If you can't do transparency, use flat pure green (#00FF00).
- No ground shadow, no text, no UI, no border.
- No slash trails, lightning, wind or petals unless the frame description asks for them.
- One single pose per image.
```

---

## 2B – long low slash (REWORK: longer blade, wider arc) – DONE Oct 19, in game

**Feedback:** the sword needs to look longer. **Pose reference:** Narmaya's crouching slash (very low, leaning forward, long blade, wide sweeping trail).

**Gameplay:** her mid-range low poke. The longer blade and trail give it about 25% more reach than now; it still hits low and cancels into Crafts.

Add to the prompt: `Draw the blade LONG: from the guard to the tip it is about as long as from her shoulder to her feet. Keep this blade length in every frame of this move.`

| File | Pose |
| --- | --- |
| `2s1.png` | Very low crouch, almost kneeling, body leaning forward, right hand on the hilt at her left hip, sword still sheathed. |
| `2s2.png` | Drawing: the long blade comes out of the sheath low and to the side, tip trailing behind her, weight shifting onto the front foot. |
| `2s3.png` | **Hit**: blade swept forward low and wide, arm fully extended, tip far in front of her at ankle-to-shin height. A long pale white-crimson slash trail curves from behind her, along the floor and up in front of her. |
| `2s4.png` | **Hit**: end of the arc, blade forward and slightly raised, trail fading. |
| `2s5.png` | Recovering: pulling the blade back toward the sheath, still low. |
| `2s6.png` | Back to her crouch, sword sheathed. |

## 5B – long iai slash (REWORK: much longer reach, horizontal draw-cut) – DONE Oct 19, in game (lightning version)

**Feedback:** needs to reach farther and be remade. **Pose reference:** Narmaya's standing iai slash: upright and side-on, the blade carried past her after one horizontal cut, a long straight slash band shooting far forward across the screen.

**Gameplay:** her longest standing poke and main mid-range button. The attack box covers the blade plus the near part of the slash band, to about 1.8 m in front of her (now about 1.05 m). The cut is at **waist-to-chest height**, so it still hits crouching opponents.

Add to the prompt:
```
The slash trail is a long, straight horizontal band of light, crimson-red at the edges and white-hot in the middle, starting at the blade and stretching far to the RIGHT, about three times as long as she is wide. No butterflies, petals or other particles. Make the image WIDE (landscape) with lots of empty space on the right so the whole trail fits without touching the edge.
```
If ChatGPT keeps cutting the trail off, ask for the frames without any trail and tell Claude; the band can be drawn on top in the same colors.

| File | Pose |
| --- | --- |
| `5b1.png` | Iai stance: standing side-on, knees slightly bent, weight on the back foot. Left hand holds the sheath at her hip with the thumb pushing the guard open, right hand on the hilt. Eyes on the opponent. |
| `5b2.png` | The draw begins: front foot sliding forward, hips turning, the first third of the blade out of the sheath with a glint of light at the sheath mouth. |
| `5b3.png` | **Hit**: one fast horizontal cut at waist-to-chest height. Right arm fully extended forward, blade level and pointing straight ahead, body still side-on. The long slash band starts at the blade and shoots far forward to the right. |
| `5b4.png` | **Hit** (follow-through, like the reference): upright and side-on, the right arm has swung the blade on past her body, so it's held out behind her at shoulder height, sheath still at her hip in the left hand. The slash band still crosses the whole space in front of her, at its brightest. |
| `5b5.png` | Same pose, the band fading and breaking into thin streaks, blade starting to come back toward the sheath. |
| `5b6.png` | Re-sheathing with a click, back in her fighting stance, trail gone. |

## 2C – Scarlet Sky (REWORK: long-range low snipe that goes under projectiles) – DONE Oct 19, in game

**Feedback:** a long-range low snipe. Safe at max range, good at shorter ranges, and it low-profiles: her body drops low enough that standard fireballs pass over her. **Pose reference:** Narmaya's lunging low slash (body stretched almost flat and close to the floor, one arm far forward).

**Gameplay:**
- She lunges forward as she cuts. It hits low and knocks down.
- During the active frames her hurtbox drops so standard projectiles fly over her. For that to work, **her head must be no higher than her standing hip** on the hit frames.
- Pushback on block plus the recovery are tuned so it's safe when it hits at the tip, and punishable up close.

Add to the prompt: `On the hit frames her whole body is stretched out LOW and long, her head no higher than her hip would be when standing, almost sliding along the floor.`

| File | Pose |
| --- | --- |
| `2m1.png` | Deep crouch, weight on the back foot, right hand on the hilt, ready to spring. |
| `2m2.png` | Launching forward low: front leg stepping far out, body tipping forward, blade starting to draw. |
| `2m3.png` | **Hit**: fully stretched lunge, body nearly horizontal and close to the floor, front knee bent and back leg straight behind her, sword arm reaching far forward with the blade sweeping along the ground. Thin red-crimson slash trail along the floor. |
| `2m4.png` | **Hit**: same low lunge, blade at the end of the sweep in front of her, trail curling up at the tip. |
| `2m5.png` | Still low, starting to pull back, blade turned up. |
| `2m6.png` | Pushing back up into a crouch. |
| `2m7.png` | Back to her crouch, blade sheathed or held at her side. |

## j.B – downward crescent jump-in (REWORK: longest downward reach, can cross up)

**Feedback:** like Narmaya's j.M in Genji stance, the jump-in with the longest downward range. It can cross up, but the cross-up hitbox is small and needs exact timing and spacing. **Pose reference:** Narmaya's inverted diving slash (body tipping over, a huge crescent swept underneath her).

**Gameplay:**
- Her best jump-in. The blade sweeps from BEHIND her, down underneath her and out in front, so it covers below her better than any other air normal.
- A small hitbox behind her on the first hit frame lets a well-spaced jump over the opponent hit from behind (cross-up). It's the only one she has.
- Hits high (must be blocked standing). It doesn't overlap j.C, which covers in front of her.

| File | Pose |
| --- | --- |
| `j5s1.png` (optional) | In the air, knees tucked, hand on the hilt. |
| `j5s2.png` | Body starting to tip forward, blade drawn and raised up and BEHIND her head in both hands. |
| `j5s3.png` | **Hit**: body tipped forward and turned slightly down, head toward the ground, legs up behind her. The blade sweeps DOWN behind and underneath her. A pale white crescent slash trail starts behind her back and curves underneath her body. |
| `j5s4.png` | **Hit**: the blade has passed under her and points forward and down, past her knees. The crescent trail is a big curve under her whole body. |
| `j5s5.png` | Righting herself: body turning back upright, blade low in front. |
| `j5s6.png` (optional) | Knees tucked, blade at her side, ready to land. |

## j.C – chargeable crescent (REWORK: hold to charge, like Yuuki's j.C)

**Feedback:** uncharged, partly charged or fully charged. It covers a good angle in front of and below her, for air-to-air and air-to-ground. The partial charge lets her answer fuzzy options and air-to-air exchanges. **Reference:** Yuuki's j.C hitbox (DFCI), a strong forward-and-down angle.

The current art already has the right shape (it covers the front-and-down angle). Only the charge pose is new.

**Gameplay (first-pass numbers):**

| Version | How | Effect |
| --- | --- | --- |
| Uncharged | Tap C | As now: 9 frames to hit, 550 damage. |
| Partial | Hold C 10–23 frames, release | About 1.2× damage and a slightly bigger arc. Knocks down an opponent who is in the air. |
| Full | Hold 24+ frames (she swings by herself at 30) | 1.5× damage, the biggest arc and a gold flash. Bounces an airborne opponent off the ground, so she can combo after landing. |

She keeps falling while she charges, so how long she holds it decides where the swing happens. The flash at partial and at full charge is done in the engine.

| File | Pose |
| --- | --- |
| `j5m1.png` – `j5m6.png` | Keep the current frames (no redraw). |
| `j5m2h1.png` | **Charging (new):** same pose as `j5m2.png` (blade raised high behind her head in both hands, body coiled), held tighter, a soft gold-white glow gathering along the blade edge. |
| `j5m2h2.png` | **Charging (new):** same as `j5m2h1.png` with the glow a little brighter and her hair and skirt fluttering upward. This pair loops while C is held. |
| `j5m3f.png`, `j5m4f.png` (optional) | **Full charge only:** same as `j5m3` and `j5m4`, but the crescent trail is twice as wide and gold-crimson with small gold lightning crackles. Without these, the full charge reuses the normal frames with an engine glow. |

---

## 5C redo – full two-handed lightning draw-cut (8 frames) – DONE Oct 20, in game

**Why:** the current 5C is off-model (red scarf, both socks strapped) and its white-blue crescent slash doesn't match her gold-lightning theme or show-on-hit-only rule.

**Concept:** 5C is the big version of 5B. 5B is a quick one-handed iai flash; 5C is a committed two-handed draw: she steps in, the blade comes out and cuts through in one wide horizontal arc. No slash trail is drawn by ChatGPT: Claude adds a big gold lightning slash in the engine that shows on hit/block only (same as 5B, bigger), plus heavier screen shake.

**Gameplay (unchanged for now):** 14 startup, ~3 active, ~16 recovery, 650 damage, level 3. The lunge carries her forward, so reach stays about 1.6 m.

Start a NEW ChatGPT chat. Attach `idle1.png`, her full-body render and `5b4.png` (for blade size). Paste the master prompt, then this block:

```
MOVE: 5C – a heavy two-handed draw-cut. She steps forward, draws the tachi from her left hip and cuts in one wide horizontal arc at chest height, then flicks the blade and resheathes it.
Draw the blade LONG: from the guard to the tip it is about as long as from her shoulder to her feet. Keep this blade length in every frame.
NO scarf, NO slash trail, NO lightning, NO motion lines – just her and the sword. Same size and ground line in every frame.
Draw ONE frame per image. Start with frame 1 only.

Frame 1 (5m1): Ready stance, knees bent, weight on the back foot. Left hand holding the sheath at her left hip, right hand resting on the hilt. Calm, focused face.
Frame 2 (5m2): Coiling: she sinks lower and turns her shoulders away, both hands on the hilt, the sheath tilted down behind her. Front foot just starting to lift for a step.
Frame 3 (5m3): Stepping in: big forward step, front foot landing far ahead. The blade is halfway out of the sheath, low by her hip, edge facing forward.
Frame 4 (5m4): THE CUT: long lunge, back leg straight, front knee bent. Both arms fully extended forward at chest height, the long blade pointing straight ahead and level, body stretched toward the opponent.
Frame 5 (5m5): Follow-through: the blade has swept past, arms crossed over to her left side, blade horizontal behind her shoulder line, torso twisted. Still in the lunge.
Frame 6 (5m6): Chiburi: she snaps the blade down and out to her right side to flick it clean, one hand on the hilt, the other back on the sheath. Weight starting to come back.
Frame 7 (5m7): Resheathing: stepping her front foot back, sliding the blade back into the sheath at her left hip, tip almost in.
Frame 8 (5m8): Back in the ready stance from frame 1, sword fully sheathed.
```

Then "Draw frame 2 only", and so on. Save as `5m1.png` – `5m8.png` in `actors/cecilia/_incoming/`. Eight drawings instead of six so it plays at the 2–3 game frames per drawing standard (the in-betweens in the smoothness table below are then not needed for 5C).

---

## Smoothness pass: in-between frames (Oct 20)

**Why it looks choppy:** BlazBlue normals use roughly 10–16 drawings, each on screen for only 2–3 game frames. Cecilia's use 4–7, and some are held for 5–11 frames, so at 60 FPS the pose visibly jumps. Her hit and block reactions are a single drawing each. More drawings is the real fix; once they arrive, Claude retimes every move to 2–3 frames per drawing and keeps startup, active and recovery the same.

**How to ask:** in the same chat as the move, attach the two frames on either side and say: `Draw the in-between pose exactly halfway between these two frames. Same character, same size, same ground line.` Name it after the earlier frame plus `b` (and `c` for a second one): the in-between of `5b2` and `5b3` is `5b2b.png`.

| Priority | Move | Add | Between |
| --- | --- | --- | --- |
| 1 | Hit reactions | `hurt_gweak2-3`, `hurt_gstrong2-4`, `hurt_cr2-3`, `hurt_aweak2-3`, `hurt_astrong2-3` | Snap back → most bent → starting to recover |
| 1 | Blocks | `blocking1b`, `blocking2b`, `blocking3b` | Guard pose pushed back slightly, sheath braced |
| 2 | 5C | – | covered by the 8-frame 5C redo above |
| 2 | 5B | 3 | 5b1→5b2, 5b2→5b3, 5b5→5b6 |
| 2 | 2C | 3 | 2m1→2m2, 2m2→2m3, 2m5→2m6 |
| 2 | 2B | 3 | 2s1→2s2, 2s2→2s3, 2s4→2s5 |
| 2 | j.C | 3 | j5m1→j5m2, j5m2→j5m3, j5m4→j5m5 |
| 3 | 5A, 2A, 4A, j.A | 2 each | Wind-up → hit, and hit → recovery |
| 3 | Crouch | `stand2duck_b`, `duck2stand_b` | Halfway down / halfway up |
| 3 | Air dashes | 2 each | Launch → full speed |

About 40 drawings for the whole set; the priority-1 rows alone (about 15) fix the stiffest-looking moments.

**Received:** `hurt_gweak2`, `hurt_gweak3` (Oct 20, in game: impact → most bent, held through hitstun → recovering).

**Done in the engine without new art (Oct 20):**
- The fighter being hit shakes during hitstop (about 3 px on hit, 1.5 px on block), like BlazBlue. Works for every fighter.
- Her single-drawing hit and block reactions now snap back and lean on impact, hold, then ease upright (Offset + Rotation keys on the same drawing). Strong and air hits push harder.
- Heavy hits (hitstop 12+) shake the camera; blocked heavies shake less. `CameraShakeAction` now works too (`FighterCamera.Shake`).
- Afterimages: fading gold ghosts behind her on forward dash, backdash, all air dashes and the 2C slide (`AnimationData.Afterimages = true`; tint and count on the `AnimationViewer`). Needs a Build in Godot.
