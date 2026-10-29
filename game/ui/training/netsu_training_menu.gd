extends Control
## TRAINING MENU  (pause > Training Menu, Training mode only)  -  Oct 24 2026
##
##                         ✦  TRAINING MENU  ✦
##   ┌───────────────┬─────────────────────────────────────────────┐
##   │ » DUMMY       │  Dummy Action              <   Stand    >  │
##   │   RECOVERY    │  CPU Level                 <   Normal   >  │
##   │   GAUGES      │  Guard                     <  Guard All >  │
##   │   DISPLAY     │  Counter Hit               <    Off     >  │
##   │   RECORDING   │  ...                                        │
##   │   QUICK SELECT│                                             │
##   └───────────────┴─────────────────────────────────────────────┘
##   help for the highlighted row                      button prompts
##
## Up / Down picks a tab, A or Right opens its rows; in the rows Left / Right changes a value,
## A runs an action, B goes back to the tabs (B there closes the menu).
## Settings live in GameSettings' "training" section (saved like every other setting) and reach
## the fight straight away: game/ui/training/netsu_training_hud.gd sends them to the engine
## (engine/sakuga/Game/NetsuTraining.cs). QUICK SELECT changes fighters, colours, assists, stage
## and music, then restarts the fight.
## Opened by game/ui/pause/netsu_pause_menu.gd, which hands over its footer and the training HUD.
##
## TO ADD A SETTING: a key in GameSettings.DEFAULTS["training"], a row in _rows(), and its use in
## NetsuTraining.cs (Apply reads it by the same key).

## Back out of the menu (the pause menu comes back).
signal closed
## Close the menu AND the pause menu: back to the fight (Reset Position, Record, Play...).
signal resume
## Quick Select restarted the fight (the pause menu stops reacting).
signal leaving

const CANVAS := Vector2(1920, 1080)
const TAB_PROMPTS := "UP / DOWN  TAB     A  OPEN     B  BACK"
const ROW_PROMPTS := "SELECT     LEFT / RIGHT  CHANGE     A  CONFIRM     B  TABS"
const ROW_TEXT := Color(0.9, 0.92, 1.0)

const TABS := [
	{"id": "dummy", "label": "DUMMY", "blurb": "What the dummy does on its own, how it guards, and where a reset puts you both."},
	{"id": "recovery", "label": "RECOVERY", "blurb": "Recovering in the air, getting up after a knockdown, and what the dummy does as it gets up."},
	{"id": "gauges", "label": "GAUGES", "blurb": "Health, Craft Gauge, Burst gauge and the assist gauge for each side."},
	{"id": "display", "label": "DISPLAY", "blurb": "Training data, input history, hitboxes and the shortcut guide."},
	{"id": "recording", "label": "RECORDING", "blurb": "Record the dummy doing something, then play it back (also on wake-up)."},
	{"id": "quick", "label": "QUICK SELECT", "blurb": "Change fighters, colours, assists, stage and music, then restart."},
]

## Set by the pause menu before adding this node.
var footer: Dictionary = {}
var hud: Node = null

@export_group("Layout (1920x1080)")
@export var panel: Rect2 = Rect2(170, 196, 1580, 724)
@export var tab_width: float = 400.0
@export var title_y: float = 128.0

var _tab := 0
var _in_rows := false
var _row := 0
var _rows_now: Array = []
var _quick := {}

var _content: Control
var _tab_labels: Array[Label] = []
var _tab_bar: Node2D
var _tab_marks: Node2D
var _rows_root: Control
var _row_bar: Node2D
var _row_marks: Node2D
var _help: Label
var _closing := false


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	size = CANVAS
	_init_quick()
	var dim := ColorRect.new()
	dim.color = Color(0.01, 0.02, 0.1, 0.62)
	dim.mouse_filter = Control.MOUSE_FILTER_IGNORE
	dim.size = CANVAS
	add_child(dim)
	_content = Control.new()
	_content.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_content.size = CANVAS
	_content.pivot_offset = CANVAS / 2.0
	add_child(_content)
	NetsuUI.page_title(_content, "TRAINING MENU", title_y / NetsuUI.K, 46)
	NetsuUI.frame_panel(_content, panel)
	var split := NetsuUI.gradient_rect(Color(0.55, 0.75, 1.0, 0.15), Color(0.55, 0.75, 1.0, 0.7), true)
	split.position = Vector2(panel.position.x + tab_width, panel.position.y + 26)
	split.size = Vector2(1.5, panel.size.y - 52)
	_content.add_child(split)
	_build_tabs()
	_rows_root = Control.new()
	_rows_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_rows_root.size = CANVAS
	_content.add_child(_rows_root)
	_build_help()
	_select_tab(0, false)
	_animate_in()


# --- Input ----------------------------------------------------------------------------------

func _unhandled_input(event: InputEvent) -> void:
	if _closing:
		return
	if not _in_rows:
		if event.is_action_pressed("ui_down", true):
			_select_tab(_tab + 1)
		elif event.is_action_pressed("ui_up", true):
			_select_tab(_tab - 1)
		elif event.is_action_pressed("ui_accept") or event.is_action_pressed("ui_right"):
			_enter_rows()
		elif event.is_action_pressed("ui_cancel"):
			_close()
		elif _is_menu_event(event):
			pass
		else:
			return
	else:
		if event.is_action_pressed("ui_down", true):
			_move_row(1)
		elif event.is_action_pressed("ui_up", true):
			_move_row(-1)
		elif event.is_action_pressed("ui_right", true):
			_change(1, false)
		elif event.is_action_pressed("ui_left", true):
			_change(-1, false)
		elif event.is_action_pressed("ui_accept"):
			_accept()
		elif event.is_action_pressed("ui_cancel"):
			_leave_rows()
		elif _is_menu_event(event):
			pass
		else:
			return
	get_viewport().set_input_as_handled()


func _is_menu_event(event: InputEvent) -> bool:
	for a in ["ui_up", "ui_down", "ui_left", "ui_right", "ui_accept", "ui_cancel"]:
		if event.is_action(a):
			return true
	return false


# --- Tabs -----------------------------------------------------------------------------------

func _build_tabs() -> void:
	_tab_bar = Node2D.new()
	_content.add_child(_tab_bar)
	var x := panel.position.x + 70.0
	for i in TABS.size():
		var l := NetsuUI.label(TABS[i]["label"], 27, ROW_TEXT, NetsuUI.sans(5))
		l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		l.position = Vector2(x, _tab_y(i) - 30)
		l.size = Vector2(tab_width - 90, 60)
		_content.add_child(l)
		_tab_labels.append(l)
	_tab_marks = Node2D.new()
	_content.add_child(_tab_marks)


func _tab_y(i: int) -> float:
	return panel.position.y + 78.0 + i * 76.0


func _select_tab(index: int, sound: bool = true) -> void:
	_tab = wrapi(index, 0, TABS.size())
	_row = 0
	if sound:
		_audio(0)
	_build_rows()
	_refresh()


func _enter_rows() -> void:
	if _rows_now.is_empty():
		return
	_in_rows = true
	_row = _first_row()
	_audio(1)
	_refresh()


func _leave_rows() -> void:
	_in_rows = false
	_audio(0)
	_refresh()


func _close() -> void:
	if _closing:
		return
	_closing = true
	closed.emit()
	_animate_out(queue_free)


# --- Rows -----------------------------------------------------------------------------------

func _rows(id: String) -> Array:
	var rows := _tab_rows(id)
	if id in ["dummy", "recovery", "gauges", "display"]:
		rows.append({"type": "spacer"})
		rows.append(_action("Restore Defaults", "restore", "Put this tab's settings back to how they started."))
	if _p2_human() and id in ["dummy", "recovery", "recording"]:
		rows.push_front({"type": "spacer"})
		rows.push_front({"type": "info", "label": "Player 2 Controls the Dummy",
			"text": "Recording Off" if id == "recording" else "Settings Off"})
	return rows


## A second player joined on the character select and controls the dummy: the dummy's own behaviour
## and recording are off (NetsuTraining does the same), Reset Position and the gauges still work.
func _p2_human() -> bool:
	var cfg = MatchSetup.settings()
	return cfg != null and int(cfg.P2SelectedDevice) >= 0


func _tab_rows(id: String) -> Array:
	var on_off := [[true, false], ["On", "Off"]]
	match id:
		"dummy":
			return [
				_pick("Dummy Action", "dummy", [0, 1, 2, 3, 4], ["Stand", "Crouch", "Jump", "CPU", "Playback"],
					"Stand, crouch, keep jumping, let the CPU fight, or repeat your recording (Recording tab)."),
				_pick("CPU Level", "cpu_level", range(GameSettings.DIFFICULTIES.size()), GameSettings.DIFFICULTIES,
					"How strong the dummy fights when Dummy Action is CPU."),
				_pick("Guard", "guard", [0, 1, 2, 3], ["None", "Guard All", "After First Hit", "Random"],
					"Guard All blocks high and low correctly. After First Hit lets the first hit land, then blocks the rest of the string. Random blocks some strings."),
				_pick("Counter Hit", "counter_hit", [false, true], ["Off", "Always"],
					"Always: the hit that starts each combo on the dummy is a counter hit (more hitstun)."),
				{"type": "spacer"},
				_pick("Reset Position", "reset_mode", [0, 1, 2, 3, 4, 5],
					["Center", "Dummy in Left Corner", "Dummy in Right Corner", "Sides Swapped", "You in Left Corner", "You in Right Corner"],
					"Where Q / Back puts you both (hold left / right for a corner, down to swap sides). A: reset now.", "reset"),
			]
		"recovery":
			return [
				_pick("Air Recovery", "air_recovery", [0, 1, 2, 3], ["Off", "Neutral", "Forward", "Random"],
					"Recovering when knocked into the air, as soon as it's allowed. Neutral flips backwards."),
				_pick("Wake-up", "wakeup", [0, 1, 2, 3, 4], ["Stay Down", "Quick Rise", "Roll Forward", "Roll Back", "Random"],
					"How the dummy gets up once it's on the ground. Rolls work after soft knockdowns, Quick Rise only after an ordinary fall (not a knockdown hit); nothing works after a hard knockdown."),
				_pick("Wake-up Action", "wakeup_action", range(9),
					["None", "Jump", "Back Jump", "Backdash", "5A", "2A", "Assist Call", "Burst", "Recording"],
					"Done on the first frame the dummy can act after getting up (a reversal). Recording plays your recording."),
			]
		"gauges":
			var health := [[100, 75, 50, 25, 10, 0], ["100%", "75%", "50%", "25%", "10%", "No Refill"]]
			var craft := [[-1, -2, 0, 1, 2, 3, 4], ["Always Full", "Normal", "0 Bars", "1 Bar", "2 Bars", "3 Bars", "4 Bars"]]   # Oct 28: the gauge holds 4 bars
			var burst := [[-1, -2], ["Always Full", "Normal"]]
			var health_help := "Health goes back to this once a combo is over. No Refill: it keeps dropping (nobody is K.O.'d)."
			var craft_help := "Always Full refills whenever you're free. Normal works as in a match. A number of bars: back to that after each combo."
			var burst_help := "Always Full refills whenever you're free (not during Overdrive). Normal works as in a match."
			return [
				_pick("P1 Health", "p1_health", health[0], health[1], health_help),
				_pick("P2 Health", "p2_health", health[0], health[1], health_help),
				_pick("P1 Craft Gauge", "p1_craft", craft[0], craft[1], craft_help),
				_pick("P2 Craft Gauge", "p2_craft", craft[0], craft[1], craft_help),
				_pick("P1 Burst Gauge", "p1_burst", burst[0], burst[1], burst_help),
				_pick("P2 Burst Gauge", "p2_burst", burst[0], burst[1], burst_help),
				_pick("Assist Gauge", "assist_instant", [true, false], ["Instant Refill", "Normal"],
					"Instant Refill: the assist is ready again as soon as it has left."),
			]
		"display":
			return [
				_pick("Training Data", "show_info", on_off[0], on_off[1], "Damage, combo, scaling and frame advantage panels."),
				_pick("Input History", "show_inputs", on_off[0], on_off[1], "The list of recent inputs down the side."),
				_pick("Hitboxes", "show_hitboxes", on_off[0], on_off[1], "Show hit and hurt boxes (F10 also toggles them)."),
				_pick("Shortcut Guide", "show_guide", on_off[0], on_off[1], "The reset / record / play keys along the bottom of the screen."),
			]
		"recording":
			return [
				_action("Record Dummy", "record_start", "Back to the fight: you control the dummy and everything is recorded (up to 20 s). R / LSB stops it."),
				_action("Play Recording", "play_start", "Back to the fight and play the recording. T / RSB plays or stops it in the fight."),
				_pick("Playback", "playback_repeat", [false, true], ["Once", "Repeat"],
					"Once plays it a single time; Repeat loops it until you stop it. Dummy Action: Playback always loops."),
				{"type": "info", "label": "Recorded", "help": "Length of the recording.", "text": _recorded_text()},
				_action("Clear Recording", "clear", "Forget the recording."),
			]
		"quick":
			return [
				_quick_row("P1 Fighter", "p1", "Player 1's fighter."),
				_quick_row("P1 Color", "c1", "Player 1's colours."),
				_quick_row("P1 Assist", "a1", "Player 1's assist (S)."),
				{"type": "spacer"},
				_quick_row("P2 Fighter", "p2", "The dummy's fighter."),
				_quick_row("P2 Color", "c2", "The dummy's colours."),
				_quick_row("P2 Assist", "a2", "The dummy's assist."),
				{"type": "spacer"},
				_quick_row("Stage", "st", "Where to train."),
				_quick_row("Music", "mu", "Auto plays player 1's theme."),
				{"type": "spacer"},
				_action("Apply and Restart", "apply", "Start training again with these picks (settings stay as they are)."),
			]
	return []


func _pick(label: String, key: String, values: Array, names: Array, help: String, on_accept: String = "") -> Dictionary:
	return {"type": "pick", "label": label, "key": key, "values": values, "names": names, "help": help, "accept": on_accept}


func _action(label: String, action: String, help: String) -> Dictionary:
	return {"type": "action", "label": label, "action": action, "help": help}


func _quick_row(label: String, key: String, help: String) -> Dictionary:
	return {"type": "quick", "label": label, "key": key, "help": help}


func _first_row() -> int:
	for i in _rows_now.size():
		if _rows_now[i]["type"] in ["pick", "action", "quick"]:
			return i
	return 0


func _move_row(dir: int) -> void:
	var i := _row
	for n in _rows_now.size():
		i = wrapi(i + dir, 0, _rows_now.size())
		if _rows_now[i]["type"] in ["pick", "action", "quick"]:
			break
	_row = i
	_audio(0)
	_refresh()


func _change(dir: int, wrap: bool) -> void:
	var r: Dictionary = _rows_now[_row]
	match r["type"]:
		"pick":
			var values: Array = r["values"]
			var cur := maxi(values.find(GameSettings.get_value("training", r["key"])), 0)
			var next := wrapi(cur + dir, 0, values.size()) if wrap else clampi(cur + dir, 0, values.size() - 1)
			if next == cur:
				return
			GameSettings.set_value("training", r["key"], values[next])
		"quick":
			if not _quick_step(r["key"], dir):
				return
		_:
			return
	_audio(0)
	_refresh()


func _accept() -> void:
	var r: Dictionary = _rows_now[_row]
	match r["type"]:
		"pick":
			if r.get("accept", "") == "reset":
				_audio(1)
				if hud and hud.has_method("reset_positions"):
					hud.call("reset_positions", int(GameSettings.get_value("training", "reset_mode")))
				_resume()
			else:
				_change(1, true)
		"quick":
			_quick_step(r["key"], 1)
			_audio(0)
			_refresh()
		"action":
			_audio(1)
			match r["action"]:
				"record_start", "play_start":
					if hud and hud.has_method("command"):
						hud.call("command", r["action"])
					_resume()
				"clear":
					if hud and hud.has_method("command"):
						hud.call("command", "clear")
					for row in _rows_now:
						if row["type"] == "info" and row["label"] == "Recorded":
							row["text"] = "Nothing yet"
					_refresh()
					_notice("Recording cleared.")
				"apply":
					_apply_quick()
				"restore":
					var keys: Array = []
					for row in _rows_now:
						if row["type"] == "pick":
							keys.append(row["key"])
					GameSettings.restore_keys("training", keys)
					_refresh()
					_notice("Defaults restored.")


func _resume() -> void:
	if _closing:
		return
	_closing = true
	resume.emit()
	_animate_out(queue_free)


func _notice(text: String) -> void:
	if _help:
		_help.text = text


## A value label's text, a size smaller when it doesn't fit (long stage and song names).
func _set_value(l: Label, text: String) -> void:
	var font: Font = l.get_theme_font("font")
	var size := 26
	while size > 17 and font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x > l.size.x - 8:
		size -= 1
	l.add_theme_font_size_override("font_size", size)
	l.text = text


func _recorded_text() -> String:
	var frames := 0
	if hud and hud.get("_status") is Dictionary:
		frames = int(hud.get("_status").get("frames", 0))
	return "Nothing yet" if frames == 0 else "%.1f seconds" % (frames / 60.0)


# --- Quick Select -------------------------------------------------------------------------------

func _init_quick() -> void:
	var cfg = MatchSetup.settings()
	_quick = {"p1": 0, "c1": 0, "a1": 0, "p2": 0, "c2": 1, "a2": 0, "st": 0, "mu": MatchSetup.music_choice}
	if cfg == null:
		return
	_quick["p1"] = int(cfg.P1SelectedCharacter)
	_quick["c1"] = int(cfg.P1SelectedColor)
	_quick["p2"] = int(cfg.P2SelectedCharacter)
	_quick["c2"] = MatchSetup.engine_color(1) if MatchSetup.has_method("engine_color") else int(cfg.P2SelectedColor)
	_quick["st"] = int(cfg.SelectedStage)
	_quick["a1"] = maxi(MatchSetup.assist_for_side(0), 0)
	_quick["a2"] = maxi(MatchSetup.assist_for_side(1), 0)


## Steps one Quick Select value; false when nothing changed.
func _quick_step(key: String, dir: int) -> bool:
	var before = _quick[key]
	match key:
		"p1", "p2":
			var n := MatchSetup.fighter_count()
			if n <= 1:
				return false
			_quick[key] = wrapi(int(_quick[key]) + dir, 0, n)
			_quick["c1" if key == "p1" else "c2"] = 0
		"c1", "c2":
			var f := int(_quick["p1" if key == "c1" else "p2"])
			var n := MatchSetup.palette_count(f)
			if n <= 1:
				return false
			_quick[key] = wrapi(int(_quick[key]) + dir, 0, n)
		"a1", "a2":
			var n := MatchSetup.assist_count()
			if n <= 1:
				return false
			_quick[key] = wrapi(int(_quick[key]) + dir, 0, n)
		"st":
			var n := MatchSetup.stage_count()
			if n <= 1:
				return false
			_quick[key] = wrapi(int(_quick[key]) + dir, 0, n)
		"mu":
			# AUTO, RANDOM, then each song
			var order: Array = [MatchSetup.MUSIC_AUTO, MatchSetup.MUSIC_RANDOM]
			for i in MatchSetup.song_count():
				order.append(i)
			var i := maxi(order.find(_quick[key]), 0)
			_quick[key] = order[wrapi(i + dir, 0, order.size())]
	# same fighter on both sides can't wear the same colours
	if _quick["p1"] == _quick["p2"] and _quick["c1"] == _quick["c2"]:
		var n := MatchSetup.palette_count(int(_quick["p2"]))
		if n > 1:
			var side := "c1" if key == "c1" else "c2"
			_quick[side] = wrapi(int(_quick[side]) + (dir if dir != 0 else 1), 0, n)
	return _quick[key] != before or key in ["c1", "c2"]


func _quick_text(key: String) -> String:
	var v = _quick.get(key, 0)
	match key:
		"p1", "p2":
			if MatchSetup.fighter_count() == 0:
				return "-"
			return str(MatchSetup.fighter_profile(int(v)).ShortName)
		"c1", "c2":
			var f := int(_quick["p1" if key == "c1" else "p2"])
			return MatchSetup.palette_name(f, int(v)) if int(v) < MatchSetup.palette_count(f) else "-"
		"a1", "a2":
			return MatchSetup.assist_name(int(v))
		"st":
			return MatchSetup.stage_name(int(v)) if int(v) < MatchSetup.stage_count() else "-"
		"mu":
			if int(v) == MatchSetup.MUSIC_AUTO:
				return "Auto (P1's Theme)"
			if int(v) == MatchSetup.MUSIC_RANDOM:
				return "Random"
			return str(MatchSetup.song_info(int(v)).get("title", "-"))
	return str(v)


func _apply_quick() -> void:
	if _closing:
		return
	_closing = true
	leaving.emit()
	var cfg = MatchSetup.settings()
	MatchSetup.music_choice = int(_quick["mu"])
	MatchSetup.assist_picks = [int(_quick["a1"]), int(_quick["a2"])]
	MatchSetup.last_stage = int(_quick["st"])
	var d1 := int(cfg.P1SelectedDevice) if cfg else 0
	var d2 := int(cfg.P2SelectedDevice) if cfg else -1
	MatchSetup.start_match(int(_quick["p1"]), int(_quick["p2"]), d1, d2, int(_quick["st"]),
		int(_quick["c1"]), int(_quick["c2"]), int(_quick["a1"]), int(_quick["a2"]))


# --- Drawing --------------------------------------------------------------------------------------

## Where the rows go: the right side of the panel above the help box.
func _row_area() -> Rect2:
	var x0 := panel.position.x + tab_width + 40.0
	return Rect2(x0, panel.position.y + 30.0, panel.end.x - 40.0 - x0, panel.size.y - 30.0 - HELP_HEIGHT)


const HELP_HEIGHT := 150.0

## The box under the rows that explains the highlighted row (or the tab).
func _build_help() -> void:
	var area := _row_area()
	var y := panel.end.y - HELP_HEIGHT + 14.0
	NetsuUI.divider(_content, area.position.x + 20, area.end.x - 20, y, true)
	var tag := NetsuUI.label("", 15, NetsuUI.CYAN, NetsuUI.sans(6))
	tag.name = "HelpTag"
	tag.position = Vector2(area.position.x + 40, y + 16)
	tag.size = Vector2(area.size.x - 80, 22)
	_content.add_child(tag)
	_help = NetsuUI.label("", 21, Color(0.82, 0.86, 0.98), NetsuUI.body())
	_help.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_help.position = Vector2(area.position.x + 40, y + 42)
	_help.size = Vector2(area.size.x - 80, HELP_HEIGHT - 70.0)
	_content.add_child(_help)


func _build_rows() -> void:
	for c in _rows_root.get_children():
		c.queue_free()
	_rows_now = _rows(TABS[_tab]["id"])
	var area := _row_area()
	var count := 0.0
	for r in _rows_now:
		count += 0.6 if r["type"] == "spacer" else 1.0
	var pitch := minf(64.0, area.size.y / maxf(count, 1.0))
	var y := area.position.y + maxf(0.0, (area.size.y - count * pitch) * 0.15)
	var value_center := area.end.x - 230.0
	_row_bar = Node2D.new()
	_rows_root.add_child(_row_bar)
	for r in _rows_now:
		if r["type"] == "spacer":
			NetsuUI.divider(_rows_root, area.position.x + 20, area.end.x - 20, y + pitch * 0.3, false)
			y += pitch * 0.6
			continue
		r["y"] = y + pitch / 2.0
		r["h"] = pitch * 0.9
		var sep := ColorRect.new()
		sep.color = Color(0.55, 0.7, 1.0, 0.12)
		sep.position = Vector2(area.position.x, y + pitch - 1)
		sep.size = Vector2(area.size.x, 1)
		sep.mouse_filter = Control.MOUSE_FILTER_IGNORE
		_rows_root.add_child(sep)
		var l := NetsuUI.label(r["label"], 26, ROW_TEXT, NetsuUI.sans(1))
		l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		l.position = Vector2(area.position.x + 70, r["y"] - 30)
		l.size = Vector2(520, 60)
		_rows_root.add_child(l)
		r["node"] = l
		match r["type"]:
			"pick", "quick", "info":
				var v := NetsuUI.label("", 26, ROW_TEXT, NetsuUI.sans(1))
				v.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
				v.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
				v.position = Vector2(value_center - 195, r["y"] - 30)
				v.size = Vector2(390, 60)
				v.clip_text = true
				_rows_root.add_child(v)
				r["value"] = v
				if r["type"] != "info":
					var left := NetsuUI.arrow(Vector2(value_center - 215, r["y"]), 22, -1, ROW_TEXT, 3.0)
					var right := NetsuUI.arrow(Vector2(value_center + 215, r["y"]), 22, 1, ROW_TEXT, 3.0)
					_rows_root.add_child(left)
					_rows_root.add_child(right)
					r["left"] = left
					r["right"] = right
			"action":
				var go := NetsuUI.arrow(Vector2(value_center + 215, r["y"]), 22, 1, ROW_TEXT, 3.0)
				_rows_root.add_child(go)
		y += pitch
	_row_marks = Node2D.new()
	_rows_root.add_child(_row_marks)
	if is_inside_tree() and _rows_root.modulate.a > 0.0:
		_cascade_rows()


func _refresh() -> void:
	# tabs: the open one keeps a dim bar while you're in its rows
	for i in _tab_labels.size():
		_tab_labels[i].add_theme_color_override("font_color", Color.WHITE if i == _tab else NetsuUI.DIM)
	for c in _tab_bar.get_children():
		c.queue_free()
	for c in _tab_marks.get_children():
		c.queue_free()
	var bar_w := tab_width - 50.0
	var bar := NetsuUI.row_bar(Vector2(bar_w, 56))
	bar.position = Vector2(panel.position.x + 25, _tab_y(_tab) - 28)
	bar.modulate.a = 0.35 if _in_rows else 1.0
	_tab_bar.add_child(bar)
	if not _in_rows:
		_tab_marks.add_child(NetsuUI.chevron(Vector2(panel.position.x + 46, _tab_y(_tab)), 24, Color.WHITE, 3.0))
	# rows
	var area := _row_area()
	for i in _rows_now.size():
		var r: Dictionary = _rows_now[i]
		var on := _in_rows and i == _row
		var ink := Color.WHITE if on else ROW_TEXT
		if r.has("node"):
			r["node"].add_theme_color_override("font_color", ink)
		match r["type"]:
			"pick":
				var values: Array = r["values"]
				var idx := maxi(values.find(GameSettings.get_value("training", r["key"])), 0)
				_set_value(r["value"], str(r["names"][idx]))
				r["value"].add_theme_color_override("font_color", ink)
				r["left"].modulate.a = 1.0 if idx > 0 else 0.25
				r["right"].modulate.a = 1.0 if idx < values.size() - 1 else 0.25
			"quick":
				_set_value(r["value"], _quick_text(r["key"]))
				r["value"].add_theme_color_override("font_color", ink)
			"info":
				r["value"].add_theme_color_override("font_color", NetsuUI.DIM)
				_set_value(r["value"], str(r.get("text", "")))
	for c in _row_bar.get_children():
		c.queue_free()
	for c in _row_marks.get_children():
		c.queue_free()
	if _in_rows and _row < _rows_now.size() and _rows_now[_row].has("y"):
		var cur: Dictionary = _rows_now[_row]
		var size := Vector2(area.size.x, cur["h"])
		var rb := NetsuUI.row_bar(size)
		rb.position = Vector2(area.position.x, cur["y"] - size.y / 2.0)
		_row_bar.add_child(rb)
		_row_marks.add_child(NetsuUI.chevron(Vector2(area.position.x + 24, cur["y"]), minf(size.y * 0.5, 24.0), Color.WHITE, 3.0))
		if cur["type"] == "action":
			_row_marks.add_child(NetsuUI.chevron(Vector2(area.position.x + 48, cur["y"]), minf(size.y * 0.45, 22.0), NetsuUI.CYAN, 3.0, true))
	var on_row := _in_rows and _row < _rows_now.size()
	var blurb: String = TABS[_tab]["blurb"]
	if _p2_human() and TABS[_tab]["id"] in ["dummy", "recovery", "recording"]:
		blurb += " Player 2 controls the dummy, so these are off."
		if TABS[_tab]["id"] == "dummy":
			blurb += " Reset Position still works."
	_help.text = _rows_now[_row].get("help", "") if on_row else blurb
	(_content.get_node("HelpTag") as Label).text = str(_rows_now[_row]["label"]).to_upper() if on_row else TABS[_tab]["label"]
	if footer.has("text"):
		footer["text"].text = ""
	if footer.has("prompts"):
		footer["prompts"].text = ROW_PROMPTS if _in_rows else TAB_PROMPTS


# --- Animation and sound ---------------------------------------------------------------------------

func _animate_in() -> void:
	_content.modulate.a = 0.0
	_content.scale = Vector2(0.96, 0.96)
	var t := create_tween().set_parallel(true).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	t.tween_property(_content, "modulate:a", 1.0, 0.2).set_delay(0.04)
	t.tween_property(_content, "scale", Vector2.ONE, 0.3).set_delay(0.04)
	for i in _tab_labels.size():
		var l := _tab_labels[i]
		var home := l.position
		l.position = home - Vector2(30, 0)
		l.modulate.a = 0.0
		t.tween_property(l, "position", home, 0.26).set_delay(0.1 + i * 0.03)
		t.tween_property(l, "modulate:a", 1.0, 0.2).set_delay(0.1 + i * 0.03)


func _cascade_rows() -> void:
	var t := create_tween().set_parallel(true)
	var k := 0
	for c in _rows_root.get_children():
		if c is Control:
			var home: float = c.position.x
			c.position.x = home + 24
			c.modulate.a = 0.0
			t.tween_property(c, "position:x", home, 0.2).set_delay(0.012 * k).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
			t.tween_property(c, "modulate:a", 1.0, 0.16).set_delay(0.012 * k)
			k += 1


func _animate_out(done: Callable) -> void:
	var t := create_tween().set_parallel(true).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_IN)
	t.tween_property(_content, "scale", Vector2(0.97, 0.97), 0.16)
	t.tween_property(self, "modulate:a", 0.0, 0.18)
	t.chain().tween_callback(done)


func _audio(index: int) -> void:
	var audio := get_node_or_null("/root/AudioManager")
	if audio and audio.has_method("PlayMenuClip"):
		audio.call("PlayMenuClip", index)
