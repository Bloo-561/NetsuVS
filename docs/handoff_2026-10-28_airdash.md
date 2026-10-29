# Handoff, Oct 28 2026: air dashes follow an Assault arc (Under Night)

**Data only, no Build.** Originals: `_backup_stage_select/pre_oct28_airdash/<path>.bak`.

All four fighters, `19_X_ForwardAirDashState` and `22_X_BackwardsAirDashState`. Before this, the dash was flat: no
gravity for 18 frames, then a fall.

- **Startup:** frames 0-3, she holds in place, the same as before.
- **Launch:** frame 4 sets X speed and an upward Y speed. Attacks are allowed from here, as before.
- **Arc:** gravity until the peak, then heavier gravity on the way down, so the fall is quicker than the rise (as in the
  reference video).
- **Landing:** she lands into 11 (normal landing) as soon as she touches the ground. If she's still airborne when the
  animation ends (40 frames), she goes to Falling with her speed kept.

| | X speed | up speed | rise | gravity up / down | peak above start | from ground level: lands at |
|---|---|---|---|---|---|---|
| forward | 48000 | 66700 | 18f | 222000 / 367000 | ~1.0 m | ~frame 36, ~2.5 m ahead |
| back | -36000 | 60000 | 16f | 225000 / 367000 | ~0.8 m | ~frame 33, ~1.7 m back |

- **Animations:** `12_X_AirDashFw_AnimData` and `14_X_AirDashBw_AnimData` Duration 22 -> 40 (the last pose holds).
- **Not changed:** 20 / 21 (they are the forward / down air jumps, not dashes).
