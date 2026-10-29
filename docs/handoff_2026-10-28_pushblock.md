# Handoff, Oct 28 2026: Pushblock is a real pushblock (no attack)

**Needs a Godot Build** (new C# action). Originals: `_backup_stage_select/pre_oct28_pushblock/<path>.bak`.

## What it does now
- A+B while blocking (standing or crouching, on the ground), 1 bar, as before.
- The defender **stays in the block pose** (stand or crouch) and the red ring plays. The attacker is pushed straight
  back about **1.6 m** over 10 frames (fast at first, then easing off). This is not a hit: no damage, no hitstun, and
  their attack just whiffs if they end up out of range.
- **Corner rule:** if the attacker is already at the wall, the defender slides back the rest instead.
- **Length:** 18 frames. The ring shows for the first 14. It's a guard state (Type 3, the same as blockstun), so
  holding back still blocks the next hit. Blockstun keeps running, so pushblock pushes you out but doesn't end
  blockstun early. Afterwards it goes to the block exit (50 standing / 55 crouching).
- **Gone:** the old version was an attack (the 5B pose, invincible to frame 7, a hitbox at frame 8 with 300 guard
  crush).

## Files (all four fighters)
- Engine: `engine/sakuga/Resources/FrameDataEvents/Actions/NetsuPushOpponentAction.cs` (Distance per frame; the
  corner rule).
- Standing: state `X_Breakthrough` (index 96, same uid) rewritten. It plays the new `X_Pushblock_Stand_AnimData`,
  which is the standing blockstun sprite plus the red ring.
- Crouching: new state `X_Pushblock_Crouch` (appended to States: CEC 119, FLN 112, LET 123, NOA 117) plus
  `X_Pushblock_Crouch_AnimData` (the crouch blockstun sprite plus the ring).
- Moves:
  - `X_Breakthrough` now only works from the standing guard states (`IsSequenceFromStates` 48-52).
  - A new move `X_Pushblock_Crouch` (same input, cost and name "Pushblock") works only from the crouching guard
    states (53-57). It was appended to `X_Stance_Main` Moves.
- `X_Breakthrough_AnimData.tres` is not used any more and was left in place.
- **Ring placement:** standing offset (-9, 43) at scale 0.85; crouching (3, -63) at scale 0.75. Both are centred on
  the blue seal.

## Not done
- Air pushblock: the move was ground-only before, and it still is.
- Projectiles aren't pushed, only the opponent.

## Test
1. Block a string standing, A+B: she stays in the block pose, the red ring appears and the attacker slides away. 1 bar.
2. Same while crouch-blocking: crouch pose, ring lower, same push.
3. Attacker in the corner: the defender slides back instead.
4. Pushblock, then the next hit: still blocked while holding back.
