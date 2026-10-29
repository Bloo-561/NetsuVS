# NetsuVS default controls

Buttons follow Dengeki Bunko Fighting Climax: **A / B / C** attacks, **S** support (assist), plus macro buttons.
To change any of these, edit the tables at the top of `game/autoloads/controls.gd`.

| Button | P1 keyboard | P2 keyboard | Controller (Xbox / PlayStation) |
|---|---|---|---|
| Move | W A S D | Arrow keys | D-pad or left stick |
| A (light) | J | Numpad 4 | X / Square |
| B (medium) | K | Numpad 5 | Y / Triangle |
| C (heavy) | L | Numpad 6 | B / Circle |
| S (support) | I | Numpad 8 | A / Cross |
| A+B macro | U | Numpad 7 | RB / R1 |
| B+C macro | O | Numpad 9 | RT / R2 |
| A+B+C macro | P | Numpad + | LB / L1 |
| Start | Enter | Numpad Enter | Start / Options |

Controller 1 is always Player 1 and controller 2 is Player 2 (a "press Start to join" screen can change this later).

**Menus** (main menu, pause menu, and "press a button" on the win screen) work on **both controllers**:
| | Keyboard | Controller (Xbox / PlayStation) |
|---|---|---|
| Move | Arrows, WASD | D-pad or left stick |
| Confirm | Enter, Space, J, I, Numpad 4 / 8 | X / Square, A / Cross, Start (our A, S, Start) |
| Back | Escape, Backspace, K, L, Numpad 5 / 6 | Y / Triangle, B / Circle, Back / Select (our B, C) |
Character select and stage select follow the same rule (A, S or Start to pick, B or C to go back).

**Anywhere:** Alt+Enter or F11 toggles fullscreen.

**Training mode shortcuts** (Oct 24, any keyboard or controller; `TRAINING_SHORTCUTS` in `game/autoloads/controls.gd`):
| | Keyboard | Controller |
|---|---|---|
| Reset positions (hold left / right: corner, down: swap sides) | Q | Back / Select |
| Record the dummy (again = stop) | R | Left stick click (L3) |
| Play the recording (again = stop) | T | Right stick click (R3) |
Details: `docs/training.md`.

## For programmers
- Menu buttons live in `MENU_KEYS` (keyboard) and `MENU_PAD` (controllers) in `game/autoloads/controls.gd`. They feed Godot's `ui_accept`, `ui_cancel`, `ui_up`... actions.
- Actions are named `p1_a`, `p2_start`, etc. and are created by code, so they don't appear in Project Settings > Input Map.
- `Controls.get_frame_input(player)` returns everything a player is holding as one number (bits). This is what rollback netcode will send each frame. Opposite directions cancel out, and macros set several bits at once.

## Rebinding in game

Players can now change keys and controller buttons in **Options** (see `docs/options.md`). The tables in `game/autoloads/controls.gd` are the defaults that "Restore Default" goes back to; the players' layouts are saved in `user://settings.cfg`.
