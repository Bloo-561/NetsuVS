extends Control
## EX / SUPER CUT-IN (Oct 24 2026; reworked the same day after Under Night In-Birth and Melty Blood)
##
## When a fighter starts an EX move (1 bar) or a super (3 bars) the engine (StanceManager, C#) calls
## MatchSetup.netsu_cut_in(), which emits MatchSetup.cut_in. This node (added by netsu_hud.gd) shows it:
##   EX Craft -> a slanted band opens across her side of the screen with a big close-up of her
##               (actors/<fighter>/Artwork/CutIn_EX.png), behind the fighters, for about half a second,
##               with the EX sound and the move's name.
##   S-Craft  -> the stage turns to dark smoke in her colour (assets/shaders/netsu_super_backdrop.gdshader),
##               a huge picture of her (CutIn_Super.png) fades in behind the fighters, the S-Craft sound
##               plays and the move's name comes up big. The smoke stays until she is out of the super
##               (MatchSetup.super_hold, from the engine).
## The outline around the fighter is the engine (AnimationViewer.SetAura); the dark stage and the burst of
## light at her chest are netsu_super_flash.gd. Her colour: FighterProfile.NetsuAuraColor
## (MatchSetup.side_color). Sounds: assets/audio/sfx/netsu_ex_flash.wav / netsu_super_flash.wav
## (made by tools/fx/make_cutin_sfx.py).
## Three layers: this node draws the names (over the HUD); it puts two more right under the fighters'
## layer: the smoke (a ColorRect with the shader) and the pictures (_draw_back).
## Presentation only: nothing in the match depends on it. Rollback can start a move twice: repeats
## within 0.6 s are ignored.
## Oct 25: no more stall on the first EX move / super of a fight. Both fighters' pictures and the two sounds are
## loaded as the fight is built (the VS screen already loads them in the background: MatchSetup.match_paths),
## and for the fight's first frames (still black) everything is drawn once, invisibly: the pictures, the smoke
## shader and the names' letters at every size they use (_warm). Loading a picture at the first EX took
## 60-100 ms, and the first use of a shader or a big font size costs a little more on top.

const CANVAS := Vector2(1920, 1080)
const BACKDROP_SHADER := "res://assets/shaders/netsu_super_backdrop.gdshader"
const SOUND_EX := "res://assets/audio/sfx/netsu_ex_flash.wav"
const SOUND_SUPER := "res://assets/audio/sfx/netsu_super_flash.wav"

## Where the face is in each fighter's cut-in pictures (pixels of the PNG) and how tall her head is in
## CutIn_EX.png (that sets the close-up's zoom). Key = the fighter's folder under actors/.
## Fighters not listed get a guess from the picture's size.
const ART := {
	"cecilia": {"ex_face": Vector2(1200, 380), "ex_head": 470.0, "super_face": Vector2(552, 205)},
	"flan": {"ex_face": Vector2(1120, 360), "ex_head": 500.0, "super_face": Vector2(330, 300)},
	"leticia": {"ex_face": Vector2(1180, 300), "ex_head": 400.0, "super_face": Vector2(565, 285)},
	"noah": {"ex_face": Vector2(690, 335), "ex_head": 360.0, "super_face": Vector2(500, 205)},
}

@export_group("EX close-up")
@export var ex_time: float = 0.62                       ## seconds the band is up
@export var band_angle: float = -12.0                   ## degrees, left-side fighter (mirrored on the right)
@export var band_center: Vector2 = Vector2(700, 390)    ## the band's middle, left-side fighter
@export var band_thickness: float = 330.0
@export var band_reach: Vector2 = Vector2(-1350, 1150)  ## how far the band runs back / forward from band_center
@export var face_along: float = -270.0                  ## where her face sits along the band
@export var head_fill: float = 1.12                     ## head height / band thickness
@export var band_color: Color = Color(0.02, 0.03, 0.1, 0.94)
@export_group("S-Craft")
@export var super_time: float = 1.3                     ## seconds the big picture and the name stay
@export var smoke_strength: float = 0.94
@export var smoke_in: float = 0.1                       ## seconds to fill the screen
@export var smoke_out: float = 0.45                     ## seconds to clear after the super
@export var smoke_min: float = 0.75                     ## seconds the smoke stays at least
@export var portrait_height: float = 1.75               ## the picture's height / the screen's
@export var portrait_face: Vector2 = Vector2(600, 330)  ## where her face goes, left-side fighter
@export var portrait_alpha: float = 0.9
@export_group("Names")
@export var text_color: Color = Color(1, 1, 1)
@export var outline_color: Color = Color(0.02, 0.03, 0.12, 0.95)
@export_group("Sound")
@export var ex_volume_db: float = -4.0
@export var super_volume_db: float = -2.0

var _active: Array = []    # {side, name, super, left, t, color, ex_tex, super_tex, art}
var _last := {}            # "side:move" -> msec
var _pics := {}
var _hold := [false, false]
var _smoke_side := -1
var _smoke_t := 0.0
var _smoke_level := 0.0
var _smoke_color := Color(0.8, 0.1, 0.2)
var _smoke_left := true
var _smoke: ColorRect
var _smoke_mat: ShaderMaterial
var _back: Control
var _placed := false
var _sfx: AudioStreamPlayer
var _name_font: Font
var _tag_font: Font
var _lines: Array = []     # speed lines in the EX band: [across (0-1), speed, length, phase]
var _sounds := {}          # path -> AudioStream (loaded as the fight starts)
var _warm := 0             # frames of invisible warm-up drawing left (the fight's first, black frames)
var _warm_step := 0
var _warm_art: Array = []  # {"ex": Texture2D, "super": Texture2D, "art": {}} per fighter

## Letters the move names can use: drawn once at every size so their glyphs are ready (_warm).
const WARM_LETTERS := "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -'!?.,&:"
## Sizes of an S-Craft's name: 96, or smaller in steps of 8 when the name is long (_draw_super_name).
const SUPER_SIZES := [96, 88, 80, 72, 64, 56, 48, 40]


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	size = CANVAS
	_name_font = NetsuUI.serif(700, 2)
	_tag_font = NetsuUI.sans(6)
	if MatchSetup.has_signal("cut_in"):
		MatchSetup.cut_in.connect(_on_cut_in)
	if MatchSetup.has_signal("super_hold"):
		MatchSetup.super_hold.connect(_on_super_hold)
	_sfx = AudioStreamPlayer.new()
	_sfx.bus = &"SFX"
	add_child(_sfx)
	var rng := RandomNumberGenerator.new()
	rng.seed = 24
	for i in 14:
		_lines.append([rng.randf_range(0.06, 0.94), rng.randf_range(1800.0, 3200.0), rng.randf_range(180.0, 520.0), rng.randf() * 5000.0])
	_back = Control.new()
	_back.name = "NetsuCutInBack"
	_back.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_back.size = CANVAS
	_back.draw.connect(_draw_back)
	_smoke = ColorRect.new()
	_smoke.name = "NetsuSuperSmoke"
	_smoke.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_smoke.visible = false
	if ResourceLoader.exists(BACKDROP_SHADER):
		_smoke_mat = ShaderMaterial.new()
		_smoke_mat.shader = load(BACKDROP_SHADER)
		_smoke.material = _smoke_mat
	else:
		_smoke.color = Color(0.01, 0.0, 0.03)
	_preload()
	_warm = SUPER_SIZES.size() + 2


## Both fighters' cut-in pictures and the two sounds, now (the fight is being built, the screen is black).
func _preload() -> void:
	for path in [SOUND_EX, SOUND_SUPER]:
		if ResourceLoader.exists(path):
			_sounds[path] = load(path)
	var cfg = MatchSetup.settings() if MatchSetup.has_method("settings") else null
	if cfg == null:
		return
	for side in 2:
		var index := int(cfg.P1SelectedCharacter if side == 0 else cfg.P2SelectedCharacter)
		if index < 0 or index >= MatchSetup.fighter_count():
			continue
		var folder := str(MatchSetup.fighter_profile(index).ShortName).to_lower()
		var ex := _pic("res://actors/%s/Artwork/CutIn_EX.png" % folder)
		var sup := _pic("res://actors/%s/Artwork/CutIn_Super.png" % folder)
		if ex or sup:
			_warm_art.append({"ex": ex if ex else sup, "super": sup if sup else ex, "art": ART.get(folder, {})})


## One frame of the warm-up: the smoke, both pictures and the letters drawn nearly transparent, under the
## fight's black screen (these layers are all below the fade).
func _warm_tick() -> void:
	if not _placed:
		_place()
	_warm -= 1
	var on := _warm > 0
	modulate.a = 0.01 if on else 1.0
	_back.modulate.a = 0.01 if on else 1.0
	if on:
		_smoke.visible = true
		_smoke.position = Vector2.ZERO
		_smoke.size = Vector2(64, 64)
		if _smoke_mat:
			_smoke_mat.set_shader_parameter("amount", 0.0)
	elif _smoke_side < 0:
		_smoke.visible = false
	queue_redraw()
	_back.queue_redraw()


func _end_warm() -> void:
	if _warm > 0:
		_warm = 1
		_warm_tick()


## The smoke and the pictures go under the fighters' layer (ViewportContainer) of the battle's CanvasLayer,
## above the stage (and above netsu_super_flash.gd's dark rect).
func _place() -> void:
	_placed = true
	var hud := get_parent()
	var root := hud.get_parent() if hud else null
	var container: Node = root.get_node_or_null("ViewportContainer") if root else null
	if container == null:
		add_child(_smoke)
		add_child(_back)
		return
	root.add_child(_smoke)
	root.add_child(_back)
	root.move_child(_smoke, container.get_index())
	root.move_child(_back, container.get_index())


func _on_cut_in(side: int, fighter: String, move_name: String, is_super: bool, from_left: bool) -> void:
	var key := "%d:%s" % [side, move_name]
	var now := Time.get_ticks_msec()
	if int(_last.get(key, -100000)) > now - 600:
		return
	_last[key] = now
	_end_warm()
	if not _placed:
		_place()
	var folder := fighter.to_lower()
	var ex_tex := _pic("res://actors/%s/Artwork/CutIn_EX.png" % folder)
	var super_tex := _pic("res://actors/%s/Artwork/CutIn_Super.png" % folder)
	var color: Color = MatchSetup.side_color(side) if MatchSetup.has_method("side_color") else (Color(0.3, 0.62, 1.0) if side == 0 else Color(1.0, 0.25, 0.38))
	_active = _active.filter(func(c): return c["side"] != side)
	_active.append({"side": side, "name": move_name, "super": is_super, "left": from_left, "t": 0.0, "color": color,
		"ex_tex": ex_tex if ex_tex else super_tex, "super_tex": super_tex if super_tex else ex_tex, "art": ART.get(folder, {})})
	if is_super:
		_smoke_side = side
		_smoke_t = 0.0
		_smoke_color = color
		_smoke_left = from_left
	var path := SOUND_SUPER if is_super else SOUND_EX
	if not _sounds.has(path) and ResourceLoader.exists(path):
		_sounds[path] = load(path)
	if _sounds.get(path):
		_sfx.stream = _sounds[path]
		_sfx.volume_db = super_volume_db if is_super else ex_volume_db
		_sfx.play()


func _on_super_hold(side: int, on: bool) -> void:
	if side >= 0 and side < 2:
		_hold[side] = on


func _pic(path: String) -> Texture2D:
	if not _pics.has(path):
		_pics[path] = load(path) if ResourceLoader.exists(path) else null
	return _pics[path]


func _process(delta: float) -> void:
	if _warm > 0:
		_warm_tick()
	if not _placed:
		return
	var hud := get_parent() as Control
	if hud and _back.get_parent() != self:
		_back.scale = hud.scale
		_back.position = hud.position
	_update_smoke(delta)
	if _active.is_empty():
		return
	for c in _active:
		c["t"] += delta
	_active = _active.filter(func(c): return c["t"] < (super_time if c["super"] else ex_time))
	queue_redraw()
	_back.queue_redraw()


func _update_smoke(delta: float) -> void:
	if _smoke_side < 0:
		return
	_smoke_t += delta
	var up: bool = _smoke_t < 8.0 and (_smoke_t < smoke_min or _hold[_smoke_side])
	var target := smoke_strength if up else 0.0
	var rate := smoke_strength / maxf(smoke_in if up else smoke_out, 0.001)
	_smoke_level = move_toward(_smoke_level, target, rate * delta)
	if not up and _smoke_level <= 0.0:
		_smoke_side = -1
	var vs := get_viewport_rect().size
	if _smoke.get_parent() != self:
		_smoke.position = Vector2.ZERO
		_smoke.size = vs
	else:
		_smoke.position = Vector2.ZERO
		_smoke.size = CANVAS
	_smoke.visible = _smoke_level > 0.001
	if _smoke_mat:
		_smoke_mat.set_shader_parameter("amount", _smoke_level)
		_smoke_mat.set_shader_parameter("seconds", _smoke_t)
		_smoke_mat.set_shader_parameter("smoke_color", _smoke_color)
		_smoke_mat.set_shader_parameter("from_left", 1.0 if _smoke_left else -1.0)
		_smoke_mat.set_shader_parameter("aspect", vs.x / maxf(vs.y, 1.0))
	else:
		_smoke.color = Color(0.01, 0.0, 0.03, _smoke_level)


# --- Drawing ---------------------------------------------------------------------------------

func _draw() -> void:
	if _warm > 0:
		_draw_warm_text()
	for c in _active:
		if c["super"]:
			_draw_super_name(c)
		else:
			_draw_ex_name(c)


func _draw_back() -> void:
	if _warm > 0:
		for w in _warm_art:
			var fake := {"side": 0, "name": "", "super": false, "left": true, "t": 0.2, "color": Color.WHITE,
				"ex_tex": w["ex"], "super_tex": w["super"], "art": w["art"]}
			_draw_band(fake)
			fake["left"] = false
			_draw_portrait(fake)
	for c in _active:
		if c["super"]:
			_draw_portrait(c)
		else:
			_draw_band(c)


## 0 -> 1 with an ease-out over `sec` from the start
func _ease_in(t: float, sec: float) -> float:
	return 1.0 - pow(1.0 - clampf(t / sec, 0.0, 1.0), 3.0)


## 1 -> 0 over the last `sec` of `total`
func _ease_out(t: float, total: float, sec: float) -> float:
	return clampf((total - t) / sec, 0.0, 1.0)


## A point on the EX band (u along it, v across it) on the 1920x1080 canvas, mirrored for the right side.
func _bp(c: Dictionary, u: float, v: float) -> Vector2:
	var a := deg_to_rad(band_angle)
	var p := band_center + Vector2(cos(a), sin(a)) * u + Vector2(-sin(a), cos(a)) * v
	if not c["left"]:
		p.x = CANVAS.x - p.x
	return p


## A quad on the band: u0..u1 along it, v0..v1 across, colours per corner (u0v0, u1v0, u1v1, u0v1).
func _band_quad(c: Dictionary, u0: float, u1: float, v0: float, v1: float, cols: PackedColorArray,
		tex: Texture2D = null, uvs: PackedVector2Array = PackedVector2Array()) -> void:
	if u1 <= u0 or v1 <= v0:
		return
	var pts := PackedVector2Array([_bp(c, u0, v0), _bp(c, u1, v0), _bp(c, u1, v1), _bp(c, u0, v1)])
	if tex:
		_back.draw_primitive(pts, cols, uvs, tex)
	else:
		_back.draw_primitive(pts, cols, PackedVector2Array())


func _draw_band(c: Dictionary) -> void:
	var t: float = c["t"]
	var k_in := _ease_in(t, 0.09)
	var k_out := _ease_out(t, ex_time, 0.16)
	var alpha := k_out
	var acc: Color = c["color"]
	var shift := -(1.0 - k_in) * 900.0 + (1.0 - k_out) * 420.0
	var half := band_thickness * 0.5 * (0.2 + 0.8 * k_in) * (0.45 + 0.55 * k_out)
	var u0 := band_reach.x + shift
	var u1 := band_reach.y + shift
	var u_fade := u1 - 420.0
	var bg := Color(band_color, band_color.a * alpha)
	var clear := Color(band_color, 0.0)
	# the band
	_band_quad(c, u0, u_fade, -half, half, PackedColorArray([bg, bg, bg, bg]))
	_band_quad(c, u_fade, u1, -half, half, PackedColorArray([bg, clear, clear, bg]))
	# her colour glowing along the middle
	var glow := Color(acc, 0.34 * alpha)
	var none := Color(acc, 0.0)
	_band_quad(c, u0, u_fade, -half, 0.0, PackedColorArray([none, none, glow, glow]))
	_band_quad(c, u0, u_fade, 0.0, half, PackedColorArray([glow, glow, none, none]))
	# speed lines streaming back past her
	var span := u1 - u0
	for l in _lines:
		var v: float = (float(l[0]) - 0.5) * 2.0 * half
		var length: float = l[2]
		var pos: float = u1 - fmod(float(l[3]) + t * float(l[1]), span + length)
		var a0 := maxf(pos, u0)
		var a1 := minf(pos + length, u1)
		if a1 > a0:
			_back.draw_line(_bp(c, a0, v), _bp(c, a1, v), Color(acc.lightened(0.4), 0.22 * alpha), 2.0)
	# the close-up, cut to the band
	var tex: Texture2D = c["ex_tex"]
	if tex:
		var ts := tex.get_size()
		var art: Dictionary = c["art"]
		var face: Vector2 = art.get("ex_face", Vector2(ts.x * 0.68, ts.y * 0.35))
		var head: float = art.get("ex_head", ts.y * 0.45)
		var s := band_thickness * head_fill / head * (1.0 + 0.05 * t)
		var fu := face_along + shift + 70.0 * t
		var fv := band_thickness * 0.04
		var au0 := fu - face.x * s
		var av0 := fv - face.y * s
		var au1 := au0 + ts.x * s
		var av1 := av0 + ts.y * s
		var cu0 := maxf(au0, u0)
		var cu1 := minf(au1, u_fade + 200.0)
		var cv0 := maxf(av0, -half)
		var cv1 := minf(av1, half)
		if cu1 > cu0 and cv1 > cv0:
			var split := maxf(cu0, cu1 - 240.0)
			var white := Color(1, 1, 1, alpha)
			var gone := Color(1, 1, 1, 0.0)
			_band_quad(c, cu0, split, cv0, cv1, PackedColorArray([white, white, white, white]), tex,
				_art_uvs(cu0, split, cv0, cv1, au0, av0, s, ts))
			_band_quad(c, split, cu1, cv0, cv1, PackedColorArray([white, gone, gone, white]), tex,
				_art_uvs(split, cu1, cv0, cv1, au0, av0, s, ts))
	# white flash as it opens
	if t < 0.13:
		var f := Color(1, 1, 1, 0.8 * (1.0 - t / 0.13))
		_band_quad(c, u0, u1, -half, half, PackedColorArray([f, Color(1, 1, 1, 0), Color(1, 1, 1, 0), f]))
	# edges: her colour with a white core, fading out at the far end
	for v in [-half, half]:
		var pts := PackedVector2Array([_bp(c, u0, v), _bp(c, u_fade, v), _bp(c, u1, v)])
		_back.draw_polyline_colors(pts, PackedColorArray([Color(acc, 0.95 * alpha), Color(acc, 0.95 * alpha), Color(acc, 0.0)]), 6.0, true)
		_back.draw_polyline_colors(pts, PackedColorArray([Color(1, 1, 1, 0.85 * alpha), Color(1, 1, 1, 0.85 * alpha), Color(1, 1, 1, 0.0)]), 2.0, true)
	# two four-point stars on the top edge
	for i in 2:
		var p := _bp(c, face_along + shift + 420.0 + i * 160.0, -half)
		_star(_back, p, 15.0 - i * 5.0, Color(1, 1, 1, alpha))


## Texture coordinates (0-1) of a band rect for a picture whose top-left is at (au0, av0), scale s.
func _art_uvs(u0: float, u1: float, v0: float, v1: float, au0: float, av0: float, s: float, ts: Vector2) -> PackedVector2Array:
	var a := Vector2((u0 - au0) / s / ts.x, (v0 - av0) / s / ts.y)
	var b := Vector2((u1 - au0) / s / ts.x, (v1 - av0) / s / ts.y)
	return PackedVector2Array([Vector2(a.x, a.y), Vector2(b.x, a.y), Vector2(b.x, b.y), Vector2(a.x, b.y)])


func _draw_portrait(c: Dictionary) -> void:
	var tex: Texture2D = c["super_tex"]
	if tex == null:
		return
	var t: float = c["t"]
	var k_in := _ease_in(t, 0.16)
	var k_out := _ease_out(t, super_time, 0.4)
	var alpha := portrait_alpha * minf(1.0, t / 0.08) * k_out
	var ts := tex.get_size()
	var art: Dictionary = c["art"]
	var face: Vector2 = art.get("super_face", Vector2(ts.x * 0.5, ts.y * 0.15))
	var s := portrait_height * CANVAS.y / ts.y * (1.07 - 0.07 * k_in + 0.025 * t)
	var left: bool = c["left"]
	var dir := 1.0 if left else -1.0
	var fx := portrait_face.x if left else CANVAS.x - portrait_face.x
	fx -= (1.0 - k_in) * 240.0 * dir
	var x0 := fx - (face.x * s if left else (ts.x - face.x) * s)
	var y0 := portrait_face.y - face.y * s
	var w := ts.x * s
	var h := ts.y * s
	# the picture (mirrored on the right so she faces the middle), fading out towards the bottom
	var y_fade := y0 + h * 0.42
	var on := Color(1, 1, 1, alpha)
	var off := Color(1, 1, 1, 0.0)
	var ua := 0.0 if left else 1.0
	var ub := 1.0 if left else 0.0
	var vf := (y_fade - y0) / h
	_back.draw_primitive(PackedVector2Array([Vector2(x0, y0), Vector2(x0 + w, y0), Vector2(x0 + w, y_fade), Vector2(x0, y_fade)]),
		PackedColorArray([on, on, on, on]), PackedVector2Array([Vector2(ua, 0), Vector2(ub, 0), Vector2(ub, vf), Vector2(ua, vf)]), tex)
	var y_end := minf(y0 + h, CANVAS.y + 40.0)
	var ve := (y_end - y0) / h
	_back.draw_primitive(PackedVector2Array([Vector2(x0, y_fade), Vector2(x0 + w, y_fade), Vector2(x0 + w, y_end), Vector2(x0, y_end)]),
		PackedColorArray([on, on, off, off]), PackedVector2Array([Vector2(ua, vf), Vector2(ub, vf), Vector2(ub, ve), Vector2(ua, ve)]), tex)
	# a sweep of light across her as she comes in
	if t < 0.3:
		var k := t / 0.3
		var sx := lerpf(x0 - 300.0, x0 + w + 300.0, k) if left else lerpf(x0 + w + 300.0, x0 - 300.0, k)
		var lw := 120.0
		var a := 0.55 * (1.0 - k)
		var col := Color(1, 1, 1, a)
		var cl := Color(1, 1, 1, 0.0)
		_back.draw_primitive(PackedVector2Array([Vector2(sx - lw + 260.0 * dir, -20), Vector2(sx + 260.0 * dir, -20),
			Vector2(sx - 260.0 * dir, CANVAS.y + 20), Vector2(sx - lw - 260.0 * dir, CANVAS.y + 20)]),
			PackedColorArray([cl, col, col, cl]), PackedVector2Array())


func _draw_ex_name(c: Dictionary) -> void:
	var t: float = c["t"]
	var k_in := _ease_in(t, 0.12)
	var k_out := _ease_out(t, ex_time, 0.16)
	var alpha := minf(1.0, t / 0.06) * k_out
	var shift := -(1.0 - k_in) * 300.0 + (1.0 - k_out) * 420.0
	var acc: Color = c["color"]
	var half := band_thickness * 0.5
	var left: bool = c["left"]
	var label: String = String(c["name"]).to_upper()
	var size_px := 64
	var tw := _name_font.get_string_size(label, HORIZONTAL_ALIGNMENT_LEFT, -1, size_px).x
	var u := 140.0 + shift
	if not left:
		u += tw   # mirrored band: the text still runs left to right, so start it further along
	var base := _bp(c, u, half - 58.0)
	var ang := deg_to_rad(band_angle) * (1.0 if left else -1.0)
	draw_set_transform(base, ang)
	_text(_tag_font, Vector2(4, -72), "EX CRAFT", 28, Color(acc.lightened(0.45), alpha), 4)
	_text(_name_font, Vector2.ZERO, label, size_px, Color(text_color, alpha), 8)
	draw_line(Vector2(0, 16), Vector2(tw, 16), Color(acc, 0.9 * alpha), 3.0)
	draw_set_transform(Vector2.ZERO, 0.0)


func _draw_super_name(c: Dictionary) -> void:
	var t: float = c["t"]
	var k_in := _ease_in(t, 0.18)
	var k_out := _ease_out(t, super_time, 0.3)
	var alpha := minf(1.0, t / 0.1) * k_out
	var left: bool = c["left"]
	var dir := 1.0 if left else -1.0
	var acc: Color = c["color"]
	var label: String = String(c["name"]).to_upper()
	var size_px := 96
	var room := CANVAS.x * 0.55
	var tw := _name_font.get_string_size(label, HORIZONTAL_ALIGNMENT_LEFT, -1, size_px).x
	if tw > room:
		# a long name: smaller, in steps of 8 (the sizes the fight's first frames warm up: SUPER_SIZES)
		size_px = maxi(40, int(size_px * room / tw) / 8 * 8)
		tw = _name_font.get_string_size(label, HORIZONTAL_ALIGNMENT_LEFT, -1, size_px).x
	# on the other side from her picture, above the fighters
	var tx := (CANVAS.x - 130.0 - tw) if left else 130.0
	tx += (1.0 - k_in) * 380.0 * dir
	var ty := CANVAS.y * 0.36
	_text(_tag_font, Vector2(tx, ty - 104), "S-CRAFT", 34, Color(acc.lightened(0.4), alpha), 5)
	_text(_name_font, Vector2(tx, ty), label, size_px, Color(text_color, alpha), 10)
	var lx0 := tx - 40.0 if left else tx
	var lx1 := tx + tw if left else tx + tw + 40.0
	draw_line(Vector2(lx0, ty + 26), Vector2(lx1, ty + 26), Color(acc, 0.9 * alpha), 4.0)
	draw_line(Vector2(lx0, ty + 26), Vector2(lx1, ty + 26), Color(1, 1, 1, 0.6 * alpha), 1.5)
	_star(self, Vector2(lx0 if left else lx1, ty + 26), 16.0, Color(1, 1, 1, alpha))


## The warm-up's letters: the tags and the EX names' size every frame, one S-Craft name size per frame.
func _draw_warm_text() -> void:
	var c := Color(1, 1, 1, 0.01)
	_text(_tag_font, Vector2(20, 100), WARM_LETTERS, 28, c, 4)
	_text(_tag_font, Vector2(20, 160), WARM_LETTERS, 34, c, 5)
	_text(_name_font, Vector2(20, 260), WARM_LETTERS, 64, c, 8)
	_text(_name_font, Vector2(20, 400), WARM_LETTERS, SUPER_SIZES[_warm_step % SUPER_SIZES.size()], c, 10)
	_warm_step += 1


## The four-point star of the game's UI (NetsuUI.sparkle), drawn on `on` (this node or the back layer).
func _star(on: CanvasItem, at: Vector2, r: float, color: Color) -> void:
	var pts := PackedVector2Array()
	for i in 8:
		var a := PI * 0.25 * i
		var rr := r if i % 2 == 0 else r * 0.26
		pts.append(at + Vector2(cos(a), sin(a)) * rr)
	on.draw_colored_polygon(pts, color)


func _text(font: Font, pos: Vector2, text: String, size_px: int, color: Color, outline: int) -> void:
	if outline > 0:
		draw_string_outline(font, pos, text, HORIZONTAL_ALIGNMENT_LEFT, -1, size_px, outline, Color(outline_color, outline_color.a * color.a))
	draw_string(font, pos, text, HORIZONTAL_ALIGNMENT_LEFT, -1, size_px, color)
