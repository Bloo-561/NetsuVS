# Versus flow

Main menu **VERSUS** -> Game Settings -> Side Select -> Character Select (fighter, then color) -> Stage Select -> VS screen -> fight.
All of it before the character select happens inside the main menu: Cecilia steps aside like she does for Options.

## 1. Game Settings (sheet inside the main menu)

`scenes/options/options_menu.gd`, page `"versus"` (`_list_rows()`): **Start Game**, Rounds to Win, Round Time,
CPU Difficulty, Character Intros, Restore Default (just these rows), Return. Values are the same ones as
Options > Game Settings (GameSettings autoload). Start Game emits `start_game`; the main menu then opens the side select.

## 2. Side Select

`scenes/versus/device_select.gd`. Controller 1, Controller 2, Keyboard 1, Keyboard 2 sit in the middle.
Each player moves **their own** device with left / right (keyboards use their battle keys or the menu keys,
controllers the D-pad / stick). One device per side; an empty side is the **CPU**.
A on a device that is on a side starts; B moves it back to the middle, B in the middle returns to Game Settings.
Unplugged controllers are greyed out ("not connected").

Result: `Controls.assign_sides(p1_device, p2_device)` - from then on the device on the Player 1 side drives
`p1_*` actions, so the engine needs no changes (its players use device 0 = `p1_*`, 1 = `p2_*`, -1 = CPU).
`MatchSetup.humans` = [side 1 is a person, side 2 is a person]. The main menu calls `Controls.clear_sides()`
when you come back to it, so menus and Training use the normal layout again.

## 3. Character Select

`scenes/character_select/character_select.gd`

- Pick a fighter with A, then a **color** with left / right (A to lock, B back to the fighter).
  The small fighter standing on the ring in front of each render is the real in-game sprite with that
  color's material: it reads the `Graphics/Mesh/Sprite` node of the color's fighter scene
  (`ColorPalettes[n].ScenePath` in `data/roster.tres`) and plays the `idle1.png, idle2.png ...` frames from the
  same folder - new fighters/colors work automatically. Since Oct 24 the roster only names each colour's scene
  (it used to load every fighter as the game started); the screen starts loading every fighter in the background as
  it opens, and keeps the two picked ones loaded for the fight. Position/size: `preview_feet`, `preview_scale` in the Inspector.
- A person next to a CPU side picks the CPU's fighter and color after their own (works with the CPU on either side).
- Same fighter on both sides can't wear the same color (the taken one is skipped).
- **A+B macro** (RB / U by default) opens Button Settings, **B+C macro** (RT / O) opens Keyboard Settings -
  the same pages as Options, over the select screen.
- **Music:** "Battle in the Moonlight" (`assets/audio/music/netsu/battle_in_the_moonlight.mp3`) loops on the BGM bus. It keeps playing into stage select (and isn't restarted when you come back from it); the battle starts its own track. Change the song with `THEME_PATH` at the top of `character_select.gd`.
- Training is unchanged: Player 2 joins by pressing A, otherwise Player 1 picks the dummy.

Colors are passed on through `MatchSetup.choose_stage(..., p1_color, p2_color)` to `P1SelectedColor` / `P2SelectedColor`.

## 4. VS screen (after the stage select)

`scenes/vs_screen/vs_screen.gd` (Oct 24): the two fighters, their assists, the stage and the song while the fight
loads in the background; fades into the fight after the jingle (A skips once it's loaded). Training skips it.
Full map: `docs/vs_screen.md`.

## Not included

Battle Menu and Rematch Limit from the Melty Blood screen (no matching engine feature yet), Watch / Replay.
