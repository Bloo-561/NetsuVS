extends Control
## ONLINE LOBBY  (Oct 24 2026; group lobbies, king of the hill: Oct 25; Nov 4: the room's new layout, PASS,
## SPECTATE ONLY, codes that can be typed on a keyboard; drawn with the Netsu UI kit like the other screens)
##
## Main menu > ONLINE. Play friends over the internet with rollback netcode, no server of our own:
##   CREATE LOBBY   this computer opens a lobby and shows a LOBBY CODE (5 digits, "48213"). Send it to your
##                  friends (C copies it). S shows the backup code (the long code below).
##   JOIN LOBBY     the code you were sent, typed (0-9, Backspace, Enter; Ctrl+V pastes) or picked digit by digit
##                  (Up / Down change the digit, Left / Right move, A joins, B goes back: controllers, and W A S D /
##                  the arrows on a keyboard). S or Tab (or typing a "."): a box for a backup code (K7Q2-M9X4-PA3D)
##                  or an address (192.168.1.20:7777).
##   SPECTATE ONLY  only watch: never put in line for a match (sent when you join; also changed in the room).
##   NAME           the name the others see (empty = "Player 2" and so on).
## The room (ONLINE LOBBY): the room bar (the host's lobby, its code); the next match in the 1P VS 2P panel (Player 1
## blue on the left, Player 2 crimson on the right) with the picks and the pick clock under the names; everyone in
## the lobby on the right, in line order (the number is the place in line, your row is lit; NOW PLAYING / PICKING /
## READY / WAITING / SPECTATING); the message panel (joins, leaves, results, passes, spectating: OnlineRoom.log_lines);
## the footer: what to do now, and the button prompts named after the keys / buttons of whatever was pressed last
## (keyboard 1, keyboard 2 or a controller: Controls.button_name), "J  READY     K  LEAVE".
##   KING OF THE HILL (the rules: game/autoloads/online_room.gd): everyone stands in one line; the first two fight
##   (king = player 1 side, challenger = player 2 side), the winner stays on, the loser goes to the back of the line.
##   SETUP (A, Nov 4): a quick menu over the room, like the training menu's rows: Fighter, Colour, Assist (anyone,
##   any time: saved as your setup, what you start with when your turn comes; shown in the room bar), Stage and Music
##   (the host's; the others see them, read only), and Ready during your pick phase (the menu opens on it: A, A =
##   ready). Up / Down = row, Left / Right = change, A = keep the changes (and close), B = close without them. The
##   room view itself changes nothing with the directions any more.
##   The two players have 60 seconds to pick (then what they have is locked in). Everyone else watches the fight: it
##   opens by itself (B there = back here; C here = watch again).
##   AB = PASS (when you're picking, or next in line): the next player waiting plays first; you go right behind them.
##   S (when not picking) = SPECTATE ONLY on / off. The host: Start = the invite screen with the codes (the host's
##   Options rules are used). B = leave (twice). None of these work while SETUP is open.
## PROFILES (Nov 4, CUSTOMIZE): each player's profile icon and title (Main Menu > CUSTOMIZE; sent with "hi", kept in the
## room's members: OnlineRoom.icon_of / title_of). The player list shows the icon (with a small chip of their fighter in
## its corner) and the title plate (NetsuTitlePlate) right of the name; the VS panel shows the icon with the fighter chip
## and the title under the name, and under each side only the fighter and the assist (stage / music: in SETUP).
## Typing (Nov 4): the code / name / reply code boxes read the keys themselves (_input), not a LineEdit. The game adds
## keys to Godot's ui_cancel (K, L, Backspace, Numpad 5 / 6) and ui_accept (J, I...), and a LineEdit stops editing
## on ui_cancel, checked before Backspace: Backspace (or a K) ended the typing, nothing typed after that went in, and
## Numpad 5 / 6 then went back to the menu. In a box, a key that types something types it; Enter / Esc / Backspace are
## the box's; only the rest (W A S D, J, K... on the digit picker; controllers) goes on to the page.
##
## The connection is the NetsuOnline autoload (engine/netcode/NetsuOnline.cs). The 5-digit code is looked up on
## a public message board (ntfy.sh), where the host posted its internet address (found with UPnP on the
## router, or a STUN server) and port (UDP 7777); a joiner posts its own there too, so both computers call
## each other at once (that gets through most home routers). Last resort: forward UDP port 7777 on the host's
## router. The long code (12 letters / numbers) holds the address itself: it's the backup, and the code
## shown when the board can't be reached; with it, a joiner that can't get through gets a REPLY CODE for the
## host to type in (S twice on the host's invite screen).
## Also accepted as a code: a plain address, "192.168.1.20:7777" (same network, port forwarding, testing).
## Docs: docs/online.md.

enum Page { MENU, HOST, JOIN, ROOM }

const MENU_ITEMS := [
	{"id": "host", "label": "CREATE LOBBY", "blurb": "Open a lobby on this computer and get a 5-digit code to send to your friends."},
	{"id": "join", "label": "JOIN LOBBY", "blurb": "Enter the 5-digit lobby code a friend sent you."},
	{"id": "spectate", "label": "SPECTATE ONLY", "blurb": ""},
	{"id": "name", "label": "NAME", "blurb": "The name the other players see in a lobby."},
	{"id": "back", "label": "BACK", "blurb": "Back to the main menu."},
]
const CODE_DIGITS := 5
## What a backup code / address / reply code box takes (letters are made capitals).
const CODE_CHARS := "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-.: "
const LEAVE_SECONDS := 2.0
const NOTE_SECONDS := 3.5

# --- The room's layout (screen pixels) ------------------------------------------------------------------------
const ROOM_BAR := Rect2(100, 190, 1110, 50)     # the host's lobby and its code
const VS_RECT := Rect2(100, 256, 1110, 344)     # 1P VS 2P, the picks, the pick clock
const LOG_RECT := Rect2(100, 618, 1110, 306)    # the room's messages
const LIST_RECT := Rect2(1250, 190, 570, 734)   # everyone in the lobby
const ROW_Y := 240.0
const ROW_STEP := 84.0
const ROW_H := 76.0
const LIST_PLATE := Vector2(214, 30)   # the title plate in the player list
const VS_PLATE := Vector2(282, 36)     # ... and under the names in the VS panel
const SLOT_W := 124.0           # JOIN: the digit boxes
const SLOT_H := 140.0
const SLOT_GAP := 26.0
const SLOT_Y := 336.0

# --- Colours (NetsuUI's palette) --------------------------------------------------------------------------------
const P1_COLOR := Color(0.16, 0.52, 1.0)             # NetsuUI.BLUE: player 1, the left
const P2_COLOR := Color(1.0, 0.16, 0.3)              # NetsuUI.RED: player 2, the right
const READY_TEXT := Color(1.0, 0.86, 0.35)           # READY!, wins (the old lobby's gold)
const BOX_FILL := Color(0.02, 0.03, 0.12, 0.9)       # the text / digit boxes (the old LineEdit's look)
const BOX_EDGE := Color(0.45, 0.7, 1.0, 0.9)
const LOG_TEXT := Color(0.97, 0.97, 1.0)
const LOCAL_TEXT := Color(0.62, 0.8, 1.0)
## Status colours: in the match, picking, ready, waiting in line, only watching.
const SETUP_RECT := Rect2(360, 200, 1200, 604)  # SETUP: the panel (portrait column | rows over the help box)
const SETUP_SIDE := 330.0
const SETUP_HELP := 150.0
const ROW_TEXT := Color(0.9, 0.92, 1.0)          # (the training menu's rows)
const STATUS := {"live": Color(1.0, 0.5, 0.6), "pick": Color(0.3, 0.82, 1.0), "ready": Color(1.0, 0.86, 0.35),
	"wait": Color(0.76, 0.78, 0.88), "spec": Color(0.86, 0.66, 0.98)}

@export var port: int = 7777

var _net: Node
var _room: Node
var _page := Page.MENU
var _sel := 0
var _my_pick := {}                 # while I'm picking: {"f", "c", "a", "ready", "match"}
var _show_backup := false          # host: the long code is shown (S)
var _leave_armed := 0.0            # B once: "press B again to leave" (seconds left)
var _note := ""                    # a short message in the INFORMATION bar for NOTE_SECONDS
var _note_t := 0.0
var _joining := false              # JOIN: a code went to NetsuOnline, the lobby isn't there yet
var _device := "kb1"               # pressed last: "kb1", "kb2", "pad1", "pad2" (the legend names its keys)
var _lan_code := ""                # host page: the same-network code / the note that came with the code
var _host_note := ""
var _t := 0.0
var _tick := 0.0
# the open text box (read by _input): {"kind": "digits" | "code" | "name" | "reply", "text", "max", "fresh",
# "placeholder"}; the lobby code is _digits (one digit or "" per box) with the cursor on _cursor
var _box := {}
var _digits: Array = ["", "", "", "", ""]
var _cursor := 0

# nodes: every page
var _title: Label
var _footer: Dictionary            # NetsuUI.footer: "text" (what to do now), "prompts" (NetsuPromptBar)
var _legend_items: Array = []      # the prompts as items (_item), for test_state
var _panel_root: Control
# nodes: the pages
var _menu_labels: Array[Label] = []
var _menu_bar: ColorRect
var _code_label: Label
var _join_caption: Label
var _info: Label
var _status: Label
var _spec_line: Label
var _box_nodes := {}
var _room_ui := {}
var _entries: Array = []
var _icons := {}                   # fighter -> its square picture (_icon)
var _setup := {}                   # SETUP open: the values being set {"f", "c", "a", "stage", "music"}, "row" (its id),
                                   # "picking" (opened in my pick phase), "match" (that pick phase's id)
var _setup_ui := {}


func _ready() -> void:
	_net = get_node_or_null("/root/NetsuOnline")
	_room = get_node_or_null("/root/OnlineRoom")
	_device = "pad1" if not Input.get_connected_joypads().is_empty() else "kb1"
	NetsuUI.picture(self, NetsuUI.MENU_BG)
	var shade := ColorRect.new()
	shade.color = Color(0.02, 0.03, 0.12, 0.58)
	shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(shade)
	NetsuUI.full_rect(shade)
	_build_header()
	_panel_root = Control.new()
	_panel_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_panel_root)
	NetsuUI.full_rect(_panel_root)
	_build_footer()
	if _net:
		_net.connect("StatusChanged", _on_status)
		_net.connect("CodeReady", _on_code_ready)
		_net.connect("ReplyCodeReady", _on_reply_code)
		_net.connect("Connected", _on_connected)
		_net.connect("Disconnected", _on_disconnected)
		_net.connect("MemberJoined", _on_member_joined)
	if _room:
		_room.room_changed.connect(_on_room_changed)
		_room.log_changed.connect(_fill_log)
		_room.lobby_opened()
	if _room and _room.active():
		_enter_room()   # back from a fight (or from watching one)
	else:
		_show_menu()
	if MatchSetup.online_notice != "":
		_set_status(MatchSetup.online_notice)
		if _page == Page.ROOM:
			_room.local_line(MatchSetup.online_notice)
		MatchSetup.online_notice = ""
	if _net == null or _room == null:
		_set_status("Online play needs the game's C# part: build the project in Godot (Build button), then restart.")


func _exit_tree() -> void:
	if _room:
		_room.lobby_closed()


func _on_room_changed() -> void:
	if _page == Page.HOST:
		_host_hud()   # (To the Room works once the room is there)
	else:
		_refresh_room()


func _process(delta: float) -> void:
	_t += delta
	var redo := false
	if _leave_armed > 0.0:
		_leave_armed = maxf(_leave_armed - delta, 0.0)
		redo = _leave_armed == 0.0   # (the "press B again" line goes away)
	if _note_t > 0.0:
		_note_t = maxf(_note_t - delta, 0.0)
		if _note_t == 0.0:
			_note = ""
			redo = true
	_tick += delta
	if _tick >= 1.0:
		_tick = 0.0
		redo = redo or _page == Page.ROOM   # (the pings)
	if redo:
		_refresh_page()
	if _page == Page.ROOM:
		_refresh_clock()
	if _page == Page.HOST and _code_label and String(_code_label.text).begins_with("."):
		_code_label.text = ".".repeat(3 + int(_t * 3.0) % 4)
	var caret: ColorRect = _box_nodes.get("caret")
	if caret and is_instance_valid(caret):
		caret.visible = fmod(_t, 1.0) < 0.62


# --- The frame (every page): the header, the page title, the footer ---------------------------------------------

func _build_header() -> void:
	NetsuUI.header(self, "ONLINE")
	_title = NetsuUI.label("", 46, Color.WHITE, NetsuUI.sans(5))
	NetsuUI.glow(_title, Color(0.25, 0.5, 1.0, 0.35), 8)
	_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_title.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_title.position = Vector2(0, 108)
	_title.size = Vector2(1920, 70)
	add_child(_title)


func _set_title(text: String) -> void:
	_title.text = text


## The kit's footer, on two rows: what to do now over the line... under it the button prompts.
func _build_footer() -> void:
	_footer = NetsuUI.footer(self, true, 826.0, 87.0, 852.0, 1600.0, 893.0)
	_footer["text"].size = Vector2(1720, 44)


## What to do now (smaller letters when it's long).
func _set_info(text: String) -> void:
	var l: Label = _footer["text"]
	l.text = text
	var f: Font = l.get_theme_font("font")
	var fs := 25
	while fs > 18 and f.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x > l.size.x:
		fs -= 1
	l.add_theme_font_size_override("font_size", fs)


## The button prompts, NetsuPromptBar style ("J  READY     K  LEAVE"); a dimmed item (can't be used now) is left out.
func _set_legend(items: Array) -> void:
	_legend_items = items
	var groups := []
	for it in items:
		if bool(it.get("dim", false)):
			continue
		var keys := []
		for k in it["keys"]:
			keys.append({"DPAD_UD": "UP / DOWN", "DPAD_LR": "LEFT / RIGHT"}.get(k, str(k).to_upper()))
		groups.append("%s  %s" % [" / ".join(keys), str(it["label"]).to_upper()])
	_footer["prompts"].text = "     ".join(groups)


## A legend entry: the keys (names, or "DPAD_UD" / "DPAD_LR" for the D-pad), what they do, dimmed = can't be used now.
func _item(keys: Array, label: String, dim := false) -> Dictionary:
	return {"keys": keys, "label": label, "dim": dim}


## The name of one of the player's buttons ("a", "b", "c", "s", "ab", "start"...) on what they pressed last.
func _kn(button: String) -> String:
	var c := get_node_or_null("/root/Controls")
	if c and c.has_method("button_name"):
		return str(c.button_name(_device, button))
	return button.to_upper()


## Legend keys for two directions: the D-pad on a controller, else the two keys ("W", "S").
func _dir_keys(a: String, b: String) -> Array:
	if _device.begins_with("pad"):
		return ["DPAD_UD" if a in ["up", "down"] else "DPAD_LR"]
	return [_kn(a), _kn(b)]


func _kb() -> bool:
	return not _device.begins_with("pad")


func _refresh_page() -> void:
	match _page:
		Page.MENU:
			_menu_hud()
		Page.HOST:
			_host_hud()
		Page.JOIN:
			_join_hud()
		Page.ROOM:
			_refresh_room()


## A short message in the INFORMATION bar (a few seconds).
func _flash(text: String) -> void:
	_note = text
	_note_t = NOTE_SECONDS
	_refresh_page()


# --- Pages --------------------------------------------------------------------------------

func _clear_panel() -> void:
	for c in _panel_root.get_children():
		c.queue_free()
	_setup = {}
	_setup_ui = {}
	_menu_labels.clear()
	_menu_bar = null
	_code_label = null
	_join_caption = null
	_info = null
	_status = null
	_spec_line = null
	_box = {}
	_box_nodes = {}
	_room_ui = {}
	_entries = []
	_show_backup = false
	_joining = false
	_note = ""
	_note_t = 0.0


func _add_status(y: float) -> void:
	_status = _lbl(_panel_root, "", 26, Color(0.8, 0.88, 1.0), NetsuUI.body(), Rect2(360, y, 1200, 60), HORIZONTAL_ALIGNMENT_CENTER)
	_status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	if _net and _net.LastStatus != "":
		_status.text = _net.LastStatus


func _show_menu() -> void:
	_page = Page.MENU
	_clear_panel()
	_set_title("PLAY ONLINE")
	NetsuUI.frame_panel(_panel_root, Rect2(610, 236, 700, 476))
	_menu_bar = ColorRect.new()
	_menu_bar.color = Color(0.2, 0.45, 1.0, 0.28)
	_menu_bar.size = Vector2(620, 66)
	_menu_bar.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_panel_root.add_child(_menu_bar)
	for i in MENU_ITEMS.size():
		var l := _lbl(_panel_root, _menu_text(i), 38, NetsuUI.DIM, NetsuUI.serif(600, 2), Rect2(650, _menu_y(i), 620, 66),
			HORIZONTAL_ALIGNMENT_CENTER)
		l.clip_text = true
		_menu_labels.append(l)
	_add_status(742)
	_select(_sel)


func _menu_y(i: int) -> float:
	return 272.0 + i * 86.0


func _menu_row(id: String) -> int:
	for i in MENU_ITEMS.size():
		if MENU_ITEMS[i]["id"] == id:
			return i
	return 0


func _menu_text(i: int) -> String:
	match MENU_ITEMS[i]["id"]:
		"name":
			var n: String = _room.my_name() if _room else ""
			return "NAME:  %s" % (n.to_upper() if n != "" else "(NONE)")
		"spectate":
			return "SPECTATE ONLY:  %s" % ("ON" if _room and _room.spectate_only else "OFF")
	return MENU_ITEMS[i]["label"]


func _select(i: int) -> void:
	_sel = wrapi(i, 0, MENU_ITEMS.size())
	for j in _menu_labels.size():
		_menu_labels[j].add_theme_color_override("font_color", NetsuUI.TEXT if j == _sel else NetsuUI.DIM)
	if _menu_bar:
		_menu_bar.position = Vector2(650, _menu_y(_sel))
	_menu_hud()


func _menu_hud() -> void:
	if _box.get("kind", "") == "name":
		if _kb():
			_set_info("Type the name the other players see, then press Enter (Esc keeps the old one).")
			_set_legend([_item(["Enter"], "Keep"), _item(["Esc"], "Cancel"), _item(["Backspace"], "Delete"), _item(["Ctrl+V"], "Paste")])
		else:
			_set_info("Names are typed on a keyboard (or pasted with Ctrl+V). %s keeps it, %s cancels." % [_kn("a"), _kn("b")])
			_set_legend([_item([_kn("a")], "Keep"), _item([_kn("b")], "Cancel")])
		return
	var id: String = MENU_ITEMS[_sel]["id"]
	var text: String = MENU_ITEMS[_sel]["blurb"]
	if id == "spectate":
		text = ("ON: you only watch. You're never put in line for a match (change it in the lobby any time)."
			if _room and _room.spectate_only else "OFF: you're put in line to play when you join. ON: you only watch the matches.")
	if _note != "":
		text = _note
	_set_info(text)
	_set_legend([_item(_dir_keys("up", "down"), "Select"), _item([_kn("a")], "Change" if id == "spectate" else "Confirm"),
		_item([_kn("b")], "Back")])


## MENU > NAME: a box to type the name in (Enter keeps it, Esc doesn't).
func _open_name_entry() -> void:
	var row := _menu_row("name")
	_menu_labels[row].visible = false
	_open_box("name", _room.my_name() if _room else "", _room.MAX_NAME if _room else 16,
		Rect2(660, _menu_y(row) - 2, 600, 70), 40, "YOUR NAME")
	_menu_hud()


func _close_name_entry() -> void:
	_close_box()
	var row := _menu_row("name")
	if row < _menu_labels.size():
		_menu_labels[row].text = _menu_text(row)
		_menu_labels[row].visible = true
	_menu_hud()


func _toggle_spectate() -> void:
	if _room:
		_room.set_spectate(not _room.spectate_only)
	var row := _menu_row("spectate")
	_menu_labels[row].text = _menu_text(row)
	_menu_hud()


func _start_host() -> void:
	if _net == null:
		return
	_net.Host(port)
	_show_invite()


## The host's code screen: right after opening the lobby, and from the room (Start).
func _show_invite() -> void:
	_page = Page.HOST
	_clear_panel()
	_set_title("YOUR LOBBY")
	NetsuUI.frame_panel(_panel_root, Rect2(360, 230, 1200, 560))
	_lbl(_panel_root, "LOBBY CODE", 28, NetsuUI.CYAN, NetsuUI.sans(8), Rect2(360, 262, 1200, 40), HORIZONTAL_ALIGNMENT_CENTER)
	_code_label = _lbl(_panel_root, "...", 104, Color.WHITE, NetsuUI.serif(700, 6), Rect2(360, 300, 1200, 140),
		HORIZONTAL_ALIGNMENT_CENTER)
	NetsuUI.glow(_code_label, Color(0.25, 0.5, 1.0, 0.4), 10)
	_info = _lbl(_panel_root, "Working out your address...", 25, NetsuUI.DIM, NetsuUI.body(), Rect2(420, 458, 1080, 140),
		HORIZONTAL_ALIGNMENT_CENTER, VERTICAL_ALIGNMENT_TOP)
	_info.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_add_status(712)
	_host_hud()
	if _net.Code != "":
		_on_code_ready(_net.Code, _net.LanCode, "")


func _host_hud() -> void:
	if _box.get("kind", "") == "reply":
		_set_info("Type the REPLY CODE the player sent you, then press Enter: both computers call each other for a while.")
		if _kb():
			_set_legend([_item(["Enter"], "Call"), _item(["Esc"], "Cancel"), _item(["Backspace"], "Delete"), _item(["Ctrl+V"], "Paste")])
		else:
			_set_legend([_item([_kn("a")], "Call"), _item([_kn("b")], "Cancel")])
		return
	_set_info(_note if _note != "" else "Send the code to your friends: they pick JOIN LOBBY and type it in (up to 8 players).")
	if _net == null:
		return
	var items := [_item([_kn("c")], "Copy Backup Code" if _show_backup else "Copy Code", _net.Code == "")]
	if _net.HasLobbyNumber and not _show_backup:
		items.append(_item([_kn("s")], "Backup Code", _net.LongCode == ""))
	else:
		items.append(_item([_kn("s")], "Enter Reply Code", _net.Code == ""))
	items.append(_item([_kn("a")], "To the Room", not (_room and _room.active())))
	items.append(_item([_kn("b")], "Back to the Room" if int(_net.MemberCount) > 0 else "Close Lobby"))
	_set_legend(items)


func _start_join() -> void:
	if _net == null:
		return
	_page = Page.JOIN
	_clear_panel()
	_set_title("JOIN A LOBBY")
	NetsuUI.frame_panel(_panel_root, Rect2(360, 230, 1200, 560))
	_join_caption = _lbl(_panel_root, "LOBBY CODE", 28, NetsuUI.CYAN, NetsuUI.sans(8), Rect2(360, 262, 1200, 40),
		HORIZONTAL_ALIGNMENT_CENTER)
	_info = _lbl(_panel_root, "", 25, NetsuUI.DIM, NetsuUI.body(), Rect2(420, 520, 1080, 110), HORIZONTAL_ALIGNMENT_CENTER,
		VERTICAL_ALIGNMENT_TOP)
	_info.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_spec_line = _lbl(_panel_root, "", 22, NetsuUI.CYAN, NetsuUI.sans(3), Rect2(360, 636, 1200, 32), HORIZONTAL_ALIGNMENT_CENTER)
	_add_status(700)
	_set_status("")
	_digits = ["", "", "", "", ""]
	_cursor = 0
	_open_digits()
	_join_hud()


func _join_hud() -> void:
	if _spec_line:
		_spec_line.text = "YOU'LL JOIN AS A SPECTATOR  (SPECTATE ONLY is on: change it on the previous page)" \
			if _room and _room.spectate_only else ""
	var kind := str(_box.get("kind", ""))
	var copy: bool = _net != null and _net.ReplyCode != ""
	var info := ""
	var items := []
	if kind == "code":
		info = "Type the backup code (like K7Q2-M9X4-PA3D) or an address (192.168.1.20:7777), then press Enter." if _kb() \
			else "Backup codes are typed on a keyboard (or pasted with Ctrl+V). %s goes back to the lobby code." % _kn("b")
		if _kb():
			items = [_item(["Enter"], "Join"), _item(["Esc"], "Lobby Code"), _item(["Backspace"], "Delete"), _item(["Ctrl+V"], "Paste")]
		else:
			items = [_item([_kn("a")], "Join"), _item([_kn("b")], "Lobby Code")]
	else:
		if _kb():
			info = "Type the 5-digit code from the host's screen (or change each digit with %s / %s), then press Enter." \
				% [_kn("up"), _kn("down")]
			items = [_item(["0-9"], "Type"), _item(_dir_keys("up", "down"), "Digit"), _item(_dir_keys("left", "right"), "Move"),
				_item(["Backspace"], "Delete"), _item(["Enter"], "Join"), _item(["Esc"], "Back"), _item(["Tab"], "Backup Code"),
				_item(["Ctrl+V"], "Paste")]
		else:
			info = "Up / Down changes the digit, Left / Right moves to the next one. %s joins when all 5 are in." % _kn("a")
			items = [_item(["DPAD_UD"], "Digit"), _item(["DPAD_LR"], "Move"), _item([_kn("a")], "Join"),
				_item([_kn("s")], "Backup Code"), _item([_kn("b")], "Back")]
	if copy:
		items.append(_item(["Ctrl+C"] if _kb() else [_kn("c")], "Copy Reply Code"))
	if _note != "":
		info = _note
	_set_info(info)
	_set_legend(items)


func _join(text: String) -> void:
	if _net == null or text.strip_edges() == "":
		return
	if _net.Join(text.strip_edges()):
		_joining = true
		if _info:
			_info.text = "Looking up the lobby..." if _net.IsLobbyNumber(text) else "Connecting..."
	_join_hud()


## Host: S opens a box for a joiner's reply code.
func _open_reply_entry() -> void:
	if not _box.is_empty() or _page != Page.HOST:
		return
	_open_box("reply", "", 20, Rect2(560, 610, 800, 80), 44, "XXXX-XXXX-XXXX")
	_host_hud()


func _leave_lobby(text: String) -> void:
	if _net:
		_net.Leave()
	_show_menu()
	_set_status(text)


# --- The text boxes (the lobby code, a backup code / address, the name, a reply code) ---------------------------

## The lobby code: CODE_DIGITS boxes, one digit each, the cursor on one of them (gold, with arrows above / below).
func _open_digits() -> void:
	_close_box_nodes()
	_box = {"kind": "digits", "fresh": true}
	var slots := []
	var x0 := 960.0 - (CODE_DIGITS * SLOT_W + (CODE_DIGITS - 1) * SLOT_GAP) / 2.0
	for i in CODE_DIGITS:
		var r := Rect2(x0 + i * (SLOT_W + SLOT_GAP), SLOT_Y, SLOT_W, SLOT_H)
		var p := _panel(_panel_root, r, BOX_FILL, BOX_EDGE, 2, 0)
		var l := _lbl(_panel_root, "", 84, Color.WHITE, _code_font(), r, HORIZONTAL_ALIGNMENT_CENTER)
		var blank := ColorRect.new()   # where a digit goes
		blank.color = Color(NetsuUI.LINE, 0.4)
		blank.position = Vector2(r.position.x + 32, r.end.y - 32)
		blank.size = Vector2(SLOT_W - 64, 2)
		blank.mouse_filter = Control.MOUSE_FILTER_IGNORE
		_panel_root.add_child(blank)
		slots.append({"panel": p, "label": l, "blank": blank, "rect": r})
	# the cursor: a diamond above and below the box (the menus' diamond)
	var up := NetsuUI.diamond(8.0, Color(0.85, 0.93, 1.0), Color(0.03, 0.05, 0.16), NetsuUI.CYAN)
	var down := NetsuUI.diamond(8.0, Color(0.85, 0.93, 1.0), Color(0.03, 0.05, 0.16), NetsuUI.CYAN)
	_panel_root.add_child(up)
	_panel_root.add_child(down)
	_box_nodes = {"slots": slots, "up": up, "down": down}
	_refresh_box()


## The serif for codes, with lining figures (Cormorant's own 1 looks like an I).
func _code_font() -> FontVariation:
	var f := NetsuUI.serif(700, 4)
	f.opentype_features = {TextServerManager.get_primary_interface().name_to_tag("lnum"): 1}
	return f


## A one-line text box ("code", "name" or "reply"); `placeholder` shows while it's empty.
func _open_box(kind: String, text: String, max_len: int, rect: Rect2, font_size: int, placeholder: String) -> void:
	_close_box_nodes()
	_box = {"kind": kind, "text": text.substr(0, max_len), "max": max_len, "fresh": true, "placeholder": placeholder}
	var p := _panel(_panel_root, rect, BOX_FILL, BOX_EDGE, 2, 0)
	var l := _lbl(_panel_root, "", font_size, Color.WHITE, _code_font() if kind != "name" else NetsuUI.serif(700, 2), Rect2(rect.position + Vector2(16, 0),
		rect.size - Vector2(32, 0)), HORIZONTAL_ALIGNMENT_CENTER)
	l.clip_text = true
	var caret := ColorRect.new()
	caret.color = Color(0.85, 0.93, 1.0)
	caret.size = Vector2(3, font_size * 0.95)
	caret.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_panel_root.add_child(caret)
	_box_nodes = {"panel": p, "label": l, "caret": caret, "rect": rect, "size": font_size}
	_refresh_box()


func _close_box_nodes() -> void:
	for key in _box_nodes:
		var v = _box_nodes[key]
		if key == "slots":
			for s in v:
				for n in [s["panel"], s["label"], s["blank"]]:
					if is_instance_valid(n):
						n.queue_free()
		elif v is Node and is_instance_valid(v):
			v.queue_free()
	_box_nodes = {}


func _close_box() -> void:
	_close_box_nodes()
	_box = {}


func _refresh_box() -> void:
	if _box_nodes.is_empty():
		return
	if str(_box.get("kind", "")) == "digits":
		var slots: Array = _box_nodes["slots"]
		for i in slots.size():
			var s: Dictionary = slots[i]
			var sel := i == _cursor
			var d: String = _digits[i]
			s["label"].text = d
			s["blank"].visible = d == ""
			var sb: StyleBoxFlat = _sb(s["panel"])
			sb.border_color = NetsuUI.CYAN if sel else (BOX_EDGE if d != "" else Color(BOX_EDGE, 0.45))
			sb.set_border_width_all(3 if sel else 2)
			sb.bg_color = Color(0.05, 0.09, 0.28, 0.95) if sel else BOX_FILL
			sb.shadow_color = Color(0.25, 0.55, 1.0, 0.45) if sel else Color(0, 0, 0, 0)
			sb.shadow_size = 10 if sel else 0
		var r: Rect2 = slots[_cursor]["rect"]
		_box_nodes["up"].position = Vector2(r.get_center().x, r.position.y - 18)
		_box_nodes["down"].position = Vector2(r.get_center().x, r.end.y + 18)
		return
	var text := str(_box.get("text", ""))
	var l: Label = _box_nodes["label"]
	var fs: int = _box_nodes["size"]
	l.text = text if text != "" else str(_box.get("placeholder", ""))
	l.add_theme_color_override("font_color", Color.WHITE if text != "" else Color(1, 1, 1, 0.22))
	var f: Font = l.get_theme_font("font")
	var w := f.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x if text != "" else 0.0
	var rect: Rect2 = _box_nodes["rect"]
	var caret: ColorRect = _box_nodes["caret"]
	caret.position = Vector2(minf(rect.get_center().x + w / 2.0 + 4.0, rect.end.x - 14.0), rect.get_center().y - caret.size.y / 2.0)


func _digit_text() -> String:
	return "".join(_digits)


func _step_digit(step: int) -> void:
	var d: String = _digits[_cursor]
	_digits[_cursor] = ("0" if step > 0 else "9") if d == "" else str(wrapi(int(d) + step, 0, 10))
	_refresh_box()


func _move_cursor(step: int) -> void:
	_cursor = clampi(_cursor + step, 0, CODE_DIGITS - 1)
	_refresh_box()


func _to_code_mode(text: String) -> void:
	_open_box("code", text.to_upper(), 40, Rect2(460, 330, 1000, 150), 60, "K7Q2-M9X4-PA3D")
	if _join_caption:
		_join_caption.text = "BACKUP CODE OR ADDRESS"
	_join_hud()


func _to_digits_mode() -> void:
	_open_digits()
	if _join_caption:
		_join_caption.text = "LOBBY CODE"
	_join_hud()


## A key while a box is open (from _input, before anything else sees it). True = the box used it.
func _box_key(e: InputEventKey) -> bool:
	var kind := str(_box.get("kind", ""))
	if e.echo and bool(_box.get("fresh", false)):
		return true   # the key that opened the box is still held down: it doesn't type
	if not e.echo:
		_box["fresh"] = false
	var code: int = e.keycode if e.keycode != KEY_NONE else e.physical_keycode
	var cmd: bool = e.ctrl_pressed or e.meta_pressed
	if (cmd and code == KEY_V) or (e.shift_pressed and code == KEY_INSERT):
		if not e.echo:
			_paste(DisplayServer.clipboard_get())
		return true
	if cmd or e.alt_pressed:
		return false   # (Ctrl+C copies, Alt+Enter goes full screen...)
	match code:
		KEY_ENTER, KEY_KP_ENTER:
			if not e.echo:
				_box_submit()
			return true
		KEY_ESCAPE:
			if not e.echo:
				_box_cancel()
			return true
		KEY_BACKSPACE:
			_box_backspace(e.echo)
			return true
		KEY_DELETE:
			if kind == "digits":
				_digits[_cursor] = ""
				_refresh_box()
			return true
		KEY_TAB:
			if not e.echo and _page == Page.JOIN:
				if kind == "digits":
					_to_code_mode("")
				else:
					_to_digits_mode()
			return true
	var c := _typed_char(e)
	if c == "":
		return false
	if kind == "digits":
		if c >= "0" and c <= "9":
			_digits[_cursor] = c
			_cursor = mini(_cursor + 1, CODE_DIGITS - 1)
			_refresh_box()
			return true
		if c == "." or c == ":":
			_to_code_mode(_digit_text() + c)   # an address being typed
			return true
		return false   # a letter: the picker's / the page's buttons (W A S D, J joins, K goes back, I: backup code)
	_type_char(c)
	return true


## What a key types: the numpad always types its digit (whatever Num Lock says), else the key's character.
func _typed_char(e: InputEventKey) -> String:
	var pk: int = e.physical_keycode if e.physical_keycode != KEY_NONE else e.keycode
	if pk >= KEY_KP_0 and pk <= KEY_KP_9:
		return str(pk - KEY_KP_0)
	if pk == KEY_KP_PERIOD:
		return "."
	if e.unicode >= 32:
		return String.chr(e.unicode)
	return ""


func _type_char(c: String) -> void:
	var kind := str(_box.get("kind", ""))
	if kind in ["code", "reply"]:
		c = c.to_upper()
		if not CODE_CHARS.contains(c):
			return
	var text := str(_box.get("text", ""))
	if text.length() >= int(_box.get("max", 16)):
		return
	_box["text"] = text + c
	_refresh_box()


func _box_backspace(echo: bool) -> void:
	if str(_box.get("kind", "")) == "digits":
		if _digits[_cursor] != "":
			_digits[_cursor] = ""
		elif _cursor > 0:
			_cursor -= 1
			_digits[_cursor] = ""
		elif not echo and _digit_text() == "":
			_box_cancel()   # nothing left to delete: back, like Backspace in the menus
			return
		_refresh_box()
		return
	var text := str(_box.get("text", ""))
	if text == "":
		if not echo and str(_box.get("kind", "")) == "code":
			_to_digits_mode()
		return
	_box["text"] = text.substr(0, text.length() - 1)
	_refresh_box()


## Ctrl+V: a 5-digit lobby number fills the digit boxes, anything else goes to the backup code box.
func _paste(text: String) -> void:
	var t := text.strip_edges()
	if t == "":
		return
	var kind := str(_box.get("kind", ""))
	if _page == Page.JOIN and kind in ["digits", "code"]:
		var digits := ""
		for ch in t:
			if ch >= "0" and ch <= "9":
				digits += ch
		var number: bool = _net.IsLobbyNumber(t) if _net else digits.length() == CODE_DIGITS
		if number:
			for i in CODE_DIGITS:
				_digits[i] = digits[i]
			_cursor = CODE_DIGITS - 1
			if kind == "code":
				_to_digits_mode()
			else:
				_refresh_box()
			return
		if kind == "digits":
			_to_code_mode("")
	for ch in t:
		if ch.unicode_at(0) >= 32:
			_type_char(ch)   # (one line: a new line in the clipboard doesn't come in)


func _box_submit() -> void:
	match str(_box.get("kind", "")):
		"digits":
			if _digit_text().length() < CODE_DIGITS:
				var blank := _digits.find("")
				_cursor = blank if blank >= 0 else _cursor
				_refresh_box()
				_flash("Enter all %d digits of the lobby code first." % CODE_DIGITS)
				return
			_join(_digit_text())
		"code":
			_join(str(_box.get("text", "")))
		"name":
			if _room:
				_room.set_my_name(str(_box.get("text", "")))
			_close_name_entry()
		"reply":
			if _net and _net.AcceptReply(str(_box.get("text", "")).strip_edges()):
				_close_box()
				_host_info()


func _box_cancel() -> void:
	match str(_box.get("kind", "")):
		"digits":
			if _joining:
				_stop_joining()
			else:
				if _net:
					_net.Leave()
				_show_menu()
				_set_status("")
		"code":
			if _joining:
				_stop_joining()
			else:
				_to_digits_mode()
		"name":
			_close_name_entry()
		"reply":
			_close_box()
			_host_info()


## JOIN: B / Esc while a code is being tried stops trying it (change the code, join again).
func _stop_joining() -> void:
	if _net:
		_net.Leave()
	_joining = false
	if _info:
		_info.text = ""
	_set_status("Stopped. Check the code and try again.")
	_join_hud()


# --- The room -----------------------------------------------------------------------------------

func _enter_room() -> void:
	_page = Page.ROOM
	_clear_panel()
	_leave_armed = 0.0
	_set_title("ONLINE LOBBY")
	_build_room()
	_refresh_room()
	_fill_log()


func _build_room() -> void:
	var ui := {}
	var root := _panel_root
	# the room bar: the host's lobby ... its code
	_glass(root, ROOM_BAR)
	var cy := ROOM_BAR.position.y
	_lbl(root, "ROOM", 20, NetsuUI.CYAN, NetsuUI.sans(8), Rect2(ROOM_BAR.position.x + 28, cy, 110, ROOM_BAR.size.y))
	ui["room_name"] = _lbl(root, "", 26, NetsuUI.TEXT, NetsuUI.sans(3), Rect2(ROOM_BAR.position.x + 140, cy, 560, ROOM_BAR.size.y))
	ui["room_name"].clip_text = true
	ui["setup_cap"] = _lbl(root, "SETUP", 20, NetsuUI.CYAN, NetsuUI.sans(8), Rect2(0, cy, 200, ROOM_BAR.size.y))
	ui["setup"] = _lbl(root, "", 22, NetsuUI.TEXT, NetsuUI.sans(2), Rect2(0, cy, 300, ROOM_BAR.size.y))
	ui["setup"].clip_text = true
	ui["setup"].text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	ui["code_cap"] = _lbl(root, "CODE", 20, NetsuUI.CYAN, NetsuUI.sans(8), Rect2(0, cy, 100, ROOM_BAR.size.y), HORIZONTAL_ALIGNMENT_RIGHT)
	ui["code"] = _lbl(root, "", 26, Color.WHITE, NetsuUI.sans(4), Rect2(ROOM_BAR.end.x - 330, cy, 300, ROOM_BAR.size.y),
		HORIZONTAL_ALIGNMENT_RIGHT)
	_build_vs(ui)
	# the messages
	NetsuUI.frame_panel(root, LOG_RECT)
	_lbl(root, "MESSAGES", 20, NetsuUI.CYAN, NetsuUI.sans(6), Rect2(LOG_RECT.position.x + 30, LOG_RECT.position.y + 14, 400, 32))
	var lines := []
	for i in 6:
		var l := _lbl(root, "", 23, LOG_TEXT, NetsuUI.body(), Rect2(LOG_RECT.position.x + 30, LOG_RECT.position.y + 56 + i * 40,
			LOG_RECT.size.x - 60, 36))
		l.clip_text = true
		l.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
		lines.append(l)
	ui["log"] = lines
	# the list
	NetsuUI.frame_panel(root, LIST_RECT)
	ui["list_title"] = _lbl(root, "", 22, NetsuUI.CYAN, NetsuUI.sans(6), Rect2(LIST_RECT.position.x + 30, LIST_RECT.position.y + 14, 500, 34))
	_entries = []
	for i in 8:
		_entries.append(_build_entry(i))
	_room_ui = ui


## One row of the player list: [number tab][avatar] [flag] name / [status bar]   wins / ping. Gold frame = you.
func _build_entry(i: int) -> Dictionary:
	var e := {}
	var root := Control.new()
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.position = Vector2(LIST_RECT.position.x + 12, ROW_Y + i * ROW_STEP)
	root.size = Vector2(LIST_RECT.size.x - 24, ROW_H)
	_panel_root.add_child(root)
	e["root"] = root
	var w := root.size.x
	e["you"] = NetsuUI.row_bar(Vector2(w, ROW_H))   # your own row: the menus' selected-row bar
	root.add_child(e["you"])
	if i < 7:
		root.add_child(NetsuUI.hairline(Vector2(10, ROW_H + 4), w - 20, Color(0.55, 0.75, 1.0, 0.3), 1.0))
	e["num"] = _lbl(root, "", 28, NetsuUI.CYAN, NetsuUI.sans(2), Rect2(4, 0, 40, ROW_H), HORIZONTAL_ALIGNMENT_CENTER)
	_profile_avatar(root, Rect2(50, 7, 62, 62), e, 26.0)
	for side in 2:   # the side in the match: a small diamond in the side's colour
		var d := NetsuUI.diamond(6.0, Color(0.85, 0.92, 1.0), Color(0.03, 0.05, 0.16), P1_COLOR if side == 0 else P2_COLOR)
		d.position = Vector2(132, 24)
		root.add_child(d)
		e["side%d" % side] = d
	e["name"] = _lbl(root, "", 23, NetsuUI.TEXT, NetsuUI.sans(2), Rect2(146, 4, w - LIST_PLATE.x - 156, 38))
	e["name"].clip_text = true
	e["name"].text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	e["status"] = _lbl(root, "", 16, NetsuUI.DIM, NetsuUI.sans(5), Rect2(146, 40, 200, 28))
	# the title plate, right of the name; wins and ping under it
	e["plate"] = NetsuTitlePlate.new()
	e["plate"].position = Vector2(w - LIST_PLATE.x - 4, 6)
	e["plate"].size = LIST_PLATE
	root.add_child(e["plate"])
	e["wins"] = _lbl(root, "", 16, READY_TEXT, NetsuUI.sans(3), Rect2(w - 240, 40, 132, 28), HORIZONTAL_ALIGNMENT_RIGHT)
	e["ping"] = _lbl(root, "", 16, NetsuUI.DIM, NetsuUI.sans(3), Rect2(w - 104, 40, 94, 28), HORIZONTAL_ALIGNMENT_RIGHT)
	return e


## A fighter icon box: the picture (OnlineIcon), a thin frame, and the player's initial when there's no picture.
func _avatar(parent: Node, rect: Rect2, into: Dictionary) -> void:
	var base := ColorRect.new()
	base.color = Color(0.04, 0.05, 0.12, 0.92)
	base.position = rect.position
	base.size = rect.size
	base.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(base)
	var pic := TextureRect.new()
	pic.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	pic.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	pic.position = rect.position
	pic.size = rect.size
	pic.mouse_filter = Control.MOUSE_FILTER_IGNORE
	pic.clip_contents = true
	parent.add_child(pic)
	into["avatar"] = pic
	into["initial"] = _lbl(parent, "", int(rect.size.y * 0.5), Color(0.6, 0.72, 1.0, 0.7), NetsuUI.serif(700), rect,
		HORIZONTAL_ALIGNMENT_CENTER)
	# a thin light frame, like the character select's slots
	parent.add_child(NetsuUI.outline(PackedVector2Array([rect.position, Vector2(rect.end.x, rect.position.y), rect.end,
		Vector2(rect.position.x, rect.end.y)]), Color(0.92, 0.94, 1.0, 0.9), 2.0))


## A player's profile icon box (ProfileCatalog: _set_profile_avatar fills it), like _avatar, with a small chip of their
## fighter (their pick, or the one they picked last) in the bottom-right corner.
func _profile_avatar(parent: Node, rect: Rect2, into: Dictionary, chip: float) -> void:
	_avatar(parent, rect, into)
	var r := Rect2(rect.end - Vector2(chip * 0.8, chip * 0.8), Vector2(chip, chip))
	var base := ColorRect.new()
	base.color = Color(0.04, 0.05, 0.12, 1.0)
	base.position = r.position
	base.size = r.size
	base.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(base)
	var pic := TextureRect.new()
	pic.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	pic.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	pic.position = r.position
	pic.size = r.size
	pic.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(pic)
	var edge := NetsuUI.outline(PackedVector2Array([r.position, Vector2(r.end.x, r.position.y), r.end, Vector2(r.position.x, r.end.y)]),
		Color(0.92, 0.94, 1.0, 0.95), 1.5)
	parent.add_child(edge)
	into["chip"] = [base, pic, edge]


## The profile icon (an older game sends none: the default icon), the fighter chip (hidden with no fighter yet).
func _set_profile_avatar(into: Dictionary, id: int, f: int) -> void:
	var pic: TextureRect = into["avatar"]
	ProfileCatalog.apply_icon(pic, _room.icon_of(id) if id >= 0 else "")
	pic.visible = id >= 0
	into["initial"].visible = false
	var face := _icon(f)
	into["chip"][1].texture = face
	for n in into["chip"]:
		n.visible = id >= 0 and face != null


func _build_vs(ui: Dictionary) -> void:
	var root := _panel_root
	var r := VS_RECT
	NetsuUI.frame_panel(root, r)
	# blue light on the left (player 1), crimson on the right (player 2)
	var half := (r.size.x - 16.0) / 2.0
	var lights := [NetsuUI.gradient_rect(Color(P1_COLOR, 0.2), Color(P1_COLOR, 0.0), false),
		NetsuUI.gradient_rect(Color(P2_COLOR, 0.0), Color(P2_COLOR, 0.2), false)]
	for side in 2:
		lights[side].position = Vector2(r.position.x + 8 + side * half, r.position.y + 8)
		lights[side].size = Vector2(half, r.size.y - 16)
		root.add_child(lights[side])
	var cx := r.get_center().x
	var vs := _lbl(root, "VS", 92, Color.WHITE, NetsuUI.serif(700), Rect2(cx - 100, r.position.y + 40, 200, 120),
		HORIZONTAL_ALIGNMENT_CENTER)
	NetsuUI.glow(vs, Color(0.3, 0.5, 1.0, 0.5), 12)
	NetsuUI.divider(root, r.position.x + 30, r.end.x - 30, r.position.y + 170)
	var sides := []
	for side in 2:
		var s := {}
		var left := side == 0
		var accent: Color = P1_COLOR if left else P2_COLOR
		var al := HORIZONTAL_ALIGNMENT_RIGHT if left else HORIZONTAL_ALIGNMENT_LEFT
		var tag_x := r.position.x + 30.0 if left else r.end.x - 510.0
		s["tag"] = _lbl(root, "", 21, accent.lightened(0.35), NetsuUI.sans(6), Rect2(tag_x, r.position.y + 14, 480, 32),
			HORIZONTAL_ALIGNMENT_LEFT if left else HORIZONTAL_ALIGNMENT_RIGHT)
		_profile_avatar(root, Rect2(cx - 205 if left else cx + 101, r.position.y + 50, 104, 104), s, 40.0)
		var nx := r.position.x + 30.0 if left else cx + 225.0
		var nw := cx - 245 - r.position.x - 30
		s["name"] = _lbl(root, "", 32, Color.WHITE, NetsuUI.sans(3), Rect2(nx, r.position.y + 46, nw, 44), al)
		s["name"].clip_text = true
		s["name"].text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
		NetsuUI.glow(s["name"], Color(0.02, 0.03, 0.12, 0.7), 5)
		s["plate"] = NetsuTitlePlate.new()
		s["plate"].size = VS_PLATE
		s["plate"].position = Vector2(nx + nw - VS_PLATE.x + 6 if left else nx - 6, r.position.y + 92)
		root.add_child(s["plate"])
		s["status"] = _lbl(root, "", 20, NetsuUI.DIM, NetsuUI.sans(6), Rect2(nx, r.position.y + 130, nw, 30), al)
		sides.append(s)
	ui["vs"] = sides
	# under the names: each side's fighter and assist, the pick clock between them
	var st := {}
	var cols := []
	var col_w := cx - 120.0 - r.position.x - 30.0
	for side in 2:
		var left := side == 0
		var accent: Color = P1_COLOR if left else P2_COLOR
		var x := r.position.x + 30.0 if left else cx + 120.0
		var al := HORIZONTAL_ALIGNMENT_RIGHT if left else HORIZONTAL_ALIGNMENT_LEFT
		var c := {}
		c["fighter"] = _lbl(root, "", 54, Color.WHITE, NetsuUI.serif(700, 2), Rect2(x, r.position.y + 196, col_w, 66), al)
		NetsuUI.glow(c["fighter"], Color(accent, 0.45), 8)
		c["detail"] = _lbl(root, "", 20, NetsuUI.TEXT, NetsuUI.sans(4), Rect2(x, r.position.y + 268, col_w, 30), al)
		c["fighter"].clip_text = true
		c["detail"].clip_text = true
		cols.append(c)
	st["side"] = cols
	st["clock"] = _lbl(root, "", 44, Color.WHITE, NetsuUI.sans(4), Rect2(cx - 100, r.position.y + 200, 200, 54), HORIZONTAL_ALIGNMENT_CENTER)
	st["caption"] = _lbl(root, "", 15, NetsuUI.CYAN, NetsuUI.sans(3), Rect2(cx - 110, r.position.y + 250, 220, 24), HORIZONTAL_ALIGNMENT_CENTER)
	ui["strip"] = st


## A slim glass bar (the room bar): navy, a light edge, the footer's diamonds at its ends.
func _glass(parent: Node, rect: Rect2) -> void:
	var pts := PackedVector2Array([rect.position, Vector2(rect.end.x, rect.position.y), rect.end, Vector2(rect.position.x, rect.end.y)])
	var fill := Polygon2D.new()
	fill.polygon = pts
	fill.vertex_colors = PackedColorArray([Color(0.04, 0.06, 0.2, 0.88), Color(0.04, 0.06, 0.2, 0.88),
		Color(0.02, 0.03, 0.12, 0.92), Color(0.02, 0.03, 0.12, 0.92)])
	parent.add_child(fill)
	parent.add_child(NetsuUI.outline(pts, Color(0.3, 0.62, 1.0, 0.2), 8.0))
	parent.add_child(NetsuUI.outline(pts, Color(NetsuUI.LINE, 0.9), 1.5))
	for x in [rect.position.x, rect.end.x]:
		var d := NetsuUI.diamond(7.0, Color(NetsuUI.LINE, 0.95), Color(0.03, 0.05, 0.16, 1.0))
		d.position = Vector2(x, rect.get_center().y)
		parent.add_child(d)


## Under the VS bar: each side's pick (fighter, colour, assist), the pick clock between them, the stage and rules.
func _build_strip(_ui: Dictionary) -> void:
	pass   # (built with the VS panel: _build_vs)


func _refresh_room() -> void:
	if _page != Page.ROOM or _room == null or _room_ui.is_empty():
		return
	var room: Dictionary = _room.room
	if room.is_empty():
		for e in _entries:
			e["root"].visible = false
		_set_info("Joining the lobby...")
		_set_legend([_item([_kn("b")], "Leave")])
		return
	var m: Dictionary = _room.current_match()
	var state := str(m.get("state", "none"))
	var my_side: int = _room.my_side()
	# my pick: starts from what the host has for me when a new pick phase comes up
	if my_side >= 0 and state == "picking":
		var mine: Dictionary = _room.pick_of(_room.my_id)
		if int(_my_pick.get("match", -1)) != int(m.get("id", -1)):
			_my_pick = {"f": int(mine.get("f", 0)), "c": int(mine.get("c", 0)), "a": int(mine.get("a", 0)),
				"ready": bool(mine.get("ready", false)), "match": int(m.get("id", -1))}
		elif bool(mine.get("ready", false)):
			_my_pick["ready"] = true   # (the clock ran out: the host locked it in)
	if not _setup.is_empty():
		var picking_now := my_side >= 0 and state == "picking"
		if bool(_setup["picking"]) and (not picking_now or int(m.get("id", -1)) != int(_setup["match"])):
			_close_setup()   # my pick phase is over (the fight is on, or I passed / it moved on): nothing to keep
			_flash("Your pick phase is over: SETUP closed without your changes.")
			return
		if picking_now and not bool(_setup["picking"]):
			_setup["picking"] = true   # my turn came while it's open: the Ready row comes in, the changes stay
			_setup["match"] = int(m.get("id", -1))
			_build_setup()
	_fill_top(room)
	_fill_list(room, m)
	_fill_vs(room, m, state)
	_fill_strip(room, m, state)
	if _setup.is_empty():
		_room_hud(m, state, my_side)
	else:
		_refresh_setup()


func _fill_top(room: Dictionary) -> void:
	_set_title("" if not _setup.is_empty() else "ONLINE LOBBY")   # (SETUP draws its own title, over its dimming)
	var nl: Label = _room_ui["room_name"]
	nl.text = "%s'S LOBBY" % _room.member_name(0).to_upper()
	var code := str(room.get("code", ""))
	var cl: Label = _room_ui["code"]
	cl.text = code
	var w := cl.get_theme_font("font").get_string_size(code, HORIZONTAL_ALIGNMENT_LEFT, -1, 26).x
	_room_ui["code_cap"].position.x = cl.position.x + cl.size.x - w - 16.0 - _room_ui["code_cap"].size.x
	_room_ui["code_cap"].visible = code != ""
	# your setup, between the lobby's name and the code
	nl.size.x = 360.0
	var name_w := minf(nl.get_theme_font("font").get_string_size(nl.text, HORIZONTAL_ALIGNMENT_LEFT, -1, 26).x, nl.size.x)
	var sc: Label = _room_ui["setup_cap"]
	var sv: Label = _room_ui["setup"]
	sc.position.x = nl.position.x + name_w + 48.0
	sc.size.x = sc.get_theme_font("font").get_string_size(sc.text, HORIZONTAL_ALIGNMENT_LEFT, -1, 20).x + 16.0
	sv.position.x = sc.position.x + sc.size.x + 4.0
	sv.size.x = maxf(0.0, (_room_ui["code_cap"].position.x if code != "" else ROOM_BAR.end.x) - 40.0 - sv.position.x)
	var mine := _setup_text()
	sv.text = mine if mine != "" else "NOT SET  ·  %s" % _kn("a")
	sv.add_theme_color_override("font_color", NetsuUI.TEXT if mine != "" else NetsuUI.DIM)
	var fs := 22
	while fs > 17 and sv.get_theme_font("font").get_string_size(sv.text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x > sv.size.x:
		fs -= 1
	sv.add_theme_font_size_override("font_size", fs)
	var n: int = room.get("members", {}).size()
	_room_ui["list_title"].text = "PLAYERS  %d / 8" % n


## The list: everyone in line order, then whoever is spectating (in the order they came in).
func _fill_list(room: Dictionary, m: Dictionary) -> void:
	var members: Dictionary = room.get("members", {})
	var line: Array = room.get("queue", [])
	var ids: Array = []
	for v in line:
		ids.append(int(v))
	for v in room.get("order", []):
		if not int(v) in ids and members.has(str(v)):
			ids.append(int(v))
	for i in _entries.size():
		var e: Dictionary = _entries[i]
		e["root"].visible = i < ids.size()
		if i >= ids.size():
			continue
		var id: int = ids[i]
		var pos := line.find(id)
		var me: bool = id == _room.my_id
		e["you"].visible = me
		e["num"].text = str(pos + 1) if pos >= 0 else "-"
		e["num"].add_theme_color_override("font_color", NetsuUI.CYAN if pos >= 0 else NetsuUI.DIM)
		var who: String = _room.member_name(id)
		_set_profile_avatar(e, id, _fighter_of(id, m))
		e["plate"].title_id = _room.title_of(id)
		var in_match: bool = _room.turn_of(id) in ["pick", "fight"]
		var side := 0 if id == int(m.get("p1", -1)) else (1 if id == int(m.get("p2", -1)) else -1)
		e["side0"].visible = in_match and side == 0
		e["side1"].visible = in_match and side == 1
		var nl: Label = e["name"]
		nl.position.x = 146.0 if in_match else 126.0
		nl.size.x = e["plate"].position.x - 14.0 - nl.position.x
		nl.text = who.to_upper() + ("  ·  HOST" if id == 0 else "")
		nl.add_theme_color_override("font_color", Color.WHITE if me else NetsuUI.TEXT)
		var fs := 23   # (a long name: smaller letters before it's cut short)
		while fs > 18 and nl.get_theme_font("font").get_string_size(nl.text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x > nl.size.x:
			fs -= 1
		nl.add_theme_font_size_override("font_size", fs)
		_style_status(e["status"], _status_of(id))
		e["status"].position.x = nl.position.x
		var wins := int(members.get(str(id), {}).get("wins", 0))
		e["wins"].text = ("%d WIN%s" % [wins, "" if wins == 1 else "S"]) if wins > 0 else ""
		e["ping"].text = _ping_text(id)


func _fill_vs(room: Dictionary, m: Dictionary, state: String) -> void:
	var ids := [int(m.get("p1", -1)), int(m.get("p2", -1))]
	if not state in ["picking", "fighting"]:
		var line: Array = room.get("queue", [])
		ids = [int(line[0]) if line.size() > 0 else -1, int(line[1]) if line.size() > 1 else -1]
	var streak := int(room.get("streak", 0))
	for side in 2:
		var s: Dictionary = _room_ui["vs"][side]
		var id: int = ids[side]
		if side == 0:
			var king := id >= 0 and id == int(room.get("streak_id", -2)) and streak > 0
			s["tag"].text = ("1P  ·  KING  ·  %d WIN%s IN A ROW" % [streak, "" if streak == 1 else "S"]) if king else "1P  ·  PLAYER 1 SIDE"
		else:
			s["tag"].text = "2P  ·  CHALLENGER"
		if id < 0:
			s["name"].text = "WAITING FOR A CHALLENGER" if side == 1 else "WAITING FOR PLAYERS"
			s["name"].add_theme_color_override("font_color", Color(NetsuUI.DIM, 0.7))
			s["name"].add_theme_font_size_override("font_size", 24)
			s["status"].text = "Send them the lobby code!" if side == 1 else ""
			s["status"].add_theme_color_override("font_color", NetsuUI.DIM)
			_set_profile_avatar(s, -1, -1)
			s["plate"].title_id = ""
			continue
		s["name"].text = _room.member_name(id).to_upper() + ("   (YOU)" if id == _room.my_id else "")
		s["name"].add_theme_color_override("font_color", Color.WHITE)
		s["name"].add_theme_font_size_override("font_size", 32)
		_style_status(s["status"], _status_of(id))
		_set_profile_avatar(s, id, _fighter_of(id, m))
		s["plate"].title_id = _room.title_of(id)


func _fill_strip(_room_d: Dictionary, m: Dictionary, state: String) -> void:
	var st: Dictionary = _room_ui["strip"]
	# (Nov 4: the stage / music / rules line is gone from the panel: SETUP shows the stage and music)
	for side in 2:
		var c: Dictionary = st["side"][side]
		var id := int(m.get("p1" if side == 0 else "p2", -1))
		var pick := {}
		if state == "fighting":
			var p: Dictionary = m.get("p", {})
			var k := str(side + 1)
			pick = {"f": int(p.get("f" + k, 0)), "c": int(p.get("c" + k, 0)), "a": int(p.get("a" + k, 0)), "ready": true}
		elif state == "picking":
			pick = _my_pick if id == _room.my_id else _room.pick_of(id)
		if pick.is_empty():
			c["fighter"].text = ""
			c["detail"].text = ""
			continue
		var f := clampi(int(pick.get("f", 0)), 0, maxi(0, MatchSetup.fighter_count() - 1))
		var prof = MatchSetup.fighter_profile(f)
		var fighter := String(prof.ShortName).to_upper() if prof else "?"
		c["fighter"].text = fighter
		c["detail"].text = "ASSIST  %s" % MatchSetup.assist_name(int(pick.get("a", 0))).to_upper()
	_refresh_clock()


## The pick clock (every frame).
func _refresh_clock() -> void:
	if _room_ui.is_empty() or _room == null:
		return
	var st: Dictionary = _room_ui["strip"]
	var m: Dictionary = _room.current_match()
	var state := str(m.get("state", "none"))
	var clock: Label = st["clock"]
	if state == "picking":
		var left := ceili(_room.pick_time_left())
		var here: bool = _room.pickers_here()
		clock.text = ("%d" % left) if here else "· · ·"
		clock.add_theme_color_override("font_color", Color(1.0, 0.45, 0.4) if here and left <= 10 else Color.WHITE)
		st["caption"].text = "SECONDS TO PICK" if here else "COMING BACK"
		if _setup_ui.has("clock"):
			_setup_ui["clock"].text = clock.text
			_setup_ui["clock"].add_theme_color_override("font_color", clock.get_theme_color("font_color"))
			_setup_ui["clock_cap"].text = st["caption"].text
	elif state == "fighting":
		clock.text = "LIVE"
		clock.add_theme_color_override("font_color", Color(1.0, 0.35, 0.35))
		st["caption"].text = "FIGHT IN PROGRESS"
	else:
		clock.text = ""
		st["caption"].text = "WAITING FOR PLAYERS" if not _room.room.is_empty() else ""


## The message panel: the latest lines of the room log (and this computer's own), oldest at the top.
func _fill_log() -> void:
	if _page != Page.ROOM or _room_ui.is_empty() or _room == null:
		return
	var lines: Array = _room.log_lines
	var labels: Array = _room_ui["log"]
	var first := maxi(0, lines.size() - labels.size())
	var shown := lines.size() - first
	for i in labels.size():
		var l: Label = labels[i]
		if first + i >= lines.size():
			l.text = ""
			continue
		var e: Dictionary = lines[first + i]
		l.text = str(e.get("text", ""))
		var a := 1.0 - (shown - 1 - i) * 0.1   # (older lines a little dimmer)
		l.add_theme_color_override("font_color", Color(LOCAL_TEXT if bool(e.get("local", false)) else LOG_TEXT, a))


## The INFORMATION line and the buttons for the room.
func _room_hud(m: Dictionary, state: String, my_side: int) -> void:
	var me: int = _room.my_id
	var host: bool = _net != null and bool(_net.IsHost)
	var turn: String = _room.turn_of(me)
	var picking := turn == "pick"
	var ready := picking and bool(_my_pick.get("ready", false))
	var items := []
	items.append(_item([_kn("a")], "Setup / Ready" if picking and not ready else "Setup"))
	if ready:
		items.append(_item([_kn("b")], "Not Ready"))
	if not picking:
		if state == "fighting":
			items.append(_item([_kn("c")], "Watch"))
		items.append(_item([_kn("s")], "Back in Line" if turn == "spec" else "Spectate"))
	items.append(_item([_kn("ab")], "Pass", _room.pass_target(me) < 0))
	if host:
		items.append(_item([_kn("start")], "Invite"))
	if not ready:
		items.append(_item([_kn("b")], "Leave"))
	_set_legend(items)
	_set_info(_room_info(m, state, my_side, turn))


func _room_info(m: Dictionary, state: String, my_side: int, turn: String) -> String:
	if _leave_armed > 0.0:
		return "Press %s again to leave the lobby." % _kn("b")
	if _note != "":
		return _note
	var me: int = _room.my_id
	var p1: String = _room.member_name(int(m.get("p1", -1)))
	var p2: String = _room.member_name(int(m.get("p2", -1)))
	if turn == "pick":
		var other := p2 if my_side == 0 else p1
		if bool(_my_pick.get("ready", false)):
			return "Ready! The fight starts when %s is ready too." % other
		var next: int = _room.pass_target(me)
		return "You're up against %s! Press %s for SETUP: pick your fighter, then Ready.%s" % [other, _kn("a"),
			("  %s passes your turn to %s." % [_kn("ab"), _room.member_name(next)]) if next >= 0 else ""]
	var what := ""
	if state == "fighting":
		what = "%s and %s are fighting: press %s to watch." % [p1, p2, _kn("c")]
	elif state == "picking":
		what = ("%s and %s are picking their fighters." if _room.pickers_here() else "Waiting for %s and %s to come back.") % [p1, p2]
	else:
		var code := str(_room.room.get("code", ""))
		what = "Waiting for 2 players in line%s." % ((": send your friends the lobby code %s" % code) if code != "" else "")
	var where := ""
	match turn:
		"next":
			var behind: int = _room.pass_target(me)
			where = "You're next: you fight the winner.%s" % (("  %s lets %s go first." % [_kn("ab"), _room.member_name(behind)])
				if behind >= 0 else "")
		"line":
			if state in ["picking", "fighting"]:
				where = "You're %s in line." % _ordinal(_room.queue_position(me) + 1)
		"spec":
			where = "Spectate only: you watch every match and are never put in line (%s: back in line)." % _kn("s")
	return (what + "  " + where).strip_edges()


func _ordinal(n: int) -> String:
	var suffix := "th"
	if n % 100 < 11 or n % 100 > 13:
		suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
	return "%d%s" % [n, suffix]


## [text, style] of a player's status: "live" (in the match), "ready", "wait" (in line), "spec" (only watching).
func _status_of(id: int) -> Array:
	match _room.turn_of(id):
		"fight":
			return ["NOW PLAYING", "live"]
		"pick":
			var pk: Dictionary = _my_pick if id == _room.my_id else _room.pick_of(id)
			if bool(pk.get("ready", false)):
				return ["READY!", "ready"]
			if str(_room.member(id).get("state", "")) != "lobby":
				return ["COMING BACK...", "wait"]
			return ["PICKING...", "pick"]
		"next":
			return ["NEXT UP", "wait"]
		"line":
			return ["WAITING", "wait"]
		"join":
			return ["JOINING...", "wait"]
	return ["SPECTATING", "spec"]


func _style_status(text: Label, st: Array) -> void:
	text.text = st[0]
	text.add_theme_color_override("font_color", STATUS.get(st[1], NetsuUI.DIM))


## The fighter shown for a player: their pick in the match, else the one they picked last (-1: none yet).
func _fighter_of(id: int, m: Dictionary) -> int:
	var state := str(m.get("state", ""))
	var side := 0 if id == int(m.get("p1", -1)) else (1 if id == int(m.get("p2", -1)) else -1)
	if side >= 0 and state == "fighting":
		return int(m.get("p", {}).get("f%d" % (side + 1), -1))
	if side >= 0 and state == "picking":
		var pk: Dictionary = _my_pick if id == _room.my_id else _room.pick_of(id)
		if not pk.is_empty():
			return int(pk.get("f", -1))
	return int(_room.member(id).get("f", -1))


## A fighter's picture for the list / VS bar: their select screen Portrait (head and shoulders), as a square from its
## top middle (like the select screen's slots, character_select.gd PORTRAIT_CROP), else their OnlineIcon; null = none.
func _icon(f: int) -> Texture2D:
	if _icons.has(f):
		return _icons[f]
	var tex: Texture2D = null
	if f >= 0 and f < MatchSetup.fighter_count():
		var prof = MatchSetup.fighter_profile(f)
		if prof:
			var portrait = prof.get("Portrait")
			if portrait is Texture2D:
				var ts: Vector2 = portrait.get_size()
				var side := minf(ts.x, ts.y * 0.885)
				var crop := AtlasTexture.new()
				crop.atlas = portrait
				crop.region = Rect2((ts.x - side) / 2.0, ts.y * 0.03, side, side)
				tex = crop
			elif prof.get("OnlineIcon") is Texture2D:
				tex = prof.get("OnlineIcon")
	_icons[f] = tex
	return tex


## The fighter's picture (_icon), or the player's initial when there's none.
func _set_avatar(into: Dictionary, f: int, who: String) -> void:
	var tex := _icon(f)
	into["avatar"].texture = tex
	into["initial"].visible = tex == null
	into["initial"].text = who.substr(0, 1).to_upper() if who != "" else ""


func _ping_text(id: int) -> String:
	if _net == null:
		return ""
	var ping := -1
	if bool(_net.IsHost) and id != 0:
		ping = int(_net.PingOf(id))
	elif not bool(_net.IsHost) and id == _room.my_id:
		ping = int(_net.Ping)
	return ("%d ms" % ping) if ping >= 0 else ""


func _set_ready(on: bool) -> void:
	if _room.my_side() < 0 or str(_room.current_match().get("state", "")) != "picking":
		return
	_my_pick["ready"] = on
	_send_pick()
	_refresh_room()


func _send_pick() -> void:
	_room.send_pick(int(_my_pick.get("f", 0)), int(_my_pick.get("c", 0)), int(_my_pick.get("a", 0)), bool(_my_pick.get("ready", false)))


## AB: give my turn to the next player waiting (when it's my turn, or I'm next).
func _try_pass() -> void:
	var me: int = _room.my_id
	if not _room.turn_of(me) in ["pick", "next"]:
		_flash("Pass gives your turn away: it works while you're picking, or when you're next in line.")
		return
	var other: int = _room.pass_target(me)
	if other < 0:
		_flash("Nobody is waiting behind you, so there's nobody to pass your turn to.")
		return
	_room.pass_turn()
	_flash("You passed: %s goes first." % _room.member_name(other))


# --- SETUP: the quick menu (A in the room) ----------------------------------------------------------------------

func _picking_now() -> bool:
	return _room.my_side() >= 0 and str(_room.current_match().get("state", "")) == "picking"


## What I fight with: my pick while I'm picking, else my saved setup (OnlineRoom.my_setup; {} = not set yet).
func _my_setup() -> Dictionary:
	if _picking_now() and not _my_pick.is_empty():
		return {"f": int(_my_pick["f"]), "c": int(_my_pick["c"]), "a": int(_my_pick["a"])}
	return _room.my_setup.duplicate()


## "FLAN  ·  STARLIGHT  ·  ADIN" ("" = not set).
func _setup_text() -> String:
	var s := _my_setup()
	if s.is_empty():
		return ""
	var f := clampi(int(s["f"]), 0, maxi(0, MatchSetup.fighter_count() - 1))
	var prof = MatchSetup.fighter_profile(f)
	var colour := MatchSetup.palette_name(f, int(s["c"])) if MatchSetup.palette_count(f) > int(s["c"]) else ""
	return "%s  ·  %s  ·  %s" % [String(prof.ShortName).to_upper() if prof else "?", colour.to_upper(),
		MatchSetup.assist_name(int(s["a"])).to_upper()]


## A music choice's name (MatchSetup.MUSIC_AUTO / MUSIC_RANDOM / a song), as the training menu's Quick Select has them.
func _music_name(choice: int) -> String:
	if choice == MatchSetup.MUSIC_AUTO:
		return "Auto (P1's Theme)"
	if choice == MatchSetup.MUSIC_RANDOM or choice < 0 or choice >= MatchSetup.song_count():
		return "Random"
	return str(MatchSetup.song_info(choice).get("title", ""))


func _open_setup() -> void:
	var s := _my_setup()
	if s.is_empty():
		var f := int(_room.member(_room.my_id).get("f", -1))
		s = {"f": maxi(f, 0), "c": 0, "a": 0}
	var picking := _picking_now()
	_setup = {"f": int(s["f"]), "c": int(s["c"]), "a": int(s["a"]), "stage": int(_room.room.get("stage", -1)),
		"music": int(_room.music()), "picking": picking, "match": int(_room.current_match().get("id", -1)) if picking else -1}
	_setup["row"] = "ready" if picking and not bool(_my_pick.get("ready", false)) else "fighter"
	_leave_armed = 0.0
	_build_setup()
	_refresh_room()


func _close_setup() -> void:
	if _setup_ui.has("root") and is_instance_valid(_setup_ui["root"]):
		_setup_ui["root"].queue_free()
	_setup_ui = {}
	_setup = {}
	if _page == Page.ROOM:
		_refresh_room()


## The rows: [id, label]; "" = a divider between the groups.
func _setup_rows() -> Array:
	var rows := [["fighter", "Fighter"], ["colour", "Colour"], ["assist", "Assist"], ["", ""], ["stage", "Stage"],
		["music", "Music"]]
	if bool(_setup.get("picking", false)):
		rows.append_array([["", ""], ["ready", "Cancel Ready" if bool(_my_pick.get("ready", false)) else "Ready"]])
	return rows


func _setup_ids() -> Array:
	var ids := []
	for r in _setup_rows():
		if r[0] != "":
			ids.append(r[0])
	return ids


## Can Left / Right change this row now? (Stage / Music: the host's. My picks: not once I'm ready.)
func _setup_editable(id: String) -> bool:
	match id:
		"fighter", "colour", "assist":
			return not (bool(_setup.get("picking", false)) and bool(_my_pick.get("ready", false)))
		"stage", "music":
			return _net != null and bool(_net.IsHost)
	return false


## A row's [index, count] in its list (Stage: -1 = random; Music: -2 = player 1's theme, -1 = random).
func _setup_range(id: String) -> Array:
	match id:
		"fighter":
			return [int(_setup["f"]), MatchSetup.fighter_count()]
		"colour":
			return [int(_setup["c"]), MatchSetup.palette_count(int(_setup["f"]))]
		"assist":
			return [int(_setup["a"]), MatchSetup.assist_count()]
		"stage":
			return [_setup_stage() + 1, MatchSetup.stage_count() + 1]
		"music":
			return [_setup_music() + 2, MatchSetup.song_count() + 2]
	return [0, 1]


## The stage / music shown: the host's own changes, everyone else's the room's (they can change while it's open).
func _setup_stage() -> int:
	return int(_setup["stage"]) if _setup_editable("stage") else int(_room.room.get("stage", -1))


func _setup_music() -> int:
	return int(_setup["music"]) if _setup_editable("music") else int(_room.music())


func _setup_value(id: String) -> String:
	match id:
		"fighter":
			var prof = MatchSetup.fighter_profile(clampi(int(_setup["f"]), 0, maxi(0, MatchSetup.fighter_count() - 1)))
			return String(prof.FighterName) if prof else "?"
		"colour":
			return MatchSetup.palette_name(int(_setup["f"]), int(_setup["c"])) if MatchSetup.palette_count(int(_setup["f"])) > int(_setup["c"]) else ""
		"assist":
			return MatchSetup.assist_name(int(_setup["a"]))
		"stage":
			var st := _setup_stage()
			return "Random" if st < 0 or st >= MatchSetup.stage_count() else MatchSetup.stage_name(st)
		"music":
			return _music_name(_setup_music())
	return ""


func _setup_help(id: String) -> String:
	var host: bool = _net != null and bool(_net.IsHost)
	match id:
		"fighter":
			return "Who you fight with. Kept as your setup: every time your turn comes, you start with it."
		"colour":
			return "Your fighter's colours. When both players have the same fighter in the same colours, player 2 gets the next ones."
		"assist":
			return "The partner you call in during the fight."
		"stage":
			return ("Where the next matches are fought. Random: a new stage every match." if host else
				"Where the next matches are fought. The host picks it.")
		"music":
			return ("The battle music for the next matches. Auto plays player 1's theme; Random picks a song each match, the same one on every computer."
				if host else "The battle music for the next matches. The host picks it.")
		"ready":
			if bool(_my_pick.get("ready", false)):
				return "You're ready. Cancel it to change your fighter, colour or assist before the clock runs out."
			return "Fight with this setup. The fight starts when your opponent is ready too; when the clock runs out, what you have is locked in."
	return ""


func _build_setup() -> void:
	if _setup_ui.has("root") and is_instance_valid(_setup_ui["root"]):
		_setup_ui["root"].free()
	var ui := {}
	var root := Control.new()
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.size = Vector2(1920, 1080)
	_panel_root.add_child(root)
	ui["root"] = root
	# the room stays there, dimmed (as the training menu dims the fight), the title over it; the footer stays lit
	var dim := ColorRect.new()
	dim.color = Color(0.01, 0.02, 0.1, 0.62)
	dim.mouse_filter = Control.MOUSE_FILTER_IGNORE
	dim.size = Vector2(1920, 1080)
	root.add_child(dim)
	var title := NetsuUI.label("SETUP", 46, Color.WHITE, NetsuUI.sans(5))
	NetsuUI.glow(title, Color(0.25, 0.5, 1.0, 0.35), 8)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	title.position = _title.position
	title.size = _title.size
	root.add_child(title)
	ui["title"] = title
	var r := SETUP_RECT
	NetsuUI.frame_panel(root, r)
	var split := NetsuUI.gradient_rect(Color(0.55, 0.75, 1.0, 0.15), Color(0.55, 0.75, 1.0, 0.7), true)
	split.position = Vector2(r.position.x + SETUP_SIDE, r.position.y + 26)
	split.size = Vector2(1.5, r.size.y - 52)
	root.add_child(split)
	# the portrait column: the fighter's picture, name, colour and assist (and the pick clock in my pick phase)
	var cx := r.position.x + SETUP_SIDE / 2.0
	_avatar(root, Rect2(cx - 115, r.position.y + 44, 230, 230), ui)
	ui["fighter"] = _lbl(root, "", 40, Color.WHITE, NetsuUI.serif(700, 2), Rect2(r.position.x + 20, r.position.y + 290,
		SETUP_SIDE - 40, 54), HORIZONTAL_ALIGNMENT_CENTER)
	NetsuUI.glow(ui["fighter"], Color(0.3, 0.5, 1.0, 0.45), 8)
	ui["detail"] = _lbl(root, "", 18, NetsuUI.TEXT, NetsuUI.sans(1), Rect2(r.position.x + 20, r.position.y + 348,
		SETUP_SIDE - 40, 60), HORIZONTAL_ALIGNMENT_CENTER)
	ui["detail"].autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	if bool(_setup["picking"]):
		ui["clock"] = _lbl(root, "", 44, Color.WHITE, NetsuUI.sans(4), Rect2(r.position.x + 20, r.end.y - 136, SETUP_SIDE - 40, 54),
			HORIZONTAL_ALIGNMENT_CENTER)
		ui["clock_cap"] = _lbl(root, "", 15, NetsuUI.CYAN, NetsuUI.sans(3), Rect2(r.position.x + 20, r.end.y - 84, SETUP_SIDE - 40, 24),
			HORIZONTAL_ALIGNMENT_CENTER)
	# the rows (the training menu's: label, value between arrows, the lit bar on the selected one), the help box under
	var area := Rect2(r.position.x + SETUP_SIDE + 40, r.position.y + 30, r.size.x - SETUP_SIDE - 80, r.size.y - 30 - SETUP_HELP)
	ui["area"] = area
	var rows := _setup_rows()
	var count := 0.0
	for row in rows:
		count += 0.6 if row[0] == "" else 1.0
	var pitch := minf(64.0, area.size.y / maxf(count, 1.0))
	var y := area.position.y + maxf(0.0, (area.size.y - count * pitch) * 0.15)
	var value_center := area.end.x - 230.0
	ui["bar"] = Node2D.new()
	root.add_child(ui["bar"])
	var built := {}
	for row in rows:
		if row[0] == "":
			NetsuUI.divider(root, area.position.x + 20, area.end.x - 20, y + pitch * 0.3, false)
			y += pitch * 0.6
			continue
		var e := {"y": y + pitch / 2.0, "h": pitch * 0.9}
		var sep := ColorRect.new()
		sep.color = Color(0.55, 0.7, 1.0, 0.12)
		sep.position = Vector2(area.position.x, y + pitch - 1)
		sep.size = Vector2(area.size.x, 1)
		sep.mouse_filter = Control.MOUSE_FILTER_IGNORE
		root.add_child(sep)
		e["label"] = _lbl(root, row[1], 26, ROW_TEXT, NetsuUI.sans(1), Rect2(area.position.x + 70, e["y"] - 30, 300, 60))
		if row[0] == "ready":
			e["go"] = NetsuUI.arrow(Vector2(value_center + 215, e["y"]), 22, 1, ROW_TEXT, 3.0)
			root.add_child(e["go"])
		else:
			e["value"] = _lbl(root, "", 26, ROW_TEXT, NetsuUI.sans(1), Rect2(value_center - 195, e["y"] - 30, 390, 60),
				HORIZONTAL_ALIGNMENT_CENTER)
			e["value"].clip_text = true
			e["left"] = NetsuUI.arrow(Vector2(value_center - 215, e["y"]), 22, -1, ROW_TEXT, 3.0)
			e["right"] = NetsuUI.arrow(Vector2(value_center + 215, e["y"]), 22, 1, ROW_TEXT, 3.0)
			root.add_child(e["left"])
			root.add_child(e["right"])
		built[row[0]] = e
		y += pitch
	ui["rows"] = built
	ui["marks"] = Node2D.new()
	root.add_child(ui["marks"])
	var hy := r.end.y - SETUP_HELP + 14.0
	NetsuUI.divider(root, area.position.x + 20, area.end.x - 20, hy, true)
	ui["help_tag"] = _lbl(root, "", 15, NetsuUI.CYAN, NetsuUI.sans(6), Rect2(area.position.x + 40, hy + 16, area.size.x - 80, 22))
	ui["help"] = _lbl(root, "", 21, Color(0.82, 0.86, 0.98), NetsuUI.body(), Rect2(area.position.x + 40, hy + 42, area.size.x - 80,
		SETUP_HELP - 70.0))
	ui["help"].autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	ui["help"].vertical_alignment = VERTICAL_ALIGNMENT_TOP
	_setup_ui = ui


func _refresh_setup() -> void:
	if _setup.is_empty() or not _setup_ui.has("rows"):
		return
	if not _setup["row"] in _setup_ids():
		_setup["row"] = "fighter"
	var host: bool = _net != null and bool(_net.IsHost)
	var area: Rect2 = _setup_ui["area"]
	for id in _setup_ui["rows"]:
		var e: Dictionary = _setup_ui["rows"][id]
		var on: bool = id == _setup["row"]
		var ink := Color.WHITE if on else ROW_TEXT
		e["label"].add_theme_color_override("font_color", ink)
		if e.has("value"):
			var can := _setup_editable(id)
			_set_row_value(e["value"], _setup_value(id))
			e["value"].add_theme_color_override("font_color", ink if can else NetsuUI.DIM)
			var rg := _setup_range(id)
			e["left"].visible = can
			e["right"].visible = can
			e["left"].modulate.a = 1.0 if int(rg[0]) > 0 else 0.25
			e["right"].modulate.a = 1.0 if int(rg[0]) < int(rg[1]) - 1 else 0.25
		if id == "ready":
			e["label"].text = "Cancel Ready" if bool(_my_pick.get("ready", false)) else "Ready"
	for c in _setup_ui["bar"].get_children():
		c.queue_free()
	for c in _setup_ui["marks"].get_children():
		c.queue_free()
	var cur: Dictionary = _setup_ui["rows"][_setup["row"]]
	var size := Vector2(area.size.x, cur["h"])
	var rb := NetsuUI.row_bar(size)
	rb.position = Vector2(area.position.x, cur["y"] - size.y / 2.0)
	_setup_ui["bar"].add_child(rb)
	_setup_ui["marks"].add_child(NetsuUI.chevron(Vector2(area.position.x + 24, cur["y"]), minf(size.y * 0.5, 24.0), Color.WHITE, 3.0))
	if _setup["row"] == "ready":
		_setup_ui["marks"].add_child(NetsuUI.chevron(Vector2(area.position.x + 48, cur["y"]), minf(size.y * 0.45, 22.0), NetsuUI.CYAN, 3.0, true))
	var tag: String = "%s  ·  HOST ONLY" % str(_setup["row"]).to_upper() if _setup["row"] in ["stage", "music"] and not host \
		else str(_setup["row"]).to_upper()
	_setup_ui["help_tag"].text = tag if _setup["row"] != "ready" else str(_setup_ui["rows"]["ready"]["label"].text).to_upper()
	_setup_ui["help"].text = _setup_help(_setup["row"])
	# the portrait column
	var f := clampi(int(_setup["f"]), 0, maxi(0, MatchSetup.fighter_count() - 1))
	var prof = MatchSetup.fighter_profile(f)
	_set_avatar(_setup_ui, f, String(prof.ShortName) if prof else "")
	_setup_ui["fighter"].text = String(prof.ShortName).to_upper() if prof else ""
	_setup_ui["detail"].text = "COLOUR  %s\nASSIST  %s" % [_setup_value("colour").to_upper(), _setup_value("assist").to_upper()]
	# the footer: what this is, and the menu's prompts
	var picking: bool = bool(_setup["picking"])
	if picking and bool(_my_pick.get("ready", false)):
		_set_info("You're ready: the fight starts when your opponent is.")
	elif picking:
		_set_info("Your turn: set up your fighter, then Ready.")
	else:
		_set_info("Your setup: what you start with when your turn comes.")
	var row: String = _setup["row"]
	var confirm := "Confirm"
	if row == "ready":
		confirm = "Cancel Ready" if bool(_my_pick.get("ready", false)) else "Ready"
	_set_legend([_item(_dir_keys("up", "down"), "Select"), _item(_dir_keys("left", "right"), "Change", not _setup_editable(row)),
		_item([_kn("a")], confirm), _item([_kn("b")], "Cancel")])


## A value's text, a size smaller when it doesn't fit (long stage and song names), as the training menu's.
func _set_row_value(l: Label, text: String) -> void:
	var font: Font = l.get_theme_font("font")
	var fs := 26
	while fs > 17 and font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x > l.size.x - 8:
		fs -= 1
	l.add_theme_font_size_override("font_size", fs)
	l.text = text


## Everything goes to SETUP while it's open (Pass, Spectate, Leave, Invite, Watch can't be pressed by accident).
func _setup_input(event: InputEvent) -> bool:
	var ids := _setup_ids()
	var i: int = ids.find(_setup["row"])
	if _dir(event, "up"):
		_setup["row"] = ids[maxi(i - 1, 0)]
	elif _dir(event, "down"):
		_setup["row"] = ids[mini(i + 1, ids.size() - 1)]
	elif _dir(event, "left"):
		_setup_step(-1)
	elif _dir(event, "right"):
		_setup_step(1)
	elif _btn(event, "a") or (event.is_action_pressed("ui_accept") and not _btn(event, "s") and not _btn(event, "start")):
		# (the menus' "accept" also has S and Start on it (I, Enter): here only A, so S / Invite do nothing by accident)
		_setup_confirm()
		return true
	elif _back(event):
		_close_setup()
		return true
	else:
		return event is InputEventKey or event is InputEventJoypadButton or event is InputEventJoypadMotion
	_refresh_setup()
	return true


func _setup_step(step: int) -> void:
	var id: String = _setup["row"]
	if not _setup_editable(id):
		return
	var rg := _setup_range(id)
	var n := maxi(1, int(rg[1]))
	var to := clampi(int(rg[0]) + step, 0, n - 1)
	match id:
		"fighter":
			if to != int(_setup["f"]):
				_setup["f"] = to
				var side := maxi(_room.my_side(), 0) if bool(_setup["picking"]) else 0
				_setup["c"] = 0 if MatchSetup.palette_count(to) <= side else side
		"colour":
			_setup["c"] = to
		"assist":
			_setup["a"] = to
		"stage":
			_setup["stage"] = to - 1
		"music":
			_setup["music"] = to - 2


## A: keep the changes (Ready row: and get ready / cancel it).
func _setup_confirm() -> void:
	var row: String = _setup["row"]
	var picking: bool = bool(_setup["picking"])
	if row == "ready" and bool(_my_pick.get("ready", false)):
		_set_ready(false)   # (stays open: change something, then Ready again)
		return
	var f := int(_setup["f"])
	var c := int(_setup["c"])
	var a := int(_setup["a"])
	if picking and not bool(_my_pick.get("ready", false)):
		_my_pick["f"] = f
		_my_pick["c"] = c
		_my_pick["a"] = a
		_my_pick["ready"] = row == "ready"
		_room.set_setup(f, c, a, false)
		_send_pick()
	elif not picking:
		_room.set_setup(f, c, a)
	if _net != null and bool(_net.IsHost):
		if int(_setup["stage"]) != int(_room.room.get("stage", -1)):
			_room.set_stage(int(_setup["stage"]))
		if int(_setup["music"]) != int(_room.music()):
			_room.set_music(int(_setup["music"]))
	_close_setup()


# --- Network events ---------------------------------------------------------------------------

func _on_status(text: String) -> void:
	if _page == Page.ROOM:
		if not (text.begins_with("A player joined") or text.begins_with("Joined the lobby")) and _room:
			_room.local_line(text)   # (joins are in the room log)
		return
	_set_status(text)


func _set_status(text: String) -> void:
	if _status and is_instance_valid(_status):
		_status.text = text


func _on_code_ready(code: String, lan_code: String, note: String) -> void:
	if _page != Page.HOST or _code_label == null:
		return
	_code_label.text = code
	_show_backup = false
	_host_info(lan_code, note)


## The lines under the host's code (the backup code while it's shown) and the buttons that go with them.
func _host_info(lan_code := "", note := "") -> void:
	if lan_code != "":
		_lan_code = lan_code
	if note != "":
		_host_note = note
	if _info == null or _net == null:
		return
	var lines := []
	if _show_backup:
		lines.append("BACKUP CODE   %s" % _net.LongCode)
		lines.append("For when the 5-digit code doesn't work for someone (%s copies it). If they then send you a REPLY CODE, press %s again." \
			% [_kn("c"), _kn("s")])
	else:
		if _lan_code != "" and _lan_code != _net.Code:
			lines.append("Same network as you? Their code is  %s" % _lan_code)
		if _host_note != "":
			lines.append(_host_note)
		lines.append("Port: UDP %d" % int(_net.LocalPort))
	_info.text = "\n".join(lines)
	_host_hud()


func _on_reply_code(code: String) -> void:
	if _page == Page.JOIN and _info:
		_info.text = "Couldn't reach the host directly. Send them your REPLY CODE and keep this screen open:\n%s" % code
		_join_hud()


func _on_connected(host: bool) -> void:
	if not host:
		_joining = false
		_enter_room.call_deferred()   # (after OnlineRoom has said hello)


## Host: the first player in takes the host from the invite screen to the room.
func _on_member_joined(_id: int) -> void:
	if _page == Page.HOST and _box.is_empty() and int(_net.MemberCount) == 1:
		_enter_room.call_deferred()


func _on_disconnected(reason: String) -> void:
	_joining = false
	if _page == Page.ROOM:
		_show_menu()
	elif _page == Page.JOIN:
		if _info:
			_info.text = ""   # try another code
		_join_hud()
	if _page in [Page.MENU, Page.JOIN]:
		_set_status(reason)


# --- Input --------------------------------------------------------------------------------------

## The keys go to an open text box first, before Godot's ui_ actions (and a page) can take them.
func _input(event: InputEvent) -> void:
	_track_device(event)
	if SceneRouter.is_busy() or _box.is_empty():
		return
	if event is InputEventKey and event.pressed and _box_key(event):
		get_viewport().set_input_as_handled()


func _unhandled_input(event: InputEvent) -> void:
	if SceneRouter.is_busy():
		return
	if event is InputEventKey and event.pressed and not event.echo and event.keycode == KEY_C \
			and (event.ctrl_pressed or event.meta_pressed):
		_copy_code()
		get_viewport().set_input_as_handled()
		return
	var handled := false
	match _page:
		Page.MENU:
			handled = _menu_input(event)
		Page.HOST:
			handled = _host_input(event)
		Page.JOIN:
			handled = _join_input(event)
		Page.ROOM:
			handled = _room_input(event)
	if handled:
		get_viewport().set_input_as_handled()


## What was pressed last: a key of keyboard 1's / 2's layout, another key (keeps the keyboard it was), a controller.
## Digit keys (a code being typed) don't switch keyboards.
func _track_device(event: InputEvent) -> void:
	var dev := _device
	if event is InputEventKey and event.pressed and not event.echo:
		var pk: int = event.physical_keycode if event.physical_keycode != KEY_NONE else event.keycode
		var digit := (pk >= KEY_0 and pk <= KEY_9) or (pk >= KEY_KP_0 and pk <= KEY_KP_9)
		var layout := ""
		var c := get_node_or_null("/root/Controls")
		if c and not digit:
			for n in [1, 2]:
				if c.keyboard.get(n, {}).values().has(pk):
					layout = "kb%d" % n
					break
		if layout != "":
			dev = layout
		elif not dev.begins_with("kb"):
			dev = "kb1"
	elif event is InputEventJoypadButton and event.pressed:
		dev = "pad2" if event.device == 1 else "pad1"
	elif event is InputEventJoypadMotion and absf(event.axis_value) > 0.6:
		dev = "pad2" if event.device == 1 else "pad1"
	if dev != _device:
		_device = dev
		_refresh_page()


## One of the player's buttons, on either keyboard layout or controller (one person plays per computer online).
func _btn(event: InputEvent, button: String) -> bool:
	return event.is_action_pressed("p1_" + button) or event.is_action_pressed("p2_" + button)


func _dir(event: InputEvent, d: String) -> bool:
	return event.is_action_pressed("ui_" + d, true) or event.is_action_pressed("p1_" + d, true) \
		or event.is_action_pressed("p2_" + d, true)


## Confirm / back: A or a menu "accept" key; B or a menu "cancel" key. (S and C are also menu accept / cancel keys,
## so the pages check those first.)
func _confirm(event: InputEvent) -> bool:
	return _btn(event, "a") or event.is_action_pressed("ui_accept")


func _back(event: InputEvent) -> bool:
	return _btn(event, "b") or event.is_action_pressed("ui_cancel")


func _menu_input(event: InputEvent) -> bool:
	if not _box.is_empty():   # the name box: the keyboard's Enter / Esc are read by _input; a controller's A / B here
		if _confirm(event):
			_box_submit()
		elif _back(event):
			_box_cancel()
		else:
			return false
		return true
	var id: String = MENU_ITEMS[_sel]["id"]
	if _dir(event, "down"):
		_select(_sel + 1)
	elif _dir(event, "up"):
		_select(_sel - 1)
	elif id == "spectate" and (_dir(event, "left") or _dir(event, "right")):
		_toggle_spectate()
	elif _confirm(event):
		match id:
			"host":
				_start_host()
			"join":
				_start_join()
			"spectate":
				_toggle_spectate()
			"name":
				_open_name_entry()
			"back":
				SceneRouter.go_to(SceneRouter.MAIN_MENU)
	elif _back(event):
		SceneRouter.go_to(SceneRouter.MAIN_MENU)
	else:
		return false
	return true


func _host_input(event: InputEvent) -> bool:
	if not _box.is_empty():   # the reply code box (keyboard: _input)
		if _confirm(event):
			_box_submit()
		elif _back(event):
			_box_cancel()
		else:
			return false
		return true
	if _btn(event, "c"):
		_copy_code()
	elif _btn(event, "s"):
		if _net.Code == "":
			pass   # no code yet
		elif _net.HasLobbyNumber and not _show_backup and _net.LongCode != "":
			_show_backup = true   # first S: the backup code; second S: the reply code box
			_host_info()
		else:
			_open_reply_entry()
	elif _btn(event, "start") or _confirm(event):
		if _room and _room.active():
			_enter_room()
	elif _back(event):
		if int(_net.MemberCount) > 0:
			_enter_room()
		else:
			_leave_lobby("Lobby closed.")
	else:
		return false
	return true


## JOIN: the digit picker (Up / Down, Left / Right, A, B; S = the backup code box), or the backup code box (A / B).
func _join_input(event: InputEvent) -> bool:
	var kind := str(_box.get("kind", ""))
	var copy: bool = _net != null and _net.ReplyCode != ""
	if kind == "digits":
		if _dir(event, "up"):
			_step_digit(1)
		elif _dir(event, "down"):
			_step_digit(-1)
		elif _dir(event, "left"):
			_move_cursor(-1)
		elif _dir(event, "right"):
			_move_cursor(1)
		elif _btn(event, "s"):
			_to_code_mode("")
		elif _btn(event, "c") and copy:
			_copy_code()
		elif _confirm(event):
			_box_submit()
		elif _back(event):
			_box_cancel()
		else:
			return false
		return true
	if kind == "code":
		if _btn(event, "c") and copy:
			_copy_code()
		elif _confirm(event):
			_box_submit()
		elif _back(event):
			_box_cancel()
		else:
			return false
		return true
	return false


func _room_input(event: InputEvent) -> bool:
	if _room == null or _room.room.is_empty():
		if _back(event):
			_leave_lobby("You left the lobby.")
			return true
		return false
	if not _setup.is_empty():
		return _setup_input(event)
	var picking := _picking_now()
	var ready := bool(_my_pick.get("ready", false))
	var host: bool = _net != null and bool(_net.IsHost)
	if _btn(event, "ab"):
		_try_pass()
	elif _btn(event, "s"):
		if not picking:
			var on: bool = not _room.spectating(_room.my_id)
			_room.set_spectate(on)
			_flash("Spectate only: you'll watch the matches." if on else "Back in line: you're at the back.")
	elif _btn(event, "c"):
		# (C is also a "back" key in menus: never leave with it here)
		if str(_room.current_match().get("state", "")) == "fighting" and not picking:
			_room.watch()
	elif host and _btn(event, "start"):
		_show_invite()
	elif _confirm(event):
		_open_setup()
	elif _back(event):
		if picking and ready:
			_set_ready(false)
		elif _leave_armed > 0.0:
			_leave_lobby("You left the lobby." if not host else "Lobby closed.")
		else:
			_leave_armed = LEAVE_SECONDS
			_refresh_room()
	else:
		return false
	return true


func _copy_code() -> void:
	if _net == null:
		return
	var code := ""
	match _page:
		Page.HOST:
			code = _net.LongCode if _show_backup else _net.Code
		Page.JOIN:
			code = _net.ReplyCode
		Page.ROOM:
			code = str(_room.room.get("code", "")) if _room else ""
	if code == "":
		return
	DisplayServer.clipboard_set(code)
	if _page == Page.ROOM:
		_flash("Copied %s to the clipboard." % code)
	else:
		_set_status("Copied %s to the clipboard." % code)


# --- Small helpers ------------------------------------------------------------------------------

func _lbl(parent: Node, text: String, font_size: int, color: Color, font: Font, rect: Rect2,
		align := HORIZONTAL_ALIGNMENT_LEFT, valign := VERTICAL_ALIGNMENT_CENTER) -> Label:
	var l := NetsuUI.label(text, font_size, color, font)
	l.position = rect.position
	l.size = rect.size
	l.horizontal_alignment = align
	l.vertical_alignment = valign
	parent.add_child(l)
	return l


## A box (a Panel with its own StyleBoxFlat: _sb(panel) changes its colours later).
func _panel(parent: Node, rect: Rect2, fill: Color, edge := Color(0, 0, 0, 0), width := 0, radius := 0) -> Panel:
	var p := Panel.new()
	p.position = rect.position
	p.size = rect.size
	p.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var sb := StyleBoxFlat.new()
	sb.bg_color = fill
	sb.border_color = edge
	sb.set_border_width_all(width)
	sb.set_corner_radius_all(radius)
	sb.anti_aliasing = true
	p.add_theme_stylebox_override("panel", sb)
	parent.add_child(p)
	return p


func _sb(p: Panel) -> StyleBoxFlat:
	return p.get_theme_stylebox("panel") as StyleBoxFlat


# --- For tests / tools ------------------------------------------------------------------------

## Test driver hooks (container tests): open a lobby, join one, pick, get ready.
func test_host() -> void:
	_start_host()


func test_join(code: String) -> void:
	_start_join()
	_join(code)


func test_pick(fighter: int, color: int, assist: int) -> void:
	if _page != Page.ROOM or _room.my_side() < 0:
		return
	_my_pick["f"] = fighter
	_my_pick["c"] = color
	_my_pick["a"] = assist
	_send_pick()
	_refresh_room()


func test_stage(index: int) -> void:
	if _page == Page.ROOM and bool(_net.IsHost):
		_room.set_stage(index)


func test_ready() -> void:
	if _page == Page.ROOM:
		_set_ready(true)


## SETUP: the menu as test_state shows it ({} = closed).
func test_setup() -> Dictionary:
	if _setup.is_empty():
		return {}
	var values := {}
	for id in _setup_ids():
		values[id] = _setup_value(id) if id != "ready" else str(_setup_ui["rows"]["ready"]["label"].text)
	return {"row": _setup["row"], "rows": _setup_ids(), "values": values, "f": _setup["f"], "c": _setup["c"], "a": _setup["a"],
		"stage": _setup_stage(), "music": _setup_music(), "editable": _setup_editable(_setup["row"])}


func test_page() -> int:
	return _page


func test_room() -> void:
	if _page != Page.ROOM:
		_enter_room()


## What the screen shows (harness tests): the page, the open box, the code, INFORMATION and the legend's labels.
func test_state() -> Dictionary:
	var legend := []
	for it in _legend_items:
		legend.append("%s:%s%s" % ["/".join(it["keys"]), it["label"], " (dim)" if bool(it.get("dim", false)) else ""])
	return {"page": ["MENU", "HOST", "JOIN", "ROOM"][_page], "box": str(_box.get("kind", "")), "text": str(_box.get("text", "")),
		"digits": _digit_text(), "slots": _digits.duplicate(), "cursor": _cursor, "joining": _joining,
		"info": _footer["text"].text, "legend": legend, "device": _device, "setup": test_setup(),
		"your_setup": str(_room_ui["setup"].text) if _room_ui.has("setup") and is_instance_valid(_room_ui["setup"]) else "",
		"vs": _test_vs(), "list": _test_list()}


## The VS panel as shown: per side {"name", "title", "fighter", "detail", "icon"}.
func _test_vs() -> Array:
	var out := []
	if _room_ui.is_empty():
		return out
	for side in 2:
		var s: Dictionary = _room_ui["vs"][side]
		var c: Dictionary = _room_ui["strip"]["side"][side]
		out.append({"name": s["name"].text, "title": s["plate"].title_id, "fighter": c["fighter"].text, "detail": c["detail"].text,
			"icon": s["avatar"].texture, "chip": s["chip"][1].visible})
	return out


## The player list as shown: [{"name", "title", "icon"}] for the visible rows.
func _test_list() -> Array:
	var out := []
	for e in _entries:
		if e["root"].visible:
			out.append({"name": e["name"].text, "title": e["plate"].title_id, "icon": e["avatar"].texture})
	return out
