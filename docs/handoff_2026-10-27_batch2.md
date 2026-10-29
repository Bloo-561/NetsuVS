# Handoff, Oct 27 2026: batch 2 (OTG, corner, specials, character changes)

**Needs a Godot Build** (C# changed). Originals: `_backup_stage_select/pre_oct27_c33/<path>.bak` (data files) and `pre_oct27_rules/` (engine).

## Engine
- OTG = hard knockdown: after the OTG window ends they get up at once, invulnerable, no input until get-up ends (`NetsuOtgGetUpMargin = 0`, `NetsuDownTotalFrames = 20`).
- Corner bug: `StanceManager.ExecuteMove` now clears knockback for non-normal moves, so MoveX/MoveY work in the corner (Noah 214B rise, Flan 214 jump).
- Counter hit with a special: +8 hitstun (on top of the normal counter bonus), no repeat penalty, no juggle decay, knockback x125%, bounce x150%. Exports on GameManager: `NetsuSpecialCounterExtraHitstun`, `...KnockbackPercent`, `...BouncePercent`.
- Stronger repeat proration: `NetsuRepeatNormalUntech` 3 -> 6, `NetsuRepeatSpecialUntech` 7 -> 12 (same move/strength only).

## Characters
- Flan: 236B lifts higher (Y 70000 -> 90000 ground, 60000 -> 80000 air). j.236 disabled (`UseOnAir = false` on move 65; list not shifted).
- Leticia: 214A = short beam (~45% length), 214B = full-screen straight beam (hold branch and zigzag removed), 214C unchanged (already straight). Sprite beam scale for 214A is 835; check it lines up with the hitbox.
- Cecilia: 214A or 214B dash, then A = palm strike (throw sprites), then C (or hold B) = slash-through to the other side. Slash-through: Duration 34 -> 62 (very unsafe on block), no restand, hit lifts (Y 30000, hitstun 36), sheathe sprites at the end. Counter hit uses the engine bonus above.
- Noah: j.214A already had 3 hits (grab 300, blast 900, recoil 400). Recoil hitstun 40 -> 58 so he recovers first.
- 6C: 10F startup, -12 on block for all four (xlsx edits).

## Test checklist
1. Hit, KO only below 0, OTG then immediate get-up.
2. Noah 214B and Flan 214 facing the corner.
3. Counter hit a special: more hitstun, bigger bounce.
4. Same special twice vs A then B: damage/juggle drops harder on the repeat.
5. Leticia 214A/B/C beam length and sprite match.
6. Cecilia 214A > A, 214A > C, 214B > C; block slash-through and punish.
7. Noah j.214A: can he block/act before the opponent after the recoil?

## Known gaps
- Frame-data xlsx sheets are stale for throws and burst; regenerate with `tools/frame_data/make_sheets.py`.
- Cecilia sheathe uses time-based sprites (also plays on block). A hit-only sheathe state would need a new state.
- Flan Stigmata walk sprites are parked, unused.
