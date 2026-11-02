extends Control
## OPTIONS  (Oct 19 2026 mockups)
##
## The settings list grows out of the main menu's OPTIONS row (to the right of
## the menu, under the logo). Picking a page opens a full screen: the hall
## background, "✦ OPTIONS" in the corner, the page title and a glowing framed
## panel with the rows.
##
## Normally this runs INSIDE the main menu (embedded = true): the main menu adds
## it when OPTIONS is picked, Cecilia steps aside, and the settings list grows
## out of the OPTIONS row. Backing out emits `closed` and the main menu brings
## her back. Opened on its own (scenes/options/options_menu.tscn) it draws its
## own background instead. The pause menu and the character select open single
## pages (start_page) the same way.
##
##   Settings pages:  Up / Down  move    Left / Right  change    A  pick    B  back
##   Button pages:    Up / Down  move    Left / Right  other player    A  change    B  back
##
## Values are stored by the GameSettings autoload (game/autoloads/game_settings.gd),
## button layouts by Controls (game/autoloads/controls.gd).
##
## TO ADD A SETTING: add it to GameSettings.DEFAULTS, then add a row in _list_rows().
## Row types:  pick (left/right through a list), volume (0-100%), action, spacer.
## Layout numbers are mockup pixels (1672 x 941), converted with NetsuUI.m().

const CATEGORIES := [
	{"id": "system", "label": "SYSTEM SETTINGS", "title": "SYSTEM SETTINGS",
		"blurb": "Saving and language."},
	{"id": "sound", "label": "SOUND SETTINGS", "title": "SOUND SETTINGS",
		"blurb": "Music, sound effect, voice and announcer volume."},
	{"id": "pad", "label": "BUTTON SETTINGS", "title": "BUTTON SETTINGS",
		"blurb": "Choose what each controller button does, for both players."},
	{"id": "keyboard", "label": "KEYBOARD SETTINGS (BATTLE)", "title": "KEYBOARD SETTINGS (BATTLE)",
		"blurb": "Keyboard keys for fighting, for both players."},
	{"id": "menu_keys", "label": "KEYBOARD SETTINGS (MENU)", "title": "KEYBOARD SETTINGS (MENU)",
		"blurb": "Keyboard keys for moving around the menus."},
	{"id": "display", "label": "DISPLAY SETTINGS", "title": "DISPLAY SETTINGS",
		"blurb": "Window size, fullscreen, VSync and screen shape."},
	{"id": "game", "label": "GAME SETTINGS", "title": "GAME SETTINGS",
		"blurb": "CPU difficulty, rounds, round time and character intros."},
	{"id": "return", "label": "RETURN", "title": "", "blurb": "Back to the main menu."},
]

const BUTTON_NAMES := {
	"up": "Up", "down": "Down", "left": "Left", "right": "Right",
	"a": "A  (Light Attack)", "b": "B  (Medium Attack)", "c": "C  (Heavy Attack)", "s": "S  (Support)",
	"ab": "A + B", "bc": "B + C", "abc": "A + B + C", "start": "Start / Pause",
}
const MENU_NAMES := {
	"ui_up": "Up", "ui_down": "Down", "ui_left": "Left", "ui_right": "Right",
	"ui_accept": "Confirm", "ui_cancel": "Back",
}
## Xbox face-button colours for the controller icons.
const PAD_COLORS := {"A": Color(0.2, 0.68, 0.45), "B": Color(0.88, 0.22, 0.27),
	"X": Color(0.16, 0.5, 0.95), "Y": Color(0.95, 0.75, 0.2)}
const LIST_PROMPTS := "SELECT     LEFT / RIGHT  CHANGE     A  CONFIRM     B  BACK"
const MENU_PROMPTS := "UP / DOWN  SELECT     A  CONFIRM     B  BACK"
const ROW_TEXT := Color(0.9, 0.92, 1.0)

## Emitted when the player backs out (embedded mode). The node frees itself.
signal closed

## Emitted by "Start Game" on the Versus page (the main menu then opens the side select).
signal start_game

## True when running inside the main menu (set before adding it to the tree).
@export var embedded: bool = false
## Open straight onto one page ("versus", "pad", "keyboard", ...) instead of the
## settings list; backing out of that page closes the whole panel. Used by the
## Versus button and by the character select's settings shortcuts.
@export var start_page: String = ""
## Behind an open page: "hall" (the dark hall picture, menus) or "dim" (darken
## whatever is underneath - the pause menu uses this over the fight).
@export var backdrop: String = "hall"
## Embedded mode: the main menu's footer ({"root", "text", "prompts"}) to write help text into.
var footer_override: Dictionary = {}

@export_group("Settings list (mockup pixels)")
## The list lines up with the main menu rows: same first row and spacing.
@export var category_x: float = 615.0
@export var category_first_y: float = 341.0
@export var category_step: float = 54.5
@export var category_font_size: int = 30
@export_group("Rebinding")
@export var capture_seconds: float = 6.0

var _footer: Dictionary
var _cat := 0
var _cat_labels: Array[Label] = []
var _cat_bar: Node2D
var _cat_gem: Node2D
var _behind: Control          # the settings list (and its own background when not embedded)
var _list_shade: Control = null   # embedded: a soft dark band under the list (the menu art has bright lamps there)

var _page := ""               # open page id ("" = choosing a category)
var _sheet: Control
var _columns: Array = []      # one Array of row Dictionaries per column
var _col := 0
var _row := 0
var _row_bar: Node2D
var _row_marks: Node2D
var _back: Control              # the open page's background (hall or dim)
var _content: Control           # everything else on the page (scales / fades as one)
var _into: Node                 # where the build functions add things right now
var _row_holders: Array[Control] = []
var _head_holder: Control
var _title_holder: Control
var _panel_holder: Control

var _capture := {}            # rebinding in progress: {"kind", "player", "button", "time"}
var _capture_box: Control
var _capture_title: Label
var _capture_name: Label
var _capture_count: Label
var _notice_tween: Tween
var _link: Control            # the line + spark joining OPTIONS to the settings list
var _closing := false


func _ready() -> void:
	_behind = Control.new()
	_behind.mouse_filter = Control.MOUSE_FILTER_IGNORE
	NetsuUI.full_rect(_behind)
	add_child(_behind)
	if not embedded:
		NetsuUI.picture(_behind, NetsuUI.MENU_BG)
		var shade := NetsuUI.gradient_rect(Color(0.02, 0.04, 0.16, 0.7), Color(0.02, 0.04, 0.16, 0.2), false)
		shade.size = Vector2(1920, 1080)
		_behind.add_child(shade)
		NetsuUI.header(_behind, "OPTIONS")
	else:
		# over the main menu's picture a bright lamp sits behind the lower rows: a soft dark glow behind the list (an
		# ellipse fading out on every side, so it has no edges) keeps them readable
		var k := NetsuUI.K
		var g := Gradient.new()
		g.offsets = PackedFloat32Array([0.0, 0.55, 1.0])
		g.colors = PackedColorArray([Color(0.02, 0.04, 0.16, 0.62), Color(0.02, 0.04, 0.16, 0.45), Color(0.02, 0.04, 0.16, 0.0)])
		var tex := GradientTexture2D.new()
		tex.gradient = g
		tex.fill = GradientTexture2D.FILL_RADIAL
		tex.fill_from = Vector2(0.5, 0.5)
		tex.fill_to = Vector2(1.0, 0.5)
		var shade := TextureRect.new()
		shade.texture = tex
		shade.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
		var top := _cat_y(0) - 40 * k
		var bottom := _cat_y(CATEGORIES.size() - 1) + 40 * k
		var mid := Vector2((category_x + 230) * k, (top + bottom) / 2.0)
		shade.size = Vector2(1200, bottom - top + 300)
		shade.position = mid - shade.size / 2.0
		_list_shade = shade
		_behind.add_child(_list_shade)
	_build_link()
	_build_categories()
	if embedded and not footer_override.is_empty():
		_footer = footer_override
		_footer["prompts"].text = MENU_PROMPTS
	else:
		_footer = NetsuUI.footer(self, false)
		_footer["prompts"].text = MENU_PROMPTS
	_build_capture_box()
	if start_page == "":
		_play_preview_music()   # only the full Options screen plays music (Nov 2: and only if nothing is playing)
	Controls.bindings_changed.connect(_refresh_sheet)
	if start_page != "":
		_behind.visible = false   # just the one page, no settings list
		_open_page(start_page)
		return
	_select_category(0, false)
	_entrance()


# --- Input -------------------------------------------------------------------------

func _input(event: InputEvent) -> void:
	if _capture.is_empty():
		return
	get_viewport().set_input_as_handled()
	if event is InputEventKey and event.pressed and not event.echo:
		if event.physical_keycode == KEY_ESCAPE or event.keycode == KEY_ESCAPE:
			_end_capture("Cancelled.")
			return
		if _capture["kind"] == "pad":
			return
		var key: int = event.physical_keycode if event.physical_keycode != KEY_NONE else event.keycode
		if _capture["kind"] == "keyboard":
			Controls.set_key(_capture["player"], _capture["button"], key)
		else:
			Controls.set_menu_key(_capture["button"], key)
		_end_capture("%s set to %s." % [_capture_label(), Controls.key_name(key)])
		return
	if _capture["kind"] != "pad" or event.device != _capture["player"] - 1:
		return
	var pad_input := {}
	if event is InputEventJoypadButton and event.pressed:
		pad_input = {"button": int(event.button_index)}
	elif event is InputEventJoypadMotion and event.axis in [JOY_AXIS_TRIGGER_LEFT, JOY_AXIS_TRIGGER_RIGHT] \
			and event.axis_value > 0.6:
		pad_input = {"axis": int(event.axis), "dir": 1.0}
	if pad_input.is_empty():
		return
	Controls.set_pad(_capture["player"], _capture["button"], pad_input)
	_end_capture("%s set to %s." % [_capture_label(), Controls.pad_name(pad_input)])


func _unhandled_input(event: InputEvent) -> void:
	if SceneRouter.is_busy() or not _capture.is_empty() or _closing:
		return
	if _page == "":
		if event.is_action_pressed("ui_down", true):
			_select_category(_cat + 1)
		elif event.is_action_pressed("ui_up", true):
			_select_category(_cat - 1)
		elif event.is_action_pressed("ui_accept"):
			_open_category()
		elif event.is_action_pressed("ui_cancel"):
			_leave()
		else:
			return
	else:
		var binding := _page in ["pad", "keyboard", "menu_keys"]
		if event.is_action_pressed("ui_down", true):
			_move_row(1)
		elif event.is_action_pressed("ui_up", true):
			_move_row(-1)
		elif event.is_action_pressed("ui_right", true) or event.is_action_pressed("ui_left", true):
			var dir := 1 if event.is_action_pressed("ui_right", true) else -1
			if binding:
				_move_col(dir)
			else:
				_change(dir, false)
		elif event.is_action_pressed("ui_accept"):
			_accept()
		elif event.is_action_pressed("ui_cancel"):
			_close_page()
		else:
			return
	get_viewport().set_input_as_handled()


func _process(delta: float) -> void:
	if _capture.is_empty():
		return
	_capture["time"] -= delta
	_capture_count.text = "ESC  CANCEL      %d" % ceili(maxf(_capture["time"], 0.0))
	if _capture["time"] <= 0.0:
		_end_capture("No input - nothing changed.")


# --- Categories ----------------------------------------------------------------------

func _cat_y(i: int) -> float:
	return (category_first_y + category_step * i) * NetsuUI.K


func _select_category(index: int, animate: bool = true) -> void:
	_cat = wrapi(index, 0, CATEGORIES.size())
	for i in _cat_labels.size():
		_cat_labels[i].add_theme_color_override("font_color", Color.WHITE if i == _cat else NetsuUI.DIM)
	var target := Vector2((category_x - 31) * NetsuUI.K, _cat_y(_cat) - 28 * NetsuUI.K)
	if animate:
		create_tween().tween_property(_cat_bar, "position", target, 0.12).set_trans(Tween.TRANS_CUBIC)
		create_tween().tween_property(_cat_gem, "position", Vector2((category_x + 10) * NetsuUI.K, _cat_y(_cat)), 0.12)
	else:
		_cat_bar.position = target
		_cat_gem.position = Vector2((category_x + 10) * NetsuUI.K, _cat_y(_cat))
	_footer["text"].text = CATEGORIES[_cat]["blurb"]


func _open_category() -> void:
	var id: String = CATEGORIES[_cat]["id"]
	var punch := create_tween()
	punch.tween_property(_cat_labels[_cat], "scale", Vector2(1.05, 1.05), 0.06)
	punch.tween_property(_cat_labels[_cat], "scale", Vector2.ONE, 0.1)
	if id == "return":
		_leave()
		return
	_open_page(id)


func _open_page(id: String) -> void:
	var title := "GAME SETTINGS"   # the Versus page
	for c in CATEGORIES:
		if c["id"] == id:
			title = c["title"]
	_page = id
	_build_sheet(title)
	_footer["prompts"].text = LIST_PROMPTS


func _close_page() -> void:
	if start_page != "":
		_close_direct()
		return
	if _sheet:
		var old := _sheet
		_animate_out(old, old.queue_free)
	_sheet = null
	_page = ""
	_columns.clear()
	_footer["prompts"].text = MENU_PROMPTS
	_select_category(_cat, false)


## Opened straight onto a page: backing out closes everything.
func _close_direct() -> void:
	if _closing:
		return
	_closing = true
	closed.emit()
	if _sheet:
		_animate_out(_sheet, queue_free)
	else:
		queue_free()


func _leave() -> void:
	var audio := get_node_or_null("/root/AudioManager")
	if audio and _preview_playing:   # Nov 2: only stop the preview song this screen started (the menu theme keeps going)
		audio.call("StopBGM")
	_preview_playing = false
	if not embedded:
		SceneRouter.go_to(SceneRouter.MAIN_MENU)
		return
	if _closing:
		return
	_closing = true
	closed.emit()   # the main menu starts bringing Cecilia back right away
	var t := create_tween().set_parallel(true).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_IN)
	for i in _cat_labels.size():
		var l := _cat_labels[i]
		var d := 0.02 * (_cat_labels.size() - 1 - i)
		t.tween_property(l, "modulate:a", 0.0, 0.16).set_delay(d)
		t.tween_property(l, "position:x", l.position.x - 60.0, 0.2).set_delay(d)
	t.tween_property(_cat_bar, "modulate:a", 0.0, 0.15)
	t.tween_property(_cat_gem, "modulate:a", 0.0, 0.15)
	t.tween_property(_link, "modulate:a", 0.0, 0.2)
	if _list_shade:
		t.tween_property(_list_shade, "modulate:a", 0.0, 0.2)
	t.chain().tween_callback(queue_free)


# --- Rows ------------------------------------------------------------------------------

func _list_rows(id: String) -> Array:
	var on_off := {"values": [true, false], "names": ["On", "Off"]}
	var rows: Array = []
	match id:
		"versus":
			var vtimes: Array = GameSettings.ROUND_TIMES
			rows = [
				_action("Start Game", "start", "Choose sides, then fighters."),
				_pick("Rounds to Win", "game", "rounds_versus",
					{"values": [1, 2, 3, 4, 5], "names": ["1", "2", "3", "4", "5"]}, "Rounds needed to win the match."),
				_pick("Round Time", "game", "time_versus",
					{"values": vtimes, "names": vtimes.map(func(v): return "∞" if v < 0 else str(v))},
					"Seconds per round."),
				_pick("CPU Difficulty", "game", "difficulty",
					{"values": range(GameSettings.DIFFICULTIES.size()), "names": GameSettings.DIFFICULTIES},
					"How strong the CPU fights when a side has no player."),
				_pick("Character Intros", "game", "intros", on_off, "Play the fighters' intro animations before a match."),
			]
		"system":
			rows = [
				_pick("Auto Save", "system", "auto_save", on_off, "Save every change the moment you make it."),
				_action("Save", "save", "Save all settings and button layouts now."),
				_pick("Display Language", "system", "language",
					{"values": range(GameSettings.LANGUAGES.size()), "names": GameSettings.LANGUAGES},
					"More languages later."),
			]
		"sound":
			rows = [
				_volume("Master Volume", "master", "Everything at once."),
				_volume("BGM Volume", "bgm", "Music. The theme playing now uses this."),
				_volume("SFX Volume", "sfx", "Hits, menus and other sound effects."),
				_volume("Voice Volume", "voice", "Character voices."),
				_volume("Announcer Volume", "announcer", "The round announcer."),
				_pick("Round Announcements", "sound", "announcements", on_off, "Turn the round announcer on or off."),
			]
		"display":
			var res: Array = GameSettings.resolution_choices()
			var res_names: Array = res.map(func(i): return "%d x %d" % [GameSettings.RESOLUTIONS[i].x, GameSettings.RESOLUTIONS[i].y])
			rows = [
				_pick("Screen Resolution", "display", "resolution", {"values": res, "names": res_names},
					"Window size (used in Window mode)."),
				_pick("Screen Mode", "display", "window_mode",
					{"values": [0, 1, 2], "names": GameSettings.WINDOW_MODES},
					"Borderless fills the screen; Fullscreen takes over the monitor. F11 also toggles."),
				_pick("VSync", "display", "vsync", on_off, "Stops screen tearing. Turn off for slightly less input delay."),
				_pick("Aspect Ratio Retention", "display", "keep_aspect", on_off,
					"On: keep 16:9 with black bars. Off: stretch to fill the window."),
			]
		"game":
			var times: Array = GameSettings.ROUND_TIMES
			var time_names: Array = times.map(func(t): return "∞" if t < 0 else str(t))
			var rounds := {"values": [1, 2, 3, 4, 5], "names": ["1", "2", "3", "4", "5"]}
			rows = [
				_pick("CPU Difficulty", "game", "difficulty",
					{"values": range(GameSettings.DIFFICULTIES.size()), "names": GameSettings.DIFFICULTIES},
					"How strong the CPU fights in Versus and Arcade."),
				_pick("Rounds to Win (Versus Mode)", "game", "rounds_versus", rounds, "Rounds needed to win a Versus match."),
				_pick("Round Time (Versus Mode)", "game", "time_versus", {"values": times, "names": time_names},
					"Seconds per round in Versus."),
				_pick("Rounds to Win (Arcade Mode)", "game", "rounds_arcade", rounds, "Rounds needed to win an Arcade fight."),
				_pick("Round Time (Arcade Mode)", "game", "time_arcade", {"values": times, "names": time_names},
					"Seconds per round in Arcade."),
				_pick("Character Intros", "game", "intros", on_off, "Play the fighters' intro animations before a match."),
			]
	rows.append({"type": "spacer"})
	rows.append(_action("Restore Default", "restore", "Put this page back to the default settings."))
	rows.append(_action("Return", "return", "Back to the settings list." if start_page == "" else "Close this page."))
	return rows


func _bind_rows(kind: String, player: int) -> Array:
	var rows: Array = []
	var buttons: Array
	match kind:
		"pad":
			buttons = Controls.REBIND_PAD
		"keyboard":
			buttons = Controls.REBIND_KEYBOARD
		_:
			buttons = Controls.REBIND_MENU
	for b in buttons:
		rows.append({"type": "bind", "kind": kind, "player": player, "button": b,
			"label": MENU_NAMES[b] if kind == "menu_keys" else BUTTON_NAMES[b],
			"help": "Press A, then the new %s." % ("button" if kind == "pad" else "key")})
		# thin group lines: directions | attacks | macros
		if b in ["right", "s"] and kind != "menu_keys" and b != buttons[-1]:
			rows.append({"type": "spacer", "group": true})
	rows.append({"type": "spacer"})
	rows.append(_action("Restore Default", "restore", "Put this column back to the default layout."))
	rows.append(_action("Return", "return", "Back to the settings list." if start_page == "" else "Close this page."))
	return rows


func _pick(label: String, section: String, key: String, choices: Dictionary, help: String) -> Dictionary:
	return {"type": "pick", "label": label, "section": section, "key": key,
		"values": choices["values"], "names": choices["names"], "help": help}


func _volume(label: String, key: String, help: String) -> Dictionary:
	return {"type": "volume", "label": label, "section": "sound", "key": key, "help": help}


func _action(label: String, action: String, help: String) -> Dictionary:
	return {"type": "action", "label": label, "action": action, "help": help}


func _move_row(dir: int) -> void:
	var rows: Array = _columns[_col]
	var i := _row
	for n in rows.size():
		i = wrapi(i + dir, 0, rows.size())
		if rows[i]["type"] != "spacer":
			break
	_row = i
	_audio("PlayMenuClip", 0)
	_refresh_sheet()


func _move_col(dir: int) -> void:
	if _columns.size() < 2:
		return
	_col = wrapi(_col + dir, 0, _columns.size())
	_row = mini(_row, _columns[_col].size() - 1)
	if _columns[_col][_row]["type"] == "spacer":
		_row += 1
	_refresh_sheet()


func _change(dir: int, wrap: bool) -> void:
	var r: Dictionary = _columns[_col][_row]
	match r["type"]:
		"pick":
			var values: Array = r["values"]
			var cur := maxi(values.find(GameSettings.get_value(r["section"], r["key"])), 0)
			var next := wrapi(cur + dir, 0, values.size()) if wrap else clampi(cur + dir, 0, values.size() - 1)
			if next == cur:
				return
			GameSettings.set_value(r["section"], r["key"], values[next])
			if r["key"] == "announcements" and values[next]:
				_audio("PlayAnnouncerClip", 0)
		"volume":
			var v: int = GameSettings.get_value("sound", r["key"])
			var nv := clampi(v + dir * 5, 0, 100)
			if nv == v:
				return
			GameSettings.set_value("sound", r["key"], nv)
			match r["key"]:
				"sfx", "master":
					_audio("PlayMenuClip", 1)
				"announcer":
					_audio("PlayAnnouncerClip", 0)
		_:
			return
	_refresh_sheet()


func _accept() -> void:
	var r: Dictionary = _columns[_col][_row]
	match r["type"]:
		"pick":
			_change(1, true)
		"bind":
			_start_capture(r)
		"action":
			match r["action"]:
				"save":
					_notice("Settings saved." if GameSettings.save() else "Couldn't save the settings file!")
				"start":
					_closing = true
					start_game.emit()
				"restore":
					_restore_defaults()
				"return":
					_close_page()


func _restore_defaults() -> void:
	var player: int = _col + 1
	match _page:
		"pad":
			Controls.reset_pad(player)
			GameSettings.bindings_changed()
			_notice("Controller %d back to the default layout." % player)
		"keyboard":
			Controls.reset_keyboard(player)
			GameSettings.bindings_changed()
			_notice("Player %d keyboard back to the default layout." % player)
		"menu_keys":
			Controls.reset_menu_keys()
			GameSettings.bindings_changed()
			_notice("Menu keys back to the default layout.")
		"versus":
			GameSettings.restore_keys("game", ["rounds_versus", "time_versus", "difficulty", "intros"])
			_notice("Defaults restored.")
		_:
			GameSettings.restore_defaults(_page)
			_notice("Defaults restored.")
	_refresh_sheet()


# --- Rebinding ---------------------------------------------------------------------------

func _start_capture(r: Dictionary) -> void:
	_capture = {"kind": r["kind"], "player": r["player"], "button": r["button"], "time": capture_seconds}
	if r["kind"] == "pad":
		_capture_title.text = "PRESS A BUTTON ON CONTROLLER %d FOR" % r["player"]
	else:
		_capture_title.text = "PRESS A KEY FOR"
	_capture_name.text = _capture_label()
	_capture_box.visible = true
	_capture_box.modulate.a = 0.0
	create_tween().tween_property(_capture_box, "modulate:a", 1.0, 0.1)


func _end_capture(message: String) -> void:
	_capture = {}
	_capture_box.visible = false
	GameSettings.bindings_changed()
	_notice(message)
	_refresh_sheet()


func _capture_label() -> String:
	var b: String = _capture.get("button", "")
	var text: String = MENU_NAMES.get(b, BUTTON_NAMES.get(b, b))
	if _capture.get("kind") == "menu_keys":
		return text
	return "P%d  %s" % [_capture["player"], text]


# --- Building: the settings list -----------------------------------------------------------

## The line from the main menu's OPTIONS row to the settings list, with a spark where they meet.
func _build_link() -> void:
	var k := NetsuUI.K
	_link = Control.new()
	_link.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_behind.add_child(_link)
	var x := (category_x - 52) * k
	var top := _cat_y(0) - 34 * k
	var bottom := _cat_y(CATEGORIES.size() - 1) + 34 * k
	var line := NetsuUI.gradient_rect(Color(0.55, 0.75, 1.0, 0.0), Color(0.55, 0.75, 1.0, 0.7), true)
	line.position = Vector2(x, top)
	line.size = Vector2(1.5, bottom - top)
	_link.add_child(line)
	var options_y := _cat_y(5)   # the main menu's OPTIONS row
	_link.add_child(NetsuUI.hairline(Vector2(330 * k, options_y), x - 330 * k, Color(0.55, 0.78, 1.0, 0.85), 1.5, "left"))
	var spark := NetsuUI.sparkle(14.0, Color.WHITE)
	spark.position = Vector2(x, options_y)
	_link.add_child(spark)


func _build_categories() -> void:
	var k := NetsuUI.K
	_cat_bar = Node2D.new()
	var h := 56.0 * k
	var w := 640.0 * k
	var skew := 31.0 * k
	var shape := NetsuUI.para(w, h, skew)
	var fill := Polygon2D.new()
	fill.polygon = shape
	fill.vertex_colors = PackedColorArray([Color(0.3, 0.38, 0.95, 0.75), Color(0.35, 0.4, 0.9, 0.0),
		Color(0.3, 0.35, 0.85, 0.0), Color(0.25, 0.33, 0.9, 0.75)])
	_cat_bar.add_child(fill)
	_cat_bar.add_child(NetsuUI.hairline(Vector2(skew, 0), w, Color(0.75, 0.88, 1.0, 0.9), 1.5, "right"))
	_cat_bar.add_child(NetsuUI.hairline(Vector2(0, h), w, Color(0.75, 0.88, 1.0, 0.9), 1.5, "right"))
	_behind.add_child(_cat_bar)
	_cat_gem = NetsuUI.diamond(9.0 * k, Color.WHITE, Color(0.05, 0.2, 0.6, 0.9), NetsuUI.CYAN)
	_behind.add_child(_cat_gem)
	for i in CATEGORIES.size():
		var l := NetsuUI.label(CATEGORIES[i]["label"], category_font_size, NetsuUI.DIM, NetsuUI.serif(600, 2))
		l.position = Vector2((category_x + 36) * k, _cat_y(i) - 30)
		l.size = Vector2(760, 60)
		l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		l.pivot_offset = Vector2(0, 30)
		_behind.add_child(l)
		_cat_labels.append(l)


# --- Building: a page ------------------------------------------------------------------------

## Panel / row geometry for the open page, in screen pixels.
func _layout() -> Dictionary:
	var k := NetsuUI.K
	var bind := _page in ["pad", "keyboard", "menu_keys"]
	var rows: Array = _columns[0]
	if bind:
		var pitch := 46.5 if _page == "pad" else 37.2
		var n := 0.0
		for r in rows:
			n += (0.35 if r.get("group", false) else 0.8) if r["type"] == "spacer" else 1.0
		var head := 108.0 if _page == "pad" else 75.0
		var body := head + n * pitch + 26.0
		var top := clampf(482.0 - body / 2.0, 150.0, 400.0)
		var two := _columns.size() > 1
		var x0 := 205.0 if two else 470.0
		var x1 := 1468.0 if two else 1204.0
		return {"bind": true, "frame": Rect2(x0 * k, top * k, (x1 - x0) * k, body * k), "title_y": top - 50.0,
			"pitch": pitch * k, "first": (top + head) * k, "head_y": (top + (36.0 if _page != "pad" else 57.0)) * k}
	var count := 0.0
	for r in rows:
		count += 0.8 if r["type"] == "spacer" else 1.0
	var p := minf(75.0, 520.0 / count)
	var body2 := 50.0 + count * p + 34.0
	var top2 := clampf(478.0 - body2 / 2.0, 183.0, 400.0)
	var fx0 := 280.0 if _page == "versus" else 210.0
	var fx1 := 1395.0 if _page == "versus" else 1462.0
	var has_volume := false
	for r in rows:
		if r["type"] == "volume":
			has_volume = true
	var al := 968.0 if _page == "versus" else (867.0 if has_volume else 1130.0)
	var ar := 1269.0 if _page == "versus" else (1347.0 if has_volume else 1350.0)
	return {"bind": false, "frame": Rect2(fx0 * k, top2 * k, (fx1 - fx0) * k, body2 * k), "title_y": top2 - 58.0,
		"pitch": p * k, "first": (top2 + 50.0) * k, "bar_x0": (fx0 + 56) * k, "bar_x1": (fx1 - 56) * k,
		"arrow_l": al * k, "arrow_r": ar * k, "volume": has_volume}


func _build_sheet(title: String) -> void:
	_sheet = Control.new()
	_sheet.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_sheet.size = Vector2(1920, 1080)
	add_child(_sheet)
	if not embedded or footer_override.is_empty():
		move_child(_sheet, _footer["root"].get_index())   # under the footer and the capture box
	_columns.clear()
	_col = 0
	_row = 0
	match _page:
		"pad", "keyboard":
			_columns = [_bind_rows(_page, 1), _bind_rows(_page, 2)]
		"menu_keys":
			_columns = [_bind_rows(_page, 1)]
		_:
			_columns = [_list_rows(_page)]
	_back = Control.new()
	_back.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_back.size = Vector2(1920, 1080)
	_sheet.add_child(_back)
	if backdrop == "dim":
		var dim := ColorRect.new()
		dim.color = Color(0.01, 0.02, 0.1, 0.72)
		dim.mouse_filter = Control.MOUSE_FILTER_IGNORE
		dim.size = Vector2(1920, 1080)
		_back.add_child(dim)
	else:
		NetsuUI.settings_backdrop(_back, 0.45)
	_content = Control.new()
	_content.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_content.size = Vector2(1920, 1080)
	_content.pivot_offset = Vector2(960, 540)
	_sheet.add_child(_content)
	_head_holder = _holder()
	if backdrop != "dim":
		NetsuUI.header(_head_holder, "VERSUS" if _page == "versus" else "OPTIONS")
	_title_holder = _holder()
	_panel_holder = _holder()
	_row_holders.clear()
	_into = _content
	var lay := _layout()
	NetsuUI.page_title(_title_holder, title, lay["title_y"])
	NetsuUI.frame_panel(_panel_holder, lay["frame"])
	_row_bar = Node2D.new()
	_row_marks = Node2D.new()
	if lay["bind"]:
		for c in _columns.size():
			_build_bind_column(c, lay)
		if _columns.size() > 1:
			var r: Rect2 = lay["frame"]
			var cx := r.position.x + r.size.x / 2.0
			var line := NetsuUI.gradient_rect(Color(0.55, 0.75, 1.0, 0.2), Color(0.55, 0.75, 1.0, 0.75), true)
			line.position = Vector2(cx - 0.75, r.position.y + 28)
			line.size = Vector2(1.5, r.size.y - 56)
			_panel_holder.add_child(line)
			var d := NetsuUI.diamond(10.0, Color(0.7, 0.88, 1.0), Color(0.03, 0.06, 0.2))
			d.position = Vector2(cx, r.position.y + r.size.y / 2.0)
			_panel_holder.add_child(d)
	else:
		_build_list_column(lay)
	_refresh_sheet()
	_animate_in()


func _holder() -> Control:
	var h := Control.new()
	h.mouse_filter = Control.MOUSE_FILTER_IGNORE
	h.size = Vector2(1920, 1080)
	_content.add_child(h)
	return h


## A new holder for one row's pieces (so the rows can slide in one after another).
func _row_holder() -> Control:
	var h := _holder()
	_row_holders.append(h)
	_into = h
	return h


## Page opens: the background fades up, the panel grows into place, the header
## slides in from the left, the title drops in, then the rows slide in one by one.
func _animate_in() -> void:
	_back.modulate.a = 0.0
	_content.modulate.a = 0.0
	_content.scale = Vector2(0.96, 0.96)
	var t := create_tween().set_parallel(true).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	t.tween_property(_back, "modulate:a", 1.0, 0.22)
	t.tween_property(_content, "modulate:a", 1.0, 0.22).set_delay(0.04)
	t.tween_property(_content, "scale", Vector2.ONE, 0.32).set_delay(0.04)
	_head_holder.position.x = -60
	t.tween_property(_head_holder, "position:x", 0.0, 0.35).set_delay(0.06)
	_title_holder.position.y = -24
	_title_holder.modulate.a = 0.0
	t.tween_property(_title_holder, "position:y", 0.0, 0.3).set_delay(0.1)
	t.tween_property(_title_holder, "modulate:a", 1.0, 0.25).set_delay(0.1)
	for i in _row_holders.size():
		var h := _row_holders[i]
		h.position.x = -40
		h.modulate.a = 0.0
		var d := 0.14 + 0.025 * (i % 16)
		t.tween_property(h, "position:x", 0.0, 0.28).set_delay(d)
		t.tween_property(h, "modulate:a", 1.0, 0.22).set_delay(d)
	for n in [_row_bar, _row_marks]:
		n.modulate.a = 0.0
		t.tween_property(n, "modulate:a", 1.0, 0.2).set_delay(0.2)


## Page closes: the panel shrinks back a touch and everything fades.
func _animate_out(sheet: Control, done: Callable) -> void:
	var back: Control = sheet.get_child(0)
	var content: Control = sheet.get_child(1)
	var t := create_tween().set_parallel(true).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_IN)
	t.tween_property(content, "scale", Vector2(0.97, 0.97), 0.16)
	t.tween_property(content, "modulate:a", 0.0, 0.16)
	t.tween_property(back, "modulate:a", 0.0, 0.2).set_delay(0.04)
	t.chain().tween_callback(done)


func _row_label(text: String, size: int) -> Label:
	var l := NetsuUI.label(text, size, ROW_TEXT, NetsuUI.sans(1))
	l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	return l


func _build_list_column(lay: Dictionary) -> void:
	var k := NetsuUI.K
	var pitch: float = lay["pitch"]
	var x0: float = lay["bar_x0"]
	var x1: float = lay["bar_x1"]
	var y: float = lay["first"]
	_content.add_child(_row_bar)
	for r in _columns[0]:
		_row_holder()
		if r["type"] == "spacer":
			var sy := y + pitch * 0.4
			NetsuUI.divider(_into, x0, x1, sy)
			y += pitch * 0.8
			continue
		r["y"] = y + pitch / 2.0
		r["x0"] = x0
		r["x1"] = x1
		r["h"] = pitch * 0.92
		var sep := ColorRect.new()   # faint line under each row
		sep.color = Color(0.55, 0.7, 1.0, 0.12)
		sep.position = Vector2(x0, y + pitch - 1)
		sep.size = Vector2(x1 - x0, 1)
		sep.mouse_filter = Control.MOUSE_FILTER_IGNORE
		_into.add_child(sep)
		var l := _row_label(r["label"], 28)
		l.position = Vector2(x0 + 95 * k, r["y"] - 30)
		l.size = Vector2(700, 60)
		_into.add_child(l)
		r["node"] = l
		var al: float = lay["arrow_l"]
		var ar: float = lay["arrow_r"]
		match r["type"]:
			"pick", "volume":
				var v := _row_label("", 28)
				v.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
				var vc := (al + ar) / 2.0
				if r["type"] == "volume":
					vc = 1204.0 * k
					var segs: Array = []
					for s in 10:
						var sq := ColorRect.new()
						sq.position = Vector2((928.0 + s * 19.2) * k, r["y"] - 7.5 * k)
						sq.size = Vector2(15.0 * k, 15.0 * k)
						sq.mouse_filter = Control.MOUSE_FILTER_IGNORE
						_into.add_child(sq)
						segs.append(sq)
					r["segs"] = segs
				v.position = Vector2(vc - 150, r["y"] - 30)
				v.size = Vector2(300, 60)
				_into.add_child(v)
				r["value"] = v
				var left := NetsuUI.arrow(Vector2(al, r["y"]), 24, -1, ROW_TEXT, 3.0)
				var right := NetsuUI.arrow(Vector2(ar, r["y"]), 24, 1, ROW_TEXT, 3.0)
				_into.add_child(left)
				_into.add_child(right)
				r["left"] = left
				r["right"] = right
			"action":
				var go := NetsuUI.arrow(Vector2(ar, r["y"]), 24, 1, ROW_TEXT, 3.0)
				_into.add_child(go)
		y += pitch
	_content.add_child(_row_marks)


func _build_bind_column(c: int, lay: Dictionary) -> void:
	var k := NetsuUI.K
	var two := _columns.size() > 1
	var frame: Rect2 = lay["frame"]
	var x0: float = (258.0 * k if c == 0 else 880.0 * k) if two else frame.position.x + 50 * k
	var x1: float = (800.0 * k if c == 0 else 1412.0 * k) if two else frame.end.x - 50 * k
	var center := (x0 + x1) / 2.0
	var kind := _page
	_into = _panel_holder
	var head_text := "ALL PLAYERS"
	if kind == "pad":
		head_text = "CONTROLLER %d" % (c + 1)
	elif kind == "keyboard":
		head_text = "PLAYER %d" % (c + 1)
	var accent := Color(0.4, 0.8, 1.0) if c == 0 else Color(1.0, 0.32, 0.4)
	var hy: float = lay["head_y"]
	var head := NetsuUI.label(head_text, 30, accent, NetsuUI.sans(5 if kind != "pad" else 3))
	head.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	head.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	head.position = Vector2(center - 300, hy - 26)
	head.size = Vector2(600, 52)
	_into.add_child(head)
	var hw := NetsuUI.sans(5).get_string_size(head_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 30).x
	for s: float in [-1.0, 1.0]:
		var from_x := center + s * (hw / 2.0 + 30)
		var length := absf((x1 if s > 0 else x0) - from_x)
		_into.add_child(NetsuUI.hairline(Vector2(from_x - (length if s < 0 else 0.0), hy + 6), length,
			Color(accent, 0.7), 1.5, "left" if s < 0 else "right"))
		var notch := NetsuUI.arrow(Vector2(center + s * (hw / 2.0 + 18), hy + 2), 30, int(s), Color(accent, 0.6), 2.0)
		_into.add_child(notch)
	if kind == "pad":
		var connected := Input.get_connected_joypads().has(c)
		var status := NetsuUI.label(Input.get_joy_name(c) if connected else "(Not Connected)", 20,
			Color(0.8, 0.84, 0.95) if connected else Color(accent, 0.85), NetsuUI.body())
		status.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		status.position = Vector2(center - 300, hy + 18)
		status.size = Vector2(600, 30)
		_into.add_child(status)
	elif kind == "menu_keys":
		var note := NetsuUI.label("Arrow keys, Enter and Escape always work too.", 20, Color(0.8, 0.84, 0.95), NetsuUI.body())
		note.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		note.position = Vector2(center - 400, hy + 18)
		note.size = Vector2(800, 30)
		_into.add_child(note)
	_into.add_child(NetsuUI.hairline(Vector2(x0, lay["first"] - 6 * k), x1 - x0, Color(0.55, 0.75, 1.0, 0.35), 1.0, "none"))
	if c == 0:
		_content.add_child(_row_bar)
	var pitch: float = lay["pitch"]
	var y: float = lay["first"]
	for r in _columns[c]:
		_row_holder()
		if r["type"] == "spacer":
			var gap := pitch * (0.35 if r.get("group", false) else 0.8)
			NetsuUI.divider(_into, x0, x1, y + gap / 2.0, false)
			y += gap
			continue
		r["y"] = y + pitch / 2.0
		r["x0"] = x0
		r["x1"] = x1
		r["h"] = pitch * 0.92
		var sep := ColorRect.new()
		sep.color = Color(0.55, 0.7, 1.0, 0.12)
		sep.position = Vector2(x0, y + pitch - 1)
		sep.size = Vector2(x1 - x0, 1)
		sep.mouse_filter = Control.MOUSE_FILTER_IGNORE
		_into.add_child(sep)
		var l := _row_label(r["label"], 24 if kind != "pad" else 26)
		l.position = Vector2(x0 + 89 * k, r["y"] - 30)
		l.size = Vector2(420, 60)
		_into.add_child(l)
		r["node"] = l
		if r["type"] == "bind":
			r["cap"] = _make_cap(Vector2(x1 - 102 * k, r["y"]), pitch)
		else:
			_into.add_child(NetsuUI.arrow(Vector2(x1 - 96 * k, r["y"]), 22, 1, ROW_TEXT, 3.0))
		y += pitch
	if c == _columns.size() - 1:
		_content.add_child(_row_marks)


## A key cap / controller button icon, centred on `at`.
func _make_cap(at: Vector2, pitch: float) -> Dictionary:
	var holder := CenterContainer.new()
	holder.position = at - Vector2(100, pitch / 2.0)
	holder.size = Vector2(200, pitch)
	holder.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var style := StyleBoxFlat.new()
	style.content_margin_left = 12
	style.content_margin_right = 12
	var panel := PanelContainer.new()
	panel.add_theme_stylebox_override("panel", style)
	panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var label := NetsuUI.label("", 20, Color.WHITE, NetsuUI.sans(0))
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	panel.add_child(label)
	holder.add_child(panel)
	_into.add_child(holder)
	return {"panel": panel, "label": label, "style": style, "h": minf(pitch - 6.0, 38.0)}


func _set_cap(cap: Dictionary, text: String, round_button: bool) -> void:
	var style: StyleBoxFlat = cap["style"]
	var label: Label = cap["label"]
	var h: float = cap["h"]
	label.text = text
	var face_button: bool = round_button and PAD_COLORS.has(text)
	if face_button:
		style.bg_color = PAD_COLORS[text]
		style.set_border_width_all(2)
		style.border_color = Color(1, 1, 1, 0.85)
		style.set_corner_radius_all(int(h / 2.0))
		style.content_margin_left = 0
		style.content_margin_right = 0
		cap["panel"].custom_minimum_size = Vector2(h, h)
	else:
		style.bg_color = Color(0.03, 0.06, 0.18, 0.95)
		style.set_border_width_all(2)
		style.border_color = Color(0.92, 0.95, 1.0, 0.9)
		style.set_corner_radius_all(5)
		style.content_margin_left = 12
		style.content_margin_right = 12
		cap["panel"].custom_minimum_size = Vector2(h * 1.15, h)
	cap["panel"].size = Vector2.ZERO   # shrink to fit the new text


func _build_capture_box() -> void:
	_capture_box = Control.new()
	_capture_box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_capture_box.visible = false
	add_child(_capture_box)
	var shade := ColorRect.new()
	shade.color = Color(0.01, 0.02, 0.08, 0.6)
	shade.size = Vector2(1920, 1080)
	shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_capture_box.add_child(shade)
	NetsuUI.frame_panel(_capture_box, Rect2(560, 390, 800, 280))
	_capture_title = NetsuUI.label("", 24, Color(0.75, 0.88, 1.0), NetsuUI.sans(5))
	_capture_name = NetsuUI.label("", 46, Color.WHITE, NetsuUI.sans(3))
	_capture_count = NetsuUI.label("", 22, Color(0.75, 0.8, 0.95), NetsuUI.sans(4))
	var y := 420.0
	for l in [_capture_title, _capture_name, _capture_count]:
		l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		l.position = Vector2(560, y)
		l.size = Vector2(800, 60)
		_capture_box.add_child(l)
		y += 70.0 if l != _capture_name else 90.0


# --- Refreshing ---------------------------------------------------------------------------

func _refresh_sheet() -> void:
	if _sheet == null or _columns.is_empty():
		return
	for c in _columns.size():
		for i in _columns[c].size():
			var r: Dictionary = _columns[c][i]
			var on: bool = c == _col and i == _row
			var ink := Color.WHITE if on else ROW_TEXT
			if r.has("node"):
				r["node"].add_theme_color_override("font_color", ink)
			match r["type"]:
				"pick":
					var values: Array = r["values"]
					var idx := maxi(values.find(GameSettings.get_value(r["section"], r["key"])), 0)
					r["value"].text = str(r["names"][idx])
					r["value"].add_theme_color_override("font_color", ink)
					r["left"].modulate.a = 1.0 if idx > 0 else 0.25
					r["right"].modulate.a = 1.0 if idx < values.size() - 1 else 0.25
				"volume":
					var v: int = GameSettings.get_value("sound", r["key"])
					r["value"].text = "%d%%" % v
					r["value"].add_theme_color_override("font_color", ink)
					r["left"].modulate.a = 1.0 if v > 0 else 0.25
					r["right"].modulate.a = 1.0 if v < 100 else 0.25
					var lit := int(round(v / 10.0))
					for s in r["segs"].size():
						r["segs"][s].color = Color(0.36, 0.68, 1.0) if s < lit else Color(0.2, 0.25, 0.42, 0.9)
				"bind":
					match r["kind"]:
						"pad":
							_set_cap(r["cap"], Controls.pad_name(Controls.pad_binding(r["player"], r["button"])), true)
						"keyboard":
							_set_cap(r["cap"], Controls.key_name(Controls.keyboard[r["player"]].get(r["button"])), false)
						_:
							var keys: Array = Controls.menu_keys.get(r["button"], [])
							_set_cap(r["cap"], Controls.key_name(keys[0] if not keys.is_empty() else null), false)
	var cur: Dictionary = _columns[_col][_row]
	var bar_size := Vector2(cur["x1"] - cur["x0"], cur["h"])
	var pos := Vector2(cur["x0"], cur["y"] - bar_size.y / 2.0)
	for child in _row_bar.get_children():
		child.queue_free()
	_row_bar.add_child(NetsuUI.row_bar(bar_size))
	_row_bar.position = pos
	for child in _row_marks.get_children():
		child.queue_free()
	var bind_page := _page in ["pad", "keyboard", "menu_keys"]
	var h := minf(bar_size.y * 0.5, 26.0)
	_row_marks.add_child(NetsuUI.chevron(Vector2(pos.x + 22, cur["y"]), h, Color.WHITE, 3.0))
	if bind_page:
		_row_marks.add_child(NetsuUI.chevron(Vector2(pos.x + 46, cur["y"]), h * 0.8, NetsuUI.CYAN, 3.0, true))
	elif cur.get("action", "") == "start":
		_row_marks.add_child(NetsuUI.chevron(Vector2(pos.x + 52, cur["y"]), h * 0.9, NetsuUI.CYAN, 3.0, true))
	_footer["text"].text = cur.get("help", "")


func _notice(text: String) -> void:
	_footer["text"].text = text
	_footer["text"].modulate.a = 0.0
	if _notice_tween:
		_notice_tween.kill()
	_notice_tween = create_tween()
	_notice_tween.tween_property(_footer["text"], "modulate:a", 1.0, 0.15)


# --- Sound ------------------------------------------------------------------------------------

func _audio(method: String, index: int) -> void:
	var audio := get_node_or_null("/root/AudioManager")
	if audio and audio.has_method(method):
		audio.call(method, index)


## Plays the first song in data/soundtrack.tres so BGM volume can be heard. Nov 2: not when music is already playing
## (the main menu theme carries on under Options and is what you hear while changing the volume).
var _preview_playing := false
func _play_preview_music() -> void:
	var audio := get_node_or_null("/root/AudioManager")
	if audio == null or not ResourceLoader.exists("res://data/soundtrack.tres"):
		return
	if audio.has_method("PlayingBGM") and audio.call("PlayingBGM"):
		return
	var list = load("res://data/soundtrack.tres")
	if list == null:
		return
	var songs = list.get("elements")
	if songs and songs.size() > 0 and songs[0].get("clip"):
		audio.call("PlayBGM", songs[0].get("clip"))
		_preview_playing = true


## The settings list "grows" out of the OPTIONS row: the joining line draws
## first, then the entries slide out from the left one after another.
func _entrance() -> void:
	var t := create_tween().set_parallel(true)
	var start := 0.15 if embedded else 0.0   # let Cecilia start stepping aside first
	_link.modulate.a = 0.0
	t.tween_property(_link, "modulate:a", 1.0, 0.25).set_delay(start)
	for node in [_cat_bar, _cat_gem]:
		node.modulate.a = 0.0
		t.tween_property(node, "modulate:a", 1.0, 0.2).set_delay(start + 0.12)
	if _list_shade:
		_list_shade.modulate.a = 0.0
		t.tween_property(_list_shade, "modulate:a", 1.0, 0.25).set_delay(start)
	for i in _cat_labels.size():
		var l := _cat_labels[i]
		var home := l.position
		l.position = home - Vector2(70, 0)
		l.modulate.a = 0.0
		var d := start + 0.1 + 0.035 * i
		t.tween_property(l, "modulate:a", 1.0, 0.2).set_delay(d)
		t.tween_property(l, "position", home, 0.3).set_delay(d).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
