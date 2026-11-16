# Handoff Nov 8 2026: Online menus rework + controller prompts + Cross confirms

**C# changed (NetsuOnline.cs): Build in Godot before testing.** Nothing was run (no Godot here); checked by hand only.
Backups: `_backup_stage_select/pre_online_menu_nov08/` (online_lobby.gd.bak = before everything today,
online_lobby.after_menu.gd.bak = after the menu-only pass, controls.gd.bak, netsu_prompt_bar.gd.bak, online_room.gd.bak,
NetsuOnline.cs.bak).

## 1. Cross (PS5) / A (Xbox) picks again on character select and stage select
The Link Break pad layout moved S to LB and made the bottom face button **D**; the select screens confirmed with A / S /
Start only. D was added: `character_select.gd _is_pick`, `stage_select.gd`, `Controls.device_pressed` ("confirm").

## 2. Button prompts follow the controller in use
- `Controls.prompt_style`: "kb", "xbox" or "ps" (the last thing pressed; PlayStation found by the joypad's name:
  ps5/ps4/dualsense/dualshock/sony/"wireless controller"). Signal `prompt_style_changed`. `PS_NAMES` (A->CROSS,
  LB->L1, LT->L2, START->OPTIONS...). `pad_name()` gives PlayStation names in "ps" (Options, lobby legend too).
- `NetsuPromptBar`: the letters in prompt strings are Xbox positions. PS: Cross / Circle / Square / Triangle drawn as
  shapes in their colours, L1 / R1 / L2 / R2 / OPTIONS pills. Xbox: coloured A / B / X / Y. Keyboard: A / B show
  player 1's keys (J / K). Every footer redraws by itself when another device is used.

## 3. ONLINE menu (first page)
Left list over a dark band, line globes, blue bar from the screen edge, values (NAME, SPECTATE ONLY) in a column.
Header "✦ ONLINE", no centred title.

## 4. CREATE LOBBY panel (right of the list, shown while CREATE LOBBY is selected)
A moves into it (cursor on Create Lobby: A, A opens the lobby). Rows: Host (your name, A edits), Players 2-8,
Rounds to Win 1-5, Round Time (GameSettings.ROUND_TIMES), Stage, Music, Comment (typed, 24 chars), Create Lobby.
Start = Create from any row, B = back to the list.
- Kept in `OnlineRoom.host_options` {"max", "rounds", "time", "comment"}; rounds also saved as Options' online rounds;
  stage / music as MatchSetup metas `online_stage` / `online_music` (as before).
- Room gets `"max"`, `"comment"`; rules rounds / time from host_options. `NetsuOnline.MaxPlayers` (new, C#) is set
  before Host(): `LobbyFull` uses it.

## 5. The lobby room (network-lobby layout)
- Top: the room table across the screen: ROOM, PLAYERS n/max, CODE, ROUNDS, TIME, STAGE, MUSIC, COMMENT.
- NEXT MATCH bar: "1P NAME · FIGHTER  VS  NAME · FIGHTER 2P", PICKING 42 / LIVE on the right.
- Players table: # (place in line), SIDE (1P / 2P), PLAYER (profile icon + fighter chip, name, title plate),
  FIGHTER (fighter + assist; others' assist only while picking / fighting), PING, WINS, STATUS. Your row lit with an edge.
- Right: LOBBY MENU (Up / Down, A): Change Character (SETUP; "Pick Your Fighter" on your turn), Ready / Cancel Ready,
  Pass, Watch the Match, Spectate Only ON/OFF, Invite / Lobby Code (host: invite screen; guest: copies the code),
  Leave / Close Lobby (twice). Unusable rows are dimmed and say why. Cursor goes to the first row when your pick
  phase starts (A, A = SETUP, Ready as before).
- MESSAGES under the menu (last 8 lines, wrapped). Shortcuts kept: AB pass, S spectate, C watch, Start invite, B leave.
- Header "✦ ONLINE LOBBY". SETUP overlay unchanged. `_test_vs` now reads the NEXT MATCH bar.
- Layout knobs: `ROOM_COLS`, `TABLE_COLS`, `TROW_*`, `CMD_*`, `MSG_RECT`, `CREATE_*` in online_lobby.gd.

## Test plan
1. Build. PS5 pad: main menu prompts show shapes; character select / stage select pick with Cross.
2. Touch the keyboard: prompts switch to J / K; Xbox pad: coloured letters.
3. Online > CREATE LOBBY: panel on the right; A, change Players to 2, Comment, Create. Room table shows 2 / 2 and the comment.
4. Second computer joins; a third is refused ("full"). Pick phase: A, A = SETUP, Ready. Menu rows, Pass, Leave twice.

## Gaps
- Message colours for this computer's own lines are gone (one Label now).
- Another player's assist isn't known outside a match (shown blank).
- Guests on an older version ignore max / comment (shown as 8 / None).
