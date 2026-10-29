# Handoff — Oct 26 2026, evening (TamaDeez: systems)

**Build first:** C# changed. Press **Build** in Godot before playing.

Second batch of Tamaki's second list. Still to come: Flan (her moves and her Overdrive extras), menus & art, and the
hurtbox / hitbox pass for everyone.

## 1. OTG and knockdowns
- **OTG lasts longer:** 45 frames (was 40), and it stays full until the combo is down to 50% damage scaling (it used
  to start shrinking straight away, so in a real combo there was almost none). Then shorter, none at 15%.
- **Hard knockdowns are shorter:** a knockdown keeps them on the floor at most **50 frames** from landing (every
  knockdown was 76). Then they get up (invincible, as before).
- **Supers can't OTG:** a super's hits never connect on a fighter lying on the ground.
- Numbers: `NetsuOtgWindowFrames` / `NetsuDownTotalFrames` on the **GameManager** node (`scenes/battle/battle.tscn`).

## 2. Techs flash white
Teching (any air or ground recovery) flashes the fighter white for 10 frames (bright sprite + white edge).

## 3. Assist Cancel only on a real hit
An Assist Cancel needs the attack to have done damage: no Assist Cancel on a whiff or on block. (Calling from neutral
or in the air is unchanged.)

## 4. Throws cancel into EX, supers and Overdrive
Once the throw has hit (its Throw Forward / Throw Back state), its recovery can be cancelled into any EX move, super
or Overdrive whose input is done (with the gauge for it).

## 5. Overdrive (BlazBlue Central Fiction style), for everyone
- Same gauge as Burst (as before): use it for one or the other.
- **Length depends on health:** 4 s at full health, up to 10 s near zero (straight line in between).
- **No Burst against it:** anyone hit by a fighter in Overdrive can't Burst until that combo ends.
- **Activation:** the whole fight stops for 45 frames while she strikes her **win pose** and **glows**; nobody can input
  (then the usual short flash freeze). `NetsuOverdrivePauseFrames` on the GameManager node.
- **While it runs:** a **timer** (seconds left) next to her Burst gauge, and the stage is **tinted a little darker**
  (`overdrive_dim` on the NetsuSuperFlash node, made by the HUD).
- Flan's Overdrive extras (236 always wall bounces, 214 ground bounces, jump-cancel 623) come in her batch.

## 6. Mary's 6S
Mary and her note now face the way her caller faces (before: toward the opponent, so after a cross-up the note flew
the wrong way). `NetsuFaceCaller` on the move in `data/assist_list.tres` (and `face_caller` in `tools/sprite_port/assists.py`).

## Not checked here
No Godot here: Build, then the checklist. Rollback: two new saved values (`NetsuNoBurst`, the Overdrive drain).

## Testing checklist
1. Training: 2C (sweep) then 2A on the downed dummy at once: hits, dummy stays down. Long combo ending in a knockdown,
   then OTG: still works if the combo wasn't too long. The dummy gets up sooner than before.
2. A super on a lying dummy: whiffs.
3. Training > dummy air recovery / tech on: the dummy flashes white as it techs.
4. Assist Cancel: 5A whiffed then S → nothing; 5A on hit then S → the assist comes (1 bar).
5. Throw (B+C) then 236C / a super / A+B+C during its recovery: comes out.
6. Overdrive at full health: about 4 s on the timer; at low health: longer. Win pose + glow at the start, can't input.
   While in Overdrive, combo the dummy and try Burst with it (P2 / dummy): no Burst.
7. Mary 6S after jumping over the opponent: the note goes the way your fighter faces.

## Backups
`_backup_stage_select/pre_push_oct26_systems/` (every file this replaced, `.bak`).
