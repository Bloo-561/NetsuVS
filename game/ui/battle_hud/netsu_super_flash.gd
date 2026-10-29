extends Control
## EX / SUPER FLASH (Oct 24 2026)
##
## When a fighter spends Craft Gauge on a big move, the fight shows it:
##   EX move (1 bar) or super (3 bars) -> the stage goes dark for as long as the move's flash
##       freezes the opponent, and a burst of light (spinning rays, a glow, a ring that opens
##       out) goes off at the fighter's chest. The frozen opponent (and its assist) is darkened:
##       that part is the engine (SakugaActor.NetsuSuperFlashLook, C#).
##   Assist Cancel (S during your attack, 1 bar) -> a small white burst, no dark screen.
##   Any other move with a flash (cost under 1 bar) -> a burst, no dark screen.
## The engine calls MatchSetup.netsu_super_flash() as the flash starts; this node listens to
## MatchSetup.super_flash. netsu_hud.gd adds it to the battle's CanvasLayer, right above the
## fighters' layer (ViewportContainer), and puts a full-screen dark rect at the bottom of that
## layer: over the stage, under the fighters and the HUD.
## Oct 24 (evening): EX moves and supers also get a streak of light through the fighter and sparks
## drifting off her in her colour (MatchSetup.side_color); the close-up / smoke / big picture are
## netsu_cut_in.gd and the outline around her is the engine (AnimationViewer.SetAura).
## Presentation only: nothing in the match depends on it. Rollback can report a flash twice;
## repeats within repeat_guard seconds are ignored.
## Oct 24 (late): EX moves and supers first stop the whole fight for a moment (the engine's pause,
## GameManager.NetsuPause: the camera closes in on her, FighterCamera). While it lasts the stage is
## darker still (pause_ex_dim / pause_super_dim); it eases back to ex_dim / super_dim as the fight goes on.
## Oct 25: for the fight's first frames (still black) one burst and a spark are drawn nearly transparent, so this
## layer's additive material is compiled then and not at the first EX move (which stalled for a moment).

@export_group("Dark screen")
@export var ex_dim: float = 0.55           ## darkness for EX moves (0-1)
@export var super_dim: float = 0.65        ## darkness for supers
@export var dim_color: Color = Color(0.016, 0.008, 0.04)
@export var dim_in: float = 0.05           ## seconds to go dark
@export var dim_out: float = 0.3           ## seconds to fade back after the freeze
@export var pause_ex_dim: float = 0.86     ## darkness while an EX move's pause holds the fight
@export var pause_super_dim: float = 0.9   ## darkness while a super's pause holds the fight
@export var pause_out: float = 0.18        ## seconds to ease from the pause's darkness to the flash's
@export var overdrive_dim: float = 0.28    ## Oct 26 evening: the stage's tint while anyone's Overdrive runs (MatchSetup.overdrive_hud)

@export_group("Burst")
@export var burst_time: float = 0.55       ## seconds
@export var ray_count: int = 14
@export var ray_length: float = 1.7        ## metres in the fight (a fighter is about 1.4 m tall)
@export var ray_width: float = 0.035       ## metres, at the centre
@export var ray_spin: float = 3.0          ## radians per second
@export var glow_radius: float = 0.75      ## metres
@export var ring_from: float = 0.27        ## metres
@export var ring_to: float = 1.45          ## metres
@export var ring_width: float = 4.0        ## screen pixels
@export var p1_color: Color = Color(0.55, 0.8, 1.0)     ## glow colour, player 1 side
@export var p2_color: Color = Color(1.0, 0.55, 0.62)    ## glow colour, player 2 side
@export var ray_color: Color = Color(1.0, 0.94, 0.78)
@export var cancel_scale: float = 0.55     ## Assist Cancel burst size
@export var rc_color: Color = Color(1.0, 0.1, 0.08)     ## Oct 27 c35: Roman Cancel glow (red)
@export var rc_ray_color: Color = Color(1.0, 0.45, 0.35)
@export var rc_scale: float = 1.25         ## Roman Cancel burst size
@export var rc_tint: float = 0.0          ## Roman Cancel: how red the stage goes while the fight is stopped (0-1)
@export var repeat_guard: float = 0.4      ## seconds

@export_group("Streak and sparks")
@export var streak_time: float = 0.28      ## seconds the line of light through her lasts
@export var streak_length: float = 2600.0  ## screen pixels
@export var spark_count: int = 18          ## EX (supers get half again as many)
@export var spark_time: float = 0.75       ## seconds
@export var spark_speed: float = 0.9       ## metres per second
@export var spark_size: float = 0.07       ## metres

var _dim: ColorRect
var _dim_level := 0.0
var _dim_target := 0.0
var _dim_hold := 0.0
var _bursts: Array = []      # {side, pos: Vector3, t, size, time, color, ring, big}
var _sparks: Array = []      # {pos: Vector3, vel: Vector3, t, time, size, color}
var _rng := RandomNumberGenerator.new()
var _last := {}              # "side:kind" -> msec
var _glow: GradientTexture2D
var _container: SubViewportContainer
var _viewport: SubViewport
var _camera: Camera3D
var _game: Node              # GameManager (C#): the pause (NetsuPauseInfo)
var _pause_kind := 0         # 0 EX, 1 super: the last big flash
var _warm := 0               # frames of invisible warm-up drawing left
var _rc_hold := 0.0          # Oct 27 c35: seconds of red stage tint left (Roman Cancel)
var _rc_level := 0.0


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var add := CanvasItemMaterial.new()
	add.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	material = add
	_glow = _make_glow()
	if MatchSetup.has_signal("super_flash"):
		MatchSetup.super_flash.connect(_on_flash)
	_place.call_deferred()


## Above the fighters' layer, and the dark rect at the very bottom of the CanvasLayer.
func _place() -> void:
	var root := get_parent()
	if root == null:
		return
	_container = root.get_node_or_null("ViewportContainer") as SubViewportContainer
	if _container:
		_viewport = _container.get_node_or_null("Viewport_Foreground") as SubViewport
		if _viewport:
			_camera = _viewport.get_node_or_null("CharacterCamera") as Camera3D
		root.move_child(self, _container.get_index() + 1)
	_dim = ColorRect.new()
	_dim.name = "NetsuStageDim"
	_dim.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_dim.color = Color(dim_color, 0.0)
	_dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_child(_dim)
	root.move_child(_dim, 0)
	var battle := root.get_parent()
	if battle:
		for n in battle.get_children():
			if n.has_method("NetsuPauseInfo"):
				_game = n
	_warm = 4


func _warm_tick() -> void:
	_warm -= 1
	if _warm > 0:
		modulate.a = 0.01   # under the fight's black screen anyway
		var pos := Vector3(0.0, 1.0, 0.0)
		_bursts = [{"side": -1, "pos": pos, "t": 0.05, "size": 1.0, "time": burst_time, "color": p1_color, "ring": true, "big": true}]
		_sparks = [{"side": -1, "pos": pos, "vel": Vector3.ZERO, "t": 0.05, "time": spark_time, "size": spark_size, "color": p1_color}]
		queue_redraw()
	else:
		modulate.a = 1.0
		_bursts = _bursts.filter(func(b): return b["side"] != -1)
		_sparks = _sparks.filter(func(p): return p["side"] != -1)
		queue_redraw()


func _make_glow() -> GradientTexture2D:
	var g := Gradient.new()
	g.offsets = PackedFloat32Array([0.0, 0.35, 1.0])
	g.colors = PackedColorArray([Color(1, 1, 1, 1), Color(1, 1, 1, 0.55), Color(1, 1, 1, 0)])
	var tex := GradientTexture2D.new()
	tex.gradient = g
	tex.fill = GradientTexture2D.FILL_RADIAL
	tex.fill_from = Vector2(0.5, 0.5)
	tex.fill_to = Vector2(1.0, 0.5)
	tex.width = 128
	tex.height = 128
	return tex


func _on_flash(side: int, pos: Vector3, cost: int, frames: int) -> void:
	if _warm > 0:
		_warm = 1
		_warm_tick()
	# kind: 0 EX, 1 super, 2 Assist Cancel, 3 another flash, 4 Roman Cancel (cost -2; Oct 28: removed from the
	# engine, nothing sends -2 any more). Oct 29: EX moves cost 10000 (1 bar), supers 30000 (units x5).
	var kind := 4 if cost == -2 else (2 if cost < 0 else (1 if cost >= 30000 else (0 if cost >= 10000 else 3)))
	var key := "%d:%d" % [side, kind]
	var now := Time.get_ticks_msec()
	if float(now - int(_last.get(key, -100000))) < repeat_guard * 1000.0:
		return
	_last[key] = now
	var col := p1_color if side == 0 else p2_color
	if kind <= 1 and MatchSetup.has_method("side_color"):
		col = MatchSetup.side_color(side).lerp(Color(1, 1, 1), 0.25)
	if kind == 4:
		col = rc_color
		_rc_hold = float(frames) / 60.0 + 0.1
	if kind <= 1:
		_dim_target = super_dim if kind == 1 else ex_dim
		_dim_hold = maxf(_dim_hold, float(frames) / 60.0 + dim_in)
		_pause_kind = kind
	var big := kind <= 1 or kind == 4
	_bursts = _bursts.filter(func(b): return b["side"] != side)
	_bursts.append({"side": side, "pos": pos, "t": 0.0,
		"size": rc_scale if kind == 4 else (1.0 if big else (cancel_scale if kind == 2 else 0.8)),
		"time": burst_time * 1.15 if kind == 4 else (burst_time if big else burst_time * 0.6),
		"color": Color(1, 1, 1) if kind == 2 else col, "ring": kind != 2, "big": big,
		"ray": rc_ray_color if kind == 4 else ray_color})
	if big:
		_sparks = _sparks.filter(func(p): return p["side"] != side)
		var n := spark_count + (int(spark_count * 0.5) if kind == 1 else 0) + (spark_count if kind == 4 else 0)
		for i in n:
			var ang := _rng.randf() * TAU
			var dir := Vector3(cos(ang), sin(ang) * 0.8 + 0.35, 0.0).normalized()
			var start := pos + Vector3(_rng.randf_range(-0.35, 0.35), _rng.randf_range(-0.55, 0.45), 0.0)
			_sparks.append({"side": side, "pos": start, "vel": dir * spark_speed * _rng.randf_range(0.4, 1.3),
				"t": -_rng.randf_range(0.0, 0.12), "time": spark_time * _rng.randf_range(0.6, 1.1),
				"size": spark_size * _rng.randf_range(0.5, 1.3), "color": col})


func _process(delta: float) -> void:
	if _warm > 0:
		_warm_tick()
		return
	var pausing := false
	if _game:
		var info = _game.call("NetsuPauseInfo")
		pausing = info is Array and info.size() > 0 and int(info[0]) > 0
	if pausing:
		var dark := pause_super_dim if _pause_kind == 1 else pause_ex_dim
		_dim_hold = maxf(_dim_hold - delta, 0.05)
		_dim_level = move_toward(_dim_level, dark, delta * dark / maxf(dim_in, 0.001))
	elif _dim_hold > 0.0:
		_dim_hold -= delta
		var rate := _dim_target / maxf(dim_in, 0.001)
		if _dim_level > _dim_target:   # coming out of the pause: ease back to the flash's darkness
			rate = maxf(pause_ex_dim, pause_super_dim) / maxf(pause_out, 0.001)
		_dim_level = move_toward(_dim_level, _dim_target, delta * rate)
	else:
		# back to no darkness, or to the Overdrive tint while one runs
		var rest := 0.0   # Oct 28: no stage tint for Overdrive any more (it's a low-health state now)
		if _dim_level > rest:
			_dim_level = move_toward(_dim_level, rest, delta * maxf(_dim_target, 0.05) / maxf(dim_out, 0.001))
		elif _dim_level < rest:
			_dim_level = move_toward(_dim_level, rest, delta * rest / maxf(dim_out, 0.001))
	if _rc_hold > 0.0:
		_rc_hold -= delta
		_rc_level = move_toward(_rc_level, rc_tint, delta * 6.0)
	else:
		_rc_level = move_toward(_rc_level, 0.0, delta * 2.0)
	if _dim:
		if _rc_level > 0.001 and _dim_level < 0.05:
			_dim.color = Color(rc_color.r * 0.55, 0.0, 0.0, _rc_level)
		else:
			_dim.color = Color(dim_color, _dim_level)
	if _bursts.is_empty() and _sparks.is_empty():
		return
	for b in _bursts:
		b["t"] += delta
	_bursts = _bursts.filter(func(b): return b["t"] < b["time"])
	for p in _sparks:
		p["t"] += delta
		if p["t"] > 0.0:
			p["pos"] += p["vel"] * delta
			p["vel"] *= 0.97
	_sparks = _sparks.filter(func(p): return p["t"] < p["time"])
	queue_redraw()


## A point of the fight (metres) on this layer: through the fighters' camera, then from its
## viewport's pixels onto the container's rect.
func _to_screen(world: Vector3) -> Vector2:
	if _camera == null or _viewport == null or _container == null:
		return size * 0.5
	var p := _camera.unproject_position(world)
	var vs := Vector2(_viewport.size)
	if vs.x <= 0.0 or vs.y <= 0.0:
		return size * 0.5
	var r := _container.get_rect()
	return r.position + p / vs * r.size


func _draw() -> void:
	for b in _bursts:
		_draw_burst(b)
	for p in _sparks:
		_draw_spark(p)


## A spark: a small glow with a white core that grows in, then shrinks away.
func _draw_spark(p: Dictionary) -> void:
	var t: float = p["t"]
	if t <= 0.0:
		return
	var k := clampf(t / float(p["time"]), 0.0, 1.0)
	var c := _to_screen(p["pos"])
	var metre := (_to_screen(p["pos"] + Vector3(0, 1, 0)) - c).length()
	var r: float = p["size"] * metre * (0.5 + 0.5 * sin(minf(1.0, k * 4.0) * PI * 0.5)) * (1.0 - k * 0.6)
	var a := 1.0 - k
	draw_texture_rect(_glow, Rect2(c - Vector2(r, r) * 2.0, Vector2(r, r) * 4.0), false, Color(p["color"], 0.8 * a))
	draw_texture_rect(_glow, Rect2(c - Vector2(r, r) * 0.6, Vector2(r, r) * 1.2), false, Color(1, 1, 1, a))


func _draw_burst(b: Dictionary) -> void:
	var t: float = b["t"]
	var k := clampf(t / float(b["time"]), 0.0, 1.0)
	var a := 1.0 - k
	var pos: Vector3 = b["pos"]
	var c := _to_screen(pos)
	var metre := (_to_screen(pos + Vector3(0, 1, 0)) - c).length()
	if metre <= 0.0:
		return
	var s: float = b["size"] * metre
	var col: Color = b["color"]
	var rays: Color = b.get("ray", ray_color)
	# rays: grow out over the first 0.1 s and spin
	var length := ray_length * s * minf(1.0, t / 0.1)
	var half := ray_width * s
	var spin := t * ray_spin
	for i in ray_count:
		var ang := spin + TAU * float(i) / float(ray_count)
		var d := Vector2(cos(ang), sin(ang))
		var n := Vector2(-d.y, d.x)
		draw_polygon(PackedVector2Array([c + n * half, c + d * length, c - n * half]),
			PackedColorArray([Color(rays, 0.5 * a), Color(rays, 0.0), Color(rays, 0.5 * a)]))
	# glow: the side's colour, with a white core; swells in over ~5 frames
	var r := glow_radius * s * (0.6 + 0.4 * sin(minf(1.0, t / 0.083) * PI * 0.5))
	draw_texture_rect(_glow, Rect2(c - Vector2(r, r), Vector2(r, r) * 2.0), false, Color(col, 0.85 * a))
	draw_texture_rect(_glow, Rect2(c - Vector2(r, r) * 0.45, Vector2(r, r) * 0.9), false, Color(1, 1, 1, 0.9 * a))
	# a line of light straight through her (EX moves and supers)
	if b.get("big", false) and t < streak_time:
		var ks := t / streak_time
		var half_len := streak_length * 0.5 * (0.35 + 0.65 * minf(1.0, t / 0.05))
		var th := maxf(2.0, 0.05 * s * (1.0 - ks))
		var sa := 0.9 * (1.0 - ks)
		draw_polygon(PackedVector2Array([c - Vector2(half_len, 0), c - Vector2(0, th * 2.0), c + Vector2(half_len, 0), c + Vector2(0, th * 2.0)]),
			PackedColorArray([Color(col, 0.0), Color(col, sa), Color(col, 0.0), Color(col, sa)]))
		draw_polygon(PackedVector2Array([c - Vector2(half_len * 0.7, 0), c - Vector2(0, th * 0.6), c + Vector2(half_len * 0.7, 0), c + Vector2(0, th * 0.6)]),
			PackedColorArray([Color(1, 1, 1, 0.0), Color(1, 1, 1, sa), Color(1, 1, 1, 0.0), Color(1, 1, 1, sa)]))
	# ring opening out
	if b["ring"]:
		var rr := (ring_from + k * (ring_to - ring_from)) * s
		draw_arc(c, rr, 0.0, TAU, 72, Color(1, 1, 1, a), ring_width, true)
