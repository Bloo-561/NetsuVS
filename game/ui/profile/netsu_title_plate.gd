class_name NetsuTitlePlate
extends Control
## TITLE PLATE (Nov 4 2026): a player's title (ProfileCatalog.TITLES) drawn as a name plate in the Netsu UI kit's
## style, at any size: the plate is as big as this Control (keep it about 6-8x as wide as it is tall).
##   a long navy-glass plate with pointed ends and a diamond at each tip (the kit's hairlines with diamond ends),
##   a double edge in the title's accent colour, a little picture at both ends (sakura, stars, a comet, a black
##   hole... ProfileCatalog.STYLES), and the title in the Cormorant serif, shrunk to fit.
## Locked titles (ProfileCatalog.is_unlocked) are drawn grey with a "?".
##
##   var p := NetsuTitlePlate.new()
##   p.title_id = "cecilia_main"
##   p.size = Vector2(420, 60)
## Used by Main Menu > CUSTOMIZE (game/ui/profile/netsu_customize.gd), the profile card (netsu_profile_card.gd)
## and the online lobby's player list / VS panel.

## A ProfileCatalog.TITLES id. "" = nothing is drawn.
@export var title_id: String = "":
	set(value):
		title_id = value
		queue_redraw()
## Draw it locked ("?") whatever the catalog says.
@export var force_locked := false:
	set(value):
		force_locked = value
		queue_redraw()
## 0..1: how bright the plate is (dimmed rows in a list).
@export var dim := 0.0:
	set(value):
		dim = value
		queue_redraw()

static var _font: FontVariation


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	resized.connect(queue_redraw)


static func font() -> FontVariation:
	if _font == null:
		_font = NetsuUI.serif(700, 1)
		_font.opentype_features = {TextServerManager.get_primary_interface().name_to_tag("lnum"): 1}
	return _font


func _draw() -> void:
	if title_id == "":
		return
	var entry := ProfileCatalog.title(title_id)
	var locked := force_locked or entry.is_empty() or not ProfileCatalog.is_unlocked(entry)
	var st := ProfileCatalog.style("locked" if locked else str(entry.get("style", "plain")))
	var text := "?" if locked else str(entry.get("text", ""))
	draw_plate(self, Rect2(Vector2.ZERO, size), st, text, dim, not locked)


## Draws a plate on any CanvasItem (also used for the "?" plates of locked titles).
static func draw_plate(ci: CanvasItem, r: Rect2, st: Dictionary, text: String, dim := 0.0, motifs := true) -> void:
	var w := r.size.x
	var h := r.size.y
	if w < 8.0 or h < 6.0:
		return
	var o := r.position
	var accent: Color = st["accent"]
	var deep: Color = st["deep"]
	var ink: Color = st["ink"]
	if dim > 0.0:
		accent = accent.lerp(Color(0.4, 0.42, 0.5), dim * 0.6)
		ink = Color(ink, 1.0 - dim * 0.45)
	var e := h * 0.36                    # how far the pointed ends reach in
	var tip := h * 0.13                  # room for the diamonds at the tips
	var L := o.x + tip
	var R := o.x + w - tip
	var T := o.y + h * 0.08
	var B := o.y + h * 0.92
	var M := o.y + h * 0.5
	var shape := PackedVector2Array([Vector2(L, M), Vector2(L + e, T), Vector2(R - e, T), Vector2(R, M),
		Vector2(R - e, B), Vector2(L + e, B)])
	# soft glow around it
	var glow := shape.duplicate()
	glow.append(shape[0])
	ci.draw_polyline(glow, Color(accent, 0.22), maxf(2.0, h * 0.14), true)
	# fill: the style's deep colour, lighter in the middle, darker at the bottom (navy glass)
	var mid_top := Color(deep.lerp(accent, 0.34), 0.96)
	var mid_bot := Color(deep.darkened(0.35), 0.96)
	var end_col := Color(deep.darkened(0.2), 0.96)
	var cx := o.x + w / 2.0
	ci.draw_polygon(PackedVector2Array([Vector2(L, M), Vector2(L + e, T), Vector2(cx, T), Vector2(R - e, T), Vector2(R, M),
		Vector2(R - e, B), Vector2(cx, B), Vector2(L + e, B)]),
		PackedColorArray([end_col, end_col, mid_top, end_col, end_col, mid_bot, mid_bot, mid_bot]))
	# the top half's sheen
	ci.draw_polygon(PackedVector2Array([Vector2(L + e * 0.5, (T + M) / 2.0), Vector2(L + e, T), Vector2(R - e, T),
		Vector2(R - e * 0.5, (T + M) / 2.0)]), PackedColorArray([Color(1, 1, 1, 0.0), Color(1, 1, 1, 0.1),
		Color(1, 1, 1, 0.1), Color(1, 1, 1, 0.0)]))
	if motifs:
		_scatter(ci, st, Rect2(L + e, T, R - L - 2.0 * e, B - T), accent)
	# the edges: a bright outer line, a fainter inner one
	var edge := shape.duplicate()
	edge.append(shape[0])
	ci.draw_polyline(edge, Color(accent.lightened(0.25), 0.95), maxf(1.0, h * 0.045), true)
	var ins := h * 0.13
	var inner := PackedVector2Array([Vector2(L + ins * 1.2, M), Vector2(L + e + ins * 0.4, T + ins), Vector2(R - e - ins * 0.4, T + ins),
		Vector2(R - ins * 1.2, M), Vector2(R - e - ins * 0.4, B - ins), Vector2(L + e + ins * 0.4, B - ins), Vector2(L + ins * 1.2, M)])
	ci.draw_polyline(inner, Color(accent, 0.38), maxf(1.0, h * 0.022), true)
	# the diamonds at the tips
	for x in [L, R]:
		_diamond(ci, Vector2(x, M), h * 0.15, Color(accent.lightened(0.4), 0.95), Color(0.03, 0.05, 0.16, 1.0))
	# the lettering: as big as fits between the pictures at the ends; on a small plate where a long title would get
	# too small to read, the end pictures are left out to make room (the colours still say which title it is)
	var f := font()
	var ms := h * 0.27
	var pad := h * 0.62
	var fs := _fit(f, text, (R - L) - 2.0 * (pad + ms * 1.15 + h * 0.12), int(h * 0.5))
	var ends := motifs
	if motifs and h < 48.0 and fs < int(h * 0.46):
		ends = false
		fs = _fit(f, text, (R - L) - 2.0 * (e * 0.9), int(h * 0.5))
	if ends:
		_motif(ci, str(st.get("motif", "plain")), Vector2(L + pad, M), ms, accent, -1)
		_motif(ci, str(st.get("motif", "plain")), Vector2(R - pad, M), ms, accent, 1)
	var tw := f.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x
	var base := Vector2(cx - tw / 2.0, M + fs * 0.33)
	var ol := maxi(2, int(h * 0.09))
	ci.draw_string_outline(f, base, text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, ol + 3, Color(accent, 0.2))
	ci.draw_string_outline(f, base, text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, ol, Color(deep.darkened(0.6), 0.92))
	ci.draw_string(f, base, text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, ink)


static func _fit(f: Font, text: String, room: float, start: int) -> int:
	var fs := start
	while fs > 7 and f.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x > room:
		fs -= 1
	return fs


static func _diamond(ci: CanvasItem, c: Vector2, r: float, edge: Color, fill: Color) -> void:
	var pts := PackedVector2Array([c + Vector2(0, -r), c + Vector2(r, 0), c + Vector2(0, r), c + Vector2(-r, 0)])
	ci.draw_colored_polygon(pts, fill)
	pts.append(pts[0])
	ci.draw_polyline(pts, edge, maxf(1.0, r * 0.28), true)


static func _star(ci: CanvasItem, c: Vector2, r: float, points: int, inner: float, col: Color, rot := -PI / 2.0) -> void:
	var pts := PackedVector2Array()
	for i in points * 2:
		var a := rot + i * PI / points
		pts.append(c + Vector2(cos(a), sin(a)) * (r if i % 2 == 0 else r * inner))
	ci.draw_colored_polygon(pts, col)


static func _ring(ci: CanvasItem, c: Vector2, rx: float, ry: float, col: Color, width: float, from := 0.0, to := TAU) -> void:
	var pts := PackedVector2Array()
	var n := 28
	for i in n + 1:
		var a := lerpf(from, to, float(i) / n)
		pts.append(c + Vector2(cos(a) * rx, sin(a) * ry))
	ci.draw_polyline(pts, col, width, true)


## A faint pattern across the plate behind the lettering (fixed positions: the same plate looks the same everywhere).
static func _scatter(ci: CanvasItem, st: Dictionary, box: Rect2, accent: Color) -> void:
	var h := box.size.y
	var spots := [[0.08, 0.3], [0.2, 0.75], [0.33, 0.22], [0.47, 0.8], [0.6, 0.28], [0.72, 0.72], [0.86, 0.35], [0.94, 0.7]]
	match str(st.get("motif", "")):
		"sakura":
			for i in spots.size():
				var p: Vector2 = box.position + Vector2(spots[i][0] * box.size.x, spots[i][1] * h)
				_petal(ci, p, h * 0.09, 0.6 + i * 0.7, Color(1.0, 0.72, 0.82, 0.22))
			# a thin lightning line along the bottom (Lightning Dash)
			var bolt := PackedVector2Array()
			var steps := 14
			for i in steps + 1:
				bolt.append(box.position + Vector2(box.size.x * i / steps, h * (0.86 if i % 2 == 0 else 0.74)))
			ci.draw_polyline(bolt, Color(1.0, 0.9, 0.55, 0.28), maxf(1.0, h * 0.025), true)
		"star", "crown":
			for i in spots.size():
				var p: Vector2 = box.position + Vector2(spots[i][0] * box.size.x, spots[i][1] * h)
				_star(ci, p, h * (0.06 if i % 2 else 0.04), 4, 0.3, Color(1.0, 0.92, 0.6, 0.3))
		"comet":
			var tail := PackedVector2Array([box.position + Vector2(box.size.x * 0.1, h * 0.2),
				box.position + Vector2(box.size.x * 0.9, h * 0.12), box.position + Vector2(box.size.x * 0.9, h * 0.2)])
			ci.draw_colored_polygon(tail, Color(0.6, 0.92, 1.0, 0.14))
			for i in [1, 3, 5, 7]:
				var p: Vector2 = box.position + Vector2(spots[i][0] * box.size.x, spots[i][1] * h)
				ci.draw_circle(p, maxf(1.0, h * 0.025), Color(0.8, 0.96, 1.0, 0.4))
		"void":
			_ring(ci, box.get_center(), box.size.x * 0.42, h * 0.32, Color(0.7, 0.42, 1.0, 0.16), maxf(1.0, h * 0.04))
			_ring(ci, box.get_center(), box.size.x * 0.3, h * 0.2, Color(0.7, 0.42, 1.0, 0.1), maxf(1.0, h * 0.03))
		"tester":
			for i in 4:   # scan lines
				var y := box.position.y + h * (0.22 + i * 0.19)
				var x := box.position.x
				while x < box.end.x:
					ci.draw_line(Vector2(x, y), Vector2(minf(x + h * 0.25, box.end.x), y), Color(0.5, 1.0, 0.8, 0.12), maxf(1.0, h * 0.02))
					x += h * 0.45
		"ember":
			for i in spots.size():
				var p: Vector2 = box.position + Vector2(spots[i][0] * box.size.x, (1.0 - spots[i][1] * 0.6) * h)
				ci.draw_circle(p, maxf(1.0, h * (0.025 if i % 2 else 0.018)), Color(1.0, 0.7, 0.3, 0.45))
		"rollback", "frames":
			for i in 6:
				var x := box.position.x + box.size.x * (0.1 + i * 0.16)
				ci.draw_line(Vector2(x, box.position.y + h * 0.15), Vector2(x - h * 0.2, box.end.y - h * 0.15),
					Color(accent, 0.08), maxf(1.0, h * 0.05))


static func _petal(ci: CanvasItem, c: Vector2, r: float, angle: float, col: Color) -> void:
	var pts := PackedVector2Array()
	for i in 12:
		var a := TAU * i / 12.0
		var p := Vector2(cos(a) * r, sin(a) * r * 0.55)
		if i == 0:
			p.x *= 1.25   # the notch end
		pts.append(c + p.rotated(angle))
	ci.draw_colored_polygon(pts, col)


## The little picture at one end. dir = -1 (left end) / 1 (right end).
static func _motif(ci: CanvasItem, motif: String, c: Vector2, s: float, accent: Color, dir: int) -> void:
	var light := accent.lightened(0.45)
	var lw := maxf(1.0, s * 0.14)
	match motif:
		"sakura":   # a five-petal sakura blossom
			for i in 5:
				var a := -PI / 2.0 + TAU * i / 5.0 + (0.3 if dir > 0 else 0.0)
				_petal(ci, c + Vector2(cos(a), sin(a)) * s * 0.55, s * 0.5, a, Color(1.0, 0.68, 0.8, 0.95))
			ci.draw_circle(c, s * 0.2, Color(1.0, 0.88, 0.45))
			ci.draw_circle(c, s * 0.09, Color(0.85, 0.2, 0.35))
		"star":
			_star(ci, c, s * 1.05, 5, 0.45, Color(1.0, 0.84, 0.36))
			_star(ci, c, s * 0.52, 5, 0.45, Color(1.0, 0.97, 0.8))
			_star(ci, c + Vector2(-dir * s * 1.05, -s * 0.7), s * 0.3, 4, 0.3, Color(1.0, 0.95, 0.75, 0.9))
		"comet":   # a comet head with its tail streaming inward
			var tail := PackedVector2Array([c + Vector2(0, -s * 0.42), c + Vector2(-dir * s * 1.9, -s * 0.05),
				c + Vector2(0, s * 0.42)])
			ci.draw_polygon(tail, PackedColorArray([Color(0.6, 0.92, 1.0, 0.75), Color(0.4, 0.8, 1.0, 0.0), Color(0.6, 0.92, 1.0, 0.75)]))
			ci.draw_circle(c, s * 0.5, Color(0.55, 0.9, 1.0, 0.45))
			ci.draw_circle(c, s * 0.34, Color(0.92, 0.99, 1.0))
		"void":   # a black hole: a dark disc in a violet ring
			_ring(ci, c, s * 1.05, s * 0.42, Color(0.82, 0.58, 1.0, 0.9), lw, PI, TAU)
			ci.draw_circle(c, s * 0.62, Color(0.72, 0.4, 1.0, 0.55))
			ci.draw_circle(c, s * 0.5, Color(0.02, 0.0, 0.06))
			_ring(ci, c, s * 1.05, s * 0.42, Color(0.9, 0.7, 1.0, 1.0), lw, 0.0, PI)
		"tester":   # a beta badge (left), a check mark (right)
			ci.draw_circle(c, s * 0.82, Color(0.42, 1.0, 0.72, 0.95))
			ci.draw_circle(c, s * 0.66, Color(0.02, 0.16, 0.12))
			if dir < 0:
				var f := NetsuTitlePlate.font()
				var fs := int(s * 1.25)
				var gw := f.get_string_size("β", HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x
				ci.draw_string(f, c + Vector2(-gw / 2.0, fs * 0.33), "β", HORIZONTAL_ALIGNMENT_LEFT, -1, fs, Color(0.7, 1.0, 0.86))
			else:
				ci.draw_polyline(PackedVector2Array([c + Vector2(-s * 0.36, 0), c + Vector2(-s * 0.08, s * 0.3), c + Vector2(s * 0.4, -s * 0.32)]),
					Color(0.7, 1.0, 0.86), lw * 1.3, true)
		"ember":   # a flame
			var pts := PackedVector2Array()
			for i in 17:
				var t := float(i) / 16.0
				var a := lerpf(PI * 0.15, PI * 1.85, t)
				var rr := s * 0.55
				var p := Vector2(sin(a) * rr, -cos(a) * rr * 0.9 + s * 0.2)
				if i == 0 or i == 16:
					p = Vector2(0, -s * 1.15)
				pts.append(c + p)
			ci.draw_colored_polygon(pts, Color(1.0, 0.5, 0.18, 0.95))
			var inner := PackedVector2Array()
			for p in pts:
				inner.append(c + (p - c) * 0.55 + Vector2(0, s * 0.18))
			ci.draw_colored_polygon(inner, Color(1.0, 0.86, 0.4))
		"d20":   # a twenty-sided die
			var hex := PackedVector2Array()
			for i in 6:
				var a := -PI / 2.0 + TAU * i / 6.0
				hex.append(c + Vector2(cos(a), sin(a)) * s * 0.95)
			ci.draw_colored_polygon(hex, Color(0.86, 0.66, 0.98, 0.3))
			hex.append(hex[0])
			ci.draw_polyline(hex, light, lw, true)
			var tri := PackedVector2Array([c + Vector2(0, -s * 0.55), c + Vector2(s * 0.5, s * 0.34), c + Vector2(-s * 0.5, s * 0.34), c + Vector2(0, -s * 0.55)])
			ci.draw_polyline(tri, light, lw, true)
			for i in 3:
				ci.draw_line(tri[i], hex[[0, 2, 4][i]], Color(light, 0.6), lw * 0.7, true)
		"crown":
			var cr := PackedVector2Array([c + Vector2(-s * 0.9, s * 0.55), c + Vector2(-s * 0.95, -s * 0.45), c + Vector2(-s * 0.45, s * 0.02),
				c + Vector2(0, -s * 0.75), c + Vector2(s * 0.45, s * 0.02), c + Vector2(s * 0.95, -s * 0.45), c + Vector2(s * 0.9, s * 0.55)])
			ci.draw_colored_polygon(cr, Color(1.0, 0.82, 0.36))
			for p in [cr[1], cr[3], cr[5]]:
				ci.draw_circle(p, s * 0.14, Color(1.0, 0.95, 0.75))
		"shield":
			var sh := PackedVector2Array([c + Vector2(-s * 0.72, -s * 0.7), c + Vector2(s * 0.72, -s * 0.7), c + Vector2(s * 0.68, s * 0.05),
				c + Vector2(0, s * 0.85), c + Vector2(-s * 0.68, s * 0.05)])
			ci.draw_colored_polygon(sh, Color(0.62, 0.76, 0.96, 0.9))
			var inner := PackedVector2Array()
			for p in sh:
				inner.append(c + (p - c) * 0.6)
			ci.draw_colored_polygon(inner, Color(0.12, 0.18, 0.38))
			ci.draw_line(c + Vector2(0, -s * 0.4), c + Vector2(0, s * 0.45), light, lw, true)
		"frames":   # a frame meter: little bars
			var hs := [0.5, 0.9, 0.9, 0.5, 0.3]
			for i in 5:
				var x := c.x + (i - 2) * s * 0.42
				var bh: float = s * 1.6 * hs[i]
				ci.draw_rect(Rect2(x - s * 0.15, c.y - bh / 2.0, s * 0.3, bh), Color(0.3, 0.82, 1.0) if i in [1, 2] else Color(1.0, 0.45, 0.55))
		"rollback":   # double chevrons pointing in
			for k in 2:
				var x := c.x + dir * (k * s * 0.6 - s * 0.3)
				ci.draw_polyline(PackedVector2Array([Vector2(x + dir * s * 0.32, c.y - s * 0.62), Vector2(x - dir * s * 0.32, c.y),
					Vector2(x + dir * s * 0.32, c.y + s * 0.62)]), Color(1.0, 0.55, 0.65) if k == 0 else light, lw * 1.2, true)
		_:   # "plain": the kit's four-point sparkle
			_star(ci, c, s * 0.95, 4, 0.24, Color(0.85, 0.93, 1.0))
