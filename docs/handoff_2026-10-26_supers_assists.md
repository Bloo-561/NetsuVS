# Handoff — Oct 26 2026, night (TamaDeez: super inputs, slower assists, Eren 6S, Harie 6S, more HP)

**Build first** (`NetsuAssist.cs` changed). Godot picks up the new Harie states by itself.

## Supers: 236 + B+C and 214 + B+C only
236236 / 214214 + a button no longer do supers (too easy to get by accident). The two shared inputs
`actors/_shared/sakuga/Inputs/49_Input_236236.tres` and `50_Input_214214.tres` now hold exactly what
`25_Input_236BC` / `48_Input_214BC` do, so every super that used them (Cecilia's Thunder Plunge and counter super,
Noah's Raging Storm and God Press) now takes 236 + B+C / 214 + B+C, like Flan's and Leticia's already did. Command
lists updated.

## Assists come out slower (all of them)
Pressing S still pays / starts the pose at once, but the assist appears **12 frames later** (0.2 s); for an Assist
Cancel or a call from blockstun **6 frames** later, so cancels still combo. If your fighter is hit or grabbed during
that wait, the call is lost and the gauge starts refilling. Numbers: `NetsuAssist.NetsuCallDelay` /
`NetsuCancelDelay`. Saved for rollback (`NetsuAssistState` keys 13 / 14).

## Eren 6S (Falling Spin)
- **10 more frames** in his crouch before the jump (on top of the 12 above).
- **Jumps a set distance** (about 3.9 m forward, 6 m/s) instead of aiming at the opponent. He only turns around on
  landing if he actually passed them, then does the double slash toward them.
Files: `actors/assists/eren/States/3_ERN_6S.tres`, `4_ERN_6S_land.tres`, `AnimationData/3_ERN_6S_AnimData.tres`.

## Harie 6S (Swimming Wave)
**Three passes**, faster: across (12.5 m/s, was 7.5), turns ~3 m past the opponent and swims back, turns again and
swims across a third time. Passes 1 and 2 hit once each (hitstun 50, was 26, so the next pass still catches them);
if pass 3 hits, it carries them (3 hits, now 11 m/s) and the last hit launches as before.
New states `6_HRE_6S_back` / `7_HRE_6S_last` (added to `0_HRE_Data.tres`).

## More health (+40%)
Cecilia 10000 → 14000, Leticia 10000 → 14000, Noah 10000 → 14000, Flan 11000 → 15400 (`MaxHealth` in each
`0_<TAG>_Data.tres`).

## Testing checklist
1. Build. 236236 + C / 214214 + C: no super (236C / 214C EX instead). 236 + B+C / 214 + B+C: supers.
2. S in neutral: a short beat before the assist shows up. Get hit right after pressing S: no assist, gauge refills.
3. Assist Cancel from a normal on hit still combos.
4. Eren 6S at close and far range: same jump length every time.
5. Harie 6S: three passes, the third launches.
6. Rounds last longer.

## Backups
`_backup_stage_select/pre_push_oct26_supers_assists.zip`.
