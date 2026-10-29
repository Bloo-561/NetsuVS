# Handoff — Oct 26 2026, night (TamaDeez: boxes, Burst, chains, assists, Cecilia / Leticia fixes, online rounds)

**Build first:** C# changed. Open the project (Godot imports Leticia's new 5C pieces by itself), then **Build**.

## Universal hurtboxes + attack boxes to the floor (all four fighters, engine)
`engine/sakuga/Collision/PhysicsBody.cs` (`NetsuBox`, `NetsuHurtScale`). Only the boxes the game uses change (what F10
shows too); the `.tres` files keep their drawn sizes.
- **Hurtboxes:** each fighter's hurtboxes are stretched / squashed up and down so her standing hurtbox is the same
  height for everyone (`NetsuUniversalHeight` = 14000, 1.4 m). Cecilia / Flan were 1.33 m, Leticia / Noah 1.46 m. A
  move that hits one of them standing hits all of them; crouching and air boxes get the same factor.
- **Attack boxes** reach from their top down to the fighter's feet (the floor when standing), same width. A box that
  must stay high: tick `NetsuKeepHeight` on it (none do yet). Assists and projectiles are unchanged.

## Burst
Was 3 m wide, active only 2 frames and blockable (a mid). Now **4.8 m wide x 4 m tall, active 8 frames, unblockable**
(`Hitboxes/100_Hitbox_Burst.tres`, `AnimationData/1001_*_Burst_AnimData.tres`, all four fighters).

## No looping normals
A normal can't be cancelled into again in the same chain: 5C > 2C > 5C is gone (5C > 2C still works). Cancelling a
light into itself (2A > 2A) still works. The chain resets when she's back in neutral, hit or blocking.
`StanceManager.NetsuChainBlocked`; saved for rollback (`SakugaActorState` key 20, `NetsuChainUsed`).

## Guard Cancel
There isn't one: the old Breakthrough (guard cancel) was already removed in v2. **Pushblock** (A+B while blocking,
1 bar, pushes away, no damage) and **assist from blockstun** (S while blocking, 1 bar) are still in.

## Assists
- **Every assist hit is a mid** (their projectiles too): blocked standing or crouching. Unblockables stay unblockable.
- **Blocked by the caller's side:** you block an assist (or its projectile, or any projectile) by holding away from
  the fighter who owns it, where she is when it connects, not from where the assist is.
`SakugaActor.BaseDamage`, `NetsuIsAssistHit`.

## Cecilia
- **Rework sprites now match her idle size.** Each new frame was measured against her idle (head size and body area)
  and corrected with the frame's `Scale` (0.78 to 1.08; 236C was drawn ~28% too big, the 5C swing ~12–15%, the throw
  and 236A/B ~7%). The hurt / hit boxes of those frames were scaled the same way.
- **5C no longer moves her forward** (`States/65_CEC_5C.tres`, MoveX 50000 → 0).
- **214C is the old EX Dash Slash** (the invincible dash that slashes through them again and again on hit): new state
  115 (`States/115_CEC_214C_DashSlash.tres`, its animation and `Hitboxes/120_Hitbox_214C_DashSlash_*`), move
  `Moves/68_CEC_214C.tres`. 236C stays the new slash barrage.

## Leticia 5C
Bigger: the two muzzle flashes are cut out of the 5C frames and drawn 1.8x (recovery frame 1.5x), and the hitbox
reaches ~1.75 m from her instead of ~1.25 m (`Hitboxes/7_Hitbox_5C_3.tres`). New pieces: `Sprites/v2/5c_2_body`,
`5c_2_fx1/2`, `5c_3_body`, `5c_3_fx1/2`.

## Online
Online matches are first to 2 by default, whatever Versus is set to (`GameSettings` "rounds_online"; the host's rules
still win). Done earlier, already on disk.

## Testing checklist
1. Build. F10 in training: hurtboxes of all four about the same height; attack boxes reach the floor.
2. Burst out of a long combo, from close and far (up to ~2.4 m): always hits, can't be blocked.
3. 5C > 2C > 5C: the last 5C doesn't come out. 2A > 2A > 2A still works.
4. Assist that hits low / overhead: blocks both standing and crouching. Assist from behind: hold away from the caller.
5. Cecilia: 5B / 5C / 236A-C / 214 / throw / j.C / counter super look the same size as idle; 5C stays in place; 214C
   is the dash slash (2 bars).
6. Leticia 5C: big flashes, hits from farther.
7. Rollback sync test if you run it (new saved value `NetsuChainUsed`).

## Backups
`_backup_stage_select/pre_push_oct26_boxes.zip` (every file this replaced).
