extends Control
## TRAINING (in the fight, Training mode only)  -  Oct 24 2026
##
## The fight side of Training mode:
##   - sends the Training Menu's settings (GameSettings "training" section) to the engine
##     (GameManager.NetsuSetTraining -> engine/sakuga/Game/NetsuTraining.cs) when the fight starts and
##     whenever one changes, and applies the display ones (training data, input history, hitboxes);
##   - the shortcuts, on any keyboard / controller (Controls.TRAINING_SHORTCUTS):
##       Q / Back          reset positions (hold left / right: the dummy in that corner,
##                         down: sides swapped, down + left / right: you in that corner)
##       R / left stick    record the dummy: you control it until you press again
##       T / right stick   play the recording back (press again to stop)
##   - draws the REC / PLAYBACK chip under the timer, a short flash on reset and the shortcut guide
##     along the bottom (Training Menu > Display > Shortcut Guide);
##   - (Oct 25) the frame data spreadsheets (data/frame_data/*.xlsx): saved while Training runs, they're
##     put into the fight right away (GameManager.NetsuReloadFrameData) and a note lists what changed.
## The Training Menu itself (pause > Training Menu) is netsu_training_menu.gd.
## Lives in scenes/battle/battle.tscn under CanvasLayer; switches itself off in other modes.

const CANVAS := Vector2(1920, 1080)
## The guide along the bottom: [label, keyboard key, controller button].
const GUIDE := [["RESET", "Q", "BACK"], ["RECORD", "R", "LSB"], ["PLAY", "T", "RSB"]]

@export var record_color: Color = Color(1.0, 0.26, 0.34)
@export var play_color: Color = Color(0.35, 0.75, 1.0)
@export var panel_color: Color = Color(0.03, 0.05, 0.17, 0.88)
@export var line_color: Color = Color(0.7, 0.86, 1.0)
## Centre of the REC / PLAYBACK chip (under the round timer).
@export var status_y: float = 196.0
## Baseline of the shortcut guide.
@export var guide_y: float = 1052.0

var _game: Node          # GameManager (C#)
var _ui: Node            # the CanvasLayer
var _mahou_pause: CanvasItem
var _active := false
var _font: Font
var _bold: Font
var _status := {}
var _time := 0.0
var _flash := 0.0
var _guide := true
var _p2_person := false   # a second player joined on the character select and controls the dummy
var _fd_poll := 0.0       # frame data spreadsheets: time since they were last checked
var _fd_lines: PackedStringArray = []   # what the last reload changed
var _fd_show := 0.0       # seconds the note stays up


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	size = CANVAS
	_ui = get_parent()
	var root: Node = _ui.get_parent() if _ui else null
	if root:
		for n in root.get_children():
			if n.has_method("NetsuSetTraining"):
				_game = n
	_mahou_pause = _ui.get_node_or_null("PauseMenu") as CanvasItem if _ui else null
	_active = _game != null and MatchSetup.mode_name == "Training"
	visible = _active
	set_process(_active)
	set_process_unhandled_input(_active)
	if not _active:
		return
	_font = NetsuUI.sans(2)
	_bold = NetsuUI.sans(5, true)
	var cfg = MatchSetup.settings()
	_p2_person = cfg != null and int(cfg.P2SelectedDevice) >= 0
	GameSettings.changed.connect(_on_setting)
	_push.call_deferred()   # after the engine's own _Ready (it sets the panels' defaults)
	_place.call_deferred()
	get_viewport().size_changed.connect(_fit)
	_fit()


func _fit() -> void:
	var view := get_viewport_rect().size
	scale = Vector2.ONE * (view.x / CANVAS.x)
	position = Vector2(0, (view.y - CANVAS.y * scale.y) / 2.0)


## Just under the pause menu (over the HUD and the training panels).
func _place() -> void:
	var pause := _ui.get_node_or_null("NetsuPauseMenu")
	if pause:
		_ui.move_child(self, pause.get_index())


# --- Settings ----------------------------------------------------------------------------

func _on_setting(section: String, _key: String) -> void:
	if section == "training":
		_push()


func _push() -> void:
	if _game == null:
		return
	_game.call("NetsuSetTraining", MatchSetup.training_options())
	var fg := _ui.get_node_or_null("GameHUD_Foreground")
	if fg:
		var info := fg.get_node_or_null("TrainingInfo") as CanvasItem
		if info:
			info.visible = bool(GameSettings.get_value("training", "show_info"))
		var history := fg.get_node_or_null("InputHistory") as CanvasItem
		if history:
			history.visible = bool(GameSettings.get_value("training", "show_inputs"))
	_game.call("NetsuShowHitboxes", bool(GameSettings.get_value("training", "show_hitboxes")))
	_guide = bool(GameSettings.get_value("training", "show_guide"))


# --- Shortcuts ---------------------------------------------------------------------------

func _paused() -> bool:
	return _mahou_pause != null and _mahou_pause.visible


func _unhandled_input(event: InputEvent) -> void:
	if _paused() or SceneRouter.is_busy():
		return
	if event.is_action_pressed("training_reset"):
		reset_positions(_held_reset_mode())
	elif event.is_action_pressed("training_record"):
		command("record")
	elif event.is_action_pressed("training_play"):
		command("play")
	else:
		return
	get_viewport().set_input_as_handled()


## The reset spot from the direction player 1 holds (none = the Training Menu's Reset Position).
func _held_reset_mode() -> int:
	var left := Input.is_action_pressed("p1_left")
	var right := Input.is_action_pressed("p1_right")
	var down := Input.is_action_pressed("p1_down")
	if down and left:
		return 4
	if down and right:
		return 5
	if down:
		return 3
	if left:
		return 1
	if right:
		return 2
	return int(GameSettings.get_value("training", "reset_mode"))


## mode: 0 centre, 1 / 2 the dummy in the left / right corner, 3 sides swapped,
## 4 / 5 you in the left / right corner (NetsuTraining.Reset*).
func reset_positions(mode: int) -> void:
	command("reset", mode)
	_flash = 1.0


## "record" / "play" (start or stop, the shortcuts), "record_start" / "play_start" (always start, the
## Training Menu), "stop", "clear", "reset" (engine/sakuga/Game/NetsuTraining.cs, NetsuTraining.Command).
func command(name: String, value: int = 0) -> void:
	if _game:
		_game.call("NetsuTrainingCommand", name, value)


# --- Drawing -------------------------------------------------------------------------------

func _process(delta: float) -> void:
	_time += delta
	_flash = maxf(_flash - delta * 4.0, 0.0)
	if _game:
		var s = _game.call("NetsuTrainingStatus")
		_status = s if s is Dictionary else {}
		_fd_poll += delta
		if _fd_poll >= 0.5 and _game.has_method("NetsuReloadFrameData"):
			_fd_poll = 0.0
			var report := str(_game.call("NetsuReloadFrameData"))
			if report != "":
				_fd_lines = _frame_data_lines(report)
				_fd_show = 6.0
				_flash = 0.6
	_fd_show = maxf(_fd_show - delta, 0.0)
	queue_redraw()


## "Cecilia: 5A startup 6 -> 8; 5A damage 250 -> 300\nMary: ..." -> one line per change (at most 7).
func _frame_data_lines(report: String) -> PackedStringArray:
	var lines: PackedStringArray = []
	for part in report.split("\n", false):
		var who := part.get_slice(":", 0)
		var rest := part.substr(who.length() + 1).strip_edges()
		for change in rest.split("; ", false):
			if lines.size() >= 7:
				lines.append("...")
				return lines
			lines.append("%s  %s" % [who, change])
	return lines


func _draw() -> void:
	if _flash > 0.0:
		draw_rect(Rect2(Vector2.ZERO, CANVAS), Color(0.02, 0.03, 0.1, 0.6 * _flash))
	_draw_status()
	if _fd_show > 0.0 and not _paused():
		_draw_frame_data_note()
	if _guide and not _paused():
		_draw_guide()


## FRAME DATA UPDATED and the changes, under the timer for a few seconds after a spreadsheet was saved.
func _draw_frame_data_note() -> void:
	var alpha := clampf(_fd_show / 0.5, 0.0, 1.0)
	var size := 17
	var w := 560.0
	for line in _fd_lines:
		w = maxf(w, _font.get_string_size(line, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x + 60.0)
	w = minf(w, 1500.0)
	var h := 52.0 + 25.0 * _fd_lines.size()
	var x0 := CANVAS.x / 2.0 - w / 2.0
	var y0 := status_y + 44.0
	draw_rect(Rect2(x0, y0, w, h), Color(panel_color, 0.92 * alpha))
	draw_rect(Rect2(x0, y0, 6, h), Color(play_color, alpha))
	draw_rect(Rect2(x0, y0, w, h), Color(line_color, 0.6 * alpha), false, 1.5)
	draw_string(_bold, Vector2(x0 + 26, y0 + 32), "FRAME DATA UPDATED", HORIZONTAL_ALIGNMENT_LEFT, -1, 20, Color(1, 1, 1, alpha))
	var y := y0 + 60.0
	for line in _fd_lines:
		draw_string(_font, Vector2(x0 + 26, y), line, HORIZONTAL_ALIGNMENT_LEFT, w - 52.0, size, Color(0.86, 0.9, 1.0, alpha))
		y += 25.0


## REC (red, blinking) or PLAYBACK (blue) with the time and a progress line, under the timer.
func _draw_status() -> void:
	var rec: bool = _status.get("recording", false)
	var play: bool = _status.get("playing", false)
	if not rec and not play:
		return
	var frames := int(_status.get("frames", 0))
	var index := int(_status.get("index", 0))
	var most := maxi(int(_status.get("max", 1200)), 1)
	var accent := record_color if rec else play_color
	var title := "REC" if rec else "PLAYBACK"
	var now := float(frames if rec else index) / 60.0
	var total := float(most if rec else frames) / 60.0
	var clock := "%.1f / %.1f s" % [now, total]
	var w := 340.0
	var h := 44.0
	var x0 := CANVAS.x / 2.0 - w / 2.0
	var y0 := status_y - h / 2.0
	var lean := 12.0
	var band := PackedVector2Array([Vector2(x0 + lean, y0), Vector2(x0 + w + lean, y0), Vector2(x0 + w, y0 + h), Vector2(x0, y0 + h)])
	draw_polygon(band, PackedColorArray([panel_color, panel_color, Color(panel_color, 0.75), Color(panel_color, 0.75)]))
	draw_polyline(PackedVector2Array([band[0], band[1], band[2], band[3], band[0]]), Color(accent, 0.85), 1.5, true)
	draw_colored_polygon(PackedVector2Array([band[0], band[0] + Vector2(7, 0), band[3] + Vector2(7, 0), band[3]]), accent)
	var mark := Vector2(x0 + 34, status_y)
	if rec:
		var blink := 0.55 + 0.45 * sin(_time * 7.0)
		draw_circle(mark, 9.0, Color(accent, blink))
		draw_arc(mark, 13.0, 0.0, TAU, 24, Color(accent, 0.35 * blink), 2.0, true)
	else:
		draw_colored_polygon(PackedVector2Array([mark + Vector2(-7, -9), mark + Vector2(9, 0), mark + Vector2(-7, 9)]), accent)
	draw_string(_bold, Vector2(x0 + 56, status_y + 8), title, HORIZONTAL_ALIGNMENT_LEFT, -1, 22, Color.WHITE)
	var cw := _font.get_string_size(clock, HORIZONTAL_ALIGNMENT_LEFT, -1, 19).x
	draw_string(_font, Vector2(x0 + w - 22 - cw, status_y + 7), clock, HORIZONTAL_ALIGNMENT_LEFT, -1, 19, Color(0.86, 0.9, 1.0))
	var p := clampf(now / maxf(total, 0.01), 0.0, 1.0)
	draw_line(Vector2(x0 + 10, y0 + h + 5), Vector2(x0 + w - 10, y0 + h + 5), Color(line_color, 0.18), 3.0)
	draw_line(Vector2(x0 + 10, y0 + h + 5), Vector2(x0 + 10 + (w - 20) * p, y0 + h + 5), accent, 3.0)
	var hint := "You control the dummy   ·   R / LSB  stop" if rec else "T / RSB  stop"
	var hw := _font.get_string_size(hint, HORIZONTAL_ALIGNMENT_LEFT, -1, 16).x
	draw_string_outline(_font, Vector2(CANVAS.x / 2.0 - hw / 2.0, y0 + h + 30), hint, HORIZONTAL_ALIGNMENT_LEFT, -1, 16, 6, Color(0.01, 0.02, 0.1, 0.8))
	draw_string(_font, Vector2(CANVAS.x / 2.0 - hw / 2.0, y0 + h + 30), hint, HORIZONTAL_ALIGNMENT_LEFT, -1, 16, Color(0.86, 0.9, 1.0))


## "[Q | BACK] RESET   [R | LSB] RECORD   [T | RSB] PLAY" centred along the bottom.
func _draw_guide() -> void:
	var size := 17
	var key_size := 15
	var gap := 34.0
	var parts: Array = []
	var total := 0.0
	var human: bool = _p2_person or _status.get("human", false)   # player 2 controls the dummy: no recording
	for g in GUIDE:
		if human and g[0] != "RESET":
			continue
		var key := "%s | %s" % [g[1], g[2]]
		var kw := _bold.get_string_size(key, HORIZONTAL_ALIGNMENT_LEFT, -1, key_size).x + 18.0
		var lw := _font.get_string_size(g[0], HORIZONTAL_ALIGNMENT_LEFT, -1, size).x
		parts.append([key, kw, g[0], lw])
		total += kw + 8.0 + lw
	total += gap * (parts.size() - 1)
	var x := CANVAS.x / 2.0 - total / 2.0
	var y := guide_y
	var back := Rect2(x - 22, y - 22, total + 44, 32)
	draw_rect(back, Color(0.01, 0.02, 0.09, 0.55))
	draw_line(back.position, Vector2(back.end.x, back.position.y), Color(line_color, 0.3), 1.0)
	for p in parts:
		var pill := Rect2(x, y - 18, p[1], 24)
		draw_rect(pill, Color(0.9, 0.93, 1.0, 0.9))
		draw_string(_bold, Vector2(x + 9, y), p[0], HORIZONTAL_ALIGNMENT_LEFT, -1, key_size, Color(0.08, 0.1, 0.3))
		x += p[1] + 8.0
		draw_string(_font, Vector2(x, y), p[2], HORIZONTAL_ALIGNMENT_LEFT, -1, size, Color(0.92, 0.94, 1.0))
		x += p[3] + gap
