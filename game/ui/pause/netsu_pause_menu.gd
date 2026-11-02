extends Control
## PAUSE MENU + COMMAND LIST  (Oct 19 2026 mockups)
##
## The fight engine still decides WHEN the game is paused (pause button ->
## GameManager.PauseControl, which shows/hides Mahou's PauseMenu node). That old
## menu is kept invisible; this one watches it, FADES IN when the game pauses and
## FADES OUT when it resumes.
##
##   Up / Down  choose      A  pick      B or Start  back to the fight
##
## Sound / Button / Keyboard Settings open the same pages as Options
## (scenes/options/options_menu.gd) over the darkened fight. In Training mode there's
## a Training Menu row too (game/ui/training/netsu_training_menu.gd), picked by default. The Command List
## reads actors/<fighter>/command_list.json - one file per fighter - plus the moves of
## the assist that player picked (MatchSetup.assist_command_section).
## Oct 25: the Command List shows each move's name and input only; Up / Down picks a move and its description
## (the third item of each row in command_list.json) shows in the footer, on up to two lines (it used to sit at the
## end of the row and ran over the inputs and past the panel). Left / Right: the other fighter.
##
## Lives in scenes/battle/battle.tscn under CanvasLayer, drawn on a 1920x1080
## canvas scaled to the window like the other Netsu battle overlays.
## Layout numbers are mockup pixels (1672 x 941), converted with NetsuUI.m().

const CANVAS := Vector2(1920, 1080)
const OPTIONS_SCENE := "res://scenes/options/options_menu.tscn"
const TRAINING_MENU := preload("res://game/ui/training/netsu_training_menu.gd")
const PROMPTS := "SELECT     A  CONFIRM     B  RESUME"

const ITEMS := [
	{"id": "close", "label": "Close", "icon": "close", "help": "Back to the fight."},
	{"id": "commands", "label": "Command List", "icon": "commands", "help": "Every move and how to do it."},
	{"id": "sound", "label": "Sound Settings", "icon": "sound", "help": "Music, effects, voice and announcer volume."},
	{"id": "pad", "label": "Button Settings", "icon": "pad", "help": "Change controller buttons."},
	{"id": "keyboard", "label": "Keyboard Settings", "icon": "keyboard", "help": "Change keyboard keys."},
	{"id": "restart", "label": "Restart Match", "icon": "restart", "help": "Start this match again from round 1."},
	{"id": "chars", "label": "Return to Character Select", "icon": "chars", "help": "Pick different fighters."},
	{"id": "menu", "label": "Return to Main Menu", "icon": "menu", "help": "Leave the match."},
]
## A divider line is drawn before this row.
const DIVIDER_BEFORE := 5
## Training mode only, right under Close.
const TRAINING_ITEM := {"id": "training", "label": "Training Menu", "icon": "training",
	"help": "Dummy, recovery, gauges, display, recording, and quick fighter / stage changes."}

@export var fade_time: float = 0.18
@export_group("Layout (mockup pixels)")
@export var panel_rect: Rect2 = Rect2(388, 147, 897, 636)
@export var first_row_y: float = 295.0
@export var row_step: float = 55.7
@export var row_x: Vector2 = Vector2(476, 1195)   ## the selected bar's left / right ends
@export var icon_x: float = 576.0
@export var label_x: float = 626.0
@export var row_font_size: int = 28

var _items: Array = ITEMS.duplicate()   # ITEMS, plus the Training Menu row in Training mode
var _divider := DIVIDER_BEFORE
var _training := false
var _mahou: Control       # the engine's own (hidden) pause menu - tells us if the game is paused
var _game: Node           # GameManager (has PauseControl)
var _open := false
var _sel := 0
var _sub: Control = null  # an open settings page or the command list
var _cmd: Control = null  # the command list, when open
var _cmd_side := 0
var _cmd_rows: Array = []   # the command list's rows: {"bar": ColorRect, "name": String, "note": String}
var _cmd_sel := 0
var _leaving := false

var _band: Control
var _labels: Array[Label] = []
var _icons: Array[NetsuIcon] = []
var _bar: Node2D
var _marks: Node2D
var _footer: Dictionary
var _fade: Tween


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	process_mode = Node.PROCESS_MODE_ALWAYS
	size = CANVAS
	var ui := get_parent()
	_mahou = ui.get_node_or_null("PauseMenu") as Control if ui else null
	if ui and ui.get_parent():
		for n in ui.get_parent().get_children():
			if n.has_method("PauseControl"):
				_game = n
	if _mahou:
		_mahou.modulate.a = 0.0   # keep the engine's menu working, but never drawn
		for c in _mahou.find_children("*", "Control", true, false):
			c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_training = MatchSetup.mode_name == "Training"
	if _training:
		_items.insert(1, TRAINING_ITEM)
		_divider = DIVIDER_BEFORE + 1
		row_step = minf(row_step, 50.0)   # one more row: a little tighter
		first_row_y = minf(first_row_y, 290.0)
	_build()
	visible = false
	modulate.a = 0.0
	get_viewport().size_changed.connect(_fit)
	_fit()


func _fit() -> void:
	var view := get_viewport_rect().size
	scale = Vector2.ONE * (view.x / CANVAS.x)
	position = Vector2(0, (view.y - CANVAS.y * scale.y) / 2.0)


func _process(_delta: float) -> void:
	if _mahou == null:
		return
	_mahou.modulate.a = 0.0
	# the engine gives its hidden Resume button keyboard focus when pausing -
	# take it away so only our menu (or a settings page) reacts to buttons
	var focus := get_viewport().gui_get_focus_owner()
	if focus and _mahou.is_ancestor_of(focus):
		get_viewport().gui_release_focus()
	var paused := _mahou.visible
	if paused and not _open:
		_show()
	elif not paused and _open and not _leaving:
		if _sub != null:
			_set_paused(true)   # a settings page is open: stay paused (Start/Enter also toggle pause)
		else:
			_hide()


# --- Input --------------------------------------------------------------------------

func _input(event: InputEvent) -> void:
	if not _open or _leaving or modulate.a < 0.5:
		return
	if _sub != null and _sub != _cmd:
		return   # the settings page handles its own input
	if event.is_action_pressed("pause"):
		return   # the engine resumes the game; we fade out
	var handled := true
	if _cmd != null:
		if event.is_action_pressed("ui_cancel") or event.is_action_pressed("ui_accept"):
			_close_sub()
		elif event.is_action_pressed("ui_left") or event.is_action_pressed("ui_right"):
			_cmd_side = 1 - _cmd_side
			_refresh_commands()
		elif event.is_action_pressed("ui_down", true):
			_select_command(_cmd_sel + 1)
		elif event.is_action_pressed("ui_up", true):
			_select_command(_cmd_sel - 1)
		else:
			handled = _is_menu_event(event)
	elif event.is_action_pressed("ui_down", true):
		_select(_sel + 1)
	elif event.is_action_pressed("ui_up", true):
		_select(_sel - 1)
	elif event.is_action_pressed("ui_accept"):
		_choose()
	elif event.is_action_pressed("ui_cancel"):
		_set_paused(false)
	else:
		handled = _is_menu_event(event)
	if handled:
		get_viewport().set_input_as_handled()   # keeps the hidden engine menu from reacting too


func _is_menu_event(event: InputEvent) -> bool:
	for a in ["ui_up", "ui_down", "ui_left", "ui_right", "ui_accept", "ui_cancel"]:
		if event.is_action(a):
			return true
	return false


func _choose() -> void:
	var item: Dictionary = _items[_sel]
	var l := _labels[_sel]
	var pop := create_tween()
	pop.tween_property(l, "scale", Vector2(1.04, 1.04), 0.05)
	pop.tween_property(l, "scale", Vector2.ONE, 0.08)
	_audio(1)
	match item["id"]:
		"close":
			_set_paused(false)
		"commands":
			_open_commands()
		"training":
			_open_training()
		"sound", "pad", "keyboard":
			_open_settings(item["id"])
		"restart":
			_leave(SceneRouter.BATTLE)
		"chars":
			_leave(SceneRouter.CHARACTER_SELECT)
		"menu":
			_leave(SceneRouter.MAIN_MENU)


func _set_paused(on: bool) -> void:
	if _game:
		_game.call("PauseControl", on)


func _leave(scene: String) -> void:
	_leaving = true
	SceneRouter.go_to(scene)


# --- Showing / hiding ------------------------------------------------------------------

func _show() -> void:
	_open = true
	visible = true
	var first := 1 if _training else 0   # Training: the Training Menu row is picked
	_select(first, false)
	_footer["text"].text = _items[first]["help"]
	_footer["prompts"].text = PROMPTS
	if _fade:
		_fade.kill()
	_band.position.y = 24.0
	_band.scale = Vector2(0.95, 0.95)
	_band.modulate.a = 1.0
	_fade = create_tween().set_parallel(true).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	_fade.tween_property(self, "modulate:a", 1.0, fade_time)
	_fade.tween_property(_band, "position:y", 0.0, fade_time + 0.08)
	_fade.tween_property(_band, "scale", Vector2.ONE, fade_time + 0.12)
	for i in _labels.size():
		var l := _labels[i]
		l.modulate.a = 0.0
		_fade.tween_property(l, "modulate:a", 1.0, 0.16).set_delay(0.04 + i * 0.025)


func _hide() -> void:
	_open = false
	if _fade:
		_fade.kill()
	_fade = create_tween().set_parallel(true).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_IN)
	_fade.tween_property(self, "modulate:a", 0.0, fade_time)
	_fade.tween_property(_band, "position:y", 16.0, fade_time)
	_fade.tween_property(_band, "scale", Vector2(0.97, 0.97), fade_time)
	_fade.chain().tween_callback(func(): visible = false)


func _row_y(i: int) -> float:
	var y := first_row_y + i * row_step
	if i >= _divider:
		y += row_step * 0.5
	return y * NetsuUI.K


func _select(index: int, animate: bool = true) -> void:
	_sel = wrapi(index, 0, _items.size())
	for i in _labels.size():
		_labels[i].add_theme_color_override("font_color", Color.WHITE if i == _sel else Color(0.9, 0.92, 1.0))
	var target := Vector2(row_x.x * NetsuUI.K, _row_y(_sel) - 26 * NetsuUI.K)
	if animate:
		_audio(0)
		create_tween().tween_property(_bar, "position", target, 0.1).set_trans(Tween.TRANS_CUBIC)
		create_tween().tween_property(_marks, "position", target, 0.1).set_trans(Tween.TRANS_CUBIC)
	else:
		_bar.position = target
		_marks.position = target
	if _footer:
		_footer["text"].text = _items[_sel]["help"]


# --- Settings pages (shared with Options) --------------------------------------------------

func _open_settings(page: String) -> void:
	var opt: Control = load(OPTIONS_SCENE).instantiate()
	opt.set("embedded", true)
	opt.set("start_page", page)
	opt.set("backdrop", "dim")
	opt.set("footer_override", _footer)
	add_child(opt)
	move_child(_footer["root"], get_child_count() - 1)   # footer stays on top
	opt.connect("closed", _close_sub)
	_sub = opt
	_band_away()


func _close_sub() -> void:
	if _cmd != null:
		var cmd := _cmd
		var t := create_tween().set_parallel(true).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_IN)
		t.tween_property(cmd, "modulate:a", 0.0, 0.16)
		t.tween_property(cmd, "scale", Vector2(0.97, 0.97), 0.16)
		t.chain().tween_callback(cmd.queue_free)
		_cmd = null
	_sub = null
	_footer_lines(1)
	_footer["prompts"].text = PROMPTS
	_footer["text"].text = _items[_sel]["help"]
	var t2 := create_tween().set_parallel(true).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	t2.tween_property(_band, "modulate:a", 1.0, 0.2).set_delay(0.08)
	t2.tween_property(_band, "scale", Vector2.ONE, 0.28).set_delay(0.08)


## Training Menu (Training mode): tabs of dummy / gauge / display settings, recording, quick select.
func _open_training() -> void:
	var menu: Control = TRAINING_MENU.new()
	menu.set("footer", _footer)
	menu.set("hud", get_parent().get_node_or_null("NetsuTrainingHUD"))
	add_child(menu)
	move_child(_footer["root"], get_child_count() - 1)   # footer stays on top
	menu.connect("closed", _close_sub)
	menu.connect("resume", func():
		_close_sub()
		_set_paused(false))
	menu.connect("leaving", func(): _leaving = true)
	_sub = menu
	_band_away()


## The pause panel steps back (shrinks a little and fades) while a page opens over it.
func _band_away() -> void:
	var t := create_tween().set_parallel(true).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_IN)
	t.tween_property(_band, "modulate:a", 0.0, 0.16)
	t.tween_property(_band, "scale", Vector2(0.95, 0.95), 0.18)


## Fades the children of `root` in from top to bottom (a quick cascade).
func _cascade(root: Node, start: float = 0.08) -> void:
	var t := create_tween().set_parallel(true)
	for c in root.get_children():
		if not (c is CanvasItem):
			continue
		var y := 0.0
		if c is Control:
			y = c.position.y
			var home: float = c.position.x
			c.position.x = home - 24
			t.tween_property(c, "position:x", home, 0.26).set_delay(start + y / 1080.0 * 0.3).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
		c.modulate.a = 0.0
		t.tween_property(c, "modulate:a", 1.0, 0.2).set_delay(start + y / 1080.0 * 0.3)


# --- Command list --------------------------------------------------------------------------

func _fighter_index(side: int) -> int:
	var cfg = MatchSetup.settings()
	if cfg == null:
		return side
	return int(cfg.P1SelectedCharacter if side == 0 else cfg.P2SelectedCharacter)


func _load_commands(fighter: int) -> Dictionary:
	if MatchSetup.fighter_count() <= fighter:
		return {}
	var short := str(MatchSetup.fighter_profile(fighter).ShortName).to_lower()
	var path := "res://actors/%s/command_list.json" % short
	if not FileAccess.file_exists(path):
		return {}
	var parsed = JSON.parse_string(FileAccess.get_file_as_string(path))
	return parsed if parsed is Dictionary else {}


func _open_commands() -> void:
	# Nov 2 2026: the new command list (game/ui/command_list/netsu_command_list.gd): System / Characters / Assists
	# tabs, built from the fighters' own move data, with live previews. The old list's code below is unused.
	_band_away()
	var cl := NetsuCommandList.new()
	cl.overlay = true
	cl.footer_override = _footer
	cl.start_tab = "characters"
	cl.start_fighter = _fighter_index(0)
	cl.start_opponent = _fighter_index(1)   # previews hit the fighter you're playing against
	cl.start_assist = maxi(0, MatchSetup.assist_for_side(0))
	cl.side = 0
	cl.closed.connect(_close_command_list)
	add_child(cl)
	move_child(_footer["root"], get_child_count() - 1)
	_sub = cl
	_footer_lines(1)
	cl.pivot_offset = CANVAS / 2.0
	cl.modulate.a = 0.0
	cl.scale = Vector2(0.97, 0.97)
	var t := create_tween().set_parallel(true).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	t.tween_property(cl, "modulate:a", 1.0, 0.2).set_delay(0.06)
	t.tween_property(cl, "scale", Vector2.ONE, 0.3).set_delay(0.06)


func _close_command_list() -> void:
	if _sub is NetsuCommandList:
		_cmd = _sub   # _close_sub fades out and frees _cmd, then puts the pause menu back
		_close_sub()


## Oct 25: Normals and Specials go in the left column, the supers, System and the assist on the right.
const LEFT_SECTIONS := ["normals", "specials"]
const NUMPAD_HINT := "Numpad notation, facing right: 6 = forward, 4 = back, 2 = down, 236 = quarter circle forward."


func _refresh_commands() -> void:
	if _cmd == null:
		return
	for c in _cmd.get_children():
		c.queue_free()
	var k := NetsuUI.K
	var box := Rect2(NetsuUI.m(88, 120), Vector2(1498, 718) * k)
	# Oct 25 evening: solid behind the (see-through) panel, so the fight's HUD text (BURST...) doesn't show through
	var backing := ColorRect.new()
	backing.color = Color(0.02, 0.03, 0.12, 1.0)
	backing.position = box.position
	backing.size = box.size
	backing.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_cmd.add_child(backing)
	NetsuUI.frame_panel(_cmd, box)
	# title, left
	var title_y := 156.0 * k
	var tick := NetsuUI.diamond(7.0, Color(0.75, 0.9, 1.0), Color(0.3, 0.6, 1.0))
	tick.position = Vector2(150 * k, title_y)
	_cmd.add_child(tick)
	_cmd.add_child(NetsuUI.hairline(Vector2(158 * k, title_y), 26 * k, Color(0.7, 0.88, 1.0), 1.5, "none"))
	var font := NetsuUI.sans(8)
	var title := NetsuUI.label("COMMAND LIST", 46, Color.WHITE, font)
	title.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	title.position = Vector2(190 * k, title_y - 32)
	title.size = Vector2(700, 64)
	_cmd.add_child(title)
	var tw := font.get_string_size("COMMAND LIST", HORIZONTAL_ALIGNMENT_LEFT, -1, 46).x
	_cmd.add_child(NetsuUI.hairline(Vector2(190 * k + tw + 6, title_y), 150 * k, Color(0.7, 0.88, 1.0), 1.5, "right"))
	# fighter and player, right
	var fighter := _fighter_index(_cmd_side)
	var data := _load_commands(fighter)
	var name_text: String = str(data.get("fighter", ""))
	if name_text == "" and MatchSetup.fighter_count() > fighter:
		name_text = str(MatchSetup.fighter_profile(fighter).FighterName)
	var who := RichTextLabel.new()
	who.bbcode_enabled = true
	who.fit_content = true
	who.scroll_active = false
	who.autowrap_mode = TextServer.AUTOWRAP_OFF
	who.mouse_filter = Control.MOUSE_FILTER_IGNORE
	who.add_theme_font_override("normal_font", NetsuUI.sans(6))
	who.add_theme_font_size_override("normal_font_size", 26)
	var accent := "#5ab8ff" if _cmd_side == 0 else "#ff4a63"
	who.text = "[right][color=%s]%s[/color]  [color=#9aa6c8]·[/color]  PLAYER %d[/right]" % [accent, name_text.to_upper(), _cmd_side + 1]
	who.position = Vector2(900 * k, title_y - 18)
	who.size = Vector2(627 * k, 40)
	_cmd.add_child(who)
	var sections: Array = data.get("sections", []).duplicate()
	var assist_section: Dictionary = MatchSetup.assist_command_section(MatchSetup.assist_for_side(_cmd_side))
	if not assist_section.is_empty() and not sections.is_empty():
		sections.append(assist_section)
	if sections.is_empty():
		var none := NetsuUI.label("No command list for this fighter yet.", 28, Color(0.9, 0.92, 1.0), NetsuUI.sans(1))
		none.position = Vector2(162 * k, 230 * k)
		none.size = Vector2(1400, 50)
		_cmd.add_child(none)
		return
	# split into columns, then fit the taller one
	var cols: Array = [[], []]
	for s in sections:
		var key := str(s.get("title", "")).to_lower()
		cols[0 if key in LEFT_SECTIONS else 1].append(s)
	if cols[0].is_empty() or cols[1].is_empty():
		cols = [sections.slice(0, (sections.size() + 1) / 2), sections.slice((sections.size() + 1) / 2)]
	var avail := 600.0   # mockup px between the first heading and the panel bottom
	var pitch := 34.0
	for col in cols:
		var rows := 0
		for s in col:
			rows += s.get("moves", []).size()
		var need: float = col.size() * 46.0 + rows * pitch + (col.size() - 1) * 14.0
		if need > avail:
			pitch = minf(pitch, (avail - col.size() * 46.0 - (col.size() - 1) * 14.0) / maxf(rows, 1))
	var divider := NetsuUI.gradient_rect(Color(0.55, 0.75, 1.0, 0.1), Color(0.55, 0.75, 1.0, 0.45), true)
	divider.position = Vector2(848 * k, 200 * k)
	divider.size = Vector2(1.5, 610 * k)
	_cmd.add_child(divider)
	var col_x := [145.0, 890.0]
	var col_w := 660.0
	_cmd_rows = []
	for ci in 2:
		var x0: float = col_x[ci]
		var y := 217.0
		for s in cols[ci]:
			var heading := str(s.get("title", "")).to_upper()
			var gem := NetsuUI.diamond(7.0, Color(0.55, 0.85, 1.0), Color(0.35, 0.7, 1.0))
			gem.position = NetsuUI.m(x0 + 4, y)
			_cmd.add_child(gem)
			var head := NetsuUI.label(heading, 26, Color(0.45, 0.8, 1.0), NetsuUI.sans(7))
			head.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
			head.position = Vector2((x0 + 17) * k, y * k - 22)
			head.size = Vector2(600, 44)
			_cmd.add_child(head)
			_cmd.add_child(NetsuUI.hairline(NetsuUI.m(x0, y + 18), col_w * k, Color(0.5, 0.78, 1.0, 0.85), 1.5, "right"))
			y += 41.0
			for m in s.get("moves", []):
				var cy := y * k
				# the row's highlight (shown on the row picked: its description is in the footer)
				var bar := ColorRect.new()
				bar.color = Color(0.3, 0.62, 1.0, 0.2)
				bar.position = Vector2(x0 * k, (y - pitch / 2.0) * k)
				bar.size = Vector2(col_w * k, pitch * k)
				bar.mouse_filter = Control.MOUSE_FILTER_IGNORE
				bar.visible = false
				_cmd.add_child(bar)
				var edge := ColorRect.new()   # a bright edge on its left
				edge.color = Color(0.45, 0.8, 1.0, 0.95)
				edge.size = Vector2(4, pitch * k)
				edge.mouse_filter = Control.MOUSE_FILTER_IGNORE
				bar.add_child(edge)
				var font_px := 24 if pitch >= 30.0 else 22
				var move_name := NetsuUI.label(str(m[0]), font_px, Color(0.94, 0.95, 1.0), NetsuUI.sans(1))
				move_name.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
				move_name.position = Vector2((x0 + 16) * k, cy - 20)
				move_name.size = Vector2(296 * k, 40)
				move_name.clip_text = true
				move_name.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
				_cmd.add_child(move_name)
				var input := NetsuUI.label(str(m[1]), font_px, Color(0.42, 0.78, 1.0), NetsuUI.sans(3))
				input.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
				input.position = Vector2((x0 + 320) * k, cy - 20)
				input.size = Vector2((col_w - 330) * k, 40)
				input.clip_text = true
				input.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
				_cmd.add_child(input)
				_cmd_rows.append({"bar": bar, "name": str(m[0]), "note": str(m[2]) if m.size() > 2 else ""})
				var sep := ColorRect.new()
				sep.color = Color(0.55, 0.7, 1.0, 0.13)
				sep.position = Vector2(x0 * k, (y + pitch / 2.0) * k)
				sep.size = Vector2(col_w * k, 1)
				sep.mouse_filter = Control.MOUSE_FILTER_IGNORE
				_cmd.add_child(sep)
				y += pitch
			y += 14.0 + 20.0
	_select_command(_cmd_sel, false)
	_cascade(_cmd, 0.1)


## Oct 25: the footer's text on one line (the menu's help) or two (a command list description), wrapping in its width.
var _footer_y := -1.0
func _footer_lines(lines: int) -> void:
	var ft: Label = _footer["text"]
	if _footer_y < 0.0:
		_footer_y = ft.position.y
	ft.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART if lines > 1 else TextServer.AUTOWRAP_OFF
	ft.max_lines_visible = lines
	ft.size = Vector2(1100, 44 if lines <= 1 else 62)
	ft.position.y = _footer_y - (0.0 if lines <= 1 else 9.0)


## Oct 25: picks a row of the command list (wrapping round): highlights it and shows its description in the footer.
func _select_command(index: int, sound: bool = true) -> void:
	if _cmd_rows.is_empty():
		return
	_cmd_sel = posmod(index, _cmd_rows.size())
	for i in _cmd_rows.size():
		(_cmd_rows[i]["bar"] as ColorRect).visible = i == _cmd_sel
	var row: Dictionary = _cmd_rows[_cmd_sel]
	var note: String = row["note"]
	_footer["text"].text = (row["name"] + ": " + note) if note != "" else NUMPAD_HINT
	if sound:
		_audio(0)


# --- Building --------------------------------------------------------------------------------

func _build() -> void:
	var k := NetsuUI.K
	var dim := ColorRect.new()   # the fight stays visible behind a dark blue veil
	dim.color = Color(0.02, 0.04, 0.16, 0.55)
	dim.size = CANVAS
	dim.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(dim)
	# the gauges at the bottom of the fight (the Craft Points "600%", CRAFT POINTS) fade out above the footer
	# instead of peeking over its line or showing through the footer: solid from just above their numbers down
	# to the bottom of the screen
	var fade := NetsuUI.gradient_rect(Color(0.02, 0.04, 0.14, 0.0), Color(0.02, 0.04, 0.14, 1.0), true)
	fade.position = Vector2(0, 849.0 * k - 150.0)
	fade.size = Vector2(CANVAS.x, 112.0)
	add_child(fade)
	var under := ColorRect.new()
	under.color = Color(0.02, 0.04, 0.14, 1.0)
	under.position = Vector2(0, 849.0 * k - 40.0)
	under.size = Vector2(CANVAS.x, CANVAS.y - (849.0 * k - 40.0))
	under.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(under)
	_band = Control.new()
	_band.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_band.size = CANVAS
	_band.pivot_offset = CANVAS / 2.0
	add_child(_band)
	var rect := Rect2(panel_rect.position * k, panel_rect.size * k)
	NetsuUI.frame_panel(_band, rect)
	NetsuUI.page_title(_band, "PAUSE MENU", 197.0, 44)
	var x0 := row_x.x * k
	var x1 := row_x.y * k
	_band.add_child(NetsuUI.hairline(Vector2(x0, 241 * k), x1 - x0, Color(0.55, 0.75, 1.0, 0.5), 1.0, "both"))
	_bar = Node2D.new()
	var bar := NetsuUI.row_bar(Vector2(x1 - x0, 52 * k))
	_bar.add_child(bar)
	var tab := NetsuUI.poly(PackedVector2Array([Vector2(-4, 0), Vector2(10, 0), Vector2(20, 26 * k), Vector2(10, 52 * k),
		Vector2(-4, 52 * k), Vector2(6, 26 * k)]), Color(0.4, 0.78, 1.0))
	_bar.add_child(tab)
	_band.add_child(_bar)
	for i in _items.size():
		var y := _row_y(i)
		if i == _divider:
			NetsuUI.divider(_band, x0, x1, y - row_step * 0.75 * k)
		var sep := ColorRect.new()
		sep.color = Color(0.55, 0.7, 1.0, 0.14)
		sep.position = Vector2(x0, y + 26 * k)
		sep.size = Vector2(x1 - x0, 1)
		sep.mouse_filter = Control.MOUSE_FILTER_IGNORE
		_band.add_child(sep)
		var icon := NetsuIcon.new()
		icon.kind = _items[i]["icon"]
		icon.box = 30.0
		icon.position = Vector2(icon_x * k - 22, y - 22)
		icon.size = Vector2(44, 44)
		_band.add_child(icon)
		_icons.append(icon)
		var l := NetsuUI.label(_items[i]["label"], row_font_size, Color(0.9, 0.92, 1.0), NetsuUI.sans(1))
		l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		l.position = Vector2(label_x * k, y - 30)
		l.size = Vector2(700, 60)
		l.pivot_offset = Vector2(0, 30)
		_band.add_child(l)
		_labels.append(l)
	_marks = Node2D.new()
	_marks.add_child(NetsuUI.chevron(Vector2(43 * k, 26 * k), 22, Color.WHITE, 3.0))
	_band.add_child(_marks)
	_footer = NetsuUI.footer(self, false, 849.0, 87.0, 885.0, 1600.0, 889.0, true)


func _audio(index: int) -> void:
	var audio := get_node_or_null("/root/AudioManager")
	if audio and audio.has_method("PlayMenuClip"):
		audio.call("PlayMenuClip", index)
