extends Control
## ONLINE LOBBY  (Oct 24 2026; group lobbies, king of the hill: Oct 25)
##
## Main menu > ONLINE. Play friends over the internet with rollback netcode, no server of our own:
##   CREATE LOBBY  this computer opens a lobby and shows a LOBBY CODE (5 digits, "48213"). Send it to your
##                 friends (C copies it). S shows the backup code (the long code below).
##   JOIN LOBBY    type or paste (Ctrl+V) the code you were sent, press Enter.
##   NAME          the name the others see (empty = "Player 2" and so on).
##   In the lobby  up to 8 players, KING OF THE HILL (the rules: game/autoloads/online_room.gd): everyone stands in
##                 one line; the first two fight (king = player 1 side, challenger = player 2 side), the winner
##                 stays on, the loser goes to the back of the line. The two players pick a fighter (Left /
##                 Right), colour (Up / Down) and assist (S) here, A = ready (60 seconds, then what they have is
##                 locked in). Everyone else watches the fight: it opens by itself (B there = back here; A here =
##                 watch again). S = sit out / back in line. The host picks the stage (C; RANDOM = a new one
##                 each match) and its Options rules (rounds, time, intros) are used. Start (host) = the invite
##                 screen with the codes again. B = leave (twice).
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
	{"id": "name", "label": "NAME", "blurb": "The name the other players see in a lobby (A to change it)."},
	{"id": "back", "label": "BACK", "blurb": "Back to the main menu."},
]
const JOIN_HELP := "Type the 5-digit code from the host's screen, then press Enter."
const ROW_H := 46.0

@export var port: int = 7777

var _net: Node
var _room: Node
var _page := Page.MENU
var _sel := 0
var _my_pick := {}                 # while I'm picking: {"f", "c", "a", "ready", "match"}
var _reply_entry := false
var _show_backup := false          # host: the long code is shown (S)
var _name_entry := false
var _leave_armed := 0.0            # B once: "press B again to leave" (seconds left)
var _t := 0.0

# nodes
var _title: Label
var _panel_root: Control
var _footer: Dictionary
var _menu_labels: Array[Label] = []
var _menu_bar: ColorRect
var _code_label: Label
var _code_caption: Label
var _info: Label
var _status: Label
var _entry: LineEdit
var _cards: Array = [{}, {}]
var _mid: Dictionary = {}
var _list_root: Control
var _list_title: Label
var _ping_label: Label


func _ready() -> void:
	_net = get_node_or_null("/root/NetsuOnline")
	_room = get_node_or_null("/root/OnlineRoom")
	NetsuUI.settings_backdrop(self, 0.55)
	NetsuUI.header(self, "ONLINE")
	_title = NetsuUI.label("", 46, Color.WHITE, NetsuUI.sans(5))
	NetsuUI.glow(_title, Color(0.25, 0.5, 1.0, 0.35), 8)
	_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_title.position = Vector2(0, 110)
	_title.size = Vector2(1920, 70)
	add_child(_title)
	_panel_root = Control.new()
	_panel_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_panel_root)
	NetsuUI.full_rect(_panel_root)
	_footer = NetsuUI.footer(self)
	if _net:
		_net.connect("StatusChanged", _on_status)
		_net.connect("CodeReady", _on_code_ready)
		_net.connect("ReplyCodeReady", _on_reply_code)
		_net.connect("Connected", _on_connected)
		_net.connect("Disconnected", _on_disconnected)
		_net.connect("MemberJoined", _on_member_joined)
	if _room:
		_room.room_changed.connect(_refresh_room)
		_room.notice.connect(_set_status)
		_room.lobby_opened()
	if _room and _room.active():
		_enter_room()   # back from a fight (or from watching one)
	else:
		_show_menu()
	if MatchSetup.online_notice != "":
		_set_status(MatchSetup.online_notice)
		MatchSetup.online_notice = ""
	if _net == null or _room == null:
		_set_status("Online play needs the game's C# part: build the project in Godot (Build button), then restart.")


func _exit_tree() -> void:
	if _room:
		_room.lobby_closed()


func _process(delta: float) -> void:
	_t += delta
	if _leave_armed > 0.0:
		_leave_armed = maxf(_leave_armed - delta, 0.0)
		if _leave_armed == 0.0:
			_refresh_room()   # (the "press B again" line goes away)
	if _page == Page.ROOM and _net:
		if _ping_label:
			var ping: int = _net.Ping
			_ping_label.text = ("PING  %d ms" % ping) if ping >= 0 else ""
		_refresh_clock()
	if _page == Page.HOST and _code_label and String(_code_label.text).begins_with("."):
		_code_label.text = ".".repeat(3 + int(_t * 3.0) % 4)


# --- Pages --------------------------------------------------------------------------------

func _clear_panel() -> void:
	for c in _panel_root.get_children():
		c.queue_free()
	_menu_labels.clear()
	_code_label = null
	_info = null
	_entry = null
	_cards = [{}, {}]
	_mid = {}
	_list_root = null
	_list_title = null
	_ping_label = null
	_reply_entry = false
	_show_backup = false
	_name_entry = false


func _add_status(y: float) -> void:
	_status = NetsuUI.label("", 26, Color(0.8, 0.88, 1.0), NetsuUI.body())
	_status.position = Vector2(360, y)
	_status.size = Vector2(1200, 60)
	_status.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_panel_root.add_child(_status)
	if _net and _net.LastStatus != "":
		_status.text = _net.LastStatus


func _show_menu() -> void:
	_page = Page.MENU
	_clear_panel()
	_title.text = "PLAY ONLINE"
	NetsuUI.frame_panel(_panel_root, Rect2(610, 270, 700, 410))
	_menu_bar = ColorRect.new()
	_menu_bar.color = Color(0.2, 0.45, 1.0, 0.28)
	_menu_bar.size = Vector2(620, 66)
	_menu_bar.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_panel_root.add_child(_menu_bar)
	for i in MENU_ITEMS.size():
		var l := NetsuUI.label(_menu_text(i), 40, NetsuUI.DIM, NetsuUI.serif(600, 2))
		l.position = Vector2(650, 310 + i * 88)
		l.size = Vector2(620, 66)
		l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		l.clip_text = true
		_panel_root.add_child(l)
		_menu_labels.append(l)
	_add_status(720)
	_select(_sel)
	_footer["prompts"].text = "UP / DOWN  SELECT     A  CONFIRM     B  BACK"


func _menu_text(i: int) -> String:
	if MENU_ITEMS[i]["id"] == "name":
		var n: String = _room.my_name() if _room else ""
		return "NAME:  %s" % (n.to_upper() if n != "" else "(NONE)")
	return MENU_ITEMS[i]["label"]


func _select(i: int) -> void:
	_sel = wrapi(i, 0, MENU_ITEMS.size())
	for j in _menu_labels.size():
		_menu_labels[j].add_theme_color_override("font_color", NetsuUI.TEXT if j == _sel else NetsuUI.DIM)
	if _menu_bar:
		_menu_bar.position = Vector2(650, 310 + _sel * 88)
	_footer["text"].text = MENU_ITEMS[_sel]["blurb"]


## MENU > NAME: a box to type the name in (Enter keeps it, Esc doesn't).
func _open_name_entry() -> void:
	_name_entry = true
	var row := MENU_ITEMS.size() - 2
	_menu_labels[row].visible = false
	_entry = _make_entry(Vector2(660, 310 + row * 88 - 2), "YOUR NAME")
	_entry.size = Vector2(600, 70)
	_entry.max_length = _room.MAX_NAME if _room else 16
	_entry.add_theme_font_size_override("font_size", 40)
	_entry.text = _room.my_name() if _room else ""
	_entry.text_submitted.connect(_on_name_submitted)
	_entry.grab_focus.call_deferred()
	_entry.caret_column = _entry.text.length()
	_footer["prompts"].text = "ENTER  KEEP     ESC  CANCEL"


func _on_name_submitted(text: String) -> void:
	if _room:
		_room.set_my_name(text)
	_close_name_entry()


func _close_name_entry() -> void:
	if _entry:
		_entry.queue_free()
		_entry = null
	_name_entry = false
	var row := MENU_ITEMS.size() - 2
	_menu_labels[row].text = _menu_text(row)
	_menu_labels[row].visible = true
	_footer["prompts"].text = "UP / DOWN  SELECT     A  CONFIRM     B  BACK"


func _start_host() -> void:
	if _net == null:
		return
	_net.Host(port)
	_show_invite()


## The host's code screen: right after opening the lobby, and from the room (Start).
func _show_invite() -> void:
	_page = Page.HOST
	_clear_panel()
	_title.text = "YOUR LOBBY"
	NetsuUI.frame_panel(_panel_root, Rect2(360, 230, 1200, 520))
	_code_caption = NetsuUI.label("LOBBY CODE", 28, NetsuUI.CYAN, NetsuUI.sans(8))
	_code_caption.position = Vector2(360, 270)
	_code_caption.size = Vector2(1200, 40)
	_code_caption.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_panel_root.add_child(_code_caption)
	_code_label = NetsuUI.label("...", 104, Color.WHITE, NetsuUI.serif(700, 6))
	NetsuUI.glow(_code_label, Color(0.25, 0.5, 1.0, 0.4), 10)
	_code_label.position = Vector2(360, 315)
	_code_label.size = Vector2(1200, 140)
	_code_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_panel_root.add_child(_code_label)
	_info = NetsuUI.label("Working out your address...", 25, NetsuUI.DIM, NetsuUI.body())
	_info.position = Vector2(420, 470)
	_info.size = Vector2(1080, 130)
	_info.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_info.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_panel_root.add_child(_info)
	_add_status(640)
	_footer["text"].text = "Send the code to your friends: they pick JOIN LOBBY and type it in (up to 8 players)."
	_footer["prompts"].text = "C  COPY CODE     A  TO THE ROOM     B  CLOSE LOBBY"
	if _net.Code != "":
		_on_code_ready(_net.Code, _net.LanCode, "")


func _start_join() -> void:
	if _net == null:
		return
	_page = Page.JOIN
	_clear_panel()
	_title.text = "JOIN A LOBBY"
	NetsuUI.frame_panel(_panel_root, Rect2(360, 230, 1200, 520))
	var cap := NetsuUI.label("ENTER THE LOBBY CODE", 28, NetsuUI.CYAN, NetsuUI.sans(8))
	cap.position = Vector2(360, 270)
	cap.size = Vector2(1200, 40)
	cap.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_panel_root.add_child(cap)
	_entry = _make_entry(Vector2(560, 330))
	_entry.text_submitted.connect(func(t): _join(t))
	_info = NetsuUI.label(JOIN_HELP, 25, NetsuUI.DIM, NetsuUI.body())
	_info.position = Vector2(420, 470)
	_info.size = Vector2(1080, 130)
	_info.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_info.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_panel_root.add_child(_info)
	_add_status(640)
	_set_status("")
	_footer["text"].text = "A backup code (like K7Q2-M9X4-PA3D) works too, and on the same network an address (192.168.1.20)."
	_footer["prompts"].text = "ENTER  CONNECT     ESC  BACK"
	_entry.grab_focus.call_deferred()


func _make_entry(pos: Vector2, placeholder := "12345") -> LineEdit:
	var e := LineEdit.new()
	e.position = pos
	e.size = Vector2(800, 110)
	e.alignment = HORIZONTAL_ALIGNMENT_CENTER
	e.max_length = 40
	e.placeholder_text = placeholder
	e.add_theme_font_override("font", NetsuUI.serif(700, 4))
	e.add_theme_font_size_override("font_size", 72)
	e.add_theme_color_override("font_color", Color.WHITE)
	e.add_theme_color_override("font_placeholder_color", Color(1, 1, 1, 0.25))
	var box := StyleBoxFlat.new()
	box.bg_color = Color(0.02, 0.03, 0.12, 0.9)
	box.border_color = Color(0.45, 0.7, 1.0, 0.9)
	box.set_border_width_all(2)
	box.set_content_margin_all(10)
	e.add_theme_stylebox_override("normal", box)
	e.add_theme_stylebox_override("focus", box)
	_panel_root.add_child(e)
	return e


func _join(text: String) -> void:
	if _net == null or text.strip_edges() == "":
		return
	if _net.Join(text.strip_edges()):
		_info.text = "Looking up the lobby..." if _net.IsLobbyNumber(text) else "Connecting..."


## Host: S opens a box for a joiner's reply code.
func _open_reply_entry() -> void:
	if _reply_entry or _page != Page.HOST:
		return
	_reply_entry = true
	_info.text = "Type the REPLY CODE the player sent you, then press Enter (Esc: cancel)."
	_entry = _make_entry(Vector2(560, 555), "XXXX-XXXX-XXXX")
	_entry.size = Vector2(800, 80)
	_entry.add_theme_font_size_override("font_size", 48)
	_entry.text_submitted.connect(_on_reply_submitted)
	_entry.grab_focus.call_deferred()
	_status.position.y = 690


func _on_reply_submitted(text: String) -> void:
	if _net.AcceptReply(text.strip_edges()):
		_close_reply_entry()


func _close_reply_entry() -> void:
	if _entry:
		_entry.queue_free()
		_entry = null
	_reply_entry = false


func _leave_lobby(text: String) -> void:
	if _net:
		_net.Leave()
	_show_menu()
	_set_status(text)


# --- The room -----------------------------------------------------------------------------------

func _enter_room() -> void:
	_page = Page.ROOM
	_clear_panel()
	_leave_armed = 0.0
	for side in 2:
		_build_card(side)
	_build_middle()
	_build_list()
	_ping_label = NetsuUI.label("", 22, NetsuUI.DIM, NetsuUI.sans(3))
	_ping_label.position = Vector2(1560, 128)
	_ping_label.size = Vector2(300, 30)
	_ping_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_panel_root.add_child(_ping_label)
	_add_status(895)
	_status.size.y = 44
	_status.add_theme_font_size_override("font_size", 23)
	_set_status("")
	_refresh_room()


func _build_card(side: int) -> void:
	var x := 110.0 if side == 0 else 1170.0
	var accent := NetsuUI.BLUE if side == 0 else NetsuUI.RED
	NetsuUI.frame_panel(_panel_root, Rect2(x, 190, 640, 400), accent)
	var c := {}
	var clip := Control.new()
	clip.clip_contents = true
	clip.position = Vector2(x + 8, 198)
	clip.size = Vector2(624, 384)
	clip.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_panel_root.add_child(clip)
	var art := TextureRect.new()
	art.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	art.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	art.position = Vector2(150, -10)   # (the right half of the card: the names are on the left)
	art.size = Vector2(624, 700)
	art.modulate = Color(1, 1, 1, 0.92)
	art.mouse_filter = Control.MOUSE_FILTER_IGNORE
	art.flip_h = side == 1
	clip.add_child(art)
	c["art"] = art
	var shade := NetsuUI.gradient_rect(Color(0.02, 0.03, 0.12, 0.0), Color(0.02, 0.03, 0.12, 0.94), true)
	shade.position = Vector2(0, 170)
	shade.size = Vector2(624, 214)
	clip.add_child(shade)
	var tag := NetsuUI.label("", 22, accent.lightened(0.35), NetsuUI.sans(6))
	tag.position = Vector2(x + 28, 204)
	tag.size = Vector2(590, 32)
	_panel_root.add_child(tag)
	c["tag"] = tag
	var who := NetsuUI.label("", 30, Color.WHITE, NetsuUI.sans(3))
	who.position = Vector2(x + 28, 236)
	who.size = Vector2(590, 40)
	who.clip_text = true
	_panel_root.add_child(who)
	c["who"] = who
	var name_l := NetsuUI.label("", 58, Color.WHITE, NetsuUI.serif(700, 2))
	NetsuUI.glow(name_l, Color(accent, 0.45), 8)
	name_l.position = Vector2(x + 28, 440)
	name_l.size = Vector2(590, 72)
	_panel_root.add_child(name_l)
	c["name"] = name_l
	var detail := NetsuUI.label("", 22, NetsuUI.TEXT, NetsuUI.sans(2))
	detail.position = Vector2(x + 32, 512)
	detail.size = Vector2(590, 64)
	_panel_root.add_child(detail)
	c["detail"] = detail
	var ready := NetsuUI.label("", 36, Color(1.0, 0.86, 0.35), NetsuUI.sans(8))
	NetsuUI.glow(ready, Color(0.6, 0.4, 0.0, 0.6), 8)
	ready.position = Vector2(x + 28, 390)
	ready.size = Vector2(590, 50)
	ready.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT if side == 0 else HORIZONTAL_ALIGNMENT_LEFT
	_panel_root.add_child(ready)
	c["ready"] = ready
	_cards[side] = c


## Between the cards: VS, what's happening (match number, the pick clock), the last result.
func _build_middle() -> void:
	var vs := NetsuUI.label("VS", 110, Color.WHITE, NetsuUI.serif(700))
	NetsuUI.glow(vs, Color(0.3, 0.5, 1.0, 0.5), 12)
	vs.position = Vector2(760, 250)
	vs.size = Vector2(400, 150)
	vs.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_panel_root.add_child(vs)
	_mid["vs"] = vs
	var head := NetsuUI.label("", 22, NetsuUI.CYAN, NetsuUI.sans(6))
	head.position = Vector2(760, 200)
	head.size = Vector2(400, 40)
	head.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_panel_root.add_child(head)
	_mid["head"] = head
	var clock := NetsuUI.label("", 44, Color.WHITE, NetsuUI.sans(4))
	clock.position = Vector2(760, 392)
	clock.size = Vector2(400, 56)
	clock.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_panel_root.add_child(clock)
	_mid["clock"] = clock
	var caption := NetsuUI.label("", 18, NetsuUI.CYAN, NetsuUI.sans(5))
	caption.position = Vector2(760, 446)
	caption.size = Vector2(400, 28)
	caption.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_panel_root.add_child(caption)
	_mid["caption"] = caption
	var line := NetsuUI.label("", 20, NetsuUI.TEXT, NetsuUI.sans(2))
	line.position = Vector2(770, 482)
	line.size = Vector2(380, 110)
	line.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	line.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_panel_root.add_child(line)
	_mid["line"] = line


## Under the cards: everyone in the lobby, in line order (sitting out at the end), and the rules.
func _build_list() -> void:
	NetsuUI.frame_panel(_panel_root, Rect2(110, 612, 1700, 278))
	_list_title = NetsuUI.label("", 22, NetsuUI.CYAN, NetsuUI.sans(6))
	_list_title.position = Vector2(140, 620)
	_list_title.size = Vector2(1640, 36)
	_panel_root.add_child(_list_title)
	_list_root = Control.new()
	_list_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_list_root.position = Vector2(140, 660)
	_panel_root.add_child(_list_root)


func _refresh_room() -> void:
	if _page != Page.ROOM or _room == null:
		return
	var room: Dictionary = _room.room
	if room.is_empty():
		return
	var code := str(room.get("code", ""))
	_title.text = ("LOBBY  %s" % code) if code != "" else "ONLINE LOBBY"
	var m: Dictionary = _room.current_match()
	var state := str(m.get("state", "none"))
	var my_side: int = _room.my_side()
	# my pick: starts from what the host has for me when a new match comes up
	if my_side >= 0 and state == "picking":
		var mine: Dictionary = _room.pick_of(_room.my_id)
		if int(_my_pick.get("match", -1)) != int(m.get("id", -1)):
			_my_pick = {"f": int(mine.get("f", 0)), "c": int(mine.get("c", 0)), "a": int(mine.get("a", 0)),
				"ready": bool(mine.get("ready", false)), "match": int(m.get("id", -1))}
		elif bool(mine.get("ready", false)):
			_my_pick["ready"] = true   # (the clock ran out: the host locked it in)
	# the two cards
	var ids := [int(m.get("p1", -1)), int(m.get("p2", -1))]
	var line: Array = room.get("queue", [])
	if not state in ["picking", "fighting"]:
		ids = [int(line[0]) if line.size() > 0 else -1, int(line[1]) if line.size() > 1 else -1]
	for side in 2:
		_fill_card(side, ids[side], m, state)
	_fill_middle(room, m, state)
	_fill_list(room)
	_fill_prompts(m, state, my_side)


func _fill_card(side: int, id: int, m: Dictionary, state: String) -> void:
	var c: Dictionary = _cards[side]
	if c.is_empty():
		return
	var streak := int(_room.room.get("streak", 0))
	var king := side == 0 and id >= 0 and id == int(_room.room.get("streak_id", -2)) and streak > 0
	c["tag"].text = ("KING  ·  %d WIN%s IN A ROW" % [streak, "" if streak == 1 else "S"]) if king else ("PLAYER 1 SIDE" if side == 0 else "CHALLENGER")
	if id < 0:
		c["who"].text = ""
		c["name"].text = "..."
		c["detail"].text = "Waiting for a challenger to join.\nSend them the lobby code!" if side == 1 else "Waiting for players."
		c["art"].texture = null
		c["ready"].text = ""
		return
	var me: bool = id == _room.my_id
	c["who"].text = _room.member_name(id).to_upper() + ("   (YOU)" if me else "")
	var pick: Dictionary = {}
	if state == "fighting":
		var p: Dictionary = m.get("p", {})
		var k := str(side + 1)
		pick = {"f": int(p.get("f" + k, 0)), "c": int(p.get("c" + k, 0)), "a": int(p.get("a" + k, 0)), "ready": true}
	elif state == "picking":
		pick = _my_pick if me else _room.pick_of(id)
	if pick.is_empty():
		c["name"].text = ""
		c["detail"].text = "Next up." if side == 1 else "On the hill."
		c["art"].texture = null
		c["ready"].text = ""
		return
	var f := clampi(int(pick.get("f", 0)), 0, maxi(0, MatchSetup.fighter_count() - 1))
	var prof = MatchSetup.fighter_profile(f)
	c["art"].texture = prof.Render if prof else null
	c["name"].text = String(prof.ShortName).to_upper() if prof else "?"
	var color_name := MatchSetup.palette_name(f, int(pick.get("c", 0))) if MatchSetup.palette_count(f) > int(pick.get("c", 0)) else ""
	c["detail"].text = "COLOUR  %s\nASSIST  %s" % [color_name.to_upper(), MatchSetup.assist_name(int(pick.get("a", 0))).to_upper()]
	var where := str(_room.member(id).get("state", ""))
	if state == "fighting":
		c["ready"].text = "FIGHTING"
	elif bool(pick.get("ready", false)):
		c["ready"].text = "READY!"
	elif where != "lobby" and not me:
		c["ready"].text = "COMING BACK..."
	else:
		c["ready"].text = "PICKING..."


func _fill_middle(room: Dictionary, m: Dictionary, state: String) -> void:
	if _mid.is_empty():
		return
	var rules: Dictionary = room.get("rules", {})
	var rounds := int(rules.get("rounds", 2))
	var time := int(rules.get("time", 99))
	var stage := int(room.get("stage", -1))
	var stage_text := "RANDOM" if stage < 0 or stage >= MatchSetup.stage_count() else MatchSetup.stage_name(stage).to_upper()
	if state == "fighting":
		var p: Dictionary = m.get("p", {})
		stage_text = MatchSetup.stage_name(int(p.get("stage", 0))).to_upper()
	_mid["head"].text = ("MATCH %d" % int(m.get("id", 0))) if state in ["picking", "fighting"] else "KING OF THE HILL"
	var lines := ["STAGE  %s" % stage_text,
		"First to %d round%s  ·  %s" % [rounds, "" if rounds == 1 else "s", "no time limit" if time <= 0 else "%d s" % time]]
	var last: Dictionary = room.get("last", {})
	if not last.is_empty():
		var w := str(last.get("w_name", "?"))
		lines.append("LAST:  %s beat %s%s" % [w, str(last.get("l_name", "?")), "  (left)" if bool(last.get("forfeit", false)) else ""])
	_mid["line"].text = "\n".join(lines)
	_refresh_clock()


func _refresh_clock() -> void:
	if _mid.is_empty() or _room == null:
		return
	var m: Dictionary = _room.current_match()
	var state := str(m.get("state", "none"))
	if state == "picking":
		var left := ceili(_room.pick_time_left())
		var here: bool = _room.pickers_here()
		_mid["clock"].text = ("%d" % left) if here else "· · ·"
		_mid["clock"].add_theme_color_override("font_color", Color(1.0, 0.45, 0.4) if left <= 10 else Color.WHITE)
		_mid["caption"].text = "SECONDS TO PICK" if here else "PLAYERS COMING BACK"
	elif state == "fighting":
		_mid["clock"].text = "LIVE"
		_mid["clock"].add_theme_color_override("font_color", Color(1.0, 0.35, 0.35))
		_mid["caption"].text = "FIGHT ON"
	else:
		_mid["clock"].text = ""
		_mid["caption"].text = ""


func _fill_list(room: Dictionary) -> void:
	if _list_root == null:
		return
	for ch in _list_root.get_children():
		ch.queue_free()
	var members: Dictionary = room.get("members", {})
	var line: Array = room.get("queue", [])
	var ids: Array = line.duplicate()
	for v in room.get("order", []):
		if not int(v) in ids:
			ids.append(int(v))   # sitting out: after the line
	_list_title.text = "PLAYERS  %d / 8" % members.size() + ("     ·     WAITING FOR PLAYERS: SEND THE LOBBY CODE" if members.size() < 2 else "")
	var m: Dictionary = _room.current_match()
	for i in ids.size():
		var id := int(ids[i])
		var info: Dictionary = members.get(str(id), {})
		if info.is_empty():
			continue
		var col := i / 4   # (the line reads down the left column, then the right)
		var row := i % 4
		var x := col * 830.0
		var y := row * ROW_H
		var pos := line.find(id)
		var me: bool = id == _room.my_id
		var num := NetsuUI.label(("%d" % (pos + 1)) if pos >= 0 else "–", 26, NetsuUI.CYAN if pos >= 0 else NetsuUI.DIM, NetsuUI.sans(2))
		num.position = Vector2(x, y)
		num.size = Vector2(44, ROW_H)
		num.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		_list_root.add_child(num)
		var name_text := str(info.get("name", "?")).to_upper()
		if id == 0:
			name_text += "  ·  HOST"
		if me:
			name_text += "  (YOU)"
		var nm := NetsuUI.label(name_text, 26, Color.WHITE if me else NetsuUI.TEXT, NetsuUI.sans(2))
		nm.position = Vector2(x + 50, y)
		nm.size = Vector2(420, ROW_H)
		nm.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		nm.clip_text = true
		_list_root.add_child(nm)
		var bits := []
		if id == int(m.get("p1", -1)) and str(m.get("state", "")) in ["picking", "fighting"]:
			bits.append("KING" if id == int(room.get("streak_id", -2)) and int(room.get("streak", 0)) > 0 else "PLAYER 1")
		elif id == int(m.get("p2", -1)) and str(m.get("state", "")) in ["picking", "fighting"]:
			bits.append("CHALLENGER")
		elif pos >= 0:
			bits.append("IN LINE")
		else:
			bits.append("SITTING OUT")
		var wins := int(info.get("wins", 0))
		if wins > 0:
			bits.append("%d WIN%s" % [wins, "" if wins == 1 else "S"])
		match str(info.get("state", "")):
			"fight":
				bits.append("FIGHTING")
			"watch":
				bits.append("WATCHING")
			"lobby":
				pass
			_:
				bits.append("AWAY")
		if _net and bool(_net.IsHost) and id != 0:
			var ping: int = _net.PingOf(id)
			if ping >= 0:
				bits.append("%d ms" % ping)
		var st := NetsuUI.label("  ·  ".join(bits), 20, NetsuUI.DIM, NetsuUI.sans(3))
		st.position = Vector2(x + 470, y)
		st.size = Vector2(340, ROW_H)
		st.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		st.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
		st.clip_text = true
		_list_root.add_child(st)


func _fill_prompts(m: Dictionary, state: String, my_side: int) -> void:
	var host: bool = _net != null and bool(_net.IsHost)
	var parts := []
	var text := ""
	var pos: int = _room.queue_position(_room.my_id)
	if my_side >= 0 and state == "picking":
		if bool(_my_pick.get("ready", false)):
			parts = ["B  NOT READY"]
			text = "Ready! The fight starts when %s is ready too." % _room.member_name(int(m.get("p2" if my_side == 0 else "p1", -1)))
		else:
			parts = ["LEFT / RIGHT  FIGHTER", "UP / DOWN  COLOUR", "S  ASSIST", "A  READY"]
			text = "You're up! Pick your fighter, then A."
	else:
		if state == "fighting" and my_side < 0:
			parts.append("A  WATCH")
			text = "%s and %s are fighting." % [_room.member_name(int(m.get("p1", -1))), _room.member_name(int(m.get("p2", -1)))]
		elif state == "picking":
			text = "%s and %s are picking their fighters." % [_room.member_name(int(m.get("p1", -1))), _room.member_name(int(m.get("p2", -1)))]
		else:
			text = "Waiting for at least 2 players in line."
		if pos >= 2:
			text += "  You're number %d in line." % (pos + 1)
		parts.append("S  BACK IN LINE" if pos < 0 else "S  SIT OUT")
	if host:
		parts.append("C  STAGE")
		parts.append("START  CODES")
	parts.append("B  LEAVE" if not (my_side >= 0 and state == "picking" and bool(_my_pick.get("ready", false))) else "")
	if _leave_armed > 0.0:
		text = "Press B again to leave the lobby."
	_footer["text"].text = text
	var shown := []
	for p in parts:
		if p != "":
			shown.append(p)
	_footer["prompts"].text = "     ".join(shown)


func _change(field: String, step: int) -> void:
	if _room.my_side() < 0 or str(_room.current_match().get("state", "")) != "picking" or bool(_my_pick.get("ready", false)):
		return
	var side: int = _room.my_side()
	match field:
		"f":
			_my_pick["f"] = wrapi(int(_my_pick["f"]) + step, 0, maxi(1, MatchSetup.fighter_count()))
			_my_pick["c"] = 0 if MatchSetup.palette_count(int(_my_pick["f"])) <= side else side
		"c":
			_my_pick["c"] = wrapi(int(_my_pick["c"]) + step, 0, maxi(1, MatchSetup.palette_count(int(_my_pick["f"]))))
		"a":
			_my_pick["a"] = wrapi(int(_my_pick["a"]) + step, 0, maxi(1, MatchSetup.assist_count()))
	_send_pick()
	_refresh_room()


func _set_ready(on: bool) -> void:
	if _room.my_side() < 0 or str(_room.current_match().get("state", "")) != "picking":
		return
	_my_pick["ready"] = on
	_send_pick()
	_refresh_room()


func _send_pick() -> void:
	_room.send_pick(int(_my_pick.get("f", 0)), int(_my_pick.get("c", 0)), int(_my_pick.get("a", 0)), bool(_my_pick.get("ready", false)))


# --- Network events ---------------------------------------------------------------------------

func _on_status(text: String) -> void:
	if _page == Page.ROOM and (text.begins_with("A player joined") or text.begins_with("Joined the lobby")):
		return   # the list shows it
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


## The lines under the host's code (the backup code while it's shown) and the prompts that go with them.
func _host_info(lan_code := "", note := "") -> void:
	var lines := []
	if _show_backup:
		lines.append("BACKUP CODE   %s" % _net.LongCode)
		lines.append("For when the 5-digit code doesn't work for someone (C copies it). Press S again if they then send you a reply code.")
	else:
		if lan_code != "" and lan_code != _net.Code:
			lines.append("Same network as you? Their code is  %s" % lan_code)
		if note != "":
			lines.append(note)
		lines.append("Port: UDP %d" % int(_net.LocalPort))
	_info.text = "\n".join(lines)
	var tail := "     A  TO THE ROOM     B  " + ("BACK TO THE ROOM" if int(_net.MemberCount) > 0 else "CLOSE LOBBY")
	if _net.HasLobbyNumber:
		_footer["prompts"].text = ("C  COPY BACKUP CODE     S  ENTER REPLY CODE" if _show_backup else "C  COPY CODE     S  BACKUP CODE") + tail
	else:
		_footer["prompts"].text = "C  COPY CODE     S  REPLY CODE" + tail


func _on_reply_code(code: String) -> void:
	if _page == Page.JOIN and _info:
		_info.text = "Couldn't reach the host directly. Send them your REPLY CODE and keep this screen open:\n%s   (C copies it)" % code


func _on_connected(host: bool) -> void:
	if not host:
		_enter_room.call_deferred()   # (after OnlineRoom has said hello)


## Host: the first player in takes the host from the invite screen to the room.
func _on_member_joined(_id: int) -> void:
	if _page == Page.HOST and not _reply_entry and int(_net.MemberCount) == 1:
		_enter_room.call_deferred()


func _on_disconnected(reason: String) -> void:
	if _page == Page.ROOM:
		_show_menu()
	elif _page == Page.JOIN and _info:
		_info.text = JOIN_HELP   # try another code
	if _page in [Page.MENU, Page.JOIN]:
		_set_status(reason)


# --- Input --------------------------------------------------------------------------------------

func _unhandled_input(event: InputEvent) -> void:
	if SceneRouter.is_busy():
		return
	if event is InputEventKey and event.pressed and event.keycode == KEY_C and event.ctrl_pressed:
		_copy_code()
		get_viewport().set_input_as_handled()
		return
	match _page:
		Page.MENU:
			if _name_entry:
				return
			_menu_input(event)
		Page.HOST:
			if event.is_action_pressed("p1_c"):
				_copy_code()
			elif event.is_action_pressed("p1_s"):
				if _net.Code == "":
					pass   # no code yet
				elif _net.HasLobbyNumber and not _show_backup and _net.LongCode != "":
					_show_backup = true   # first S: the backup code; second S: the reply code box
					_host_info()
				else:
					_open_reply_entry()
			elif event.is_action_pressed("p1_a") or event.is_action_pressed("p1_start") or event.is_action_pressed("ui_accept"):
				if not _reply_entry and _room and _room.active():
					_enter_room()
			elif event.is_action_pressed("ui_cancel") or event.is_action_pressed("p1_b"):
				if _reply_entry:
					_close_reply_entry()
				elif int(_net.MemberCount) > 0:
					_enter_room()
				else:
					_leave_lobby("Lobby closed.")
			else:
				return
		Page.JOIN:
			if event.is_action_pressed("ui_cancel"):
				_net.Leave()
				_show_menu()
			elif event.is_action_pressed("p1_c") and _net.ReplyCode != "":
				_copy_code()
			else:
				return
		Page.ROOM:
			_room_input(event)
			return
	get_viewport().set_input_as_handled()


func _input(event: InputEvent) -> void:
	# the text boxes eat keys: Escape still backs out of them
	if _entry and _entry.has_focus() and event is InputEventKey and event.pressed and event.keycode == KEY_ESCAPE:
		get_viewport().set_input_as_handled()
		if _page == Page.HOST:
			_close_reply_entry()
		elif _name_entry:
			_close_name_entry()
		else:
			_net.Leave()
			_show_menu()


func _menu_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_down", true) or event.is_action_pressed("p1_down", true):
		_select(_sel + 1)
	elif event.is_action_pressed("ui_up", true) or event.is_action_pressed("p1_up", true):
		_select(_sel - 1)
	elif event.is_action_pressed("ui_accept") or event.is_action_pressed("p1_a"):
		match MENU_ITEMS[_sel]["id"]:
			"host":
				_start_host()
			"join":
				_start_join()
			"name":
				_open_name_entry()
			"back":
				SceneRouter.go_to(SceneRouter.MAIN_MENU)
	elif event.is_action_pressed("ui_cancel") or event.is_action_pressed("p1_b"):
		SceneRouter.go_to(SceneRouter.MAIN_MENU)


func _room_input(event: InputEvent) -> void:
	var picking: bool = _room.my_side() >= 0 and str(_room.current_match().get("state", "")) == "picking"
	var ready := bool(_my_pick.get("ready", false))
	var host: bool = bool(_net.IsHost)
	var handled := true
	if picking and not ready and (event.is_action_pressed("p1_left", true) or event.is_action_pressed("ui_left", true)):
		_change("f", -1)
	elif picking and not ready and (event.is_action_pressed("p1_right", true) or event.is_action_pressed("ui_right", true)):
		_change("f", 1)
	elif picking and not ready and (event.is_action_pressed("p1_up", true) or event.is_action_pressed("ui_up", true)):
		_change("c", -1)
	elif picking and not ready and (event.is_action_pressed("p1_down", true) or event.is_action_pressed("ui_down", true)):
		_change("c", 1)
	elif event.is_action_pressed("p1_s"):
		if picking:
			if not ready:
				_change("a", 1)
		else:
			_room.set_sit_out(_room.queue_position(_room.my_id) >= 0)
	elif event.is_action_pressed("p1_c"):
		if host:   # (C is also a "back" key in menus: never leave with it here)
			var stage := int(_room.room.get("stage", -1)) + 1
			_room.set_stage(-1 if stage >= MatchSetup.stage_count() else stage)
	elif (event.is_action_pressed("p1_start") or event.is_action_pressed("pause")) and host:
		_show_invite()
	elif event.is_action_pressed("p1_a") or event.is_action_pressed("ui_accept"):
		if picking and not ready:
			_set_ready(true)
		elif not picking:
			_room.watch()
	elif event.is_action_pressed("p1_b") or event.is_action_pressed("ui_cancel"):
		if picking and ready:
			_set_ready(false)
		elif _leave_armed > 0.0:
			_leave_lobby("You left the lobby." if not host else "Lobby closed.")
		else:
			_leave_armed = 2.0
			_refresh_room()
	else:
		handled = false
	if handled:
		get_viewport().set_input_as_handled()


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
	_set_status("Copied %s to the clipboard." % code)


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


func test_page() -> int:
	return _page


func test_room() -> void:
	if _page != Page.ROOM:
		_enter_room()
