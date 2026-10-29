# Handoff, Oct 28 2026 (night): Overdrive v2, damage, supers, grenades, charge, air dashes

**Needs a Godot Build** (C# changed). Originals: `_backup_stage_select/pre_oct28_b6/<path>.bak`.

## Overdrive (friend's proposal)
- **Activation:** automatic, once per round, the first frame a fighter is at **30% health or lower** and out of hitstun
  and blockstun. It lasts until the round ends.
- **CP bonus:** +1 Craft Gauge segment (2000) on activation, capped at the maximum.
- **Overdrive Link:** one Link. The next assist call made after activation gets **50% of its cooldown back** when that
  assist leaves. An assist already called before activation isn't refreshed. An unused Link ends with the round.
- **Damage taken:** -10% while active (`NetsuOverdriveTaken`; hits, chip and OTG hits).
- **Removed:** the old Overdrive bonuses (+20% damage, +30% meter) and the character extras (Flan's 236 wall bounce /
  214 ground bounce / 623 jump cancel in Overdrive; `SakugaParameters.OverdriveCharacterExtras = false` turns them
  back on). Burst and cancels are unchanged.
- **HUD:**
  - the portrait flashes white to red when Overdrive starts, and its rim glows red;
  - the Craft Gauge frame is brighter;
  - the health bar is red;
  - a small red / gold diamond by the assist icon shows while the Link is unused, or in use until the assist leaves.
- **Code:**
  - `SakugaParameters`: OverdriveHealthPercent 30, OverdriveGaugeBonus, OverdriveDamageTakenPercent 90,
    NetsuCheckOverdrive in Tick, cleared in Reset.
  - `NetsuAssist`: LinkReady / LinkCall.
  - Rollback: ParametersState keys 10-11, NetsuAssistState keys 16-17.

## Damage
- **Scaling** already existed: each hit takes its DamageScalingSubtract off the combo's scaling, from 100% down to 15%.
- **New: same-move damage proration.** Using the same move again in one combo also cuts damage (on top of the untech
  cut from earlier today):

  | Use in the combo | Damage |
  |---|---|
  | 2nd | 85% |
  | 3rd | 65% |
  | 4th and later | 45% |

  Code: `SakugaActor.NetsuRepeatDamagePercent`.
- **Supers:** the raw damage of each super was scaled so that, from a fresh combo, it does 2 x the fighter's strongest
  EX x 1.1 (worked out with the scaling and the 150% super bonus). Supers are only ever raised, never lowered.

  | Fighter | Strongest EX (fresh) | Target | Changes |
  |---|---|---|---|
  | Cecilia | 2938 (214C + rush) | 6464 | Sakura Morning Moon x1.72, Raijin x1.72, Raijin air x1.56 |
  | Flan | 2383 (Spiral Star) | 5243 | Radiant Breaker x1.28, Big Bang Crash x1.10 |
  | Leticia | 1840 (Comet Burst) | 4048 | Stardrive Cannon x2.02, Crimson Waltz x1.15 |
  | Noah | 2104 (Void Devour) | 4629 | Raging Storm x1.08; God Press already 4804 (unchanged) |

  - Noah's Umbral Wall / Twin Horizon and Leticia's EX grenades are projectiles and weren't counted.
  - The frame-data sheets still show the old damage until rebuilt.

## Leticia grenades: no hard knockdown
- New hitbox flag `NetsuSoftKnockdown`: the hit always gives plain hitstun, even in a juggle, so the victim can tech in
  the air or on landing.
- Set on `LFR_Contact_A/B/C` (grenade hits) and `LFR_Blast_A/B/C` (explosions).

## Charged j.C (Leticia)
- **Before:** holding B/C at j.C frame 8 (about 8 frames after the press) was enough, so a normal tap charged it.
- **Now:** the charged state also needs the button **still held through its own first 8 frames** (17 frames in all,
  about 0.28 s). Let go before that and she goes back to the normal j.C at its frame 9.
- No other charge moves (HoldA / HoldB_or_C) were found.

## Air dashes
- **Forward (Assault):** a lower hop that peaks about 0.75 m above where it started (rise 14f, up gravity 275000, down
  gravity 446000, X 48000).
  - The standing pushbox is 0.9 m tall, so a low dash runs into a standing opponent instead of crossing.
  - The crouching pushbox is 0.6 m tall, so she clears a crouching one.
- **Back:** now a stall. It drifts back 8000 (about 0.4 m in all), rises 15000 with light gravity 75000 for 12f, then
  falls at 300000.
