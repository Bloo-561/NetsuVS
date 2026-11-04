class_name NetsuLoadingChase
extends Control
## LOADING SCREEN CHASE (Nov 2 2026). On the loading screen (SceneRouter, under the emblem):
##   - bottom right: Tobias (a little orange dog, drawn here from TamaDeez's drawing) gallops after Leticia, who rides
##     her Flux Board back and forth with a flapping LOADING sign on a post at the back of the board, and Tobias's
##     bone dangling from it. Dust puffs under the dog, sparks from the board, NOW LOADING with running dots.
##   - bottom left: the story so far. One part of "Tobias vs. Leticia" per loading screen, in order; it continues
##     from where it stopped last time (saved in user://loading_story.cfg) and starts over after the last part.
## play() shows it, fade_out() hides it. Drawn on the 1920 x 1080 canvas (scaled to the window).

@export var leticia_frames: PackedStringArray = PackedStringArray([
	"res://actors/leticia/Sprites/v2/ad_1.png", "res://actors/leticia/Sprites/v2/ad_2.png"])
@export var leticia_height: float = 165.0     ## px on the 1080p screen
@export var lane: Rect2 = Rect2(1150, 850, 730, 160)   ## where they run (the bottom of it is the ground line)
@export var lap_time: float = 3.6             ## seconds for Leticia to go there and back
@export var dog_lag: float = 0.72             ## how far behind (seconds) Tobias is
@export var dog_size: float = 1.0
@export var fur: Color = Color(0.97, 0.6, 0.18)
@export var fur_line: Color = Color(0.28, 0.14, 0.05)
@export var board_glow: Color = Color(0.3, 0.95, 1.0)
@export var story_title: String = "TOBIAS VS. LETICIA"
@export var story: PackedStringArray = PackedStringArray([
	"Leticia needed a weight to balance her new Flux Board. Tobias's favourite bone was exactly the right size.",
	"Tobias noticed. Tobias always notices.",
	"Lap one around the academy courtyard. The board is faster. The dog is more determined.",
	"Cecilia offered to referee. Nobody asked her to. She just likes the chaos.",
	"Flan bet three meat buns on the dog.",
	"Noah opened a shortcut through the shadows to help Leticia. Tobias went through it first.",
	"Lap seven. The bone looks a little chewed now. Leticia blames turbulence.",
	"Leticia tried a barrel roll. So did Tobias. Only one of them meant to.",
	"The board's battery is blinking. The dog's battery does not exist.",
	"Leticia offers a truce: the bone back, plus a snack. Tobias thinks it over very carefully.",
	"Tobias accepts the snack. Tobias keeps chasing. It was never about the bone.",
	"To be continued... (the chase is, anyway)."])

const CANVAS := Vector2(1920, 1080)
const SAVE_PATH := "user://loading_story.cfg"

var _t := -1.0
var _part := 0
var _frames: Array[Texture2D] = []
var _puffs: Array = []
var _sparks: Array = []
var _puff_clock := 0.0
var _font: Font
var _thin: Font
var _layer: Control


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	visible = false
	_font = NetsuUI.sans(3, true)
	_thin = NetsuUI.sans(1)
	_layer = Control.new()   # drawn on the 1920 x 1080 canvas, scaled to the window
	_layer.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_layer.size = CANVAS
	_layer.draw.connect(_draw_all)
	add_child(_layer)
	for path in leticia_frames:
		if ResourceLoader.exists(path):
			var tex = load(path)
			if tex is Texture2D:
				_frames.append(tex)
	_part = _load_part()
	resized.connect(_fit)
	_fit()


func _fit() -> void:
	var k := size.x / CANVAS.x if size.x > 0.0 else 1.0
	_layer.scale = Vector2(k, k)
	_layer.position = Vector2(0, (size.y - CANVAS.y * k) / 2.0)


func play() -> void:
	_t = 0.0
	visible = true
	modulate.a = 1.0
	_puffs.clear()
	_sparks.clear()
	_fit()
	set_process(true)


## Fades out and moves the story on to the next part (for the next loading screen).
func fade_out(seconds: float = 0.2) -> void:
	if not visible:
		return
	_part = (_part + 1) % maxi(story.size(), 1)
	_save_part(_part)
	var tw := create_tween()
	tw.tween_property(self, "modulate:a", 0.0, seconds)
	await tw.finished
	visible = false
	_t = -1.0
	set_process(false)


func _load_part() -> int:
	var cfg := ConfigFile.new()
	if cfg.load(SAVE_PATH) == OK:
		return clampi(int(cfg.get_value("story", "part", 0)), 0, maxi(story.size() - 1, 0))
	return 0


func _save_part(part: int) -> void:
	var cfg := ConfigFile.new()
	cfg.set_value("story", "part", part)
	cfg.save(SAVE_PATH)


# --- motion ----------------------------------------------------------------------------------------

## They run round an oval seen from the side (the far half a little higher and smaller), so the dog is always right
## behind her. _run(t): x = depth (-1 far .. 1 near), y = facing (1 right, -1 left).
func _run(t: float) -> Vector2:
	var th := TAU * t / lap_time
	return Vector2(sin(th), -1.0 if sin(th) > 0.0 else 1.0)


func _oval(t: float) -> Vector2:
	var th := TAU * t / lap_time
	var cx := lane.position.x + lane.size.x * 0.5
	var a := lane.size.x * 0.5 - 110.0
	return Vector2(cx + a * cos(th), lane.end.y - 26.0 + 26.0 * sin(th))


func _depth_scale(t: float) -> float:
	return 1.0 + 0.14 * _run(t).x


func _process(delta: float) -> void:
	if _t < 0.0:
		return
	_t += delta
	# dust under the dog, sparks off the board
	_puff_clock += delta
	var dog := _dog_pos(_t)
	var let := _leticia_pos(_t)
	if _puff_clock >= 0.09:
		_puff_clock = 0.0
		_puffs.append({"p": Vector2(dog.x - _run(_t - dog_lag).y * 26.0, dog.y - 2.0), "t": 0.0,
			"v": Vector2(-_run(_t - dog_lag).y * randf_range(20.0, 50.0), -randf_range(15.0, 35.0))})
		var face := _run(_t).y
		_sparks.append({"p": let + Vector2(-face * leticia_height * 0.28, leticia_height * 0.42), "t": 0.0,
			"v": Vector2(-face * randf_range(60.0, 140.0), randf_range(-10.0, 30.0))})
	for p in _puffs:
		p["t"] += delta / 0.5
		p["p"] += p["v"] * delta
	for s in _sparks:
		s["t"] += delta / 0.35
		s["p"] += s["v"] * delta
	_puffs = _puffs.filter(func(p): return p["t"] < 1.0)
	_sparks = _sparks.filter(func(s): return s["t"] < 1.0)
	_layer.queue_redraw()


func _leticia_pos(t: float) -> Vector2:
	var g := _oval(t)
	var k := _depth_scale(t)
	var hover := 26.0 + 6.0 * sin(t * 7.0)
	return Vector2(g.x, g.y - (hover + leticia_height * 0.5) * k)


func _dog_pos(t: float) -> Vector2:
	return _oval(t - dog_lag)


# --- drawing ---------------------------------------------------------------------------------------

func _draw_all() -> void:
	if _t < 0.0:
		return
	var c := _layer
	# ground line under the lane, fading at both ends
	var gy := lane.end.y + 4.0
	c.draw_polyline_colors(PackedVector2Array([Vector2(lane.position.x - 40, gy), Vector2(lane.position.x + lane.size.x * 0.5, gy),
		Vector2(lane.end.x + 20, gy)]), PackedColorArray([Color(0.5, 0.75, 1.0, 0.0), Color(0.5, 0.75, 1.0, 0.45),
		Color(1.0, 0.4, 0.5, 0.0)]), 2.0, true)
	for p in _puffs:
		var a: float = 1.0 - p["t"]
		c.draw_circle(p["p"], 5.0 + 9.0 * p["t"], Color(0.8, 0.75, 0.7, 0.35 * a))
	for s in _sparks:
		var a: float = 1.0 - s["t"]
		c.draw_circle(s["p"], 2.5 * a + 1.0, Color(board_glow, 0.9 * a))
	# whoever is nearer the camera is drawn last
	if _run(_t).x > _run(_t - dog_lag).x:
		_draw_dog(_t)
		_draw_leticia(_t)
	else:
		_draw_leticia(_t)
		_draw_dog(_t)
	_draw_loading_label()
	_draw_story()


func _draw_leticia(t: float) -> void:
	var c := _layer
	var pos := _leticia_pos(t)
	var face := _run(t).y
	var tilt := 0.06 * sin(t * 7.0) - 0.05 * face
	# the board's under-glow
	c.draw_circle(pos + Vector2(0, leticia_height * 0.47 + 18.0), 24.0, Color(board_glow, 0.07))
	if _frames.is_empty():
		return
	var tex: Texture2D = _frames[int(t * 6.0) % _frames.size()]
	var ts := tex.get_size()
	var k := leticia_height * _depth_scale(t) / ts.y
	c.draw_set_transform(pos, tilt * face, Vector2(face * k, k))
	# the LOADING sign on its post at the back of the board, the bone tied under it
	var base := Vector2(ts.x * (0.14 - 0.5), ts.y * (0.83 - 0.5))
	var top := base + Vector2(-ts.x * 0.02, -ts.y * 0.62)
	c.draw_line(base, top, Color(0.75, 0.78, 0.85), 7.0 / k * 0.5, true)
	var flap := sin(t * 12.0) * 0.18
	var sw := ts.x * 0.5
	var sh := ts.y * 0.17
	var sign := PackedVector2Array([top, top + Vector2(-sw, sw * flap * 0.3), top + Vector2(-sw, sh + sw * flap * 0.3), top + Vector2(0, sh)])
	c.draw_colored_polygon(sign, Color(0.03, 0.05, 0.16, 0.95))
	var closed := sign.duplicate()
	closed.append(sign[0])
	c.draw_polyline(closed, Color(1.0, 0.36, 0.5), 3.0 / k * 0.5, true)
	# the bone, swinging under the sign
	var swing := sin(t * 9.0) * 0.35
	var hang := top + Vector2(-sw * 0.5, sh + sw * flap * 0.15)
	var bone := hang + Vector2(sin(swing), cos(swing)) * ts.y * 0.12
	c.draw_line(hang, bone, Color(0.6, 0.6, 0.65), 2.0 / k * 0.5, true)
	_bone(bone, ts.y * 0.06, swing)
	c.draw_texture(tex, -ts / 2.0)
	c.draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
	# the sign's text, drawn unmirrored so it always reads
	var ctr := pos + (Vector2(face, 1.0) * k) * (top + Vector2(-sw * 0.5, sh * 0.55 + sw * flap * 0.15))
	var txt := "LOADING"
	var w := _font.get_string_size(txt, HORIZONTAL_ALIGNMENT_LEFT, -1, 15).x
	c.draw_string(_font, ctr + Vector2(-w / 2.0, 5.0), txt, HORIZONTAL_ALIGNMENT_LEFT, -1, 15, Color.WHITE)


func _bone(at: Vector2, s: float, rot: float) -> void:
	var c := _layer
	var d := Vector2(cos(rot), sin(rot))
	var col := Color(0.97, 0.95, 0.88)
	c.draw_line(at - d * s, at + d * s, col, s * 0.55, true)
	for e: float in [-1.0, 1.0]:
		var end: Vector2 = at + d * s * e
		var n := Vector2(-d.y, d.x)
		c.draw_circle(end + n * s * 0.28, s * 0.32, col)
		c.draw_circle(end - n * s * 0.28, s * 0.32, col)


## Tobias: chunky orange body, long snout, one pointed ear, tail up, four stick legs galloping; a thick dark outline
## like the drawing. Drawn facing right in local units, then mirrored.
func _draw_dog(t: float) -> void:
	var c := _layer
	var tt := t - dog_lag
	var face := _run(tt).y
	var feet := _dog_pos(t)
	var gallop := t * 14.0
	var bob := absf(sin(gallop)) * 7.0
	var s := dog_size * _depth_scale(tt)
	# a leap now and then (snapping at the bone)
	var leap_ph := fposmod(t, 2.2)
	var leap := sin(clampf((leap_ph - 1.6) / 0.45, 0.0, 1.0) * PI) * 34.0
	c.draw_set_transform(feet + Vector2(0, -bob - leap), 0.0, Vector2(face * s, s))
	var line := fur_line
	var w := 3.5
	# legs (behind first: far legs a touch darker)
	var hips := [Vector2(-30, -34), Vector2(26, -34)]
	for pair in 2:
		for far: bool in [true, false]:
			var swing := sin(gallop + (0.0 if pair == 0 else PI) + (0.6 if far else 0.0)) * (0.7 if leap <= 1.0 else 0.2)
			var hip: Vector2 = hips[pair] + (Vector2(-4, 0) if far else Vector2.ZERO)
			var knee := hip + Vector2(sin(swing), cos(swing)) * 18.0
			var paw := knee + Vector2(sin(swing * 0.5) * 6.0, 16.0)
			var col := fur.darkened(0.18) if far else fur
			c.draw_polyline(PackedVector2Array([hip, knee, paw]), line, 11.0, true)
			c.draw_polyline(PackedVector2Array([hip, knee, paw]), col, 6.0, true)
	# tail, wagging up behind
	var wag := sin(t * 18.0) * 0.4
	var tail := PackedVector2Array([Vector2(-40, -48), Vector2(-56, -62 + wag * 10.0), Vector2(-60, -80 + wag * 14.0)])
	c.draw_polyline(tail, line, 11.0, true)
	c.draw_polyline(tail, fur, 6.0, true)
	# body
	var body := PackedVector2Array()
	for i in 24:
		var a := TAU * i / 24.0
		body.append(Vector2(cos(a) * 44.0, -50.0 + sin(a) * 19.0))
	_shape(body, fur, line, w)
	# neck + head with the long snout and a pointed ear
	var head := PackedVector2Array([Vector2(26, -60), Vector2(36, -86), Vector2(44, -96), Vector2(56, -98), Vector2(76, -92),
		Vector2(84, -86), Vector2(82, -79), Vector2(62, -76), Vector2(48, -66), Vector2(40, -50)])
	_shape(head, fur, line, w)
	var ear := PackedVector2Array([Vector2(44, -95), Vector2(40, -120 - sin(t * 14.0) * 3.0), Vector2(56, -98)])
	_shape(ear, fur.darkened(0.08), line, w)
	c.draw_circle(Vector2(60, -88), 3.4, Color(0.05, 0.03, 0.02))          # eye
	c.draw_circle(Vector2(84, -84), 3.0, Color(0.1, 0.05, 0.03))           # nose
	var tongue := PackedVector2Array([Vector2(66, -77), Vector2(72, -66 - sin(gallop) * 2.0), Vector2(76, -76)])
	c.draw_colored_polygon(tongue, Color(1.0, 0.45, 0.55))
	c.draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)


func _shape(points: PackedVector2Array, fill: Color, line: Color, width: float) -> void:
	_layer.draw_colored_polygon(points, fill)
	var closed := points.duplicate()
	closed.append(points[0])
	_layer.draw_polyline(closed, line, width, true)


func _draw_loading_label() -> void:
	var c := _layer
	var dots := ".".repeat(int(_t * 3.0) % 4)
	var txt := "NOW LOADING"
	var size_px := 26
	var x := lane.end.x - 250.0
	var y := lane.end.y + 48.0
	c.draw_string_outline(_font, Vector2(x, y), txt + dots, HORIZONTAL_ALIGNMENT_LEFT, -1, size_px, 8, Color(0.02, 0.03, 0.12, 0.9))
	c.draw_string(_font, Vector2(x, y), txt + dots, HORIZONTAL_ALIGNMENT_LEFT, -1, size_px, Color(0.85, 0.94, 1.0))


func _draw_story() -> void:
	if story.is_empty():
		return
	var c := _layer
	var a := clampf(_t / 0.25, 0.0, 1.0)
	var x := 70.0
	var y := lane.end.y - 30.0
	var title := "%s  ·  PART %d" % [story_title, _part + 1]
	c.draw_string(_font, Vector2(x, y), title, HORIZONTAL_ALIGNMENT_LEFT, -1, 18, Color(1.0, 0.55, 0.62, 0.95 * a))
	c.draw_line(Vector2(x, y + 9.0), Vector2(x + 520.0, y + 9.0), Color(1.0, 0.55, 0.62, 0.5 * a), 1.5, true)
	c.draw_multiline_string(_thin, Vector2(x, y + 38.0), story[_part], HORIZONTAL_ALIGNMENT_LEFT, 1080.0, 24, 2,
		Color(0.9, 0.93, 1.0, a))
