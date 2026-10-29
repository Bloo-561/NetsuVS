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
const DIRECTIONS := ["UP", "DOWN", "LEFT", "RIGHT"]

var _groups: Array = []   # [{"glyphs": [{"kind", "text"}], "label": String}]


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE


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
		var glyphs: Array = []
		if key == "":
			if lab == "SELECT":
				glyphs.append({"kind": "dpad", "text": ""})
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
					glyphs.append({"kind": "pill", "text": n.strip_edges()})
		_groups.append({"glyphs": glyphs, "label": lab})


func _glyph_width(g: Dictionary) -> float:
	match g["kind"]:
		"circle":
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
		"circle":
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
			draw_string(font, c + Vector2(-w / 2.0, size * 0.33), g["text"], HORIZONTAL_ALIGNMENT_LEFT, -1, size, glyph_ink)
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
