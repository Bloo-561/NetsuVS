# Handoff — Oct 26 2026, afternoon (TamaDeez branch: freeze lock, pushback, Special > EX, assist cost, OTG)

**Build first:** C# changed. Open the project in Godot and press **Build** (hammer, top right) before playing.

From Tamaki's first test session. Everything is in the engine, so it works for every fighter (Cecilia, Flan, Leticia,
Noah) with no data or script changes; the move scripts in `tools/sprite_port/` don't need running again.

## 1. No inputs during the EX / super freeze
An EX move could be turned into a super before it even came out (236C, then B+C right after the freeze).
- While an EX / super flash has someone frozen, **neither player can input anything** (pause still works). Each
  side's last input is held (a held direction or button stays held), but nothing new is pressed and no motion can be
  done during the freeze (`GameManager.GameLoop`, `NetsuFlashFreeze()`). The CPU waits too.
- The kara window (a B+C press in the first 2 frames of a move replaces it) no longer applies out of an EX move or a
  super (`StanceManager.NetsuKaraWindow`): those first frames come right after the freeze.

## 2. Normals push back less
Ground normals' pushback, on hit and on block, is now **60%** of what their hitboxes say.
- One number: `NetsuNormalPushbackPercent` on the **GameManager** node in `scenes/battle/battle.tscn` (Inspector;
  100 = as before). "Normal" = the attacker's move costs no meter and has Priority 6 or less (5A...2C, 4A, 6C, jump
  normals hitting a standing opponent). Specials, EX, supers, assists and projectiles keep their own pushback.
- Engine: `SakugaActor.NetsuNormalPushback` (used by `HitDamage` and `BlockHit`).
- The frame data sheets still show the hitboxes' own (unscaled) pushback.

## 3. Special > EX cancel
Any special move (no meter, Priority 7-8) that **hit or was blocked** can be cancelled into **any EX move** (2 bars)
from the hit until the special ends, for every fighter (`StanceManager.NetsuSpecialToEx`). The move's own
`CanCancelTo` list is checked first, so its follow-ups and super cancels still win. Needs the 2 bars like any EX.

## 4. Assist Cancel costs 1 bar
Was 2 bars. `NetsuAssist.AssistCancelCost` = 2000 ("100%", Melty-style); the assist move list in the pause menu says
1 bar (`MatchSetup.ASSIST_CANCEL_BARS`). The CPU still only Assist-Cancels when it keeps 2 bars after paying.

## 5. OTG and invincible wake-up
Before: any attack hit someone lying on the ground and they flopped back down (the hit used the air reaction), over
and over.
- **OTG hits keep them down.** A hit that reaches a lying fighter (Hit_Knockdown, its slide / spin, Hit_Down) only does
  damage, hitstop and meter and counts in the combo: no new hit reaction, no pick-up, no knockback, and their down
  time doesn't start again. A KO from an OTG hit plays the KO from Hit_Down.
- **The OTG window:** they can be hit like that for **40 frames** after landing at full damage scaling. The more scaled
  the combo is, the shorter it gets (none at the minimum, 15%): `window = 40 × (scaling − 15) / 85`. Number:
  `NetsuOtgWindowFrames` on the GameManager node.
- **Invincible wake-up:** after the window, while still lying, and during the get-up (Hit_GetUp) and ground tech rolls
  (Recovery_Ground*, Recovery_OTG) they **can't be hit or thrown**.
- **Supers still connect:** a super (3 bars) can hit a lying fighter after the window, so supers that finish on the
  floor (Cecilia's air Thunder Plunge surge) keep all their hits. Moves with their own invincible frames are unchanged.
- Engine: `SakugaActor` (`NetsuLying`, `NetsuOtgWindow`, `NetsuOtgOpen`, `NetsuWakeInvincible`, `NetsuOtgHit`,
  `NetsuSuperOtg`; `ContainsFrameProperty` adds the immunity), `NetsuDownFrames` saved for rollback
  (`SakugaActorState` key 17). Hit_Down / Hit_GetUp are found at HitReactions[17] / [18] (the same for everyone).

## Not checked here
These changes were made without running the game (no Godot here): **Build**, then the checklist. If Build shows red
errors, the MSBuild tab has the details.

## Testing checklist
1. **Build.** Training, any fighter, 2+ bars: 236C, then mash B+C / do 236 + B+C during the freeze: the EX comes out
   and stays an EX. Pause during the freeze still opens the menu.
2. 5A, 5B, 2B on the dummy, on hit and with the dummy blocking: they stay closer than before.
3. A special on hit (Cecilia 236A, Flan 236A...) then 236C / 214C / 623C: the EX comes out; on whiff it doesn't.
4. Assist Cancel with exactly 1 bar works; with less it doesn't.
5. A sweep (2C) or a combo ending in a knockdown, then 2A / 2B on the downed dummy right away: hits, the dummy stays
   down. Wait about a second and try again: it whiffs. Long combo into knockdown: no OTG at all. The dummy getting up
   can't be hit (meaty) or thrown.
6. Cecilia air Thunder Plunge (6C > jump > air super): every hit still lands.
7. Online / rollback: the sync test if you run it (new saved value: `NetsuDownFrames`).

## Backups
`_backup_stage_select/pre_push_oct26_tama/` (every file this replaced, `.bak`).
