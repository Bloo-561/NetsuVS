extends CanvasLayer
## CHARACTER SELECT INTRO: THE IGNITION (Nov 2 2026). Before the select screen, Netsu's heat emblem (NetsuEmblem, the
## loading screen's medallion, drawn big) lights up in time with the select theme ("Beyond the Crimson Horizon",
## 166 BPM) and ignites on the music's big hit, shattering into embers that open the screen:
##   0 - 0.34 s        black; the medallion fades in and its ring turns and locks
##   beats 1 - 3       the seven element stones light one after another; each beat the screen jolts, a crimson pulse
##                     swells behind the medallion (stronger every beat) and streaks of light rush in toward it
##   beat 4 (1.42 s)   the heat sigil ignites: white flash, a shockwave ring, the medallion bursts into burning
##                     shards and the black blows away, revealing the select screen (`revealed`)
## The time comes from the music's playback position, so every hit lands on the beat (own clock if no music).
## Not played when the select theme is already running (back from the stage select). Eats input until the reveal.

signal revealed

@export var bpm: float = 166.0
@export var beat_offset: float = 0.339
@export var reveal_beat: int = 3
@export var theme_file: String = "beyond_the_crimson_horizon_select"
@export var emblem_radius: float = 330.0
@export var crimson: Color = Color(1.0, 0.2, 0.3)
@export var ember: Color = Color(1.0, 0.62, 0.3)
@export var music_wait: float = 1.2

const CANVAS := Vector2(1920, 1080)
const OUT_TIME := 0.75        # after the ignition: shards, shockwave, fade
const E_FIRST := 0.34         # NetsuEmblem's timeline: first socket ...
const E_IGNITE := 0.94        # ... and the core igniting

var _emblem: NetsuEmblem
var _back: Control
var _front: Control
var _waited := 0.0
var _own_clock := -1.0
var _t := -1.0
var _done := false
var _shards: Array = []
var _streaks: Array = []
var _beat_seen := -1
var _rng := RandomNumberGenerator.new()
var _glow: GradientTexture2D


func _ready() -> void:
	layer = 20
	_rng.seed = 7   # same burst every time
	_back = Control.new()
	_back.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_back.mouse_filter = Control.MOUSE_FILTER_STOP
	_back.draw.connect(_draw_back)
	add_child(_back)
	_emblem = NetsuEmblem.new()
	_emblem.radius = emblem_radius
	_emblem.speed = 0.0   # its time is set from the music here
	add_child(_emblem)
	_front = Control.new()
	_front.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_front.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_front.draw.connect(_draw_front)
	add_child(_front)
	_make_shards()
	var g := Gradient.new()
	g.offsets = PackedFloat32Array([0.0, 0.35, 1.0])
	g.colors = PackedColorArray([Color(1, 1, 1, 1), Color(1, 1, 1, 0.4), Color(1, 1, 1, 0)])
	_glow = GradientTexture2D.new()
	_glow.gradient = g
	_glow.fill = GradientTexture2D.FILL_RADIAL
	_glow.fill_from = Vector2(0.5, 0.5)
	_glow.fill_to = Vector2(1.0, 0.5)
	_glow.width = 256
	_glow.height = 256


func _beat_time(i: float) -> float:
	return beat_offset + i * 60.0 / bpm


func _music_time() -> float:
	var audio := get_node_or_null("/root/AudioManager")
	if audio == null:
		return -1.0
	var player = audio.get("BGM")
	if player is AudioStreamPlayer and player.playing and player.stream != null \
			and str(player.stream.resource_path).get_file().begins_with(theme_file):
		return player.get_playback_position() + AudioServer.get_time_since_last_mix() - AudioServer.get_output_latency()
	return -1.0


## The emblem's own timeline from the music's: ring lock before beat 1, the stones spread over beats 1-3, the core
## igniting exactly on the reveal beat, then real time.
func _emblem_time(m: float) -> float:
	var reveal := _beat_time(reveal_beat)
	var b0 := _beat_time(0)
	if m < b0:
		return m * E_FIRST / maxf(b0, 0.01)
	if m < reveal:
		return E_FIRST + (m - b0) * (E_IGNITE - E_FIRST) / (reveal - b0)
	return E_IGNITE + (m - reveal)


func _process(delta: float) -> void:
	var m := _music_time()
	if m >= 0.0 and _own_clock < 0.0:
		_t = m
	else:
		_waited += delta
		if _own_clock >= 0.0:
			_own_clock += delta
			_t = _own_clock
		elif _waited >= music_wait:
			_own_clock = 0.0
			_t = 0.0
	_apply(delta)


## Everything for time _t (split out so a test can set _t directly).
func _apply(delta: float) -> void:
	var reveal := _beat_time(reveal_beat)
	if _t >= 0.0:
		if not _emblem.visible:
			_emblem.play()
			_emblem.speed = 0.0
		_emblem.set("_t", _emblem_time(_t))
	# a beat just landed: streaks rush in toward the medallion
	var beat := int(floor((_t - beat_offset) / (60.0 / bpm))) if _t >= beat_offset else -1
	if beat != _beat_seen and beat >= 0 and beat < reveal_beat:
		_beat_seen = beat
		for i in 10 + beat * 6:
			var a := _rng.randf() * TAU
			_streaks.append({"a": a, "t": 0.0, "len": _rng.randf_range(160.0, 360.0), "w": _rng.randf_range(1.5, 3.5),
				"col": crimson.lerp(ember, _rng.randf())})
	for s in _streaks:
		s["t"] += delta / 0.28
	_streaks = _streaks.filter(func(s): return s["t"] < 1.0)
	# shake on each beat (stronger every beat) and a big one on the ignition
	var shake := 0.0
	for i in reveal_beat:
		var bt := _beat_time(i)
		if _t >= bt:
			shake = maxf(shake, (5.0 + 4.0 * i) * clampf(1.0 - (_t - bt) / 0.14, 0.0, 1.0))
	if _t >= reveal:
		shake = maxf(shake, 22.0 * clampf(1.0 - (_t - reveal) / 0.3, 0.0, 1.0))
	offset = Vector2(sin(_t * 97.0), cos(_t * 83.0)) * shake if shake > 0.0 else Vector2.ZERO
	if _t >= reveal:
		var k := clampf((_t - reveal) / 0.16, 0.0, 1.0)
		_emblem.modulate.a = 1.0 - k
		_emblem.scale = Vector2.ONE * (1.0 + 0.25 * k)
		_emblem.pivot_offset = _emblem.size / 2.0
		if not _done:
			_done = true
			# the burst takes the colour of the marble that ignited in the middle
			var core := int(_emblem.get("_core"))
			if _emblem.glow_colors.size() > 0:
				ember = _emblem.glow_colors[core % _emblem.glow_colors.size()].lerp(Color(1.0, 0.62, 0.3), 0.25)
			_back.mouse_filter = Control.MOUSE_FILTER_IGNORE
			revealed.emit()
	if _t >= reveal + OUT_TIME:
		queue_free()
		return
	_back.queue_redraw()
	_front.queue_redraw()


func _input(event: InputEvent) -> void:
	if not _done and (event is InputEventKey or event is InputEventJoypadButton or event is InputEventJoypadMotion or event is InputEventMouseButton):
		get_viewport().set_input_as_handled()


func _make_shards() -> void:
	for i in 56:
		var a := _rng.randf() * TAU
		var d := _rng.randf_range(0.15, 1.0)
		var size := _rng.randf_range(12.0, 42.0)
		var pts := PackedVector2Array()
		for j in 3:
			var aa := TAU * j / 3.0 + _rng.randf_range(-0.5, 0.5)
			pts.append(Vector2(cos(aa), sin(aa)) * size * _rng.randf_range(0.6, 1.2))
		_shards.append({"a": a, "d": d, "pts": pts, "speed": _rng.randf_range(900.0, 2100.0),
			"spin": _rng.randf_range(-9.0, 9.0), "hot": _rng.randf() < 0.45})


func _k() -> float:
	var vs := _back.get_viewport_rect().size
	return vs.y / CANVAS.y


func _center() -> Vector2:
	return _back.get_viewport_rect().size / 2.0


## Behind the medallion: the black, and the crimson pulse that swells on each beat.
func _draw_back() -> void:
	var vs := _back.get_viewport_rect().size
	var reveal := _beat_time(reveal_beat)
	var gone := clampf((_t - reveal) / 0.14, 0.0, 1.0) if _t >= reveal else 0.0
	_back.draw_rect(Rect2(Vector2(-40, -40), vs + Vector2(80, 80)), Color(0.01, 0.008, 0.03, 1.0 - gone))
	if _t < 0.0 or gone >= 1.0:
		return
	var c := _center()
	var k := _k()
	var pulse := 0.0
	for i in reveal_beat:
		var bt := _beat_time(i)
		if _t >= bt:
			pulse = maxf(pulse, (0.35 + 0.25 * i) * clampf(1.0 - (_t - bt) / 0.3, 0.0, 1.0))
	var build := clampf((_t - _beat_time(0)) / (reveal - _beat_time(0)), 0.0, 1.0)   # it gets hotter toward the hit
	var base := 0.18 + 0.35 * build + 0.5 * pulse
	var r := emblem_radius * k * (2.2 + 0.25 * pulse + 0.4 * build)
	_back.draw_texture_rect(_glow, Rect2(c - Vector2(r, r), Vector2(r, r) * 2.0), false, Color(crimson, minf(1.0, base) * (1.0 - gone)))


## In front: the streaks, the ignition flash, the shockwave and the shards.
func _draw_front() -> void:
	if _t < 0.0:
		return
	var c := _center()
	var k := _k()
	var vs := _front.get_viewport_rect().size
	var reach := vs.length() * 0.6
	for s in _streaks:
		var t: float = s["t"]
		var d := Vector2(cos(s["a"]), sin(s["a"]))
		var head := c + d * lerpf(reach, emblem_radius * k * 1.05, 1.0 - pow(1.0 - t, 2.0))
		var tail := head + d * float(s["len"]) * k * (1.0 - t * 0.6)
		var a := clampf(t / 0.15, 0.0, 1.0) * clampf((1.0 - t) / 0.3, 0.0, 1.0)
		_front.draw_line(tail, head, Color(s["col"], 0.3 * a), float(s["w"]) * 4.0, true)
		_front.draw_line(tail, head, Color(Color(s["col"]).lightened(0.5), 0.9 * a), float(s["w"]), true)
	var reveal := _beat_time(reveal_beat)
	# a small white flash on each beat
	var flash := 0.0
	for i in reveal_beat:
		var bt := _beat_time(i)
		if _t >= bt:
			flash = maxf(flash, 0.12 * clampf(1.0 - (_t - bt) / 0.1, 0.0, 1.0))
	if _t >= reveal:
		var since := _t - reveal
		# shockwave
		var ring := emblem_radius * k + since * 2600.0 * k
		var ra := clampf(1.0 - since / 0.45, 0.0, 1.0)
		if ra > 0.0:
			_front.draw_arc(c, ring, 0.0, TAU, 96, Color(ember.lightened(0.4), 0.8 * ra), 28.0 * k * ra + 3.0, true)
			_front.draw_arc(c, ring * 0.82, 0.0, TAU, 96, Color(crimson, 0.5 * ra), 10.0 * k * ra + 2.0, true)
		# shards
		for s in _shards:
			var d := Vector2(cos(s["a"]), sin(s["a"]))
			var p := c + d * (float(s["d"]) * emblem_radius * k + float(s["speed"]) * since * k * (1.0 - since * 0.5))
			var rot := float(s["spin"]) * since
			var fade := clampf(1.0 - since / 0.65, 0.0, 1.0)
			var pts := PackedVector2Array()
			for q in s["pts"]:
				pts.append(p + (q as Vector2).rotated(rot) * k)
			var col: Color = ember.lerp(Color.WHITE, 0.3) if s["hot"] else Color(0.3, 0.33, 0.42)
			_front.draw_colored_polygon(pts, Color(col, fade))
			pts.append(pts[0])
			_front.draw_polyline(pts, Color(ember, 0.9 * fade), 2.0, true)
		flash = maxf(flash, 0.7 * clampf(1.0 - since / 0.28, 0.0, 1.0))
	if flash > 0.0:
		_front.draw_rect(Rect2(Vector2(-40, -40), vs + Vector2(80, 80)), Color(1, 0.97, 0.92, flash))
