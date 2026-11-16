extends Control
## NETSU LINK BREAK: the Unbalance cut-in (Nov 8 2026; second look Nov 9), after Trails of Cold Steel's Unbalance -> Link
## Attack.
##
## When a Link Break connects, the engine stops the fight for NetsuLink.BreakPauseFrames (48 frames = 0.8 s) and calls
## MatchSetup.netsu_link_break(side, pos, leader). Over the fight AND the HUD (netsu_hud.gd puts this node at the end of
## the battle's CanvasLayer), in 0.8 s:
##   0.00  impact: a short white pop, a ring of light, the brush kanji 崩 ("kuzushi": Unbalance) slams onto the opponent
##         over a tapered ink stroke, UNBALANCED under it;
##   0.16  the screen is covered like Cold Steel's Link Attack: a top band (who leads: the partner's card picture, or the
##         fighter's S-Craft picture for C+D) sweeps in from the left, a bottom band (the fighter's EX close-up) from the
##         right, a dark middle band opens between them with LINK BREAK!; the kanji flies from the opponent into it (one
##         kanji, never two);
##   0.67  the bands sweep out the other way and the fight is back.
## Presentation only (nothing here touches the match). The kanji picture is assets/ui/link/kanji_kuzushi.png (made from
## Noto Serif CJK Bold, OFL).

const CANVAS := Vector2(1920, 1080)
const KANJI := "res://assets/ui/link/kanji_kuzushi.png"
const SOUND := "res://assets/audio/sfx/netsu_super_flash.wav"
const TITLE_FONT := "res://assets/fonts/Exo2-BoldItalic.ttf"
const TAG_FONT := "res://assets/fonts/Rajdhani-Bold.ttf"

## Where the face is in each fighter's cut-in pictures (same numbers as netsu_cut_in.gd's ART).
const ART := {
	"cecilia": {"ex_face": Vector2(1200, 380), "ex_head": 470.0, "super_face": Vector2(552, 205)},
	"flan": {"ex_face": Vector2(1120, 360), "ex_head": 500.0, "super_face": Vector2(330, 300)},
	"leticia": {"ex_face": Vector2(1180, 300), "ex_head": 400.0, "super_face": Vector2(565, 285)},
	"noah": {"ex_face": Vector2(690, 335), "ex_head": 360.0, "super_face": Vector2(500, 205)},
}

@export_group("Timing (seconds)")
@export var total_time: float = 0.8            ## the engine's pause is 48 frames
@export var pop_time: float = 0.06             ## the white pop
@export var stamp_in: float = 0.07             ## the kanji slamming down
@export var bands_at: float = 0.16
@export var bands_in: float = 0.1
@export var bands_out: float = 0.13            ## at the end
@export_group("Look")
@export var band_angle: float = -6.0           ## degrees
@export var band_thickness: float = 420.0
@export var middle_thickness: float = 150.0
@export var stamp_size: float = 300.0
@export var band_dark: Color = Color(0.16, 0.01, 0.03)
@export var band_light: Color = Color(0.62, 0.05, 0.1)
@export var middle_color: Color = Color(0.29, 0.3, 0.33, 0.97)   ## Cold Steel's grey: the black kanji reads on it
@export var cover_dim: float = 0.72            ## how dark the screen gets around the bands
@export var volume_db: float = -3.0

var _fx := {}
var _kanji: Texture2D
var _title_font: Font
var _tag_font: Font
var _sfx: AudioStreamPlayer
var _container: SubViewportContainer
var _viewport: SubViewport
var _camera: Camera3D
var _lines: Array = []   # speed lines in the middle band: [v (-0.5..0.5 of its height), speed, length, phase]


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	size = CANVAS
	if ResourceLoader.exists(KANJI):
		_kanji = load(KANJI)
	_title_font = load(TITLE_FONT) if ResourceLoader.exists(TITLE_FONT) else NetsuUI.serif(700, 2)
	_tag_font = load(TAG_FONT) if ResourceLoader.exists(TAG_FONT) else NetsuUI.sans(6)
	_sfx = AudioStreamPlayer.new()
	_sfx.bus = &"SFX"
	add_child(_sfx)
	var rng := RandomNumberGenerator.new()
	rng.seed = 51
	for i in 16:
		_lines.append([rng.randf_range(-0.42, 0.42), rng.randf_range(2600.0, 4200.0), rng.randf_range(160.0, 460.0), rng.randf() * 4000.0])
	if MatchSetup.has_signal("link_break"):
		MatchSetup.link_break.connect(_on_break)
	_find_camera.call_deferred()


func _find_camera() -> void:
	var node := get_parent()
	for i in 3:
		if node == null:
			return
		_container = node.get_node_or_null("ViewportContainer") as SubViewportContainer
		if _container:
			break
		node = node.get_parent()
	if _container:
		_viewport = _container.get_node_or_null("Viewport_Foreground") as SubViewport
		if _viewport:
			_camera = _viewport.get_node_or_null("CharacterCamera") as Camera3D


## A point of the fight (metres) on this layer (like netsu_super_flash.gd).
func _to_screen(world: Vector3) -> Vector2:
	if _camera == null or _viewport == null or _container == null:
		return CANVAS * 0.5
	var p := _camera.unproject_position(world)
	var vs := Vector2(_viewport.size)
	if vs.x <= 0.0 or vs.y <= 0.0:
		return CANVAS * 0.5
	var r := _container.get_global_rect()
	var g := r.position + p / vs * r.size
	return get_global_transform().affine_inverse() * g


func _on_break(side: int, pos: Vector3, leader: int) -> void:
	var cfg = MatchSetup.settings()
	var folder := ""
	var fighter_name := ""
	if cfg != null:
		var index := int(cfg.P1SelectedCharacter if side == 0 else cfg.P2SelectedCharacter)
		if index >= 0 and index < MatchSetup.fighter_count():
			var profile = MatchSetup.fighter_profile(index)
			folder = str(profile.ShortName).to_lower()
			fighter_name = str(profile.ShortName)
	var art: Dictionary = ART.get(folder, {})
	var ex_tex := _pic("res://actors/%s/Artwork/CutIn_EX.png" % folder)
	var super_tex := _pic("res://actors/%s/Artwork/CutIn_Super.png" % folder)
	if ex_tex == null:
		ex_tex = super_tex
	if super_tex == null:
		super_tex = ex_tex
	# bottom band: the fighter's EX close-up
	var bottom := {"tex": ex_tex, "face": Vector2(art.get("ex_face", _middle_of(ex_tex))), "head": float(art.get("ex_head", _head_of(ex_tex)))}
	# top band: who leads the Break
	var top := {}
	var leader_name := fighter_name
	if leader >= 2:
		var a := MatchSetup.assist_for_side(side) if leader == 2 else MatchSetup.assist2_for_side(side)
		var icon := MatchSetup.assist_icon(a)
		leader_name = MatchSetup.assist_name(a)
		if icon:
			top = {"tex": icon, "face": Vector2(icon.get_size()) * Vector2(0.5, 0.4), "head": icon.get_size().y * 0.5}
	if top.is_empty():
		top = {"tex": super_tex, "face": Vector2(art.get("super_face", _middle_of(super_tex))), "head": _head_of(super_tex)}
	var input := "C+D" if leader <= 1 else ("D+S%d" % (leader - 1))
	_fx = {"side": side, "t": 0.0, "at": _to_screen(pos), "top": top, "bottom": bottom,
		"color": MatchSetup.side_color(side), "who": leader_name.to_upper(), "input": input}
	if ResourceLoader.exists(SOUND):
		_sfx.stream = load(SOUND)
		_sfx.volume_db = volume_db
		_sfx.play()
	queue_redraw()


func _pic(path: String) -> Texture2D:
	return load(path) if path != "" and ResourceLoader.exists(path) else null


func _middle_of(tex: Texture2D) -> Vector2:
	return Vector2(tex.get_size()) * Vector2(0.5, 0.3) if tex else Vector2.ZERO


func _head_of(tex: Texture2D) -> float:
	return tex.get_size().y * 0.22 if tex else 100.0


func _process(delta: float) -> void:
	if _fx.is_empty():
		return
	_fx["t"] = float(_fx["t"]) + delta
	if float(_fx["t"]) > total_time:
		_fx = {}
	queue_redraw()


# --- Helpers ------------------------------------------------------------------------------------------

static func _ease_out(x: float) -> float:
	x = clampf(x, 0.0, 1.0)
	return 1.0 - pow(1.0 - x, 3.0)


static func _ease_back(x: float) -> float:
	x = clampf(x, 0.0, 1.0)
	var c := 1.9
	return 1.0 + (c + 1.0) * pow(x - 1.0, 3.0) + c * pow(x - 1.0, 2.0)


## A point of a band: `u` along it, `v` across it (band space, (0, 0) = (960, center_y) + slide).
func _bp(center_y: float, slide: float, u: float, v: float) -> Vector2:
	var a := deg_to_rad(band_angle)
	var dir := Vector2(cos(a), sin(a))
	var nrm := Vector2(-dir.y, dir.x)
	return Vector2(CANVAS.x * 0.5 + slide, center_y) + dir * u + nrm * v


func _band(center_y: float, thick: float, slide: float, u0: float = -1700.0, u1: float = 1700.0) -> PackedVector2Array:
	var h := thick * 0.5
	return PackedVector2Array([_bp(center_y, slide, u0, -h), _bp(center_y, slide, u1, -h), _bp(center_y, slide, u1, h), _bp(center_y, slide, u0, h)])


## A band with a vertical gradient (dark at the edges, light in the middle), as two strips.
func _band_fill(center_y: float, thick: float, slide: float) -> void:
	var h := thick * 0.5
	var top := PackedVector2Array([_bp(center_y, slide, -1700.0, -h), _bp(center_y, slide, 1700.0, -h), _bp(center_y, slide, 1700.0, 0.0), _bp(center_y, slide, -1700.0, 0.0)])
	var bot := PackedVector2Array([_bp(center_y, slide, -1700.0, 0.0), _bp(center_y, slide, 1700.0, 0.0), _bp(center_y, slide, 1700.0, h), _bp(center_y, slide, -1700.0, h)])
	draw_polygon(top, PackedColorArray([band_dark, band_dark, band_light, band_light]))
	draw_polygon(bot, PackedColorArray([band_light, band_light, band_dark, band_dark]))


## A picture inside a polygon: its eyes sit on `anchor`, zoomed so the head is about the band's height.
func _face_poly(poly: PackedVector2Array, pic: Dictionary, anchor: Vector2, thick: float) -> void:
	var tex: Texture2D = pic.get("tex")
	if tex == null:
		return
	var ts := Vector2(tex.get_size())
	var head := float(pic.get("head", 100.0))
	var k := head / (thick * 1.1)   # picture pixels per screen pixel
	var face: Vector2 = pic.get("face", ts * 0.5)
	face.y -= head * 0.1             # the eyes, a little above the face's middle
	var uvs := PackedVector2Array()
	for q in poly:
		uvs.append((face + (q - anchor) * k) / ts)
	draw_polygon(poly, PackedColorArray([Color.WHITE]), uvs, tex)


func _line(a: Vector2, b: Vector2, color: Color, width: float) -> void:
	draw_line(a, b, color, width, true)


func _label(font: Font, pos: Vector2, text: String, px: int, color: Color, outline: int) -> void:
	if font == null:
		return
	if outline > 0:
		draw_string_outline(font, pos, text, HORIZONTAL_ALIGNMENT_LEFT, -1, px, outline, Color(0.0, 0.0, 0.02, color.a * 0.9))
	draw_string(font, pos, text, HORIZONTAL_ALIGNMENT_LEFT, -1, px, color)


func _width(font: Font, text: String, px: int) -> float:
	return font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, px).x if font else 0.0


## A tapered ink stroke (pointed ends, thick middle, ragged edge) from a to b.
func _ink_stroke(a: Vector2, b: Vector2, width: float, color: Color) -> void:
	var dir := b - a
	var n := Vector2(-dir.y, dir.x).normalized()
	var pts := PackedVector2Array()
	var steps := 14
	for i in steps + 1:
		var s := float(i) / steps
		var w := width * sin(s * PI) * (0.82 + 0.18 * sin(s * 37.0))
		pts.append(a + dir * s + n * w * 0.5)
	for i in range(steps, -1, -1):
		var s := float(i) / steps
		var w := width * sin(s * PI) * (0.85 + 0.15 * cos(s * 29.0))
		pts.append(a + dir * s - n * w * 0.5)
	draw_colored_polygon(pts, color)


# --- Drawing ------------------------------------------------------------------------------------------

func _draw() -> void:
	if _fx.is_empty():
		return
	var t := float(_fx["t"])
	var side_color: Color = _fx["color"]
	var at: Vector2 = _fx["at"]
	# the bands: in from bands_at, out over the last bands_out
	var cin := _ease_out((t - bands_at) / bands_in)
	var cout := _ease_out((t - (total_time - bands_out)) / bands_out)
	var cover := cin * (1.0 - cout)
	# 1. impact: white pop, rings of light on the opponent
	if t < pop_time:
		draw_rect(Rect2(Vector2.ZERO, CANVAS), Color(1, 1, 1, 0.55 * (1.0 - t / pop_time)))
	if t < bands_at + 0.04:
		var rr := _ease_out(t / 0.18)
		var ra := clampf(1.0 - t / (bands_at + 0.04), 0.0, 1.0)
		draw_arc(at, 60.0 + 280.0 * rr, 0.0, TAU, 64, Color(side_color.lightened(0.5), ra), 10.0 * (1.0 - rr) + 2.0, true)
		draw_arc(at, 30.0 + 180.0 * rr, 0.0, TAU, 48, Color(1, 1, 1, ra), 4.0, true)
	# 2. the Link Attack bands (they cover the whole screen)
	if cover > 0.0:
		draw_rect(Rect2(Vector2.ZERO, CANVAS), Color(0, 0, 0, cover_dim * cover))
		var gap := (band_thickness + middle_thickness) * 0.5
		var top_y := CANVAS.y * 0.5 - gap
		var bot_y := CANVAS.y * 0.5 + gap
		var drift := (t - bands_at) * 40.0   # a slow push while they're up
		var top_slide := -(1.0 - cin) * CANVAS.x * 1.2 + cout * CANVAS.x * 1.2
		var bot_slide := (1.0 - cin) * CANVAS.x * 1.2 - cout * CANVAS.x * 1.2
		# top band: who leads (eyes on the left half)
		_band_fill(top_y, band_thickness, top_slide)
		var top_win := _band(top_y, band_thickness, top_slide, -1100.0, 260.0)
		_face_poly(top_win, _fx["top"], _bp(top_y, top_slide + drift, -420.0, 0.0), band_thickness)
		_line(_bp(top_y, top_slide, -1700, band_thickness * 0.5), _bp(top_y, top_slide, 1700, band_thickness * 0.5), Color(1, 1, 1, 0.9), 3.0)
		# bottom band: the fighter (eyes on the right half)
		_band_fill(bot_y, band_thickness, bot_slide)
		var bot_win := _band(bot_y, band_thickness, bot_slide, -260.0, 1100.0)
		_face_poly(bot_win, _fx["bottom"], _bp(bot_y, bot_slide - drift, 420.0, 0.0), band_thickness)
		_line(_bp(bot_y, bot_slide, -1700, -band_thickness * 0.5), _bp(bot_y, bot_slide, 1700, -band_thickness * 0.5), Color(1, 1, 1, 0.9), 3.0)
		# middle band: opens from a line, speed lines, LINK BREAK!
		var mh := middle_thickness * cover
		var mid := _band(CANVAS.y * 0.5, mh, 0.0)
		draw_colored_polygon(mid, middle_color)
		for l in _lines:
			var u := fposmod(float(l[3]) - t * float(l[1]), 3400.0) - 1700.0
			var v := float(l[0]) * mh
			_line(_bp(CANVAS.y * 0.5, 0.0, u, v), _bp(CANVAS.y * 0.5, 0.0, u + float(l[2]), v), Color(1, 1, 1, 0.08 + 0.06 * absf(float(l[0]))), 2.0)
		_line(mid[0], mid[1], Color(side_color.lightened(0.35), 1.0), 4.0)
		_line(mid[3], mid[2], Color(side_color.lightened(0.35), 1.0), 4.0)
		if mh > middle_thickness * 0.6:
			var ta := clampf((mh / middle_thickness - 0.6) / 0.4, 0.0, 1.0)
			var title := "LINK BREAK!"
			var rot := deg_to_rad(band_angle)   # the words lie along the band
			draw_set_transform(_bp(CANVAS.y * 0.5, 0.0, -800.0 - (1.0 - cin) * 200.0, 34.0), rot, Vector2.ONE)
			_label(_title_font, Vector2(6, 6), title, 100, Color(0, 0, 0, 0.55 * ta), 0)
			_label(_title_font, Vector2.ZERO, title, 100, Color(1, 1, 1, ta), 10)
			draw_set_transform(_bp(CANVAS.y * 0.5, 0.0, 330.0, 0.0), rot, Vector2.ONE)
			_label(_tag_font, Vector2.ZERO, str(_fx["who"]), 56, Color(1, 1, 1, ta), 6)
			var sub := "UNBALANCED   ·   " + str(_fx["input"])
			_label(_tag_font, Vector2(4, 40), sub, 30, Color(side_color.lightened(0.55), ta), 4)
			draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
	# 3. the kanji: slams onto the opponent, then flies into the middle band (one kanji, never two)
	if _kanji:
		var slot := _bp(CANVAS.y * 0.5, 0.0, 60.0, 0.0)
		var slot_size := middle_thickness * 1.5
		var fly := cin
		var s := lerpf(2.3, 1.0, _ease_back(t / stamp_in))
		var pos := at.lerp(slot, fly)
		var sz := lerpf(stamp_size * s, slot_size, fly)
		var ka := 1.0 - cout
		if fly < 0.98:
			# the ink stroke and UNBALANCED stay with the opponent and fade as the kanji flies off
			var ia := (1.0 - fly) * clampf(t / stamp_in, 0.0, 1.0)
			_ink_stroke(at + Vector2(-stamp_size * 0.95, stamp_size * 0.3), at + Vector2(stamp_size * 0.95, -stamp_size * 0.36), stamp_size * 0.42, Color(0.01, 0.01, 0.03, 0.85 * ia))
			var word := "UNBALANCED"
			var ww := _width(_tag_font, word, 46)
			_label(_tag_font, at + Vector2(-ww * 0.5, stamp_size * 0.62), word, 46, Color(1, 1, 1, ia), 8)
		var shake := Vector2(sin(t * 95.0), cos(t * 81.0)) * 10.0 * maxf(0.0, 1.0 - t / 0.16)
		draw_set_transform(pos + shake, lerpf(deg_to_rad(-5.0), deg_to_rad(band_angle), fly), Vector2.ONE)
		draw_texture_rect(_kanji, Rect2(-Vector2(sz, sz) * 0.5, Vector2(sz, sz)), false, Color(1, 1, 1, ka))
		draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
