class_name NetsuEmblem
extends Control
## NETSU LOADING EMBLEM (Oct 25 2026)
##
## Shown by SceneRouter on the black screen between scenes while the next one loads, in the spirit of an
## old RPG's opening where a device lights up: an original design for Netsu, not any game's device.
##   1. a round steel medallion fades in; its outer ring turns and locks into place (a flash at the top notch);
##   2. (Oct 25 evening) seven sockets light up one after another, one per element in its quartz colour:
##      Earth (brown), Water (blue), Fire (red), Wind (green), then the higher elements Time (black),
##      Space (gold) and Mirage (silver); each stone is a faceted quartz with the element's sign beside it,
##      light running along the engraved channels from socket to socket;
##   3. each stone sends its light down a spoke into the centre, and the heat sigil in the middle (a sun with
##      twelve rays: "netsu" is heat) ignites with a flare and a ring of light;
##   4. then it glows softly until the next scene is ready, and fades out with the black.
## play() starts it, finished_lighting() says when step 3 is done, fade_out() ends it. Everything is drawn in
## code (_draw): sizes are for a 1920x1080 screen and scale with the window.

signal core_lit   ## the core has ignited (step 3)

@export var radius: float = 165.0            ## outer radius on a 1080p screen
@export var speed: float = 1.0               ## 2 = twice as fast
## The seven elements, clockwise from the top: Earth, Water, Fire, Wind, Time, Space, Mirage.
const ELEMENTS := ["earth", "water", "fire", "wind", "time", "space", "mirage"]
## Each stone's colour (the quartz) ...
@export var stone_colors: PackedColorArray = PackedColorArray([
	Color(0.6, 0.38, 0.18), Color(0.25, 0.5, 1.0), Color(1.0, 0.22, 0.2), Color(0.28, 0.88, 0.4),
	Color(0.13, 0.12, 0.17), Color(1.0, 0.8, 0.2), Color(0.84, 0.87, 0.93)])
## ... and the colour of its light (Time is a black stone: its light is a deep violet).
@export var glow_colors: PackedColorArray = PackedColorArray([
	Color(0.85, 0.52, 0.25), Color(0.35, 0.6, 1.0), Color(1.0, 0.3, 0.22), Color(0.35, 1.0, 0.5),
	Color(0.55, 0.38, 0.85), Color(1.0, 0.85, 0.3), Color(0.9, 0.93, 1.0)])
@export var core_color: Color = Color(1.0, 0.8, 0.45)
@export var steel_dark: Color = Color(0.09, 0.1, 0.15)
@export var steel_mid: Color = Color(0.26, 0.29, 0.38)
@export var steel_light: Color = Color(0.62, 0.68, 0.8)
@export var face_color: Color = Color(0.03, 0.04, 0.1)

# timeline (seconds at speed 1)
const T_APPEAR := 0.18      # fades in, ring turning
const T_LOCK := 0.3         # the ring locks
const T_FIRST := 0.34       # first socket starts
const T_STEP := 0.065       # between sockets
const T_RUN := 0.07         # light running along a channel
const T_SPOKES := 0.86      # spokes into the core
const T_IGNITE := 0.94      # the core ignites
const T_DONE := 1.06        # lit: may leave from here

var _t := -1.0              # time since play(); -1 = not playing
var _alpha := 1.0           # fade_out() takes it to 0
var _fading := false
var _lit_sent := false
var _glow: GradientTexture2D
var _glow_layer: Control


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	visible = false
	_glow = _make_glow()
	_glow_layer = Control.new()
	_glow_layer.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_glow_layer.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var add := CanvasItemMaterial.new()
	add.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	_glow_layer.material = add
	_glow_layer.draw.connect(_draw_glow)
	add_child(_glow_layer)


func play() -> void:
	_t = 0.0
	_alpha = 1.0
	_fading = false
	_lit_sent = false
	modulate.a = 1.0
	visible = true
	set_process(true)


## True once the core has ignited (the light-up is over).
func finished_lighting() -> bool:
	return _t >= T_DONE


func fade_out(seconds: float = 0.2) -> void:
	if not visible:
		return
	_fading = true
	var tw := create_tween()
	tw.tween_property(self, "modulate:a", 0.0, seconds)
	await tw.finished
	if _fading:
		visible = false
		_t = -1.0
		set_process(false)


func _process(delta: float) -> void:
	if _t < 0.0:
		return
	_t += delta * speed
	if _t >= T_IGNITE and not _lit_sent:
		_lit_sent = true
		core_lit.emit()
	queue_redraw()
	_glow_layer.queue_redraw()


func _make_glow() -> GradientTexture2D:
	var g := Gradient.new()
	g.offsets = PackedFloat32Array([0.0, 0.3, 1.0])
	g.colors = PackedColorArray([Color(1, 1, 1, 1), Color(1, 1, 1, 0.45), Color(1, 1, 1, 0)])
	var tex := GradientTexture2D.new()
	tex.gradient = g
	tex.fill = GradientTexture2D.FILL_RADIAL
	tex.fill_from = Vector2(0.5, 0.5)
	tex.fill_to = Vector2(1.0, 0.5)
	tex.width = 128
	tex.height = 128
	return tex


# --- geometry -------------------------------------------------------------------------------

func _scale() -> float:
	return size.y / 1080.0 if size.y > 0.0 else 1.0


func _center() -> Vector2:
	return size * 0.5


func _r() -> float:
	return radius * _scale()


func _n() -> int:
	return maxi(stone_colors.size(), 1)


func _dir(i: int) -> Vector2:
	var a := -PI * 0.5 + TAU * float(i) / float(_n())
	return Vector2(cos(a), sin(a))


## Where socket i sits (0 = top, then clockwise).
func _socket(i: int) -> Vector2:
	return _center() + _dir(i) * _r() * 0.56


func _glow_of(i: int) -> Color:
	return glow_colors[i % glow_colors.size()] if glow_colors.size() > 0 else stone_colors[i % stone_colors.size()]


## 0..1 over [a, b] with an ease-out.
func _k(a: float, b: float) -> float:
	return 1.0 - pow(1.0 - clampf((_t - a) / maxf(b - a, 0.0001), 0.0, 1.0), 3.0)


## How lit socket i is (0..1) and how far the light has run along the channel into it.
func _socket_lit(i: int) -> float:
	var start := T_FIRST + T_STEP * i
	return _k(start + T_RUN, start + T_RUN + 0.09)


func _channel_run(i: int) -> float:
	var start := T_FIRST + T_STEP * i
	return clampf((_t - start) / T_RUN, 0.0, 1.0)


# --- drawing --------------------------------------------------------------------------------

func _draw() -> void:
	if _t < 0.0:
		return
	var c := _center()
	var r := _r()
	var s := _scale()
	var appear := _k(0.0, T_APPEAR)
	var a := appear
	# outer ring: turns and locks
	var turn := deg_to_rad(-70.0) * (1.0 - _k(0.0, T_LOCK))
	draw_circle(c, r * 1.02, Color(0, 0, 0, 0.6 * a))                       # shadow
	draw_circle(c, r, Color(steel_mid, a))
	draw_arc(c, r * 0.93, 0.0, TAU, 96, Color(steel_dark, a), r * 0.12, true)
	draw_arc(c, r * 0.995, deg_to_rad(200), deg_to_rad(320), 48, Color(steel_light, 0.55 * a), 2.5 * s, true)   # a highlight, top left
	draw_arc(c, r * 0.995, deg_to_rad(20), deg_to_rad(140), 48, Color(0, 0, 0, 0.45 * a), 2.5 * s, true)        # shadow, bottom right
	for i in 60:
		var ang := turn + TAU * float(i) / 60.0
		var d := Vector2(cos(ang), sin(ang))
		var long := i % 10 == 0
		var r0 := r * (0.88 if long else 0.91)
		draw_line(c + d * r0, c + d * r * 0.97, Color(steel_light, (0.75 if long else 0.35) * a), (2.2 if long else 1.2) * s, true)
	# the lock: a notch at the top flashes as the ring settles
	var lock := _k(T_LOCK - 0.02, T_LOCK + 0.12) * (1.0 - _k(T_LOCK + 0.12, T_LOCK + 0.4))
	var top := c + Vector2(0, -r * 0.93)
	draw_colored_polygon(PackedVector2Array([top + Vector2(-7, -9) * s, top + Vector2(7, -9) * s, top + Vector2(0, 5) * s]),
		Color(steel_light.lerp(Color.WHITE, lock), a))
	# the face
	draw_circle(c, r * 0.84, Color(face_color, a))
	draw_arc(c, r * 0.84, 0.0, TAU, 96, Color(steel_light, 0.3 * a), 1.5 * s, true)
	draw_arc(c, r * 0.7, 0.0, TAU, 96, Color(steel_mid, 0.35 * a), 1.0 * s, true)
	# engraved channels: the hexagon through the sockets and the spokes, dark until lit
	var n := _n()
	for i in n:
		var p := _socket(i)
		var q := _socket((i + 1) % n)
		draw_line(p, q, Color(steel_dark.lightened(0.15), a), 5.0 * s, true)
		draw_line(p, c, Color(steel_dark.lightened(0.1), a), 3.0 * s, true)
	# sockets: a steel cup with a faceted quartz, dark until its turn; the element's sign outside it
	for i in n:
		var p := _socket(i)
		var lit := _socket_lit(i)
		var stone: Color = stone_colors[i % stone_colors.size()]
		draw_circle(p, r * 0.115, Color(steel_mid, a))
		draw_arc(p, r * 0.115, 0.0, TAU, 32, Color(steel_light, 0.6 * a), 1.5 * s, true)
		_draw_quartz(p, r * 0.082, stone, lit, a)
		var sign_col := Color(steel_mid.lightened(0.15), 0.9 * a).lerp(Color(_glow_of(i).lightened(0.25), a), lit)
		_draw_sign(ELEMENTS[i % ELEMENTS.size()], c + _dir(i) * r * 0.765, r * 0.05, sign_col, s)
	# the core: a steel ring and the heat sigil
	var ignite := _k(T_IGNITE, T_IGNITE + 0.14)
	draw_circle(c, r * 0.22, Color(steel_mid, a))
	draw_arc(c, r * 0.22, 0.0, TAU, 48, Color(steel_light, 0.7 * a), 2.0 * s, true)
	draw_circle(c, r * 0.17, Color(face_color.lerp(core_color.darkened(0.55), ignite), a))
	var sun := core_color.darkened(0.7).lerp(Color(1, 0.95, 0.85), ignite)
	for i in 12:
		var ang := TAU * float(i) / 12.0 + _t * 0.4 * ignite
		var d := Vector2(cos(ang), sin(ang))
		var nn := Vector2(-d.y, d.x)
		var ray_len := r * (0.15 if i % 2 == 0 else 0.11)
		draw_colored_polygon(PackedVector2Array([c + d * r * 0.075 + nn * r * 0.022, c + d * ray_len, c + d * r * 0.075 - nn * r * 0.022]), Color(sun, a))
	draw_circle(c, r * 0.07, Color(sun, a))


## The light (additive): channels running, stones glowing, the core's flare and ring.
func _draw_glow() -> void:
	if _t < 0.0:
		return
	var c := _center()
	var r := _r()
	var s := _scale()
	var pulse := 0.85 + 0.15 * sin(_t * 5.0)
	var n := _n()
	# light running along the ring of channels into each socket, staying on behind it
	for i in n:
		var run := _channel_run(i)
		if run <= 0.0:
			continue
		var col := _glow_of(i)
		var from := _socket((i + n - 1) % n) if i > 0 else _socket(0)
		var to := _socket(i)
		if i == 0:
			from = to   # the first stone lights by itself
		var head := from.lerp(to, run)
		_glow_layer.draw_line(from, head, Color(col, 0.75), 3.0 * s, true)
		_glow_layer.draw_line(from, head, Color(1, 1, 1, 0.5), 1.2 * s, true)
		if run < 1.0:
			_glow_dot(head, r * 0.09, Color(1, 1, 1, 0.9))
	# the last channel closes the ring when the last stone is lit
	var close := clampf((_t - (T_FIRST + T_STEP * float(n))) / T_RUN, 0.0, 1.0)
	if close > 0.0:
		var head := _socket(n - 1).lerp(_socket(0), close)
		_glow_layer.draw_line(_socket(n - 1), head, Color(_glow_of(0), 0.75), 3.0 * s, true)
		_glow_layer.draw_line(_socket(n - 1), head, Color(1, 1, 1, 0.5), 1.2 * s, true)
	# stones glowing, and their signs
	for i in n:
		var lit := _socket_lit(i)
		if lit <= 0.0:
			continue
		var col := _glow_of(i)
		var flare := 1.0 - _k(T_FIRST + T_STEP * i + T_RUN, T_FIRST + T_STEP * i + T_RUN + 0.3)
		_glow_dot(_socket(i), r * (0.25 + 0.18 * flare), Color(col, 0.55 * lit * pulse))
		_glow_dot(_socket(i), r * 0.09, Color(1, 1, 1, (0.3 + 0.5 * flare) * lit))
		_glow_dot(c + _dir(i) * r * 0.765, r * 0.09, Color(col, 0.35 * lit * pulse))
	# spokes: light pouring from every stone into the core
	var spoke := clampf((_t - T_SPOKES) / (T_IGNITE - T_SPOKES), 0.0, 1.0)
	if spoke > 0.0:
		for i in n:
			var p := _socket(i)
			var col := _glow_of(i)
			var head := p.lerp(c, spoke)
			_glow_layer.draw_line(p, head, Color(col, 0.7), 2.5 * s, true)
			if spoke < 1.0:
				_glow_dot(head, r * 0.07, Color(col.lightened(0.5), 0.9))
	# the core ignites: a flare, then a ring of light opening out, then a steady glow
	var ignite := _k(T_IGNITE, T_IGNITE + 0.14)
	if ignite > 0.0:
		var flash := 1.0 - _k(T_IGNITE, T_IGNITE + 0.45)
		_glow_dot(c, r * (0.5 + 1.1 * flash), Color(core_color, (0.45 + 0.5 * flash) * ignite * pulse))
		_glow_dot(c, r * 0.22, Color(1, 1, 1, (0.5 + 0.5 * flash) * ignite))
		var ring := _k(T_IGNITE, T_IGNITE + 0.6)
		if ring < 1.0:
			_glow_layer.draw_arc(c, r * (0.25 + 1.0 * ring), 0.0, TAU, 96, Color(core_color.lightened(0.3), 0.8 * (1.0 - ring)), (6.0 - 4.0 * ring) * s, true)
		# rays of light off the sigil, briefly
		if flash > 0.0:
			for i in 12:
				var ang := TAU * float(i) / 12.0
				var d := Vector2(cos(ang), sin(ang))
				var nn := Vector2(-d.y, d.x)
				var ray_len := r * (0.5 + 0.9 * (1.0 - flash))
				_glow_layer.draw_colored_polygon(PackedVector2Array([c + nn * r * 0.03, c + d * ray_len, c - nn * r * 0.03]), Color(1, 0.9, 0.7, 0.35 * flash))
	# the lock's flash
	var lock := _k(T_LOCK - 0.02, T_LOCK + 0.1) * (1.0 - _k(T_LOCK + 0.1, T_LOCK + 0.35))
	if lock > 0.0:
		_glow_dot(c + Vector2(0, -r * 0.93), r * 0.22, Color(0.75, 0.9, 1.0, 0.8 * lock))


## A faceted quartz (an elongated hexagon cut like the game's quartz icons): dark until lit.
func _draw_quartz(p: Vector2, g: float, stone: Color, lit: float, a: float) -> void:
	var base := stone.darkened(0.78).lerp(stone, lit)
	var pts := PackedVector2Array()
	for k in 6:
		var ang := -PI * 0.5 + TAU * float(k) / 6.0
		pts.append(p + Vector2(cos(ang) * 0.86, sin(ang)) * g)
	draw_colored_polygon(pts, Color(base, a))
	# facets: a lighter top-left face, a darker bottom-right face, the table in the middle
	var inner := PackedVector2Array()
	for k in 6:
		inner.append(p.lerp(pts[k], 0.45))
	draw_colored_polygon(PackedVector2Array([pts[5], pts[0], pts[1], inner[1], inner[0], inner[5]]), Color(base.lightened(0.35), a))
	draw_colored_polygon(PackedVector2Array([pts[2], pts[3], pts[4], inner[4], inner[3], inner[2]]), Color(base.darkened(0.35), a))
	draw_colored_polygon(inner, Color(base.lightened(0.12), a))
	var rim := steel_light if stone.get_luminance() > 0.2 else steel_light.lightened(0.2)
	pts.append(pts[0])
	draw_polyline(pts, Color(rim, (0.55 + 0.35 * lit) * a), 1.4 * _scale(), true)
	draw_circle(p + Vector2(-0.3, -0.42) * g, g * 0.16, Color(1, 1, 1, (0.12 + 0.6 * lit) * a))   # a glint


## The element's sign, drawn in lines (u = half its size).
func _draw_sign(kind: String, p: Vector2, u: float, col: Color, s: float) -> void:
	var w := 1.6 * s
	match kind:
		"earth":   # two mountain peaks on a line
			draw_polyline(PackedVector2Array([p + Vector2(-1.0, 0.7) * u, p + Vector2(-0.35, -0.6) * u, p + Vector2(0.05, 0.1) * u,
				p + Vector2(0.45, -0.9) * u, p + Vector2(1.0, 0.7) * u]), col, w, true)
			draw_line(p + Vector2(-1.1, 0.7) * u, p + Vector2(1.1, 0.7) * u, col, w, true)
		"water":   # a drop
			var drop := PackedVector2Array([p + Vector2(0, -1.0) * u])
			for k in 13:
				var ang := deg_to_rad(-30.0 + 240.0 * float(k) / 12.0)
				drop.append(p + Vector2(cos(ang) * 0.6, 0.35 + sin(ang) * 0.6) * u)
			drop.append(p + Vector2(0, -1.0) * u)
			draw_polyline(drop, col, w, true)
		"fire":    # a flame
			draw_polyline(PackedVector2Array([p + Vector2(0, 1.0) * u, p + Vector2(-0.65, 0.35) * u, p + Vector2(-0.45, -0.3) * u,
				p + Vector2(-0.1, 0.05) * u, p + Vector2(0.05, -1.0) * u, p + Vector2(0.6, -0.15) * u, p + Vector2(0.62, 0.4) * u,
				p + Vector2(0, 1.0) * u]), col, w, true)
		"wind":    # three gusts
			for k in 3:
				var y := (-0.6 + 0.6 * float(k)) * u
				var x0 := (-1.0 + 0.25 * float(k % 2)) * u
				draw_line(p + Vector2(x0, y), p + Vector2(0.45 * u, y), col, w, true)
				draw_arc(p + Vector2(0.45 * u, y - 0.22 * u), 0.22 * u, PI * 0.5, PI * 2.0, 10, col, w, true)
		"time":    # an hourglass
			draw_polyline(PackedVector2Array([p + Vector2(-0.6, -0.9) * u, p + Vector2(0.6, -0.9) * u, p + Vector2(-0.6, 0.9) * u,
				p + Vector2(0.6, 0.9) * u, p + Vector2(-0.6, -0.9) * u]), col, w, true)
		"space":   # a four-pointed star
			var star := PackedVector2Array()
			for k in 9:
				var ang := -PI * 0.5 + TAU * float(k) / 8.0
				var rr := 1.0 if k % 2 == 0 else 0.3
				star.append(p + Vector2(cos(ang), sin(ang)) * rr * u)
			draw_polyline(star, col, w, true)
		"mirage":  # an eye
			draw_arc(p + Vector2(0, 0.75) * u, 1.25 * u, deg_to_rad(-127), deg_to_rad(-53), 12, col, w, true)
			draw_arc(p + Vector2(0, -0.75) * u, 1.25 * u, deg_to_rad(53), deg_to_rad(127), 12, col, w, true)
			draw_circle(p, 0.25 * u, col)


func _glow_dot(at: Vector2, rad: float, color: Color) -> void:
	_glow_layer.draw_texture_rect(_glow, Rect2(at - Vector2(rad, rad), Vector2(rad, rad) * 2.0), false, color)
