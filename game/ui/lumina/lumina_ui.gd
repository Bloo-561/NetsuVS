class_name LuminaUI
extends RefCounted
## LUMINA UI KIT  (the look of Melty Blood: Type Lumina / Twi-Lumina)
##
## Misty white + lavender backgrounds, clean techy lettering in indigo,
## silver hairlines and little four-point sparkles. Every menu screen builds
## its pieces from here, so to change the look of the WHOLE game, change the
## colours / fonts below.
##
##   var title := LuminaUI.label("BATTLE MODE", 48)
##   LuminaUI.backdrop(self)                 # misty background with beams + sparkles
##   var footer := LuminaUI.footer(self)     # white bar: footer.text / footer.prompts

# --- Palette -----------------------------------------------------------------
const MIST := Color(0.95, 0.94, 0.99)        ## the white haze
const LAVENDER := Color(0.8, 0.74, 0.96)     ## soft purple glow / highlights
const VIOLET := Color(0.52, 0.42, 0.86)      ## selected items, accents
const INDIGO := Color(0.16, 0.15, 0.38)      ## main text
const SILVER := Color(0.7, 0.72, 0.86)       ## hairlines, unselected text
const STEEL := Color(0.24, 0.36, 0.68)       ## health bar blue
const P1 := Color(0.82, 0.18, 0.3)           ## player 1 accent (crimson)
const P2 := Color(0.3, 0.52, 0.96)           ## player 2 accent (azure)
const GOLD := Color(0.86, 0.72, 0.4)

# --- Fonts (all SIL Open Font License - see assets/fonts/OFL_*.txt) -------------
## Exo 2 SemiBold - screen titles, character names, stage names.
const DISPLAY := preload("res://assets/fonts/Exo2-SemiBold.ttf")
## Exo 2 Bold Italic - big punchy numbers and call-outs: timer, combo count,
## FIGHT!/KO, READY?, VS, WINNER.
const IMPACT := preload("res://assets/fonts/Exo2-BoldItalic.ttf")
## Rajdhani SemiBold - menu items, labels, tags, HUD captions, button prompts.
const MENU := preload("res://assets/fonts/Rajdhani-SemiBold.ttf")
## Rajdhani Bold - the same, heavier (selected / emphasised labels).
const MENU_BOLD := preload("res://assets/fonts/Rajdhani-Bold.ttf")
## Roboto - sentences: menu descriptions, speech bubble, training panel.
const BODY := preload("res://assets/fonts/Roboto-Regular.ttf")
## Roboto Italic - quotes (win screen).
const BODY_ITALIC := preload("res://assets/fonts/Roboto-Italic.ttf")

const BG_DAY := "res://assets/ui/lumina/bg_hall_day.png"
const BG_DUSK := "res://assets/ui/lumina/bg_hall_dusk.png"


## A font with extra space between letters (Lumina's airy look).
static func spaced(font: Font, spacing: int) -> FontVariation:
	var f := FontVariation.new()
	f.base_font = font
	f.spacing_glyph = spacing
	# Rajdhani lacks a few symbols (the infinity sign, arrows): borrow those from
	# Roboto, then Godot's built-in font, instead of drawing nothing.
	f.fallbacks = [BODY, ThemeDB.fallback_font]
	return f


static func label(text: String, size: int, color: Color = INDIGO, font: Font = MENU, spacing: int = 2) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_override("font", spaced(font, spacing))
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l


static func full_rect(c: Control) -> void:
	c.set_anchors_preset(Control.PRESET_FULL_RECT)
	c.offset_left = 0
	c.offset_top = 0
	c.offset_right = 0
	c.offset_bottom = 0


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


## Four-point sparkle shape (the Lumina "✦").
static func sparkle_points(r: float) -> PackedVector2Array:
	var t := r * 0.2
	return PackedVector2Array([Vector2(0, -r), Vector2(t, -t), Vector2(r, 0), Vector2(t, t),
		Vector2(0, r), Vector2(-t, t), Vector2(-r, 0), Vector2(-t, -t)])


static func sparkle(r: float, color: Color = Color.WHITE) -> Polygon2D:
	var p := Polygon2D.new()
	p.polygon = sparkle_points(r)
	p.color = color
	return p


## Misty background: picture + white haze + lavender floor glow + light beams
## + twinkling sparkles. Returns the root (already added to parent, at the back).
static func backdrop(parent: Control, image_path: String = BG_DAY, haze: float = 0.55, sparkles: int = 26) -> Control:
	var root := Control.new()
	root.name = "LuminaBackdrop"
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(root)
	parent.move_child(root, 0)
	full_rect(root)
	var base := ColorRect.new()
	base.color = MIST
	full_rect(base)
	root.add_child(base)
	if image_path != "" and ResourceLoader.exists(image_path):
		var pic := TextureRect.new()
		pic.texture = load(image_path)
		pic.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		pic.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
		pic.mouse_filter = Control.MOUSE_FILTER_IGNORE
		full_rect(pic)
		root.add_child(pic)
	var wash := ColorRect.new()
	wash.color = Color(MIST, haze)
	wash.mouse_filter = Control.MOUSE_FILTER_IGNORE
	full_rect(wash)
	root.add_child(wash)
	var floor_glow := gradient_rect(Color(LAVENDER, 0.0), Color(LAVENDER, 0.55), true)
	floor_glow.anchor_top = 0.55
	floor_glow.anchor_right = 1.0
	floor_glow.anchor_bottom = 1.0
	root.add_child(floor_glow)
	var beams := Node2D.new()
	root.add_child(beams)
	for b in [[180.0, 220.0, 0.35], [760.0, 120.0, 0.22], [1380.0, 260.0, 0.3]]:
		var beam := Polygon2D.new()
		beam.polygon = PackedVector2Array([Vector2(b[0] + 300, -20), Vector2(b[0] + 300 + b[1], -20),
			Vector2(b[0] + b[1] * 1.6, 1100), Vector2(b[0] - b[1] * 0.4, 1100)])
		beam.vertex_colors = PackedColorArray([Color(1, 1, 1, b[2]), Color(1, 1, 1, b[2]), Color(1, 1, 1, 0), Color(1, 1, 1, 0)])
		beams.add_child(beam)
	if sparkles > 0:
		var field := LuminaSparkles.new()
		field.count = sparkles
		root.add_child(field)
	return root


## The white bar along the bottom: a description line and the button prompts.
## Returns {"root": Control, "text": Label, "prompts": Label}.
static func footer(parent: Control, prompts: String = "SELECT     A  CONFIRM     B  BACK") -> Dictionary:
	var root := Control.new()
	root.name = "LuminaFooter"
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.anchor_top = 1.0
	root.anchor_right = 1.0
	root.anchor_bottom = 1.0
	root.offset_top = -120
	parent.add_child(root)
	var band := gradient_rect(Color(LAVENDER, 0.85), Color(MIST, 0.95), false)
	band.position = Vector2(0, 0)
	band.size = Vector2(1920, 64)
	root.add_child(band)
	var line := ColorRect.new()
	line.color = Color(VIOLET, 0.6)
	line.position = Vector2(0, 0)
	line.size = Vector2(1920, 2)
	root.add_child(line)
	var lower := ColorRect.new()
	lower.color = Color(1, 1, 1, 0.9)
	lower.position = Vector2(0, 64)
	lower.size = Vector2(1920, 56)
	root.add_child(lower)
	var text := label("", 26, INDIGO, BODY, 0)
	text.position = Vector2(60, 12)
	text.size = Vector2(1800, 44)
	root.add_child(text)
	var hint := label(prompts, 22, Color(INDIGO, 0.75), MENU, 3)
	hint.position = Vector2(60, 76)
	hint.size = Vector2(1800, 36)
	root.add_child(hint)
	return {"root": root, "text": text, "prompts": hint}


## "▸ MAIN MENU" in the top-left corner with a hairline.
static func header(parent: Control, text: String) -> Label:
	var h := label(text, 38, INDIGO, DISPLAY, 6)
	h.position = Vector2(84, 22)
	parent.add_child(h)
	var mark := sparkle(14.0, VIOLET)
	mark.position = Vector2(62, 52)
	parent.add_child(mark)
	var line := gradient_rect(Color(VIOLET, 0.7), Color(VIOLET, 0.0), false)
	line.position = Vector2(40, 84)
	line.size = Vector2(760, 2)
	parent.add_child(line)
	return h
