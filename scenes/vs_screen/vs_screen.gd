extends Control
## NETSU VS SCREEN  (Oct 24 2026) - between the stage select and the fight, Melty Blood style.
##
##   [player 1's render]        ╲   ╱        [player 2's render]
##          constellation         VS          constellation
##   ──────────── Cecilia ──────  ◆  ────── Leticia ────────────   <- names on a hairline
##                PLAYER 1                  PLAYER 2 / CPU
##                Cecilia Richter           Leticia
##                ◇ ASSIST  Mary            ◇ ASSIST  Eren
##                              [stage]
##   ♪ song - artist                                      NOW LOADING / (A) SKIP
##
## While it plays, the fight loads on other threads (MatchSetup.preload_match): the battle scene,
## the stage and both fighters. When that's done and the jingle has played (min_time), the screen
## fades to black and the fight fades in (MatchSetup.enter_battle). A / Start skips once it's loaded.
##
## Opened by MatchSetup.start_match() for the modes in MatchSetup.VS_SCREEN_MODES (Training too since Oct 24).
## Everything it shows comes from MatchSetup.versus_info(): names and renders from each fighter's
## Profile, the assist each side picked, the stage's Thumbnail and the battle song.
## Sizes, colours and timings are @exports (click the root of vs_screen.tscn). Docs: docs/vs_screen.md

@export_group("Timing (seconds)")
## Shortest time on screen. The jingle's last hit is at 4.9 s, so the fade to black ends right on it.
@export var min_time: float = 4.55
## A / Start skips to the fight after this (and once the fight is loaded).
@export var skip_after: float = 0.9
## When the VS letters land (the jingle's first big drum hit).
@export var vs_impact_at: float = 0.42
@export var fade_out_time: float = 0.35
@export var fade_in_time: float = 0.5

@export_group("Music")
## Played once when the screen opens (on the BGM bus, through the AudioManager). Empty = silence.
@export_file("*.wav", "*.ogg", "*.mp3") var music_path: String = "res://assets/audio/music/mahou/04 Versus Screen [No Loop].wav"
## Sound when the VS lands, and when A skips.
@export_file("*.wav", "*.ogg") var impact_sound: String = "res://assets/audio/menu/mahou/StrongConfirmSoundVers4.wav"

@export_group("Colours")
@export var p1_accent: Color = Color(0.25, 0.6, 1.0)      ## Player 1 blue
@export var p2_accent: Color = Color(1.0, 0.22, 0.36)     ## Player 2 crimson
## How dark the stage behind everything gets (0 = as it is, 1 = night-blue).
@export_range(0.0, 1.0) var stage_dim: float = 0.52
@export_range(0.0, 10.0) var stage_blur: float = 2.5

@export_group("Layout (1920x1080)")
## Centre of the VS letters; the names' hairline runs through it.
@export var vs_center: Vector2 = Vector2(960, 676)
@export var vs_size: int = 200
## On-screen height of a full-body render (the legs run off the bottom, so it's a half-body shot).
@export var render_height: float = 1720.0
## Where each render's middle sits across the screen (player 1, player 2).
@export var render_center_x: Vector2 = Vector2(500, 1420)
@export var render_top: float = -36.0
## Oct 26 (TamaDeez): per-render framing, by the render's file name (no extension): x = zoom (1 = render_height),
## y = nudge across (px, toward the middle is +), z = nudge up (px, negative = higher). Renders drawn with a
## smaller head (Noah) are zoomed in so every fighter looks about the same size.
@export var render_framing: Dictionary = {"Noah_Select_FullBody": Vector3(1.4, 0.0, -45.0)}
## Gap between the VS and the inner end of each name.
@export var name_gap: float = 150.0
@export var name_size: int = 108
@export var stage_card_size: Vector2 = Vector2(272, 153)
@export var stage_card_top: float = 806.0

const CANVAS := Vector2(1920, 1080)
const BACKDROP_SHADER := preload("res://scenes/vs_screen/vs_backdrop.gdshader")
const RENDER_SHADER := preload("res://scenes/vs_screen/vs_render.gdshader")
const METAL_SHADER := preload("res://scenes/vs_screen/vs_metal.gdshader")

var _info: Dictionary = {}
var _t := 0.0
var _progress := 0.0
var _loaded := false
var _leaving := false
var _skip := false
var _shake := 0.0

var _world: Control          # everything that shakes when the VS lands
var _stage_pic: TextureRect
var _renders: Array[TextureRect] = []
var _render_home: Array[Vector2] = []
var _render_slide: Array[float] = [0.0, 0.0]   # entrance offset (tweened), added to the drift
var _fx: VsFx
var _load_bar: VsLoadBar
var _vs_root: Control
var _vs_fill: Label
var _flash: ColorRect
var _footer: Dictionary
var _sfx: AudioStreamPlayer
var _music_player: AudioStreamPlayer
var _music_stream: AudioStream
var _music_volume := 0.0


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	NetsuUI.full_rect(self)
	_info = MatchSetup.versus_info()
	_sfx = AudioStreamPlayer.new()
	_sfx.bus = &"SFX"
	add_child(_sfx)
	var base := ColorRect.new()
	base.color = Color(0.02, 0.03, 0.1)
	base.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(base)
	NetsuUI.full_rect(base)
	_world = Control.new()
	_world.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_world.size = CANVAS
	add_child(_world)
	_build_backdrop()
	_build_renders()
	_fx = VsFx.new()
	_fx.p1 = p1_accent
	_fx.p2 = p2_accent
	_fx.center = vs_center
	_fx.impact_at = vs_impact_at
	_world.add_child(_fx)
	_build_names()
	_build_vs()
	_build_stage_card()
	_build_header()
	_footer = NetsuUI.footer(self)
	_footer["text"].text = _song_text()
	_footer["prompts"].text = "NOW LOADING"
	_load_bar = VsLoadBar.new()
	add_child(_load_bar)
	_flash = ColorRect.new()
	_flash.color = Color(1, 1, 1, 0)
	_flash.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_flash)
	NetsuUI.full_rect(_flash)
	_play_music()
	MatchSetup.preload_match()
	_animate()


func _process(delta: float) -> void:
	_t += delta
	_fx.time = _t
	_load_bar.time = _t
	if not _loaded:
		_progress = MatchSetup.preload_progress()
		_load_bar.progress = _progress
		if _progress >= 1.0:
			_loaded = true
			_load_bar.loaded_at = _t
			_footer["prompts"].text = "A  SKIP"
		else:
			var dots := int(_t * 3.0) % 4
			_footer["prompts"].text = "NOW LOADING" + " .".repeat(dots)
	# slow drift: the renders creep toward the middle after sweeping in
	for side in 2:
		var dir := 1.0 if side == 0 else -1.0
		var drift := 26.0 * (1.0 - exp(-maxf(_t - 0.5, 0.0) * 0.35))
		_renders[side].position.x = _render_home[side].x + dir * drift + _render_slide[side]
	if _shake > 0.0:
		_shake = maxf(_shake - delta * 2.2, 0.0)
		var amp := 14.0 * _shake * _shake
		_world.position = Vector2(randf_range(-amp, amp), randf_range(-amp, amp))
	elif _world.position != Vector2.ZERO:
		_world.position = Vector2.ZERO
	if not _leaving and _loaded and (_t >= min_time or _skip):
		_leave()


func _unhandled_input(event: InputEvent) -> void:
	if _leaving or _t < skip_after:
		return
	var accept := event.is_action_pressed("ui_accept") or event.is_action_pressed("p1_a") \
		or event.is_action_pressed("p2_a") or event.is_action_pressed("p1_start") or event.is_action_pressed("p2_start")
	if not accept:
		return
	get_viewport().set_input_as_handled()
	if not _skip:   # still loading: goes the moment it's ready
		_skip = true
		_play_sfx(impact_sound, -4.0)


func _exit_tree() -> void:
	# the jingle's tail stops with the screen (the fight starts its own song); the BGM player gets
	# its volume back in case A faded the jingle out
	if _music_player and is_instance_valid(_music_player):
		if _music_player.stream == _music_stream:
			var audio := get_node_or_null("/root/AudioManager")
			if audio:
				audio.call("StopBGM")
		_music_player.volume_db = _music_volume


# --- Leaving ---------------------------------------------------------------------

func _leave() -> void:
	_leaving = true
	_footer["prompts"].text = ""
	var t := create_tween().set_parallel(true)
	# push in a little while it goes dark
	_world.pivot_offset = vs_center
	t.tween_property(_world, "scale", Vector2.ONE * 1.045, fade_out_time + 0.25).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_IN)
	t.tween_property(_vs_root, "modulate", Color(1.6, 1.6, 1.8), fade_out_time)
	if _skip and _music_player:
		t.tween_property(_music_player, "volume_db", _music_volume - 24.0, fade_out_time)
	MatchSetup.enter_battle(fade_out_time, fade_in_time)


# --- Building --------------------------------------------------------------------

func _build_backdrop() -> void:
	_stage_pic = TextureRect.new()
	_stage_pic.texture = _info.get("stage_thumb")
	_stage_pic.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_stage_pic.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	_stage_pic.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_stage_pic.position = Vector2(-40, -40)
	_stage_pic.size = CANVAS + Vector2(80, 80)
	_stage_pic.pivot_offset = _stage_pic.size / 2.0
	var mat := ShaderMaterial.new()
	mat.shader = BACKDROP_SHADER
	mat.set_shader_parameter("blur", stage_blur)
	mat.set_shader_parameter("darken", stage_dim)
	_stage_pic.material = mat
	_world.add_child(_stage_pic)
	# blue light from the left, crimson from the right (added on top of the stage)
	var add := CanvasItemMaterial.new()
	add.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	for side in 2:
		var c: Color = (p1_accent if side == 0 else p2_accent).darkened(0.35)
		var grad := Gradient.new()
		grad.offsets = PackedFloat32Array([0.0, 0.45, 1.0])
		grad.colors = PackedColorArray([Color(c, 0.42), Color(c, 0.12), Color(c, 0.0)])
		var tex := GradientTexture2D.new()
		tex.gradient = grad
		tex.fill_from = Vector2(0.0 if side == 0 else 1.0, 0.5)
		tex.fill_to = Vector2(1.0 if side == 0 else 0.0, 0.5)
		var wash := TextureRect.new()
		wash.texture = tex
		wash.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		wash.mouse_filter = Control.MOUSE_FILTER_IGNORE
		wash.material = add
		wash.size = Vector2((CANVAS.x + 80) * 0.55, CANVAS.y + 80)
		wash.position = Vector2(-40.0 if side == 0 else CANVAS.x + 40 - wash.size.x, -40)
		_world.add_child(wash)
	var lights := NetsuLights.new()
	lights.beams = [[150.0, 70.0, 0.1, p1_accent], [250.0, 3.0, 0.32, NetsuUI.CYAN], [600.0, 150.0, 0.07, p1_accent],
		[1150.0, 150.0, 0.07, p2_accent], [1540.0, 3.0, 0.4, NetsuUI.PINK], [1760.0, 110.0, 0.1, p2_accent]]
	_world.add_child(lights)
	# darker along the top so the header reads (the footer has its own band)
	var top := NetsuUI.gradient_rect(Color(0.01, 0.02, 0.08, 0.7), Color(0.01, 0.02, 0.08, 0.0), true)
	top.position = Vector2(-40, -40)
	top.size = Vector2(CANVAS.x + 80, 260)
	_world.add_child(top)


func _build_renders() -> void:
	for side in 2:
		var s: Dictionary = _side(side)
		var tex: Texture2D = s.get("render")
		var r := TextureRect.new()
		r.texture = tex
		r.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		r.stretch_mode = TextureRect.STRETCH_SCALE
		r.flip_h = false   # renders are never mirrored (it would swap sword hands, logos...)
		r.mouse_filter = Control.MOUSE_FILTER_IGNORE
		var ratio := 0.7
		if tex:
			ratio = tex.get_size().x / maxf(tex.get_size().y, 1.0)
		var frame := Vector3(1.0, 0.0, 0.0)
		if tex and render_framing.has(tex.resource_path.get_file().get_basename()):
			frame = render_framing[tex.resource_path.get_file().get_basename()]
		r.size = Vector2(render_height * ratio, render_height) * frame.x
		var cx: float = render_center_x[side] + (frame.y if side == 0 else -frame.y)
		r.position = Vector2(cx - r.size.x / 2.0, render_top + frame.z)
		r.pivot_offset = Vector2(r.size.x / 2.0, 260)
		var mat := ShaderMaterial.new()
		mat.shader = RENDER_SHADER
		mat.set_shader_parameter("side", float(side))
		mat.set_shader_parameter("seam_x", vs_center.x / CANVAS.x)
		mat.set_shader_parameter("rim_color", (p1_accent if side == 0 else p2_accent).lightened(0.2))
		mat.set_shader_parameter("flash", 1.0)
		r.material = mat
		_world.add_child(r)
		_renders.append(r)
		_render_home.append(r.position)


func _build_names() -> void:
	var y := vs_center.y
	# soft dark band so the names read over the renders
	var band := TextureRect.new()
	var g := Gradient.new()
	g.offsets = PackedFloat32Array([0.0, 0.55, 1.0])
	g.colors = PackedColorArray([Color(0.01, 0.02, 0.09, 0.78), Color(0.01, 0.02, 0.09, 0.45), Color(0.01, 0.02, 0.09, 0.0)])
	var tex := GradientTexture2D.new()
	tex.gradient = g
	tex.fill = GradientTexture2D.FILL_RADIAL
	tex.fill_from = Vector2(0.5, 0.5)
	tex.fill_to = Vector2(1.0, 0.5)
	band.texture = tex
	band.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	band.mouse_filter = Control.MOUSE_FILTER_IGNORE
	band.position = Vector2(-60, y - 190)
	band.size = Vector2(CANVAS.x + 120, 400)
	band.name = "NameBand"
	_world.add_child(band)
	# the hairline across the screen (blue half, crimson half)
	var line := Control.new()
	line.name = "Hairline"
	line.mouse_filter = Control.MOUSE_FILTER_IGNORE
	line.position = Vector2(0, y)
	line.pivot_offset = Vector2(vs_center.x, 0)
	line.add_child(NetsuUI.hairline(Vector2(0, 0), vs_center.x, Color(p1_accent.lightened(0.45), 0.8), 1.5, "left"))
	line.add_child(NetsuUI.hairline(Vector2(vs_center.x, 0), CANVAS.x - vs_center.x, Color(p2_accent.lightened(0.45), 0.8), 1.5, "right"))
	for x in [150.0, CANVAS.x - 150.0]:
		var d := NetsuUI.diamond(6.0, Color(0.85, 0.92, 1.0, 0.9), Color(0.03, 0.05, 0.16))
		d.position = Vector2(x, 0)
		line.add_child(d)
	_world.add_child(line)
	for side in 2:
		_world.add_child(_name_block(side))


## One player's names: big short name above the hairline, PLAYER / CPU, full name and assist under it.
func _name_block(side: int) -> Control:
	var s: Dictionary = _side(side)
	var right := side == 1
	var accent: Color = p1_accent if side == 0 else p2_accent
	var root := Control.new()
	root.name = "Names%d" % (side + 1)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var inner := vs_center.x + (name_gap if right else -name_gap)
	var w := 760.0
	var x0 := inner if right else inner - w
	var align := HORIZONTAL_ALIGNMENT_LEFT if right else HORIZONTAL_ALIGNMENT_RIGHT
	var y := vs_center.y
	var big_font := NetsuUI.serif(600)
	var big_text := str(s.get("name", ""))
	var big_size := _fit_size(big_font, big_text, name_size, w - 40.0)
	var big := NetsuUI.label(big_text, big_size, Color.WHITE, big_font)
	NetsuUI.glow(big, Color(0.02, 0.03, 0.12, 0.85), 10)
	big.horizontal_alignment = align
	big.position = Vector2(x0, y - big_font.get_ascent(big_size) - 2)
	big.size = Vector2(w, big_size * 1.3)
	big.name = "Big"
	root.add_child(big)
	var tag := NetsuUI.label(str(s.get("player", "")), 22, accent.lightened(0.45), NetsuUI.sans(9))
	NetsuUI.glow(tag, Color(accent.darkened(0.6), 0.9), 6)
	tag.horizontal_alignment = align
	tag.position = Vector2(x0 + (-6 if right else 6), y + 12)
	tag.size = Vector2(w, 30)
	tag.name = "Tag"
	root.add_child(tag)
	var full := NetsuUI.label(str(s.get("full_name", "")).to_upper(), 19, NetsuUI.DIM, NetsuUI.sans(4))
	NetsuUI.glow(full, Color(0.02, 0.03, 0.12, 0.8), 5)
	full.horizontal_alignment = align
	full.position = Vector2(x0, y + 44)
	full.size = Vector2(w, 28)
	full.name = "Full"
	root.add_child(full)
	root.add_child(_assist_chip(s, accent, inner, right, y + 84))
	return root


## "[icon] ASSIST  Mary": the assist's icon in a small square like the character select's assist card.
func _assist_chip(s: Dictionary, accent: Color, inner: float, right: bool, y: float) -> Control:
	var chip := Control.new()
	chip.name = "Assist"
	chip.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var box := 46.0
	var head_font := NetsuUI.sans(6)
	var name_font := NetsuUI.serif(600)
	var head := NetsuUI.label("ASSIST", 15, accent.lightened(0.4), head_font)
	NetsuUI.glow(head, Color(0.02, 0.03, 0.12, 0.85), 5)
	var name_l := NetsuUI.label(str(s.get("assist", "")), 27, NetsuUI.TEXT, name_font)
	NetsuUI.glow(name_l, Color(0.02, 0.03, 0.12, 0.85), 6)
	var head_w := head_font.get_string_size("ASSIST", HORIZONTAL_ALIGNMENT_LEFT, -1, 15).x
	var name_w := name_font.get_string_size(name_l.text, HORIZONTAL_ALIGNMENT_LEFT, -1, 27).x
	var total := box + 14.0 + head_w + 12.0 + name_w
	var x := inner if right else inner - total
	var back := ColorRect.new()
	back.color = Color(0.03, 0.05, 0.16, 0.9)
	back.position = Vector2(x, y)
	back.size = Vector2(box, box)
	back.mouse_filter = Control.MOUSE_FILTER_IGNORE
	chip.add_child(back)
	var icon_tex: Texture2D = s.get("assist_icon")
	if icon_tex:
		var icon := TextureRect.new()
		icon.texture = icon_tex
		icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
		icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
		icon.position = Vector2(x, y)
		icon.size = Vector2(box, box)
		chip.add_child(icon)
	var rim := Line2D.new()
	rim.points = PackedVector2Array([Vector2(x, y), Vector2(x + box, y), Vector2(x + box, y + box), Vector2(x, y + box), Vector2(x, y)])
	rim.width = 2.0
	rim.default_color = accent.lightened(0.25)
	chip.add_child(rim)
	# "ASSIST" and the name share a baseline; the name's capitals are centred on the icon
	var base := y + box / 2.0 + 27.0 * 0.66 / 2.0
	head.position = Vector2(x + box + 14.0, base - head_font.get_ascent(15))
	head.size = Vector2(head_w + 4.0, head_font.get_height(15))
	chip.add_child(head)
	name_l.position = Vector2(x + box + 14.0 + head_w + 12.0, base - name_font.get_ascent(27))
	name_l.size = Vector2(name_w + 12.0, name_font.get_height(27))
	chip.add_child(name_l)
	return chip


func _build_vs() -> void:
	_vs_root = Control.new()
	_vs_root.name = "VS"
	_vs_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_vs_root.position = vs_center
	_world.add_child(_vs_root)
	var font := NetsuUI.serif(700, -6)
	var text_size := font.get_string_size("VS", HORIZONTAL_ALIGNMENT_LEFT, -1, vs_size)
	var ascent := font.get_ascent(vs_size)
	var cap := vs_size * 0.64
	# the letters' box, centred on vs_center (cap height centred on the hairline, a little high)
	var box := Vector2(text_size.x + 40, vs_size * 1.4)
	var pos := Vector2(-box.x / 2.0, -(ascent - cap / 2.0) - cap * 0.06)
	var shadow := NetsuUI.label("VS", vs_size, Color(0, 0, 0, 0), font)
	shadow.add_theme_color_override("font_outline_color", Color(0.01, 0.02, 0.1, 0.8))
	shadow.add_theme_constant_override("outline_size", 26)
	shadow.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	shadow.position = pos
	shadow.size = box
	_vs_root.add_child(shadow)
	var edge := NetsuUI.label("VS", vs_size, Color(0, 0, 0, 0), font)
	edge.add_theme_color_override("font_outline_color", Color(0.06, 0.08, 0.26, 1.0))
	edge.add_theme_constant_override("outline_size", 9)
	edge.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	edge.position = pos
	edge.size = box
	_vs_root.add_child(edge)
	_vs_fill = NetsuUI.label("VS", vs_size, Color.WHITE, font)
	_vs_fill.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_vs_fill.position = pos
	_vs_fill.size = box
	var mat := ShaderMaterial.new()
	mat.shader = METAL_SHADER
	mat.set_shader_parameter("top", ascent - cap)
	mat.set_shader_parameter("bottom", ascent)
	_vs_fill.material = mat
	_vs_root.add_child(_vs_fill)
	_vs_root.scale = Vector2.ONE * 2.6
	_vs_root.modulate.a = 0.0


func _build_stage_card() -> void:
	var card := Control.new()
	card.name = "StageCard"
	card.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var size := stage_card_size
	var top_left := Vector2(vs_center.x - size.x / 2.0, stage_card_top)
	card.position = top_left
	var pic := TextureRect.new()
	pic.texture = _info.get("stage_thumb")
	pic.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	pic.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	pic.mouse_filter = Control.MOUSE_FILTER_IGNORE
	pic.size = size
	card.add_child(pic)
	var pts := PackedVector2Array([Vector2.ZERO, Vector2(size.x, 0), size, Vector2(0, size.y)])
	card.add_child(NetsuUI.outline(pts, Color(0.55, 0.78, 1.0, 0.28), 7.0))
	card.add_child(NetsuUI.outline(pts, Color(0.8, 0.9, 1.0, 0.95), 1.5))
	for c in pts:
		var d := NetsuUI.diamond(5.0, Color(0.85, 0.93, 1.0), Color(0.03, 0.05, 0.16))
		d.position = c
		card.add_child(d)
	# "STAGE" tab on top, the name on a dark strip along the bottom
	var strip := NetsuUI.gradient_rect(Color(0.01, 0.02, 0.09, 0.0), Color(0.01, 0.02, 0.09, 0.88), true)
	strip.position = Vector2(0, size.y - 46)
	strip.size = Vector2(size.x, 46)
	card.add_child(strip)
	var stage_font := NetsuUI.serif(600)
	var stage_text := str(_info.get("stage", ""))
	var name_l := NetsuUI.label(stage_text, _fit_size(stage_font, stage_text, 20, size.x - 16.0), NetsuUI.TEXT, stage_font)
	name_l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	name_l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	name_l.clip_text = true
	name_l.position = Vector2(6, size.y - 34)
	name_l.size = Vector2(size.x - 12, 30)
	card.add_child(name_l)
	var tab := NetsuUI.label("STAGE", 14, Color(0.75, 0.88, 1.0), NetsuUI.sans(7))
	tab.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	tab.position = Vector2(0, -26)
	tab.size = Vector2(size.x, 22)
	card.add_child(tab)
	_world.add_child(card)
	card.modulate.a = 0.0


func _build_header() -> void:
	var header := Control.new()
	header.name = "Header"
	header.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(header)
	var mode := str(_info.get("mode", "Versus")).to_upper()
	var title := NetsuUI.label(mode, 30, Color.WHITE, NetsuUI.sans(12))
	NetsuUI.glow(title, Color(0.02, 0.04, 0.16, 0.85), 10)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	title.position = Vector2(0, 34)
	title.size = Vector2(CANVAS.x, 44)
	title.name = "Mode"
	header.add_child(title)
	var w := NetsuUI.sans(12).get_string_size(mode, HORIZONTAL_ALIGNMENT_LEFT, -1, 30).x
	for s: float in [-1.0, 1.0]:
		var star := NetsuUI.sparkle(11.0, Color(0.85, 0.93, 1.0))
		star.position = Vector2(960 + s * (w / 2.0 + 30), 56)
		header.add_child(star)
		var length := 150.0
		var x0 := 960 + s * (w / 2.0 + 52)
		header.add_child(NetsuUI.hairline(Vector2(x0 - (length if s < 0 else 0.0), 56), length,
			Color(p1_accent if s < 0 else p2_accent, 0.85).lightened(0.35), 1.5, "left" if s < 0 else "right"))
	var rules := NetsuUI.label(_rules_text(), 17, NetsuUI.DIM, NetsuUI.sans(5))
	NetsuUI.glow(rules, Color(0.02, 0.04, 0.16, 0.9), 8)
	rules.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	rules.position = Vector2(0, 80)
	rules.size = Vector2(CANVAS.x, 26)
	rules.name = "Rules"
	header.add_child(rules)


# --- Animation ---------------------------------------------------------------------

func _animate() -> void:
	var hit := vs_impact_at
	var t := create_tween().set_parallel(true)
	# stage: settles from a slight zoom
	_stage_pic.scale = Vector2.ONE * 1.1
	t.tween_property(_stage_pic, "scale", Vector2.ONE, 5.5).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	# renders sweep in from the sides as white silhouettes and colour in
	for side in 2:
		var r := _renders[side]
		var dir := -1.0 if side == 0 else 1.0
		_render_slide[side] = dir * 300.0
		r.modulate.a = 0.0
		t.tween_method(func(v: float): _render_slide[side] = v, dir * 300.0, 0.0, 0.55).set_delay(0.04 + side * 0.06) \
			.set_trans(Tween.TRANS_EXPO).set_ease(Tween.EASE_OUT)
		t.tween_property(r, "modulate:a", 1.0, 0.2).set_delay(0.04 + side * 0.06)
		t.tween_method(_set_render_flash.bind(side), 1.0, 0.0, 0.5).set_delay(0.1 + side * 0.06).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	# the VS drops in and lands on the drum hit
	t.tween_property(_vs_root, "scale", Vector2.ONE, 0.15).set_delay(hit - 0.15).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	t.tween_property(_vs_root, "modulate:a", 1.0, 0.08).set_delay(hit - 0.15)
	t.tween_callback(_impact).set_delay(hit)
	# a shine runs across the letters after landing, and again later
	for at in [hit + 0.1, hit + 2.2]:
		t.tween_method(func(v: float): (_vs_fill.material as ShaderMaterial).set_shader_parameter("shine", v), 0.0, 1.0, 0.45).set_delay(at)
	# hairline opens from the middle, names slide in toward it
	var line := _world.get_node("Hairline") as Control
	line.scale = Vector2(0.0, 1.0)
	t.tween_property(line, "scale", Vector2.ONE, 0.45).set_delay(hit).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	var band := _world.get_node("NameBand") as Control
	band.modulate.a = 0.0
	t.tween_property(band, "modulate:a", 1.0, 0.3).set_delay(hit - 0.1)
	for side in 2:
		var block := _world.get_node("Names%d" % (side + 1)) as Control
		var dir := -1.0 if side == 0 else 1.0
		var k := 0
		for part in block.get_children():
			var c := part as CanvasItem
			c.modulate.a = 0.0
			var delay := hit + 0.12 + k * 0.07
			if part is Control:
				var home: Vector2 = part.position
				part.position = home + Vector2(dir * 70.0, 0)
				t.tween_property(part, "position", home, 0.4).set_delay(delay).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
			t.tween_property(c, "modulate:a", 1.0, 0.25).set_delay(delay)
			k += 1
	var card := _world.get_node("StageCard") as Control
	var card_home := card.position
	card.position = card_home + Vector2(0, 24)
	t.tween_property(card, "position", card_home, 0.4).set_delay(hit + 0.45).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	t.tween_property(card, "modulate:a", 1.0, 0.3).set_delay(hit + 0.45)
	var header := get_node("Header") as CanvasItem
	header.modulate.a = 0.0
	t.tween_property(header, "modulate:a", 1.0, 0.4).set_delay(0.2)


func _impact() -> void:
	_shake = 1.0
	_flash.color = Color(1, 1, 1, 0.7)
	var t := create_tween().set_parallel(true)
	t.tween_property(_flash, "color:a", 0.0, 0.32).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	for side in 2:
		t.tween_method(_set_render_flash.bind(side), 0.45, 0.0, 0.3)
	_play_sfx(impact_sound, -6.0)


func _set_render_flash(v: float, side: int) -> void:
	(_renders[side].material as ShaderMaterial).set_shader_parameter("flash", v)


# --- Text and sound ------------------------------------------------------------------

func _side(side: int) -> Dictionary:
	var sides: Array = _info.get("sides", [])
	return sides[side] if side < sides.size() else {}


func _rules_text() -> String:
	if str(_info.get("mode", "")) == "Training":
		return "FREE PRACTICE   ◆   NO TIME LIMIT"
	var rounds := int(_info.get("rounds", 0))
	var time := int(_info.get("time", -1))
	var parts: Array[String] = []
	if rounds > 0:
		parts.append("FIRST TO %d %s" % [rounds, "ROUND" if rounds == 1 else "ROUNDS"])
	parts.append("NO TIME LIMIT" if time < 0 else "%d SECONDS" % time)
	return "   ◆   ".join(parts)


## The biggest font size up to `wanted` (down to 60% of it) at which `text` fits in `width` px.
func _fit_size(font: Font, text: String, wanted: int, width: float) -> int:
	var size := wanted
	while size > int(wanted * 0.6) and font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x > width:
		size -= 2
	return size


func _song_text() -> String:
	var title := str(_info.get("song", ""))
	if title == "":
		return ""
	var artist := str(_info.get("artist", ""))
	return "♪  " + title + ("    —    " + artist if artist != "" else "")


func _play_music() -> void:
	var audio := get_node_or_null("/root/AudioManager")
	if audio == null or music_path == "" or not ResourceLoader.exists(music_path):
		return
	var stream = load(music_path)
	if stream == null:
		return
	audio.call("PlayBGM", stream)
	_music_stream = stream
	var player = audio.get("BGM")
	if player is AudioStreamPlayer:
		_music_player = player
		_music_volume = player.volume_db


func _play_sfx(path: String, db: float = 0.0) -> void:
	if path == "" or not ResourceLoader.exists(path):
		return
	_sfx.stream = load(path)
	_sfx.volume_db = db
	_sfx.play()


# --- Light effects ---------------------------------------------------------------------

## Everything that glows, drawn additively in one node: the X of light through the VS, the
## constellation lines and stars on each side, sparks drifting up, lightning crackles, the shock
## ring when the VS lands, and the loading line along the footer.
class VsFx extends Node2D:
	var p1 := Color(0.25, 0.6, 1.0)
	var p2 := Color(1.0, 0.22, 0.36)
	var center := Vector2(960, 676)
	var impact_at := 0.42
	var time := 0.0

	var _glow: GradientTexture2D
	var _cross: GradientTexture2D
	var _paths: Array = []      # [{"pts": PackedVector2Array, "side", "start", "speed", "stars": [{"i", "r"}]}]
	var _sparks: Array = []
	var _crackles: Array = []   # [{"pts", "until", "side"}]
	var _next_crackle := 0.0
	var _rng := RandomNumberGenerator.new()

	func _ready() -> void:
		var mat := CanvasItemMaterial.new()
		mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
		material = mat
		_glow = GradientTexture2D.new()
		_glow.width = 128
		_glow.height = 128
		_glow.fill = GradientTexture2D.FILL_RADIAL
		_glow.fill_from = Vector2(0.5, 0.5)
		_glow.fill_to = Vector2(1.0, 0.5)
		var g := Gradient.new()
		g.offsets = PackedFloat32Array([0.0, 0.18, 0.5, 1.0])
		g.colors = PackedColorArray([Color(1, 1, 1, 1), Color(1, 1, 1, 0.55), Color(1, 1, 1, 0.12), Color(1, 1, 1, 0)])
		_glow.gradient = g
		_cross = GradientTexture2D.new()
		_cross.width = 64
		_cross.height = 4
		var cg := Gradient.new()
		cg.offsets = PackedFloat32Array([0.0, 0.35, 0.5, 0.65, 1.0])
		cg.colors = PackedColorArray([Color(1, 1, 1, 0), Color(1, 1, 1, 0.35), Color(1, 1, 1, 1), Color(1, 1, 1, 0.35), Color(1, 1, 1, 0)])
		_cross.gradient = cg
		_rng.seed = 20261024
		_make_paths()
		for i in 70:
			_sparks.append(_new_spark(true))
		_next_crackle = impact_at + 0.85

	func _process(delta: float) -> void:
		for i in _sparks.size():
			var s: Dictionary = _sparks[i]
			s["pos"] += s["vel"] * delta
			if s["pos"].y < -20.0:
				_sparks[i] = _new_spark(false)
		queue_redraw()

	# --- constellation layout: zig-zag lines from the screen edges toward the middle, stars on some
	# corners. They stay in the outer columns and below `face_line`, so they never cross a face.
	var face_line := 420.0
	var outer := 230.0

	func _make_paths() -> void:
		var starts := [Vector2(-30, 70), Vector2(-30, 330), Vector2(-30, 600), Vector2(-30, 880), Vector2(250, 1110)]
		var aims := [Vector2(150, 560), Vector2(760, 560), Vector2(820, 640), Vector2(700, 760), Vector2(640, 860)]
		for side in 2:
			_rng.seed = 7 + side * 31
			for k in starts.size():
				var p: Vector2 = starts[k]
				var aim: Vector2 = aims[k]
				var pts := PackedVector2Array([p])
				var steps := _rng.randi_range(3, 5)
				for i in steps:
					var to_aim := aim - p
					var dir := to_aim.normalized().rotated(_rng.randf_range(-0.8, 0.8))
					var step := clampf(to_aim.length() / float(steps - i) * _rng.randf_range(0.8, 1.25), 80.0, 320.0)
					var q := p + dir * step
					q.x = clampf(q.x, 10.0, center.x - 130.0)
					q.y = clampf(q.y, 20.0, 1040.0)
					if q.y < face_line and q.x > outer:      # keep clear of the faces
						q.x = outer if p.x <= outer else p.x
						q.y = maxf(q.y, face_line) if p.y >= face_line else q.y
					if q.distance_to(p) < 30.0:
						continue
					p = q
					pts.append(p)
				if side == 1:
					for i in pts.size():
						pts[i] = Vector2(1920.0 - pts[i].x, pts[i].y)
				var stars := []
				for i in range(1, pts.size()):
					if _rng.randf() < 0.55:
						stars.append({"i": i, "r": _rng.randf_range(0.6, 1.25)})
				_paths.append({"pts": pts, "side": side, "start": impact_at + 0.02 + _rng.randf_range(0.0, 0.45),
					"speed": _rng.randf_range(1300.0, 2000.0), "stars": stars, "pulse": _rng.randf_range(0.0, 3.0)})

	func _new_spark(anywhere: bool) -> Dictionary:
		var left := _rng.randf() < 0.5
		var x := _rng.randf_range(0.0, 900.0) if left else _rng.randf_range(1020.0, 1920.0)
		return {"pos": Vector2(x, _rng.randf_range(0.0, 1080.0) if anywhere else 1090.0),
			"vel": Vector2(_rng.randf_range(-8.0, 8.0), -_rng.randf_range(22.0, 70.0)),
			"size": _rng.randf_range(2.0, 5.0), "phase": _rng.randf() * TAU, "left": left}

	func _draw() -> void:
		var since := time - impact_at          # < 0 before the VS lands
		_draw_x(since)
		_draw_constellations()
		_draw_sparks()
		_draw_crackles(since)
		_draw_shock(since)

	func _side_color(left: bool) -> Color:
		return p1 if left else p2

	## The two crossing beams through the VS: blue on the left half, crimson on the right, white-hot in the middle.
	func _draw_x(since: float) -> void:
		var grow := clampf((time - 0.12) / 0.5, 0.0, 1.0)
		grow = 1.0 - pow(1.0 - grow, 3.0)
		if grow <= 0.0:
			return
		var boost := 1.0 + 1.6 * exp(-maxf(since, 0.0) * 5.0) * (1.0 if since >= 0.0 else 0.0)
		var breathe := 1.0 + 0.08 * sin(time * 2.3)
		var half := 1250.0 * grow
		for k in 2:
			var ang := deg_to_rad(-27.0 if k == 0 else 27.0)
			var d := Vector2(cos(ang), sin(ang))
			var a := center - d * half
			var b := center + d * half
			_beam(a, b, 150.0, 0.13 * boost * breathe)
			_beam(a, b, 26.0, 0.32 * boost * breathe)
			_beam(a, b, 5.0, 0.9 * minf(boost, 1.6))
		# glow behind the VS: blue on the V, crimson on the S, white in the middle
		var r := 230.0 * (0.9 + 0.1 * sin(time * 1.7)) * (0.4 + 0.6 * grow)
		draw_texture_rect(_glow, Rect2(center + Vector2(-110, 0) - Vector2(r, r), Vector2(r, r) * 2.0), false, Color(p1, 0.55 * grow))
		draw_texture_rect(_glow, Rect2(center + Vector2(110, 0) - Vector2(r, r), Vector2(r, r) * 2.0), false, Color(p2, 0.55 * grow))
		var w := 140.0 * boost
		draw_texture_rect(_glow, Rect2(center - Vector2(w, w), Vector2(w, w) * 2.0), false, Color(1, 1, 1, 0.35 * grow))

	func _beam(a: Vector2, b: Vector2, width: float, alpha: float) -> void:
		var segs := 28
		var d := (b - a).normalized()
		var n := Vector2(-d.y, d.x) * width * 0.5
		for i in segs:
			var t0 := float(i) / segs
			var t1 := float(i + 1) / segs
			var p0 := a.lerp(b, t0)
			var p1v := a.lerp(b, t1)
			var c0 := _beam_color(t0, alpha)
			var c1 := _beam_color(t1, alpha)
			draw_polygon(PackedVector2Array([p0 - n, p1v - n, p1v + n, p0 + n]), PackedColorArray([c0, c1, c1, c0]),
				PackedVector2Array([Vector2(0, 0.5), Vector2(0, 0.5), Vector2(1, 0.5), Vector2(1, 0.5)]), _cross)

	## Colour along a beam (t = 0 left end .. 1 right end): side colour, white in the middle, fading at the ends,
	## with bright pulses running in toward the middle.
	func _beam_color(t: float, alpha: float) -> Color:
		var from_mid := absf(t - 0.5) * 2.0          # 0 middle .. 1 ends
		var side := p1 if t < 0.5 else p2
		var c := Color(1, 1, 1).lerp(side, clampf(from_mid * 2.2, 0.0, 1.0))
		var ends := 1.0 - smoothstep(0.55, 1.0, from_mid)
		var pulse_pos := 1.0 - fmod(time * 0.55, 1.0)
		var pulse := exp(-pow((from_mid - pulse_pos) / 0.06, 2.0)) * 0.9
		c.a = alpha * ends * (1.0 + pulse)
		return c

	func _draw_constellations() -> void:
		for path in _paths:
			var pts: PackedVector2Array = path["pts"]
			var col := _side_color(path["side"] == 0)
			var drawn: float = maxf(time - path["start"], 0.0) * path["speed"]   # px of the line drawn so far
			if drawn <= 0.0:
				continue
			var walked := 0.0
			var tip := pts[0]
			var reached := 0
			for i in range(1, pts.size()):
				var seg := pts[i - 1].distance_to(pts[i])
				if walked >= drawn:
					break
				var part := clampf((drawn - walked) / seg, 0.0, 1.0)
				var end := pts[i - 1].lerp(pts[i], part)
				draw_line(pts[i - 1], end, Color(col.lightened(0.55), 0.26), 7.0, true)
				draw_line(pts[i - 1], end, Color(col.lightened(0.75), 0.85), 1.6, true)
				tip = end
				walked += seg
				if part >= 1.0:
					reached = i
			# the bright head while the line is still drawing
			var total := _length(pts)
			if drawn < total:
				_spot(tip, 26.0, Color(col.lightened(0.6), 0.9))
			# stars at the corners it has reached: pop, then twinkle
			for star in path["stars"]:
				var i: int = star["i"]
				if i > reached:
					continue
				var at := _distance_to_corner(pts, i) / float(path["speed"]) + float(path["start"])
				var age := time - at
				var pop := 1.0 + 1.4 * exp(-age * 7.0)
				var tw := 0.75 + 0.25 * sin(time * 3.1 + i * 1.9 + float(path["pulse"]))
				var r: float = star["r"]
				_spot(pts[i], 44.0 * r * pop, Color(col.lightened(0.3), 0.5 * tw))
				_spot(pts[i], 13.0 * r * pop, Color(1, 1, 1, 0.95 * tw))
			# a spark of energy running along the finished line toward the middle, now and then
			if drawn >= total:
				var cycle := fmod(time + float(path["pulse"]), 3.2) / 1.1
				if cycle < 1.0:
					_spot(_point_along(pts, cycle * total), 18.0, Color(col.lightened(0.7), 0.85 * sin(cycle * PI)))

	func _draw_sparks() -> void:
		for s in _sparks:
			var flick := 0.55 + 0.45 * sin(time * 5.0 + s["phase"])
			var col := _side_color(s["left"])
			_spot(s["pos"], s["size"] * 4.0, Color(col.lightened(0.5), 0.45 * flick))
			_spot(s["pos"], s["size"], Color(1, 1, 1, 0.7 * flick))

	## Short jagged lightning out of the VS now and then.
	func _draw_crackles(since: float) -> void:
		if since < 0.0:
			return
		if time >= _next_crackle:
			_next_crackle = time + _rng.randf_range(0.5, 1.3)
			for n in _rng.randi_range(1, 2):
				var left := _rng.randf() < 0.5
				var ang := deg_to_rad(_rng.randf_range(-35.0, 35.0)) + (PI if left else 0.0)
				var length := _rng.randf_range(220.0, 520.0)
				var start := center + Vector2(cos(ang), sin(ang)) * 90.0
				var pts := PackedVector2Array([start])
				var segs := _rng.randi_range(6, 10)
				var dir := Vector2(cos(ang), sin(ang))
				for k in segs:
					var p := start + dir * length * float(k + 1) / segs
					p += Vector2(-dir.y, dir.x) * _rng.randf_range(-26.0, 26.0)
					pts.append(p)
				_crackles.append({"pts": pts, "until": time + 0.14, "left": left})
		var keep := []
		for c in _crackles:
			if time > c["until"]:
				continue
			keep.append(c)
			var col := _side_color(c["left"])
			draw_polyline(c["pts"], Color(col.lightened(0.4), 0.35), 6.0, true)
			draw_polyline(c["pts"], Color(1, 1, 1, 0.9), 1.5, true)
		_crackles = keep

	## The shock ring when the VS lands.
	func _draw_shock(since: float) -> void:
		if since < 0.0 or since > 0.8:
			return
		for k in 2:
			var t := clampf((since - k * 0.07) / 0.6, 0.0, 1.0)
			if t <= 0.0 or t >= 1.0:
				continue
			var e := 1.0 - pow(1.0 - t, 3.0)
			var r := 60.0 + 980.0 * e
			var a := (1.0 - t) * (1.0 - t) * (0.85 if k == 0 else 0.5)
			var col := Color(0.8, 0.9, 1.0) if k == 0 else Color(1.0, 0.75, 0.85)
			draw_arc(center, r, 0.0, TAU, 128, Color(col, a * 0.35), 30.0 * (1.0 - t) + 6.0, true)
			draw_arc(center, r, 0.0, TAU, 128, Color(col, a), 3.0, true)
		var burst := 1.0 - clampf(since / 0.35, 0.0, 1.0)
		if burst > 0.0:
			var w := 520.0 * (1.0 + (1.0 - burst))
			draw_texture_rect(_glow, Rect2(center - Vector2(w, w * 0.6), Vector2(w * 2.0, w * 1.2)), false, Color(1, 1, 1, 0.7 * burst))

	func _spot(at: Vector2, radius: float, col: Color) -> void:
		draw_texture_rect(_glow, Rect2(at - Vector2(radius, radius), Vector2(radius, radius) * 2.0), false, col)

	func _length(pts: PackedVector2Array) -> float:
		var total := 0.0
		for i in range(1, pts.size()):
			total += pts[i - 1].distance_to(pts[i])
		return total

	func _distance_to_corner(pts: PackedVector2Array, corner: int) -> float:
		var total := 0.0
		for i in range(1, corner + 1):
			total += pts[i - 1].distance_to(pts[i])
		return total

	func _point_along(pts: PackedVector2Array, dist: float) -> Vector2:
		var walked := 0.0
		for i in range(1, pts.size()):
			var seg := pts[i - 1].distance_to(pts[i])
			if walked + seg >= dist:
				return pts[i - 1].lerp(pts[i], (dist - walked) / maxf(seg, 0.001))
			walked += seg
		return pts[pts.size() - 1]


## The loading line along the footer's line: runs left to right as the fight loads, flashes and
## fades when it's ready.
class VsLoadBar extends Node2D:
	var time := 0.0
	var progress := 0.0
	var loaded_at := -1.0
	var _glow: GradientTexture2D

	func _ready() -> void:
		var mat := CanvasItemMaterial.new()
		mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
		material = mat
		_glow = GradientTexture2D.new()
		_glow.fill = GradientTexture2D.FILL_RADIAL
		_glow.fill_from = Vector2(0.5, 0.5)
		_glow.fill_to = Vector2(1.0, 0.5)
		var g := Gradient.new()
		g.colors = PackedColorArray([Color(1, 1, 1, 1), Color(1, 1, 1, 0)])
		_glow.gradient = g

	func _process(_delta: float) -> void:
		queue_redraw()

	func _draw() -> void:
		var y := 849.0 * NetsuUI.K
		var x := 1920.0 * clampf(progress, 0.0, 1.0)
		var fade := 1.0
		var flash := 0.0
		if loaded_at >= 0.0:
			var k := clampf((time - loaded_at) / 0.6, 0.0, 1.0)
			fade = 1.0 - k
			flash = sin(k * PI)
			if fade <= 0.0:
				return
		var col := Color(0.55, 0.82, 1.0)
		draw_line(Vector2(0, y), Vector2(x, y), Color(col, (0.22 + 0.5 * flash) * fade), 10.0)
		draw_line(Vector2(0, y), Vector2(x, y), Color(1, 1, 1, 0.85 * fade), 2.0)
		if loaded_at < 0.0:
			var r := 34.0 + 6.0 * sin(time * 9.0)
			draw_texture_rect(_glow, Rect2(Vector2(x, y) - Vector2(r, r * 0.5), Vector2(r * 2.0, r)), false, Color(col, 0.9))
