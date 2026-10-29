# Flan Returna – Animation Brief v1

Oct 18, 2026 · First brief: everything she needs to be playable, in the order to draw it.

Flan is the close-range brawler: she walks forward behind armored, charged punches and makes the opponent feel trapped. Her gauntlets do all the work, so **her fists are the focus of every attack frame**. She doesn't use weapons, and she rarely leaves the ground.

## How to use this with ChatGPT

1. Start a new ChatGPT chat and attach two references:
   - her full-body render (the fighting-stance picture);
   - one of Cecilia's finished in-game sprites (`actors/cecilia/Sprites/idle1.png`), for size, angle and pixel style.
2. Paste the **master prompt** below once.
3. Paste one move block, then ask for **one frame per image**: "Draw frame 1 only", then "Draw frame 2", and so on. If you ask for a whole strip at once, keep the frames apart with space around each one (strips where frames touch have to be cut apart by hand).
4. Save each image with the **file name listed** (for example `idle1.png`).
5. Drop the frames in `actors/flan/_incoming/` and tell Claude. Claude removes the background, lines up her feet, scales her to match and builds the move.

**Master prompt (paste once per chat):**

```
You are drawing animation frames for a 2D fighting game sprite. The attached images are the character, Flan Returna. Keep her design EXACTLY the same in every frame:
- Petite, youthful build, a little shorter than an average adult woman.
- Short, slightly messy brown bob hair. Teal-green eyes.
- Black beret with a gold band and a small gold cross pin on the right side; a small gold star hairclip on her bangs.
- Black short-sleeved top with a high collar, gold trim and a gold cross down the front.
- Cropped white vest with gold trim and small gold crosses on the chest.
- Wide gold belt with a star buckle; a white tabard panel hanging down the front with a big gold cross.
- Black skirt with a gold ruffled hem, black bike shorts underneath.
- White armored gauntlets covering her hands and forearms, gold trim, black knuckle plates.
- Black knee-high armored boots with gold cuffs and gold trim, white shoes.
She is a bare-knuckle brawler: boxer-like stance, fists up, weight forward. She is cheerful, confident and a little reckless: an open-mouthed grin when she attacks, a big smile when she wins. Every punch is heavy and committed.

Style: crisp high-resolution anime pixel art, the same style, angle and size as the attached in-game sprite, with clean dark outlines and the colors of her render.

Rules for EVERY frame:
- Full body visible, head to toe, nothing cropped. Leave empty space around her.
- She faces RIGHT, in a side-on fighting-game view.
- Feet planted on one flat, invisible ground line (unless the frame is in the air).
- Plain transparent background. If you can't do transparency, use flat pure green (#00FF00).
- No ground shadow, no text, no UI, no border.
- No glows, stars, sparks or light effects unless the frame description asks for them.
- One single pose per image.
```

**Effect colors (use these words whenever a frame asks for an effect):**

| Effect | Description |
| --- | --- |
| Star | Small gold-yellow star sparkles and a warm gold glow (her Constellation power) |
| Polaris | Bright blue-white light gathering around the gauntlet (charged punches) |
| Holy | A thin gold halo ring of light (her shield) |
| Stigmata | Emerald-green light, wings and fists of green energy (her install) |

**Reading the frame lists:** each row is one image. **Hit** marks the frame where the attack connects, which is the pose that matters most. Optional frames can be skipped; the game reuses a neighbour.

**Suggested order:**
1. Movement: stance, walk, crouch, jump, land, block.
2. Hit reactions.
3. Normals (5A, 5B, 2A, 2B first: they're her basic combo).
4. 5C charge punch and the specials.
5. Throw and command grab.
6. S-Crafts.
7. Intro and victory.

---

## 1. Movement

She walks steadily and doesn't really dash: her "dash" is a short, heavy hop forward.

| File | Pose |
| --- | --- |
| `idle1.png` – `idle8.png` | Fighting stance from her render: fists up at chin and chest height, weight forward, knees bent. A slow bounce on her toes across the 8 frames, shoulders rising and falling. |
| `walk f1.png` – `walk f8.png` | Walking forward, a steady boxer's step: fists stay up, front foot steps, back foot follows. One full step cycle over 8 frames. |
| `walking b1.png` – `walking b7.png` | Walking backward carefully, same guard, back foot steps first. One cycle over 7 frames. |
| `stand2duck.png` | Halfway down into a crouch, guard still up. |
| `duck2stand.png` | Crouching: low and compact, knees deeply bent, fists in front of her face. |
| `crouch_exit.png` | Rising from the crouch, halfway up. |
| `jump_n1.png` – `jump_n3.png` | Neutral jump: 1 knees bending to push off, 2 leaving the ground, 3 rising with knees tucked and fists up. |
| `jump_f1.png` – `jump_f5.png` | Forward jump: a tucked forward somersault, one rotation over 5 frames. |
| `jump_b1.png` – `jump_b5.png` | Backward jump: a tucked backward somersault, one rotation over 5 frames. |
| `jump8.png` – `jump10.png` | Falling: legs coming down, fists up, preparing to land. |
| `land1.png` – `land3.png` | Landing: 1 impact with knees bent low, 2 rising, 3 back to stance. |
| `dash f1.png` – `dash f4.png` | Forward hop: a short heavy hop forward with the guard up. 1 crouch, 2 hop, 3 in the air, 4 landing. |
| `dash b1.png` – `dash b4.png` | Backdash: a quick hop backward, guard up. 1 push off, 2–3 in the air, 4 landing. |
| `blocking1.png` – `blocking3.png` | 1 standing block, both gauntlets crossed in front of her face; 2 crouching block, gauntlets crossed low; 3 air block, knees tucked behind crossed gauntlets. |

## 2. Hit reactions

| File | Pose |
| --- | --- |
| `hurt_gweak.png` | Standing, hit lightly: head snapped back, guard broken. |
| `hurt_gstrong.png` | Standing, hit hard: bent forward from a body blow. |
| `hurt_cr.png` | Crouching, hit. |
| `hurt_aweak.png`, `hurt_astrong.png` | Hit in the air: light (arms flung up) and heavy (body arched backward). |
| `hurt_airtofall.png` | Tumbling in the air, starting to fall. |
| `hurt_fall1.png`, `hurt_fall2.png` | Falling toward the ground, flat on her back, arms loose. |
| `hurt_down.png` | Lying flat on her back on the ground. |
| `hurt_kd.png` | Knocked down: slammed onto the ground, bouncing slightly. |
| `hurt_kdspin1.png` – `hurt_kdspin4.png` | Spinning knockdown through the air (one horizontal spin). |
| `hurt_gbounce1.png`, `hurt_gbounce2.png` | Bouncing off the ground: 1 impact, 2 popped back up into the air. |
| `hurt_wbounce.png` | Slammed against a wall, back flat on it. |
| `hurt_recovery1.png`, `hurt_recovery2.png` | Air recovery: a quick flip back onto her feet, fists up. |
| `otgroll1.png` – `otgroll3.png` | Rolling backward on the ground to get up. |
| `hurt_getup1.png` – `hurt_getup3.png` | Standing back up from lying down, ending in her stance. |
| `hurt_ko.png` | Knocked out: lying on her back, eyes closed (swirly eyes are fine). |

## 3. Normals

A = jab, B = straight / kick, C = heavy, chargeable punch.

### 5A – jab
| File | Pose |
| --- | --- |
| `5a1.png` | Stance, front fist starting forward. |
| `5a2.png` | **Hit**: quick front-hand jab at face height, arm fully out. |
| `5a3.png` | Fist coming back to her guard. |

### 5B – straight
| File | Pose |
| --- | --- |
| `5b1.png` | Rear shoulder pulled back, hips turning. |
| `5b2.png` | **Hit**: strong rear-hand straight at chest height, hips and back foot fully turned into the punch. |
| `5b3.png` | Arm still extended, slight follow-through. |
| `5b4.png` | Recovering to stance. |

### 5C – Guiding Star (hold C to charge)
Her signature: holding C charges the punch through 3 levels. The charge pose is called **Polaris Alignment**.

| File | Pose |
| --- | --- |
| `5c1.png` | Wind-up: rear fist pulled far back at her hip, front arm out for balance, low wide stance. |
| `5c_charge1.png`, `5c_charge2.png` | Charging (these two loop): same pose, body tensed, small **Polaris** blue-white light gathering around the rear gauntlet. Frame 2 slightly brighter. |
| `5c_charge3.png` | Fully charged: same pose, the gauntlet blazing with **Polaris** blue-white light and a few **Star** sparkles around it. |
| `5c2.png` | **Hit**: enormous straight punch at chest height, stepping deep forward, whole body behind it. No effects. |
| `5c2_gold.png` | Same pose as `5c2`, with a warm **Star** gold glow on the gauntlet (level 2). |
| `5c2_blue.png` | Same pose as `5c2`, with a burst of **Polaris** blue-white light and **Star** sparkles exploding off the fist (level 3). |
| `5c3.png` | Follow-through, arm extended, leaning forward. |
| `5c4.png` | Pulling back into stance. |

### 2A – crouching jab
| File | Pose |
| --- | --- |
| `2a1.png` | Crouching, front fist starting forward. |
| `2a2.png` | **Hit**: low jab at waist height from the crouch. |
| `2a3.png` | Fist back to guard. |

### 2B – low kick
| File | Pose |
| --- | --- |
| `2b1.png` | Crouching, front leg pulling in. |
| `2b2.png` | **Hit**: low kick along the ground at shin height with her armored boot, sole first. |
| `2b3.png` | Leg pulling back into the crouch. |

### 2C – sweep
| File | Pose |
| --- | --- |
| `2c1.png` | Low crouch, one hand on the ground, rear leg drawn in. |
| `2c2.png` | **Hit**: spinning leg sweep, leg fully extended along the floor. |
| `2c3.png` | Leg continuing round behind her. |
| `2c4.png` | Back to crouch. |

### Jumping A / B / C
| File | Pose |
| --- | --- |
| `j5a1.png` | In the air, knees tucked, fists up. |
| `j5a2.png` | **Hit** (j.A): knee strike forward, knee raised at chest height. |
| `j5a3.png` | Leg coming back down. |
| `j5b1.png` | In the air, rear fist pulled back. |
| `j5b2.png` | **Hit** (j.B): punch angled down and forward. |
| `j5b3.png` | Arm returning. |
| `j5c1.png` | In the air, both fists clasped together and raised high above her head. |
| `j5c2.png` | **Hit** (j.C): double-fist hammer smashing straight down in front of her. |
| `j5c3.png` | Follow-through, fists low in front of her knees. |

### 6B – overhead hammer (must be blocked standing)
| File | Pose |
| --- | --- |
| `6b1.png` | Small hop forward, rear fist raised high above her head. |
| `6b2.png` | **Hit**: hammer-fist swinging straight down in front of her at head height, landing on her front foot. |
| `6b3.png` | Fist low after the swing. |
| `6b4.png` | Back to stance. |

## 4. Throw and command grab

| File | Pose |
| --- | --- |
| `throw1.png` | Front hand reaching forward to grab a collar at chest height. |
| `throw2.png` | Grabbing (fist closed on nothing at chest height, pulling toward herself). |
| `throw3.png` | **Hit**: rear-hand body blow into the space in front of her stomach, still holding on. |
| `throw4.png` | Shoving forward with both hands to throw the opponent away. |

The opponent is not drawn in any frame: the game positions them.

## 5. Specials (Crafts)

### Shining Knuckle (236C) – charging straight
A dashing punch that can be held to charge (same 3 levels as 5C).

| File | Pose |
| --- | --- |
| `cr_knuckle_1.png` | Crouched low, rear fist pulled back at her hip, about to launch forward. |
| `cr_knuckle_2.png` | Charging: same pose with **Polaris** blue-white light gathering on the fist. |
| `cr_knuckle_3.png` | Lunging forward low and fast, body almost horizontal, fist still back. |
| `cr_knuckle_4.png` | **Hit**: full-body straight punch at the end of the lunge, a trail of **Star** gold sparkles behind her. |
| `cr_knuckle_5.png` | Skidding to a stop, arm extended. |
| `cr_knuckle_6.png` | Back to stance. |

### Holy Shield (214B) – parry stance → Stellar Strike
She braces behind her gauntlets. If she's hit during it, she counters with a blinding punch.

| File | Pose |
| --- | --- |
| `cr_shield_1.png` | Bracing: both gauntlets raised in front of her, feet planted, a **Holy** gold halo ring of light forming in front of her. |
| `cr_shield_2.png` | Holding: same pose, halo fully formed and bright. |
| `cr_shield_3.png` | Lowering the guard, halo fading (stance ended without a counter). |
| `cr_stellar_1.png` | Counter: stepping in through the shattering halo, rear fist pulled back. |
| `cr_stellar_2.png` | **Hit**: straight punch with a blinding white-gold flash bursting off the fist (Stellar Strike). |
| `cr_stellar_3.png` | Follow-through, flash fading, **Star** sparkles drifting. |

### Star Dipper (623B) – rising uppercut
Her anti-air. Invincible as she starts to rise.

| File | Pose |
| --- | --- |
| `cr_dipper_1.png` | Deep crouch, rear fist low by her knee. |
| `cr_dipper_2.png` | **Hit**: exploding upward, rising uppercut at head height, feet leaving the ground. |
| `cr_dipper_3.png` | **Hit**: high in the air, fist fully raised above her head, a trail of **Star** gold sparkles following the fist upward. |
| `cr_dipper_4.png` | Top of the jump, arm still up, body starting to turn. |
| `cr_dipper_5.png` | Falling back down, fists up. |
| `cr_dipper_6.png` | Landing in a crouch. |

### Iron Fist of Flan (41236C) – command grab body blow
Grabs at close range, punches through the guard, and blows the opponent away.

| File | Pose |
| --- | --- |
| `cr_iron_1.png` | Stepping forward, front hand reaching out to grab at chest height. |
| `cr_iron_2.png` | Grabbing and pulling in, rear fist cocked back. |
| `cr_iron_3.png` | **Hit**: crushing body blow into the space at stomach height, a gold **Star** burst at the fist. |
| `cr_iron_4.png` | **Hit**: second, bigger punch upward and forward, a large burst of **Star** light and sparkles (this one blows them away). |
| `cr_iron_5.png` | Follow-through, fist held out. |
| `cr_iron_6.png` | Back to stance with a satisfied grin. |

### Northern Cross (22C) – power-up (optional for now)
She stops to gain a Constellation star. Slow and risky, so it's a big pose.

| File | Pose |
| --- | --- |
| `cr_cross_1.png` | Standing tall, both gauntlets open and spread low to her sides. |
| `cr_cross_2.png` | A gold magic circle shaped like a cross and stars glowing on the ground under her, light rising around her. |
| `cr_cross_3.png` | Fists clenched at her chest, a bright **Star** sparkle bursting above her head. |

## 6. S-Crafts

### O' Stars, Seize the Divine Future! (236BC) – 2 bars
Her big finisher. A huge emerald crystal of starlight smashes down on the opponent.

| File | Pose |
| --- | --- |
| `cr_divine_1.png` | Super-flash pose: feet planted, one fist raised straight up to the sky, eyes shining, **Stigmata** green light swirling around the raised gauntlet. The game freezes on this frame. |
| `cr_divine_2.png` | Rushing forward low, fist back, green light trailing. |
| `cr_divine_3.png` | **Hit**: uppercut that launches, a column of green light rising from the fist. |
| `cr_divine_4.png` | Leaping up after them, both fists raised overhead, green light gathering into a giant shape above her. |
| `cr_divine_5.png` | **Hit**: bringing both fists down; drawn as just Flan in the pose (the crystal is a separate effect, below). |
| `cr_divine_6.png` | Landing with her back half-turned, grinning, fist raised in victory. |
| `fx_divine_crystal.png` | Effect only, no Flan: an enormous jagged emerald-green crystal made of light, glowing rings at its center. Drawn large, on its own image. |
| `cr_divine_cutin.png` (optional) | Close-up of her grinning face with green-glowing eyes, wide 16:9 banner, for a super cut-in. |

### Stigmata Install (214BC) – 2 bars
A timed power-up: green energy wings spread from her back and ghostly green fists (Stellar Fists) follow her attacks for extra damage. To keep it affordable, **she keeps her normal outfit**: the wings and fists are separate effect images the game layers over her normal sprites.

| File | Pose |
| --- | --- |
| `cr_install_1.png` | Super-flash pose: arms spread wide, head tilted back, eyes glowing **Stigmata** green, green light bursting out of her chest. The game freezes on this frame. |
| `cr_install_2.png` | Bringing her fists together in front of her, green energy wrapping around both gauntlets. |
| `cr_install_3.png` | Back to her stance, grinning, faint green glow on the gauntlets. |
| `fx_wings1.png`, `fx_wings2.png` | Effect only, no Flan: a pair of large feathered wings made of emerald-green light, seen from the side, spreading upward and back. Two frames that loop (a slight flap). |
| `fx_fist1.png` – `fx_fist3.png` | Effect only, no Flan: a translucent emerald-green energy fist the size of her gauntlet, punching forward. 1 appearing, 2 fully extended, 3 fading. |

## 7. Intro and victory

| File | Pose |
| --- | --- |
| `intro1.png` – `intro4.png` | Intro: 1 walking in, tapping her beret; 2 punching her fists together, small **Star** sparkles; 3 grinning; 4 dropping into her stance. |
| `win1.png` – `win3.png` | Victory: 1 fist pumped high in the air; 2 a big thumbs-up toward the camera with a wink; 3 holding the pose ("I'm pretty strong!"). |
