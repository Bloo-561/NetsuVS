# Handoff Nov 2 2026: Craft Gauge cap, EX Craft > S-Craft cancel

**C# changed: Build in Godot before testing.** Backup of every touched file: `_backup_stage_select/pre_meter_nov02/`.
Where `claude/game-systems.md` disagrees, this wins.

## Craft Gauge: 300% normally, 400% in Overdrive
- The gauge holds **3 bars (300%)** normally. When Overdrive starts (low health, once per round), the cap goes up to
  **4 bars (400%)** and the fighter gains **+1 bar (100%)** right away (`OverdriveGaugeBonus` 10000), as the comeback.
- New round: Overdrive ends, the cap drops back to 300% (a 4th bar kept from an Overdrive is lost).
- Engine: `SakugaParameters.CraftCapNormal` (30000), `NetsuCraftCap()` / `NetsuApplyCraftCap()` set
  `SuperGauge.MaxValue` (every gain and spend clamps to it). Called in Initialize, Reset (round start), every Tick, when
  Overdrive starts (before the bonus) and after a rollback load (`ParametersState`): the cap is worked out from
  `NetsuOverdriveOn`, so nothing new is saved. `DataContainer.MaxSuperGauge` (40000) is still the full 4-bar size.
- Training "max" Craft Gauge and auto-fill fill to the current cap (`NetsuTraining`, `GameManager`).
- HUD (`netsu_hud.gd`): still 4 cells; outside Overdrive the 4th is drawn locked (dark, hatched). `meter_normal_cap`
  export (30000).

## EX Craft > S-Craft cancel
- Any EX Craft that hit or was blocked can be cancelled into any S-Craft whose input is done, until the EX ends, for
  every fighter (`StanceManager.NetsuExToSuper`, after the move's own CanCancelTo list, the star cancel and Overdrive).
- The EX's 100% is already spent, so the S-Craft needs 300% left: with the 300% cap that means 400% in Overdrive. Outside
  Overdrive the most you can hold is 300%, so EX > S-Craft is an Overdrive-only combo in practice.
- Not yet tested in a match (no .NET build here); check in Training: Overdrive (low health), 400%, an EX then the S-Craft
  motion.
