class_name NetsuPromptBar
extends Control
## Button prompts drawn as glyphs, right-aligned:  ✚ SELECT   (A) CONFIRM   (B) BACK
##
## Set `text` the same way the old footer label was set: groups separated by 3+
## spaces, each group "KEY  LABEL" (key and label separated by 2 spaces):
##   "UP / DOWN  SELECT     A  CONFIRM     B  BACK     RB / U  BUTTON SETTINGS"
## Keys:
##   A, B, C, S              -> white circle with the letter
##   directions (UP / DOWN)  -> d-pad cross;  LEFT / RIGHT -> "< >" arrows
##   anything else ("RB / U", "ESC") -> white pills, one per " / " part
## A group with no key ("SELECT") gets the d-pad when it says SELECT, otherwise it's plain text.
## Nov 8: the keys follow the controller in use (Controls.prompt_style). The letters in `text` are Xbox names (where
## the button is): on a PlayStation pad A / B / X / Y are drawn as Cross / Circle / Square / Triangle and LB / RB /
## LT / RT / START as L1 / R1 / L2 / R2 / OPTIONS; on a keyboard A / B show player 1's keys (J / K). Xbox: coloured
## letters. The bar redraws by itself when another device is used.

var text: String = "":
	set(value):
		text = value
		_parse()
		queue_redraw()
var font: Font
var font_size: int = 20
var glyph_radius: float = 15.0
var group_gap: float = 40.0
var right_x: float = 1820.0
var center_y: float = 1014.0
var text_color := Color(0.97, 0.97, 1.0)
var glyph_color := Color(0.97, 0.97, 1.0)
var glyph_ink := Color(0.16, 0.18, 0.42)
## A dark edge around the labels and glyphs so they still read over bright art (Oct 25 2026). 0 = none.
var outline_size: int = 0
var outline_color := Color(0.02, 0.03, 0.12, 0.8)

const CIRCLE_KEYS := ["A", "B", "C", "S", "X", "Y"]
const PS_KEYS := ["CROSS", "CIRCLE", "SQUARE", "TRIANGLE"]
const PS_INK := {"CROSS": Color(0.25, 0.48, 1.0), "CIRCLE": Color(0.95, 0.22, 0.32), "SQUARE": Color(0.86, 0.38, 0.8),
	"TRIANGLE": Color(0.1, 0.68, 0.55)}
const XBOX_INK := {"A": Color(0.18, 0.62, 0.22), "B": Color(0.86, 0.18, 0.2), "X": Color(0.16, 0.42, 0.95),
	"Y": Color(0.86, 0.62, 0.05)}
const DIRECTIONS := ["UP", "DOWN", "LEFT", "RIGHT"]

var _groups: Array = []   # [{"glyphs": [{"kind", "text"}], "label": String}]


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	var c := get_node_or_null("/root/Controls")
	if c and c.has_signal("prompt_style_changed"):
		c.prompt_style_changed.connect(_on_style_changed)


func _on_style_changed() -> void:
	_parse()
	queue_redraw()


func _style() -> String:
	var c: Node = get_node_or_null("/root/Controls") if is_inside_tree() else null
	return str(c.prompt_style) if c and "prompt_style" in c else "xbox"


## One key name as the device in use shows it ("A" -> "CROSS" on a PlayStation pad, "J" on a keyboard).
func _restyle(k: String) -> String:
	var style := _style()
	if style == "ps":
		return str(Controls.PS_NAMES.get(k, k))
	if style == "kb" and k in ["A", "B"]:
		var n := str(Controls.key_name(Controls.keyboard[1].get(k.to_lower())))
		return n.to_upper() if n != "" and n != "---" else k
	if style == "xbox":   # (PlayStation names given to an Xbox pad, the other way)
		for x in Controls.PS_NAMES:
			if Controls.PS_NAMES[x] == k and x in ["A", "B", "X", "Y", "LB", "RB", "LT", "RT", "START", "BACK"]:
				return x
	return k


func _parse() -> void:
	_groups.clear()
	var re := RegEx.new()
	re.compile("\\s{3,}")
	for chunk in re.sub(text.strip_edges(), "\t", true).split("\t", false):
		var parts: PackedStringArray = chunk.split("  ", false)
		var key := ""
		var lab := chunk.strip_edges()
		if parts.size() >= 2:
			key = parts[0].strip_edges()
			lab = "  ".join(parts.slice(1)).strip_edges()
		if key != "":
			var restyled: Array = []
			for n in key.split("/", false):
				restyled.append(_restyle(n.strip_edges()))
			key = " / ".join(restyled)
		var glyphs: Array = []
		if key == "":
			if lab == "SELECT":
				glyphs.append({"kind": "dpad", "text": ""})
		elif key in PS_KEYS:
			glyphs.append({"kind": "ps", "text": key})
		elif key in CIRCLE_KEYS:
			glyphs.append({"kind": "circle", "text": key})
		else:
			var names := key.split("/", false)
			var all_dirs := true
			for n in names:
				if not n.strip_edges() in DIRECTIONS:
					all_dirs = false
			if all_dirs and key.replace(" ", "") == "LEFT/RIGHT":
				glyphs.append({"kind": "lr", "text": ""})
			elif all_dirs:
				glyphs.append({"kind": "dpad", "text": ""})
			else:
				for n in names:
					var nn: String = n.strip_edges()
					if nn in PS_KEYS:
						glyphs.append({"kind": "ps", "text": nn})
					elif nn in CIRCLE_KEYS:
						glyphs.append({"kind": "circle", "text": nn})
					else:
						glyphs.append({"kind": "pill", "text": nn})
		_groups.append({"glyphs": glyphs, "label": lab})


func _glyph_width(g: Dictionary) -> float:
	match g["kind"]:
		"circle", "ps":
			return glyph_radius * 2.0
		"dpad":
			return glyph_radius * 2.0
		"lr":
			return glyph_radius * 2.4
		_:
			return maxf(glyph_radius * 2.0, _ink_width(g["text"], _pill_size()) + glyph_radius * 0.9)


func _pill_size() -> int:
	return int(round(glyph_radius * 0.95))


func _ink_width(s: String, size: int) -> float:
	if font == null:
		return 0.0
	return font.get_string_size(s, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x


func _group_width(group: Dictionary) -> float:
	var w := 0.0
	for g in group["glyphs"]:
		w += _glyph_width(g) + glyph_radius * 0.35
	if not group["glyphs"].is_empty():
		w += glyph_radius * 0.45
	return w + _ink_width(group["label"], font_size)


func _draw() -> void:
	if font == null or _groups.is_empty():
		return
	var total := 0.0
	for i in _groups.size():
		total += _group_width(_groups[i]) + (group_gap if i > 0 else 0.0)
	var x := right_x - total
	var cap := font_size * 0.66
	for group in _groups:
		for g in group["glyphs"]:
			var w := _glyph_width(g)
			if outline_size > 0:
				_draw_halo(g, Vector2(x + w / 2.0, center_y))
			_draw_glyph(g, Vector2(x + w / 2.0, center_y))
			x += w + glyph_radius * 0.35
		if not group["glyphs"].is_empty():
			x += glyph_radius * 0.45
		if outline_size > 0:
			draw_string_outline(font, Vector2(x, center_y + cap / 2.0), group["label"], HORIZONTAL_ALIGNMENT_LEFT, -1, font_size,
				outline_size, outline_color)
		draw_string(font, Vector2(x, center_y + cap / 2.0), group["label"], HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, text_color)
		x += _ink_width(group["label"], font_size) + group_gap


## The dark edge behind a glyph: its shape, a little bigger, in outline_color.
func _draw_halo(g: Dictionary, c: Vector2) -> void:
	var r := glyph_radius
	var e := outline_size * 0.5
	match g["kind"]:
		"circle", "ps":
			draw_circle(c, r + e, outline_color)
		"dpad":
			var arm := r * 0.62 + e * 2.0
			var long := r * 1.0 + e
			draw_rect(Rect2(c - Vector2(arm / 2.0, long), Vector2(arm, long * 2.0)), outline_color)
			draw_rect(Rect2(c - Vector2(long, arm / 2.0), Vector2(long * 2.0, arm)), outline_color)
		"lr":
			for dir in [-1.0, 1.0]:
				var tip := c + Vector2(dir * r * 1.15, 0)
				var back := c + Vector2(dir * r * 0.25, 0)
				var arrow := PackedVector2Array([tip, back + Vector2(0, -r * 0.85), back + Vector2(dir * r * 0.32, 0),
					back + Vector2(0, r * 0.85), tip])
				draw_polyline(arrow, outline_color, outline_size, true)
		"pill":
			var w := _glyph_width(g) + e * 2.0
			var h := r * 1.6 + e * 2.0
			var box := StyleBoxFlat.new()
			box.bg_color = outline_color
			box.set_corner_radius_all(int(h * 0.3))
			draw_style_box(box, Rect2(c - Vector2(w / 2.0, h / 2.0), Vector2(w, h)))


func _draw_glyph(g: Dictionary, c: Vector2) -> void:
	var r := glyph_radius
	match g["kind"]:
		"circle":
			draw_circle(c, r, glyph_color)
			var size := int(round(r * 1.15))
			var w := _ink_width(g["text"], size)
			var ink: Color = XBOX_INK.get(g["text"], glyph_ink) if _style() == "xbox" else glyph_ink
			draw_string(font, c + Vector2(-w / 2.0, size * 0.33), g["text"], HORIZONTAL_ALIGNMENT_LEFT, -1, size, ink)
		"ps":   # a PlayStation face button: the white disc with its shape in its colour
			draw_circle(c, r, glyph_color)
			var ink: Color = PS_INK.get(g["text"], glyph_ink)
			var s := r * 0.48
			var lw := maxf(2.0, r * 0.17)
			match g["text"]:
				"CROSS":
					draw_line(c + Vector2(-s, -s), c + Vector2(s, s), ink, lw, true)
					draw_line(c + Vector2(-s, s), c + Vector2(s, -s), ink, lw, true)
				"CIRCLE":
					draw_arc(c, s * 1.05, 0.0, TAU, 28, ink, lw, true)
				"SQUARE":
					var q := s * 0.88
					draw_rect(Rect2(c - Vector2(q, q), Vector2(q, q) * 2.0), ink, false, lw)
				"TRIANGLE":
					var tri := PackedVector2Array([c + Vector2(0, -s * 1.1), c + Vector2(s * 1.05, s * 0.75),
						c + Vector2(-s * 1.05, s * 0.75), c + Vector2(0, -s * 1.1)])
					draw_polyline(tri, ink, lw, true)
		"dpad":
			var arm := r * 0.62
			var long := r * 1.0
			draw_rect(Rect2(c - Vector2(arm / 2.0, long), Vector2(arm, long * 2.0)), glyph_color)
			draw_rect(Rect2(c - Vector2(long, arm / 2.0), Vector2(long * 2.0, arm)), glyph_color)
			draw_circle(c, arm * 0.28, glyph_ink)
		"lr":
			for dir in [-1.0, 1.0]:
				var tip := c + Vector2(dir * r * 1.15, 0)
				var back := c + Vector2(dir * r * 0.25, 0)
				draw_colored_polygon(PackedVector2Array([tip, back + Vector2(0, -r * 0.85), back + Vector2(dir * r * 0.32, 0),
					back + Vector2(0, r * 0.85)]), glyph_color)
		"pill":
			var w := _glyph_width(g)
			var h := r * 1.6
			var rect := Rect2(c - Vector2(w / 2.0, h / 2.0), Vector2(w, h))
			var box := StyleBoxFlat.new()
			box.bg_color = glyph_color
			box.set_corner_radius_all(int(h * 0.3))
			draw_style_box(box, rect)
			var size := _pill_size()
			var tw := _ink_width(g["text"], size)
			draw_string(font, c + Vector2(-tw / 2.0, size * 0.36), g["text"], HORIZONTAL_ALIGNMENT_LEFT, -1, size, glyph_ink)
