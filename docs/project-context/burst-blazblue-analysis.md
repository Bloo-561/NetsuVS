# Burst: BlazBlue Central Fiction analysis (Nov 5)

Source: TamaDeez's 18 s training clip (Lambda-11 player vs Jin dummy set to Burst), read at 10 fps and 60 fps.

## What the clip shows
| Time | What happens |
|---|---|
| 2.4-3.7 s, 6.6-6.8 s | Training position resets (fade to black) |
| 5.8 s | Jin presses the button in neutral and gets **Overdrive**: a super flash, the fight freezes, the stage darkens, a cyan emblem appears and a 04:00 timer starts. Lambda is not pushed. |
| 8.42 s | Lambda hits Jin (300 damage) |
| 8.47-8.62 s | Jin flashes **solid green** for about 9 frames: the Burst tell. **The game does not freeze**, and Lambda keeps moving through her attack. |
| 8.63-8.70 s | Green and gold rings, then the gold explosion (about 13 frames after the press) |
| 8.78 s onward | Lambda is still in her attack, is hit, and flies to the left wall. Hard knockdown, back up at about 11.4 s. |
| 12.58 s | Lambda hits Jin again (600 damage) |
| 12.63-12.78 s | Same green tell |
| 12.82 s | Lambda's attack has finished, and she **blocks** the explosion (blue barrier streaks in front of her) and slides back a little. Jin recovers at about 13.4 s. |
| 15.5-17.6 s | Same as at 8.4 s: hit, flies to the wall, hard knockdown |

## The rules behind it
- **No freeze.** Neither fighter is frozen during the Burst.
- **About 13 frames to the hit**, with a visible tell. The tell is an observation; 13 frames is an estimate from the frames, not official frame data.
- **No guard rule.** You block it if your move has finished recovering by the time it hits. If you're still in an attack, you get hit.
- **On hit:** no damage, the attacker is blown full screen and stays knocked down.
- **On block:** small pushback, and the Burster is left recovering.
- The same button in neutral gives Overdrive. VS already works this way (A+C).

## Plan for VS (not built yet)
1. Remove the guard rule (the light-normal / jump / neutral check). Timing alone decides, as in BlazBlue.
2. Keep A: the attacker's hitstop ends when the Burst is pressed, so there is still no freeze.
3. Add about 8 frames of startup **before** the untouched Burst animation: she holds her hitstun pose, invincible. The hit then lands at about 12-13F instead of 5F. Without this, almost nothing recovers in 5 frames, so it can't be baited.
4. Optional: a green flash on her during that hold, like BlazBlue's tell. This would be a new tint, not a change to the Burst effect.
5. Keep B: a blocked Burst loses invincibility when it stops hitting and can be punished.
6. Optional: on hit, a longer hard knockdown, closer to BlazBlue's (about 2.5 s).
