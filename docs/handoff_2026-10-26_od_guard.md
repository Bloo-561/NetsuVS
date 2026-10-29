# Handoff — Oct 26 2026, evening (TamaDeez: Overdrive in neutral, assist from blockstun)

**Build first** (`NetsuAssist.cs` changed).

1. **Overdrive in neutral:** A+B+C with a full Burst gauge now works standing, walking, crouching, dashing or in the
   air, not only as a cancel from a normal or a throw. The four `Moves/50_<TAG>_ExcelCancel.tres` files had
   `SkipCheck = true` (the move was skipped by the neutral check); now false.
2. **Assist from blockstun:** pressing S while blocking calls the assist like an Assist Cancel: no pose, the small
   flash, **1 bar**, no hit needed. The fighter keeps blocking. (`NetsuAssist.CallGuard`.)

Testing: Training, full Burst gauge, stand still and press A+B+C (win pose, Overdrive). Dummy set to attack (record a
string), block it and press S with 1 bar: the assist comes; with less than 1 bar it doesn't.

Backups: `_backup_stage_select/pre_push_oct26_od_guard/`.
