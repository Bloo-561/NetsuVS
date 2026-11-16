# Handoff Nov 7 2026 (later): Netsu Link gauge

Builds on `claude/handoff-2026-11-07-link-chase.md`. Spec: "Netsu Link: Design & Implementation Spec" doc (three rules).
**C# changed: Build in Godot before testing.** Not compiled or played: no C# compiler or parser was available,
checked by hand only.

Backups: `_backup_stage_select/pre_link_gauge_nov07/` (SakugaActor.cs, NetsuAssist.cs, NetsuAssistState.cs,
match_setup.gd, netsu_hud.gd, NetsuOnline.cs as they were after the Link Chase batch).
Online version now `netsu-vs-online-10`.

## What's in
- **One Link Gauge per player, Level 1-3, kept for the whole match** (not reset between rounds; a new match makes a
  new NetsuAssist, so it starts at Level 1). Training position resets don't clear it either.
- **Teamwork fills it (100 per hit):**
  - the assist's hit (or its projectile's) landing while the opponent was already in hitstun = "COMBO ASSIST";
  - your fighter's hit (or projectile's) while the assist's buff is on = "ENCORE HIT" (Mary);
  - your fighter's hit while the assist is on screen = "SHIELD PUSH" (Adin), "TRAP SET" (Harie), "SIDE BY SIDE"
    (Eren), "TEAMWORK" (others).
  - Blocked hits, damage taken and meter fill nothing.
- **Levels:** 1000 fill for Level 2 (~10 hits), then 2000 more for Level 3 (~20). "LINK UP! LV n" and a flash of the card.
- **Losing a round:** at the next round's start, the loser gets 50% of their current level's need ("BOND TIGHTENS").
  Double K.O. and draws give nothing.
- **Level 2:** assist cooldowns x0.8 (on each call) **and the Link Chase unlocks** (it needs Level 2 now).
- **Level 3:** reached and shown, but the **Combo Craft isn't built yet**: no reward at Level 3 so far.
- **HUD (assist card):** three diamond pips on the card's top edge (lit = levels reached), a thin cyan bar just above the
  card (fill to the next level; full at Level 3), popup tags rising above the card, the card outline flashes cyan on a
  level up.

## Files
| What | Where |
| --- | --- |
| Gauge, fill, levels, round bonus, L2 cooldown, Chase gate | `engine/sakuga/Components/NetsuAssist.cs`: constants `LinkNeedLevel2` 1000, `LinkNeedLevel3` 2000, `LinkFillPerHit` 100, `LinkRoundLossPercent` 50, `LinkCooldownPercent` 80, `ChaseNeedsLinkLevel` 2; `NetsuLinkLevel`, `NetsuLinkFill`; `AddLink`, `NetsuTeamworkHit`, `NetsuLinkRoundBonus` (called from `ResetRound`); `Call` (cooldown) |
| The teamwork check | `engine/sakuga/Components/SakugaActor.cs` `BaseDamage`, hit branch: was the target in HIT_REACTION before the hit, then `root.NetsuAssist.NetsuTeamworkHit(this, wasComboed)` |
| Rollback | `GameState/NetsuAssistState.cs` keys 25-29 |
| HUD | `match_setup.gd` `netsu_assist_hud(..., link_level, link_fill, link_event, link_seq)` → `netsu_hud.gd` `_draw_assist` (pips, bar, popup), `_link_text` (popup words), `_process` (new events; a rollback replay isn't shown twice) |

## Test plan
1. Training, any fighter + Eren. Call Eren (6S or 5S), hit the dummy while he's out or juggle into his hits: tags pop,
   the bar fills. ~10 hits → LV 2 (two pips).
2. At Level 2: 6C, S → Link Chase (it doesn't come out at Level 1). Cooldown badge should read about 20% less.
3. Versus: lose a round on purpose → next round starts with half a level more.
4. Mary: 5S buff, then hit → "ENCORE HIT".

## Knobs / next
- Per-assist fill (spec: "only per-assist numbers are cooldown and fill per hit"): today one constant for all.
- Combo Craft (Level 3, 214 + S, 3 bars, back to Level 2).
- Call lines (speech box) and the "P1/P2" tag from the spec's Showing the bond: not built yet.
- The old Overdrive "Link" fields (`LinkReady`, `LinkCall`) are still there with their old names.
