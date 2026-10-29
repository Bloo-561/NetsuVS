class_name NetsuUI
extends RefCounted
## NETSU UI KIT  (title, main menu and character select, Oct 19 2026 mockups)
##
## Dark night-blue scenes, blue light on the left (Player 1) and crimson light on
## the right (Player 2), serif menu lettering and a thin glowing line along the
## bottom with diamond ends.
##
## Positions in these screens were measured on the 1672 x 941 mockup images, so
## the scripts write them in mockup pixels and convert with NetsuUI.m(x, y)
## (or NetsuUI.K for a single length).
##
##   var t := NetsuUI.label("VERSUS", 34, NetsuUI.TEXT, NetsuUI.serif())
##   var footer := NetsuUI.footer(self)          # footer.text (Label) / footer.prompts (NetsuPromptBar)
##   footer["prompts"].text = "UP / DOWN  SELECT     A  CONFIRM     B  BACK"

## Mockup pixels -> screen pixels (1920 / 1672).
const K := 1920.0 / 1672.0

# --- Palette -----------------------------------------------------------------
const NAVY := Color(0.04, 0.06, 0.18)          ## panels, glyph letters
const TEXT := Color(0.97, 0.97, 1.0)           ## selected / main text
const DIM := Color(0.76, 0.78, 0.88)           ## unselected menu items
const LINE := Color(0.62, 0.8, 1.0)            ## the glowing hairlines
const BLUE := Color(0.16, 0.52, 1.0)           ## Player 1 / left light
const CYAN := Color(0.3, 0.82, 1.0)            ## Player 1 status text, selected diamond
const RED := Color(1.0, 0.16, 0.3)             ## Player 2 / right light
const PINK := Color(0.86, 0.66, 0.98)          ## mode label on the select screen

# --- Fonts -------------------------------------------------------------------
## Cormorant Garamond (SIL Open Font License, assets/fonts/OFL_CormorantGaramond.txt):
## menu items, PRESS START, speech box, main menu footer.
const SERIF_FILE := preload("res://assets/fonts/CormorantGaramond.ttf")
## Exo 2: character select lettering and names.
const SANS_FILE := preload("res://assets/fonts/Exo2-SemiBold.ttf")
const SANS_ITALIC_FILE := preload("res://assets/fonts/Exo2-BoldItalic.ttf")
const BODY_FILE := preload("res://assets/fonts/Roboto-Regular.ttf")

const TITLE_BG := "res://assets/ui/netsu/title_bg.png"
const MENU_BG := "res://assets/ui/netsu/menu_bg.png"
const SELECT_BG := "res://assets/ui/netsu/select_bg.png"
const SLOT_EMPTY := "res://assets/ui/netsu/slot_empty.png"
const LOGO := "res://assets/ui/logo/netsu_vs_logo.png"


static func m(x: float, y: float) -> Vector2:
	return Vector2(x, y) * K


## The serif face at a weight (300 light ... 700 bold) with extra letter spacing.
static func serif(weight: int = 600, spacing: int = 0) -> FontVariation:
	var f := FontVariation.new()
	f.base_font = SERIF_FILE
	f.variation_opentype = {TextServerManager.get_primary_interface().name_to_tag("wght"): weight}
	f.spacing_glyph = spacing
	f.fallbacks = [BODY_FILE, ThemeDB.fallback_font]
	return f


static func sans(spacing: int = 0, italic: bool = false) -> FontVariation:
	var f := FontVariation.new()
	f.base_font = SANS_ITALIC_FILE if italic else SANS_FILE
	f.spacing_glyph = spacing
	f.fallbacks = [BODY_FILE, ThemeDB.fallback_font]
	return f


static func body(spacing: int = 0) -> FontVariation:
	var f := FontVariation.new()
	f.base_font = BODY_FILE
	f.spacing_glyph = spacing
	f.fallbacks = [ThemeDB.fallback_font]
	return f


static func label(text: String, size: int, color: Color, font: Font) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_override("font", font)
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l


## Soft coloured edge around text (stands in for the mockups' glow).
static func glow(l: Label, color: Color, width: int = 6) -> void:
	l.add_theme_color_override("font_outline_color", color)
	l.add_theme_constant_override("outline_size", width)


static func full_rect(c: Control) -> void:
	c.set_anchors_preset(Control.PRESET_FULL_RECT)
	c.offset_left = 0
	c.offset_top = 0
	c.offset_right = 0
	c.offset_bottom = 0


static func picture(parent: Node, path: String) -> TextureRect:
	var r := TextureRect.new()
	if ResourceLoader.exists(path):
		r.texture = load(path)
	r.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	r.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(r)
	full_rect(r)
	return r


static func gradient_rect(from: Color, to: Color, vertical: bool) -> TextureRect:
	var g := Gradient.new()
	g.set_color(0, from)
	g.set_color(1, to)
	var tex := GradientTexture2D.new()
	tex.gradient = g
	tex.fill_to = Vector2(0, 1) if vertical else Vector2(1, 0)
	var r := TextureRect.new()
	r.texture = tex
	r.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return r


## A slanted box (the shape of the menu bar, roster slots and speech box).
## `skew` > 0 leans it like "/": the top edge sits `skew` px to the right of the bottom edge.
static func para(w: float, h: float, skew: float) -> PackedVector2Array:
	return PackedVector2Array([Vector2(skew, 0), Vector2(w + skew, 0), Vector2(w, h), Vector2(0, h)])


static func poly(points: PackedVector2Array, color: Color) -> Polygon2D:
	var p := Polygon2D.new()
	p.polygon = points
	p.color = color
	return p


static func outline(points: PackedVector2Array, color: Color, width: float = 2.0) -> Line2D:
	var l := Line2D.new()
	l.points = points
	l.closed = true
	l.width = width
	l.default_color = color
	l.joint_mode = Line2D.LINE_JOINT_SHARP
	return l


## The menu diamond: an outlined rhombus, optionally with a smaller filled one inside.
static func diamond(r: float, edge: Color, fill: Color, inner: Color = Color(0, 0, 0, 0)) -> Node2D:
	var root := Node2D.new()
	var pts := PackedVector2Array([Vector2(0, -r), Vector2(r, 0), Vector2(0, r), Vector2(-r, 0)])
	root.add_child(poly(pts, fill))
	root.add_child(outline(pts, edge, maxf(1.5, r * 0.18)))
	if inner.a > 0.0:
		var ri := r * 0.45
		root.add_child(poly(PackedVector2Array([Vector2(0, -ri), Vector2(ri, 0), Vector2(0, ri), Vector2(-ri, 0)]), inner))
	return root


## Four-point star (the "✦" before CHARACTER SELECT).
static func sparkle(r: float, color: Color) -> Polygon2D:
	var t := r * 0.22
	return poly(PackedVector2Array([Vector2(0, -r), Vector2(t, -t), Vector2(r, 0), Vector2(t, t),
		Vector2(0, r), Vector2(-t, t), Vector2(-r, 0), Vector2(-t, -t)]), color)


## A hairline that fades out at one or both ends.
static func hairline(from: Vector2, length: float, color: Color, thickness: float = 2.0, fade: String = "both") -> TextureRect:
	var g := Gradient.new()
	var a0 := 0.0 if fade in ["both", "left"] else 1.0
	var a1 := 0.0 if fade in ["both", "right"] else 1.0
	g.offsets = PackedFloat32Array([0.0, 0.5, 1.0])
	g.colors = PackedColorArray([Color(color, color.a * a0), color, Color(color, color.a * a1)])
	var tex := GradientTexture2D.new()
	tex.gradient = g
	tex.fill_to = Vector2(1, 0)
	var r := TextureRect.new()
	r.texture = tex
	r.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	r.position = from - Vector2(0, thickness / 2.0)
	r.size = Vector2(length, thickness)
	return r


## The bottom bar: a glowing line with diamond ends, a darker band under it,
## a description on the left and button prompts on the right.
##   line_y / text_x / text_y / prompts_right are mockup pixels.
## Returns {"root": Control, "text": Label, "prompts": NetsuPromptBar}.
static func footer(parent: Control, serif_style: bool = true, line_y: float = 849.0, text_x: float = 87.0,
		text_y: float = 875.0, prompts_right: float = 1600.0, prompts_y: float = 883.0, solid: bool = false) -> Dictionary:
	var root := Control.new()
	root.name = "NetsuFooter"
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(root)
	full_rect(root)
	var y := line_y * K
	var band := gradient_rect(Color(0.02, 0.03, 0.12, 0.0), Color(0.02, 0.03, 0.1, 0.78), true)
	band.position = Vector2(0, y - 40)
	band.size = Vector2(1920, 1080 - y + 40)
	root.add_child(band)
	if solid:   # over the fight: hide the HUD gauges behind the footer
		var cover := ColorRect.new()
		cover.color = Color(0.02, 0.04, 0.14, 0.94)
		cover.position = Vector2(0, y)
		cover.size = Vector2(1920, 1080 - y)
		cover.mouse_filter = Control.MOUSE_FILTER_IGNORE
		root.add_child(cover)
	var glow_line := ColorRect.new()
	glow_line.color = Color(LINE, 0.16)
	glow_line.position = Vector2(0, y - 3)
	glow_line.size = Vector2(1920, 6)
	glow_line.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(glow_line)
	var line := ColorRect.new()
	line.color = Color(LINE, 0.85)
	line.position = Vector2(0, y - 1)
	line.size = Vector2(1920, 2)
	line.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(line)
	for x in [68.0, 1605.0]:
		var d := diamond(9.5 * K, Color(LINE, 0.95), Color(0.03, 0.05, 0.16, 1.0))
		d.position = Vector2(x * K, y)
		root.add_child(d)
	var font: Font = serif(500) if serif_style else body()
	var text := label("", 25 if serif_style else 22, TEXT, font)
	text.position = Vector2(text_x * K, text_y * K - 22)
	text.size = Vector2(1100, 44)
	text.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	# a soft dark edge: the footer stays readable where a render or bright art reaches it
	text.add_theme_constant_override("outline_size", 6)
	text.add_theme_color_override("font_outline_color", Color(0.02, 0.03, 0.12, 0.7))
	root.add_child(text)
	var prompts := NetsuPromptBar.new()
	prompts.outline_size = 6
	prompts.font = serif(600) if serif_style else sans(1)
	prompts.font_size = 21 if serif_style else 19
	prompts.glyph_radius = 16.0 if serif_style else 13.5
	prompts.group_gap = 44.0 if serif_style else 27.0
	prompts.right_x = prompts_right * K
	prompts.center_y = prompts_y * K
	root.add_child(prompts)
	full_rect(prompts)
	return {"root": root, "text": text, "prompts": prompts}


# --- Panels (options, pause, command list, stage select) -------------------------

## Dark hall background used behind the settings screens: the select-screen
## hall, darkened, with the blue / crimson beams. Returns the root Control.
static func settings_backdrop(parent: Control, darken: float = 0.5) -> Control:
	var root := Control.new()
	root.name = "NetsuBackdrop"
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(root)
	full_rect(root)
	picture(root, SELECT_BG)
	var shade := ColorRect.new()
	shade.color = Color(0.02, 0.03, 0.12, darken)
	shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(shade)
	full_rect(shade)
	var lights := NetsuLights.new()
	lights.beams = NetsuLights.preset("select")
	root.add_child(lights)
	return root


## "✦ OPTIONS" in the top-left corner with a hairline and a little diamond.
static func header(parent: Node, text: String) -> Label:
	var star := sparkle(13.0 * K, Color(0.85, 0.93, 1.0))
	star.position = m(70, 50)
	parent.add_child(star)
	var l := label(text, 42, Color.WHITE, sans(9))
	l.position = Vector2(96 * K, 49 * K - 30)
	l.size = Vector2(900, 60)
	l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	parent.add_child(l)
	parent.add_child(hairline(m(55, 77), 520 * K, Color(0.55, 0.78, 1.0, 0.85), 1.5, "right"))
	var d := diamond(5.0 * K, Color(0.7, 0.85, 1.0), Color(0.05, 0.1, 0.3))
	d.position = m(62, 77)
	parent.add_child(d)
	return l


## Centred page title:  ——  ✦  SYSTEM SETTINGS  ✦  ——   with a short line and a diamond under it.
## y = centre of the text in mockup pixels. Returns the Label.
static func page_title(parent: Node, text: String, y: float = 127.0, size: int = 50) -> Label:
	var font := sans(5)
	var l := label(text, size, Color.WHITE, font)
	glow(l, Color(0.25, 0.5, 1.0, 0.35), 8)
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	l.position = Vector2(0, y * K - 40)
	l.size = Vector2(1920, 80)
	parent.add_child(l)
	var w := font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x
	var cy := y * K
	for s: float in [-1.0, 1.0]:
		var star := sparkle(15.0, Color(0.85, 0.93, 1.0))
		star.position = Vector2(960 + s * (w / 2.0 + 42), cy)
		parent.add_child(star)
		var x0 := 960 + s * (w / 2.0 + 70)
		var length := 170.0
		parent.add_child(hairline(Vector2(x0 - (length if s < 0 else 0.0), cy), length, Color(0.6, 0.8, 1.0, 0.8), 1.5,
			"left" if s < 0 else "right"))
	parent.add_child(hairline(Vector2(960 - 55, cy + 34 * K), 110, Color(0.6, 0.8, 1.0, 0.9), 1.5, "both"))
	var d := diamond(6.0, Color(0.75, 0.9, 1.0), Color(0.05, 0.1, 0.3))
	d.position = Vector2(960, cy + 34 * K)
	parent.add_child(d)
	return l


## The glowing framed box (navy glass, blue edge, bright corner triangles). rect in screen pixels.
static func frame_panel(parent: Node, rect: Rect2, accent: Color = Color(0.3, 0.62, 1.0)) -> Node2D:
	var root := Node2D.new()
	parent.add_child(root)
	var pts := PackedVector2Array([rect.position, Vector2(rect.end.x, rect.position.y), rect.end, Vector2(rect.position.x, rect.end.y)])
	var fill := Polygon2D.new()
	fill.polygon = pts
	fill.vertex_colors = PackedColorArray([Color(0.04, 0.06, 0.2, 0.88), Color(0.04, 0.06, 0.2, 0.88),
		Color(0.02, 0.03, 0.12, 0.92), Color(0.02, 0.03, 0.12, 0.92)])
	root.add_child(fill)
	root.add_child(outline(pts, Color(accent, 0.22), 10.0))
	root.add_child(outline(pts, Color(accent.lightened(0.2), 0.95), 2.0))
	var leg := 36.0
	var inset := 5.0
	for c in 4:
		var corner: Vector2 = pts[c]
		var dx := 1.0 if c in [0, 3] else -1.0
		var dy := 1.0 if c in [0, 1] else -1.0
		var tri := PackedVector2Array([corner + Vector2(dx * inset, dy * inset), corner + Vector2(dx * (inset + leg), dy * inset),
			corner + Vector2(dx * inset, dy * (inset + leg))])
		root.add_child(poly(tri, Color(accent.lightened(0.35), 0.95)))
		var bracket := Line2D.new()
		bracket.points = PackedVector2Array([corner + Vector2(0, dy * (leg + 20)), corner, corner + Vector2(dx * (leg + 20), 0)])
		bracket.width = 3.0
		bracket.default_color = Color(accent.lightened(0.5), 1.0)
		root.add_child(bracket)
	return root


## ">" chevron (or ">>" when double) centred on `at`, `h` tall.
static func chevron(at: Vector2, h: float, color: Color, width: float = 3.0, double: bool = false) -> Node2D:
	var root := Node2D.new()
	root.position = at
	for i in (2 if double else 1):
		var l := Line2D.new()
		var ox := i * h * 0.45
		l.points = PackedVector2Array([Vector2(-h * 0.25 + ox, -h / 2.0), Vector2(h * 0.25 + ox, 0), Vector2(-h * 0.25 + ox, h / 2.0)])
		l.width = width
		l.default_color = color
		l.joint_mode = Line2D.LINE_JOINT_SHARP
		root.add_child(l)
	return root


## "<" (dir = -1) or ">" (dir = 1) arrow, as a Line2D node.
static func arrow(at: Vector2, h: float, dir: int, color: Color, width: float = 3.0) -> Line2D:
	var l := Line2D.new()
	l.position = at
	l.points = PackedVector2Array([Vector2(-dir * h * 0.25, -h / 2.0), Vector2(dir * h * 0.25, 0), Vector2(-dir * h * 0.25, h / 2.0)])
	l.width = width
	l.default_color = color
	l.joint_mode = Line2D.LINE_JOINT_SHARP
	return l


## The selected-row bar: bright blue on the left fading right, glowing border.
static func row_bar(size: Vector2) -> Node2D:
	var root := Node2D.new()
	var pts := PackedVector2Array([Vector2.ZERO, Vector2(size.x, 0), size, Vector2(0, size.y)])
	var fill := Polygon2D.new()
	fill.polygon = pts
	fill.vertex_colors = PackedColorArray([Color(0.1, 0.4, 0.95, 0.9), Color(0.05, 0.2, 0.6, 0.65),
		Color(0.04, 0.16, 0.5, 0.65), Color(0.08, 0.34, 0.88, 0.9)])
	root.add_child(fill)
	root.add_child(outline(pts, Color(0.35, 0.7, 1.0, 0.3), 8.0))
	root.add_child(outline(pts, Color(0.5, 0.8, 1.0, 1.0), 2.0))
	return root


## A divider line across a panel with a small diamond in the middle.
static func divider(parent: Node, x0: float, x1: float, y: float, with_diamond: bool = true) -> void:
	parent.add_child(hairline(Vector2(x0, y), x1 - x0, Color(0.55, 0.75, 1.0, 0.75), 1.5, "none"))
	if with_diamond:
		var d := diamond(6.0, Color(0.7, 0.88, 1.0), Color(0.03, 0.06, 0.2))
		d.position = Vector2((x0 + x1) / 2.0, y)
		parent.add_child(d)


# --- Transitions -------------------------------------------------------------------

## Screen entrance: the children of `root` (after the first `skip`, e.g. the
## background) fade in from top to bottom, Controls also sliding in from the left.
static func cascade(root: Node, skip: int = 0, start: float = 0.06, spread: float = 0.32, shift: float = 28.0) -> void:
	var t := root.create_tween().set_parallel(true)
	var kids := root.get_children()
	for i in range(skip, kids.size()):
		var c = kids[i]
		if not (c is CanvasItem) or not c.visible:
			continue
		var y := 540.0
		if c is Control:
			y = clampf(c.position.y + c.size.y * 0.25, 0.0, 1080.0)
			if shift != 0.0:
				var home: float = c.position.x
				c.position.x = home - shift
				t.tween_property(c, "position:x", home, 0.3).set_delay(start + y / 1080.0 * spread) \
					.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
		elif c is Node2D:
			y = clampf(c.position.y, 0.0, 1080.0)
		var a: float = c.modulate.a
		c.modulate.a = 0.0
		t.tween_property(c, "modulate:a", a, 0.22).set_delay(start + y / 1080.0 * spread)
