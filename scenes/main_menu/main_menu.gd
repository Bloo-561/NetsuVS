extends Control
## MAIN MENU  (Oct 19 2026 mockup)
##   Up / Down  move      A  pick      B  back to the title
##
## TO ADD AN ENTRY: add a line to ITEMS ("line" is what the character in the
## speech box says), then handle its id in _confirm().
## The character on the right is the first fighter in data/roster.tres
## (change `guide_fighter` to show someone else).
##
## OPTIONS opens INSIDE this screen: Cecilia and her speech box slide off to the
## right and the settings list (scenes/options/options_menu.gd) grows out of the
## OPTIONS row. Backing out of it brings her back.
##
## Layout numbers are mockup pixels (1672 x 941), converted with NetsuUI.m().
## Background: assets/ui/netsu/menu_bg.png.

const OPTIONS_SCENE := "res://scenes/options/options_menu.tscn"
const SIDE_SELECT := "res://scenes/versus/device_select.gd"

const ITEMS := [
	{"id": "versus", "label": "VERSUS", "blurb": "Fight a friend or the CPU. Set the rules, pick sides, then fighters.",
		"line": "Looking for a sparring partner?\nPick your fighter - I'll be waiting!"},
	{"id": "training", "label": "TRAINING", "blurb": "Practice combos, frame data and timing against a dummy.",
		"line": "The practice hall is open.\nWant to run some drills with me?"},
	{"id": "arcade", "label": "ARCADE", "blurb": "Battle through a gauntlet of rivals. (Coming soon)",
		"line": "One opponent after another...\nSounds like a good test of steel."},
	{"id": "network", "label": "ONLINE", "blurb": "Rollback netplay with a friend: create a lobby and send them the code.",
		"line": "Challengers from far away?\nBring it on!"},
	{"id": "gallery", "label": "GALLERY", "blurb": "Art, music and memories from the campaign. (Coming soon)",
		"line": "Memories from our journey...\nLet's look through them sometime."},
	{"id": "commands", "label": "COMMAND LIST", "blurb": "Every system, fighter and assist move, with live previews and frame data.",
		"line": "Want to go over the moves together?\nTake all the time you need."},
	{"id": "options", "label": "OPTIONS", "blurb": "Controls, sound, display and match settings.",
		"line": "Adjust the controls and sound\nhowever you like."},
	{"id": "return", "label": "RETURN", "blurb": "Back to the title screen.",
		"line": "Heading back already?\nI'll be right here."},
]
const PROMPTS := "UP / DOWN  SELECT     A  CONFIRM     B  BACK"

@export var guide_fighter: int = 0
@export_group("Layout (mockup pixels)")
## Centre of the first row and the distance between rows.
@export var first_row_y: float = 341.0
@export var row_step: float = 54.5
@export var item_x: float = 155.0
@export var diamond_x: float = 123.3
@export var item_font_size: int = 34
## Where the guide render's top-left corner goes, how big (x render pixels) and its tilt.
@export var guide_position: Vector2 = Vector2(751.2, -45.2)
@export var guide_scale: float = 1.0765
@export var guide_tilt: float = 5.45
@export var logo_position: Vector2 = Vector2(73.6, 100.9)
@export var logo_width: float = 615.5
## How far (screen px) Cecilia slides right (off screen) while Options is open.
@export var options_slide: float = 900.0

var _items: Array[Label] = []
var _diamonds: Array[Node2D] = []
var _bar: Node2D
var _guide: TextureRect
var _logo: TextureRect
var _bubble: Control
var _bubble_text: Label
var _footer: Dictionary
var _selected := 0
var _text_tween: Tween
var _guide_home := Vector2.ZERO
var _bubble_home := Vector2.ZERO
var _options: Control = null   # the open panel (Options, Versus settings or side select), if any


func _ready() -> void:
	_play_theme()
	# back at the menu: everyone's controls go back to normal
	Controls.clear_sides()
	MatchSetup.humans = []
	NetsuUI.picture(self, NetsuUI.MENU_BG)
	# deeper night-blue behind the logo and the list
	var shade := NetsuUI.gradient_rect(Color(0.02, 0.04, 0.16, 0.62), Color(0.02, 0.04, 0.16, 0.0), false)
	shade.size = Vector2(1150, 1080)
	add_child(shade)
	var lights := NetsuLights.new()
	lights.beams = NetsuLights.preset("menu")
	add_child(lights)
	_build_guide()
	_build_logo()
	_build_list()
	_build_bubble()
	_footer = NetsuUI.footer(self, true)
	_footer["prompts"].text = PROMPTS
	_select(0, false)
	_entrance()


func _unhandled_input(event: InputEvent) -> void:
	if SceneRouter.is_busy() or _options != null:
		return
	if event.is_action_pressed("ui_down", true):
		_select(_selected + 1)
	elif event.is_action_pressed("ui_up", true):
		_select(_selected - 1)
	elif event.is_action_pressed("ui_accept"):
		_confirm()
	elif event.is_action_pressed("ui_cancel"):
		SceneRouter.go_to(SceneRouter.TITLE)
	else:
		return
	get_viewport().set_input_as_handled()


func _confirm() -> void:
	var picked := _items[_selected]
	var punch := create_tween()
	punch.tween_property(picked, "scale", Vector2(1.06, 1.06), 0.06)
	punch.tween_property(picked, "scale", Vector2.ONE, 0.1)
	match ITEMS[_selected]["id"]:
		"versus":
			_open_options("versus")
		"training":
			_open_character_select("Training")
		"network":
			MatchSetup.mode_name = "Online"
			_fade_out_theme()
			SceneRouter.go_to(SceneRouter.ONLINE_LOBBY)
		"options":
			_open_options()
		"commands":
			_open_command_list()
		"return":
			SceneRouter.go_to(SceneRouter.TITLE)
		_:
			_footer["text"].text = "Coming soon!"


## Nov 2 2026: the command list (game/ui/command_list/netsu_command_list.gd) over the whole menu.
func _open_command_list() -> void:
	var cl := NetsuCommandList.new()
	cl.footer_override = _footer
	cl.start_tab = "system"
	cl.start_fighter = guide_fighter
	cl.closed.connect(_on_command_list_closed)
	add_child(cl)
	move_child(cl, _footer["root"].get_index())   # under the footer
	_options = cl
	cl.modulate.a = 0.0
	create_tween().tween_property(cl, "modulate:a", 1.0, 0.2)


func _on_command_list_closed() -> void:
	var cl := _options
	var t := create_tween()
	t.tween_property(cl, "modulate:a", 0.0, 0.16)
	t.tween_callback(cl.queue_free)
	_on_options_closed()


## Picks the engine game mode (data/game_modes/) and opens the character select.
func _open_character_select(mode: String) -> void:
	MatchSetup.mode_name = mode
	_fade_out_theme()
	SceneRouter.go_to(SceneRouter.CHARACTER_SELECT)


# --- Music ------------------------------------------------------------------------------------
## Nov 2: the main menu theme, "Reflect" by Manbou Nitouhei (OpenTracks #5657). Trimmed to the composer's loop end
## (2:50.823); plays from the start, then loops back to theme_loop_start. It keeps playing under everything opened
## from this menu (Options, Command List, Versus settings, side select) and fades out with the screen when you head into
## a mode (Training, Versus -> character select, Online): silent by the time the loading emblem shows. RETURN goes back
## to the title, which plays its own theme.
const THEME_PATH := "res://assets/audio/music/netsu/reflect.ogg"
@export var theme_loop_start: float = 24.0


## Starts the menu theme on the BGM bus (Options > Sound > BGM volume). Carries on if it's already playing.
func _play_theme() -> void:
	var audio := get_node_or_null("/root/AudioManager")
	if audio == null:
		return
	var theme = load(THEME_PATH) if ResourceLoader.exists(THEME_PATH) else null
	if theme == null:
		audio.call("StopBGM")
		return
	if "loop" in theme:
		theme.loop = true
	if "loop_offset" in theme:
		theme.loop_offset = theme_loop_start
	var player = audio.get("BGM")
	if player is AudioStreamPlayer and player.playing and player.stream == theme:
		return
	audio.call("PlayBGM", theme)


## Fades the theme out while the screen fades to black (SceneRouter.black_in), then stops it.
func _fade_out_theme() -> void:
	var audio := get_node_or_null("/root/AudioManager")
	if audio == null:
		return
	var player = audio.get("BGM")
	if not (player is AudioStreamPlayer) or not player.playing:
		return
	var level: float = player.volume_db
	var t := create_tween()
	t.tween_property(player, "volume_db", level - 40.0, maxf(0.05, float(SceneRouter.black_in))).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN)
	t.tween_callback(_stop_theme.bind(player, level))


func _stop_theme(player: AudioStreamPlayer, level: float) -> void:
	var audio := get_node_or_null("/root/AudioManager")
	if audio:
		audio.call("StopBGM")
	player.volume_db = level


# --- Building ---------------------------------------------------------------------

func _row_y(i: int) -> float:
	return (first_row_y + row_step * i) * NetsuUI.K


func _build_guide() -> void:
	_guide = TextureRect.new()
	_guide.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_guide.stretch_mode = TextureRect.STRETCH_SCALE
	_guide.mouse_filter = Control.MOUSE_FILTER_IGNORE
	if MatchSetup.fighter_count() > guide_fighter:
		var tex: Texture2D = MatchSetup.fighter_profile(guide_fighter).Render
		if tex:
			_guide.texture = tex
			# the mockup render is 1024 px wide; other renders keep the same on-screen width
			_guide.size = tex.get_size() * guide_scale * NetsuUI.K * (1024.0 / tex.get_size().x)
	_guide.position = NetsuUI.m(guide_position.x, guide_position.y)
	_guide.rotation_degrees = guide_tilt
	add_child(_guide)


func _build_logo() -> void:
	_logo = TextureRect.new()
	if ResourceLoader.exists(NetsuUI.LOGO):
		_logo.texture = load(NetsuUI.LOGO)
	_logo.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_logo.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	_logo.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var w := logo_width * NetsuUI.K
	var h := w * (633.0 / 1972.0)
	if _logo.texture:
		h = w * _logo.texture.get_size().y / _logo.texture.get_size().x
	_logo.position = NetsuUI.m(logo_position.x, logo_position.y)
	_logo.size = Vector2(w, h)
	_logo.pivot_offset = _logo.size / 2.0
	add_child(_logo)


func _build_list() -> void:
	var k := NetsuUI.K
	# separators under every row
	for i in ITEMS.size():
		var sep := NetsuUI.hairline(Vector2(96 * k, _row_y(i) + 27 * k), 264 * k, Color(NetsuUI.LINE, 0.28), 1.0, "right")
		add_child(sep)
	# the highlight bar (slanted, glowing edges, light trailing off to the left)
	_bar = Node2D.new()
	var h := 56.0 * k
	var w := 419.3 * k
	var skew := 31.0 * k
	var shape := NetsuUI.para(w, h, skew)
	var fill := Polygon2D.new()
	fill.polygon = shape
	fill.vertex_colors = PackedColorArray([Color(0.06, 0.36, 0.95, 0.92), Color(0.14, 0.42, 0.95, 0.55),
		Color(0.1, 0.36, 0.9, 0.55), Color(0.03, 0.3, 0.9, 0.92)])
	_bar.add_child(fill)
	var shine := Polygon2D.new()   # lighter upper half
	shine.polygon = PackedVector2Array([shape[0], shape[1], shape[1].lerp(shape[2], 0.5), shape[0].lerp(shape[3], 0.5)])
	shine.color = Color(0.5, 0.75, 1.0, 0.1)
	_bar.add_child(shine)
	_bar.add_child(NetsuUI.outline(shape, Color(0.45, 0.8, 1.0, 0.3), 7.0))
	_bar.add_child(NetsuUI.outline(shape, Color(0.85, 0.95, 1.0, 0.95), 2.0))
	for y in [0.0, h]:   # light along the top / bottom edges running off to the left
		var trail := NetsuUI.hairline(Vector2(-60.7 * k, y), 70.0 * k + (skew if y == 0.0 else 0.0),
			Color(0.45, 0.8, 1.0, 0.9), 2.0, "left")
		_bar.add_child(trail)
	add_child(_bar)
	for i in ITEMS.size():
		var d := NetsuUI.diamond(10.5 * k, Color(0.62, 0.64, 0.78, 0.9), Color(0.16, 0.18, 0.32, 0.9))
		d.position = Vector2(diamond_x * k, _row_y(i))
		add_child(d)
		_diamonds.append(d)
		var l := NetsuUI.label(ITEMS[i]["label"], item_font_size, NetsuUI.DIM, NetsuUI.serif(600, 1))
		l.position = Vector2(item_x * k, _row_y(i) - 30)
		l.size = Vector2(500, 60)
		l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		l.pivot_offset = Vector2(0, 30)
		add_child(l)
		_items.append(l)


func _build_bubble() -> void:
	var k := NetsuUI.K
	_bubble = Control.new()
	_bubble.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_bubble)
	_bubble_home = _bubble.position
	var top := 626.0 * k
	var h := 124.0 * k
	var skew := 62.0 * k
	# accent strip on the left edge
	var strip := PackedVector2Array([Vector2(752 * k, top), Vector2(774 * k, top), Vector2(774 * k - skew, top + h),
		Vector2(752 * k - skew, top + h)])
	_bubble.add_child(NetsuUI.poly(strip, Color(0.78, 0.76, 1.0, 0.28)))
	var main := PackedVector2Array([Vector2(774 * k, top), Vector2(1480 * k, top), Vector2(1480 * k - skew, top + h),
		Vector2(774 * k - skew, top + h)])
	var fill := Polygon2D.new()
	fill.polygon = main
	fill.vertex_colors = PackedColorArray([Color(0.12, 0.13, 0.36, 0.88), Color(0.12, 0.12, 0.34, 0.8),
		Color(0.07, 0.08, 0.24, 0.84), Color(0.06, 0.07, 0.22, 0.92)])
	_bubble.add_child(fill)
	_bubble.add_child(NetsuUI.outline(main, Color(0.86, 0.86, 1.0, 0.8), 1.5))
	var outer := Line2D.new()
	outer.points = PackedVector2Array([Vector2(752 * k, top), Vector2(752 * k - skew, top + h)])
	outer.width = 1.5
	outer.default_color = Color(0.86, 0.86, 1.0, 0.85)
	_bubble.add_child(outer)
	_bubble_text = NetsuUI.label("", 32, NetsuUI.TEXT, NetsuUI.serif(500))
	_bubble_text.add_theme_constant_override("line_spacing", 7)
	_bubble_text.position = Vector2(805 * k, 642 * k)
	_bubble_text.size = Vector2(620 * k, 84 * k)
	_bubble_text.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_bubble.add_child(_bubble_text)


func _select(index: int, animate: bool = true) -> void:
	_selected = wrapi(index, 0, ITEMS.size())
	var k := NetsuUI.K
	for i in _items.size():
		var on := i == _selected
		_items[i].add_theme_color_override("font_color", NetsuUI.TEXT if on else NetsuUI.DIM)
		_set_diamond(i, on)
	var target := Vector2(60.7 * k, _row_y(_selected) - 28.0 * k)
	if animate:
		create_tween().tween_property(_bar, "position", target, 0.12).set_trans(Tween.TRANS_CUBIC)
	else:
		_bar.position = target
	_footer["text"].text = ITEMS[_selected]["blurb"]
	_bubble_text.text = ITEMS[_selected]["line"]
	if _text_tween:
		_text_tween.kill()
	_bubble_text.visible_ratio = 0.0
	_text_tween = create_tween()
	_text_tween.tween_property(_bubble_text, "visible_ratio", 1.0, 0.5)


## Selected row: white diamond with a cyan heart. Others: grey.
func _set_diamond(i: int, on: bool) -> void:
	var old := _diamonds[i]
	var k := NetsuUI.K
	var d: Node2D
	if on:
		d = NetsuUI.diamond(10.5 * k, Color.WHITE, Color(0.05, 0.2, 0.6, 0.9), NetsuUI.CYAN)
	else:
		d = NetsuUI.diamond(10.5 * k, Color(0.62, 0.64, 0.78, 0.9), Color(0.16, 0.18, 0.32, 0.9), Color(0.4, 0.42, 0.55, 0.9))
	d.position = old.position
	d.modulate = old.modulate
	add_child(d)
	move_child(d, old.get_index())
	old.queue_free()
	_diamonds[i] = d


# --- Options (opens inside this screen) --------------------------------------------

## page "" = the whole Options screen, "versus" = Versus Game Settings.
func _open_options(page: String = "") -> void:
	_add_options_panel(page)
	_step_aside()


func _add_options_panel(page: String) -> void:
	_options = load(OPTIONS_SCENE).instantiate()
	_options.set("embedded", true)
	_options.set("start_page", page)
	_options.set("footer_override", _footer)
	add_child(_options)
	move_child(_options, _footer["root"].get_index())   # under the footer
	_options.connect("closed", _on_options_closed)
	if page == "versus":
		_options.connect("start_game", _open_side_select)


## Versus: "Start Game" on the settings sheet -> the side select.
func _open_side_select() -> void:
	var settings := _options
	settings.disconnect("closed", _on_options_closed)
	create_tween().tween_property(settings, "modulate:a", 0.0, 0.15).finished.connect(settings.queue_free)
	_options = load(SIDE_SELECT).new()
	_options.set("footer_override", _footer)
	add_child(_options)
	move_child(_options, _footer["root"].get_index())
	_options.connect("confirmed", _on_sides_confirmed)
	_options.connect("cancelled", _on_sides_cancelled)


func _on_sides_cancelled() -> void:
	_add_options_panel("versus")   # back to the Versus settings


func _on_sides_confirmed(p1_device: String, p2_device: String) -> void:
	Controls.assign_sides(p1_device, p2_device)
	MatchSetup.humans = [p1_device != "", p2_device != ""]
	_open_character_select("Versus")


## Cecilia steps out to the right, her speech box drifts away, the list dims.
func _step_aside() -> void:
	var t := create_tween().set_parallel(true).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_IN_OUT)
	t.tween_property(_guide, "position:x", _guide_home.x + options_slide, 0.5)
	t.tween_property(_guide, "modulate:a", 0.0, 0.45)
	t.tween_property(_bubble, "position:x", _bubble_home.x + 240.0, 0.3)
	t.tween_property(_bubble, "modulate:a", 0.0, 0.22)
	# the rest of the main menu fades back; the picked row stays lit
	for i in _items.size():
		if i != _selected:
			t.tween_property(_items[i], "modulate:a", 0.45, 0.25)
			t.tween_property(_diamonds[i], "modulate:a", 0.45, 0.25)


func _on_options_closed() -> void:
	_options = null
	var t := create_tween().set_parallel(true).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	t.tween_property(_guide, "position:x", _guide_home.x, 0.5).set_delay(0.08)
	t.tween_property(_guide, "modulate:a", 1.0, 0.4).set_delay(0.08)
	t.tween_property(_bubble, "position:x", _bubble_home.x, 0.35).set_delay(0.25)
	t.tween_property(_bubble, "modulate:a", 1.0, 0.3).set_delay(0.25)
	for i in _items.size():
		t.tween_property(_items[i], "modulate:a", 1.0, 0.25)
		t.tween_property(_diamonds[i], "modulate:a", 1.0, 0.25)
	_footer["prompts"].text = PROMPTS
	_select(_selected, false)   # puts back the blurb and replays her line


func _entrance() -> void:
	var home := _guide.position
	_guide_home = home
	_guide.position = home + Vector2(160, 0)
	_guide.modulate.a = 0.0
	_logo.modulate.a = 0.0
	_logo.scale = Vector2(1.04, 1.04)
	var t := create_tween().set_parallel(true).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	t.tween_property(_guide, "position", home, 0.5)
	t.tween_property(_guide, "modulate:a", 1.0, 0.4)
	t.tween_property(_logo, "modulate:a", 1.0, 0.5)
	t.tween_property(_logo, "scale", Vector2.ONE, 0.7)
	for i in _items.size():
		_items[i].modulate.a = 0.0
		t.tween_property(_items[i], "modulate:a", 1.0, 0.2).set_delay(0.05 + i * 0.04)
