class_name NetsuCommandList
extends Control
## COMMAND LIST SCREEN (Nov 2 2026; mockup: claude.ai design canvas "Netsu VS Command List")
##
## Three tabs: SYSTEM (data/command_list/system.json), CHARACTERS (every fighter on the roster, built from the
## fighter's own move data by NetsuMoveCatalog) and ASSISTS (data/assist_list.tres). Left: a scrollable list of
## moves with a still from each move, its name, tags and input; a fighter's moves are split into category tabs
## (NORMALS / CRAFTS / S-CRAFTS / UNIVERSAL). Right: the move played out against an opponent in Thor's Hall
## (NetsuMoveStage + NetsuMoveSim, straight from the move data), its description and frame data.
##
##   Up / Down        pick a move           Left / Right     category (Characters) / page (System, Assists)
##   LT / RT (Page Up / Down)   other fighter / page          LB / RB (Q / E, Tab)   other tab
##   A                play the move again   B                back
## Mouse: click a tab or a move, wheel scrolls.
##
## Opened by the pause menu (over the fight, `overlay` = true) and the main menu's COMMAND LIST.
## Emits `closed` when the player backs out; the host frees it.

signal closed

const CANVAS := Vector2(1920, 1080)
const TABS := [["system", "SYSTEM"], ["characters", "CHARACTERS"], ["assists", "ASSISTS"]]
const RAJ := "res://assets/fonts/Rajdhani-Bold.ttf"
const RAJ_SEMI := "res://assets/fonts/Rajdhani-SemiBold.ttf"
const PROMPTS := "UP / DOWN  MOVE     LEFT / RIGHT  PAGE     LB / RB  TAB     A  REPLAY     B  BACK"
const PROMPTS_CHARS := "UP / DOWN  MOVE     LEFT / RIGHT  CATEGORY     LT / RT  FIGHTER     LB / RB  TAB     A  REPLAY     B  BACK"
## A fighter's categories: the catalog's section -> the tab's name.
const CATS := [["Normals", "NORMALS"], ["Specials", "CRAFTS"], ["Supers", "S-CRAFTS"], ["Universal", "UNIVERSAL"]]
const HINTS := {
	"system": "How the game works. Pick a topic to see it in action.",
	"characters": "Numpad notation, facing right: 236 = quarter-circle fwd.",
	"assists": "Your assist's moves. Call with S, or 6 + S.",
}
const TAG_COLORS := {
	"EX": Color(1.0, 0.84, 0.4), "SUPER": Color(1.0, 0.48, 0.56), "INVINCIBLE": Color(0.62, 0.94, 1.0),
	"LAUNCHER": Color(0.72, 0.89, 1.0), "OVERHEAD": Color(1.0, 0.7, 0.48), "LOW": Color(1.0, 0.7, 0.48),
	"UNSAFE": Color(1.0, 0.6, 0.67), "GRAB": Color(0.85, 0.7, 1.0), "AIR OK": Color(0.72, 0.89, 1.0),
}

## Set by the host before add_child.
var footer_override: Dictionary = {}
var overlay := false
var start_tab := "characters"
var start_fighter := 0
var start_assist := 0
## The opponent in the previews (a roster index): the other fighter of the match in the pause menu. -1 = the next
## fighter on the roster.
var start_opponent := -1
var side := 0

var _tab := 1
var _sub := {0: 0, 1: 0, 2: 0}
var _sel := {}                 # "tab:sub:category" -> row index
var _cat := {}                 # fighter index -> category index (Characters tab)
var _all_rows: Array = []      # every row of the fighter shown (before the category filter)
var _rows: Array = []          # current rows (headings: {"heading": "..."})
var _row_nodes: Array = []     # Control per row (null for headings)
var _data: Resource = null     # the fighter (or assist) being shown
var _system_fighter := 0       # whose moves the System tab plays
var _pending: Array = []       # DataContainers loading on threads
var _opp: Resource = null      # the opponent in the previews
var _caller: Resource = null   # the fighter calling the assist (Assists tab previews)
var _spawn_lists := {}
var _ref_heights := {}
var _trigger := [false, false]
var _own_footer: Dictionary = {}

var _raj: Font
var _raj_semi: Font
var _tabs_box: Control
var _subs_box: HBoxContainer
var _who: Label
var _count: Label
var _scroll: ScrollContainer
var _list: VBoxContainer
var _stage: NetsuMoveStage
var _cats_box: HBoxContainer
var _head_labels: Array = []
var _illus: NetsuCLIllustration
var _cutin: Control
var _cutin_tex: TextureRect
var _cutin_label: Label
var _badge: Label
var _loading: Label
var _name: Label
var _tags: HBoxContainer
var _glyphs: NetsuInputGlyphs
var _desc: Label
var _grid: GridContainer
var _glow: TextureRect


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	mouse_filter = Control.MOUSE_FILTER_STOP
	size = CANVAS
	_raj = load(RAJ)
	_raj_semi = load(RAJ_SEMI)
	for i in TABS.size():
		if TABS[i][0] == start_tab:
			_tab = i
	_sub[1] = clampi(start_fighter, 0, maxi(0, MatchSetup.fighter_count() - 1))
	_sub[2] = clampi(start_assist, 0, maxi(0, MatchSetup.assist_count() - 1))
	_system_fighter = _sub[1]
	_build()
	_refresh()


# --- Building --------------------------------------------------------------------------------

func _label(text: String, fs: int, col: Color, font: Font) -> Label:
	var l := NetsuUI.label(text, fs, col, font)
	l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	return l


func _box(bg: Color, border: Color, radius: int = 4, width: int = 1) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = bg
	sb.border_color = border
	sb.set_border_width_all(width)
	sb.set_corner_radius_all(radius)
	return sb


func _panel(rect: Rect2, sb: StyleBox) -> Panel:
	var p := Panel.new()
	p.position = rect.position
	p.size = rect.size
	p.add_theme_stylebox_override("panel", sb)
	p.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(p)
	return p


func _build() -> void:
	# background
	if not overlay:   # a screen of its own: nothing of the menu behind shows through
		var solid := ColorRect.new()
		solid.color = Color(0.027, 0.043, 0.14)
		solid.size = CANVAS
		solid.mouse_filter = Control.MOUSE_FILTER_IGNORE
		add_child(solid)
		NetsuUI.picture(self, NetsuUI.MENU_BG).modulate = Color(1, 1, 1, 0.55)
	var veil := NetsuUI.gradient_rect(Color(0.02, 0.04, 0.16, 0.72 if not overlay else 0.6), Color(0.016, 0.027, 0.12, 0.96), true)
	veil.size = CANVAS
	add_child(veil)
	_glow = TextureRect.new()
	_glow.texture = _radial(Color(0.16, 0.52, 1.0, 0.2))
	_glow.position = Vector2(1000, 160)
	_glow.size = Vector2(1100, 1100)
	_glow.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_glow)
	# header
	var tick := NetsuUI.diamond(7.0, Color(0.75, 0.9, 1.0), Color(0.3, 0.6, 1.0))
	tick.position = Vector2(72, 68)
	add_child(tick)
	add_child(NetsuUI.hairline(Vector2(82, 68), 30, Color(0.7, 0.88, 1.0), 1.5, "none"))
	var title := _label("COMMAND LIST", 46, Color.WHITE, NetsuUI.sans(8, true))
	title.position = Vector2(124, 36)
	title.size = Vector2(500, 64)
	NetsuUI.glow(title, Color(0.3, 0.82, 1.0, 0.35), 8)
	add_child(title)
	var title_w := NetsuUI.sans(8, true).get_string_size("COMMAND LIST", HORIZONTAL_ALIGNMENT_LEFT, -1, 46).x
	add_child(NetsuUI.hairline(Vector2(124 + title_w + 18, 68), 170, Color(0.7, 0.88, 1.0), 1.5, "right"))
	_who = _label("", 26, Color(0.3, 0.82, 1.0), _raj)
	_who.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_who.position = Vector2(960, 36)
	_who.size = Vector2(896, 64)
	add_child(_who)
	# main tabs
	_tabs_box = Control.new()
	_tabs_box.position = Vector2(64, 116)
	_tabs_box.size = Vector2(1792, 62)
	add_child(_tabs_box)
	# sub tabs
	_subs_box = HBoxContainer.new()
	_subs_box.position = Vector2(64, 194)
	_subs_box.size = Vector2(1000, 58)
	_subs_box.add_theme_constant_override("separation", 10)
	add_child(_subs_box)
	# list panel
	_panel(Rect2(64, 268, 1000, 692), _box(Color(0.024, 0.04, 0.14, 0.82), Color(0.62, 0.8, 1.0, 0.28)))
	var head := _label("PREVIEW", 16, Color(0.56, 0.64, 0.84), _raj)
	head.position = Vector2(88, 268)
	head.size = Vector2(200, 44)
	add_child(head)
	var head2 := _label("MOVE · COMMAND", 16, Color(0.56, 0.64, 0.84), _raj)
	head2.position = Vector2(262, 268)
	head2.size = Vector2(400, 44)
	add_child(head2)
	_head_labels = [head, head2]
	_cats_box = HBoxContainer.new()
	_cats_box.position = Vector2(66, 268)
	_cats_box.size = Vector2(760, 44)
	_cats_box.add_theme_constant_override("separation", 0)
	add_child(_cats_box)
	_count = _label("", 16, Color(0.56, 0.64, 0.84), _raj)
	_count.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_count.position = Vector2(700, 268)
	_count.size = Vector2(340, 44)
	add_child(_count)
	var sep := ColorRect.new()
	sep.color = Color(0.62, 0.8, 1.0, 0.22)
	sep.position = Vector2(65, 312)
	sep.size = Vector2(998, 1)
	add_child(sep)
	_scroll = ScrollContainer.new()
	_scroll.position = Vector2(74, 318)
	_scroll.size = Vector2(984, 636)
	_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	_scroll.follow_focus = false
	add_child(_scroll)
	_list = VBoxContainer.new()
	_list.custom_minimum_size = Vector2(966, 0)
	_list.add_theme_constant_override("separation", 2)
	_scroll.add_child(_list)
	# preview
	var stage := Rect2(1100, 194, 756, 430)
	var bg := TextureRect.new()
	var g := Gradient.new()
	g.set_color(0, Color(0.047, 0.078, 0.25))
	g.set_color(1, Color(0.024, 0.04, 0.133))
	var gt := GradientTexture2D.new()
	gt.gradient = g
	gt.fill_to = Vector2(0, 1)
	bg.texture = gt
	bg.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	bg.position = stage.position
	bg.size = stage.size
	add_child(bg)
	var floor_glow := TextureRect.new()
	floor_glow.texture = _radial(Color(0.16, 0.52, 1.0, 0.3))
	floor_glow.position = stage.position + Vector2(0, 230)
	floor_glow.size = Vector2(stage.size.x, 300)
	floor_glow.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(floor_glow)
	var floor_line := NetsuUI.hairline(Vector2(stage.position.x + 30, stage.position.y + stage.size.y * 0.88), stage.size.x - 60, Color(0.62, 0.8, 1.0, 0.75), 2.0, "both")
	add_child(floor_line)
	var clip := Control.new()
	clip.clip_contents = true
	clip.position = stage.position
	clip.size = stage.size
	clip.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(clip)
	_stage = NetsuMoveStage.new()
	_stage.size = stage.size
	clip.add_child(_stage)
	_illus = NetsuCLIllustration.new()
	_illus.size = stage.size
	clip.add_child(_illus)
	_cutin = Control.new()
	_cutin.size = stage.size
	_cutin.mouse_filter = Control.MOUSE_FILTER_IGNORE
	clip.add_child(_cutin)
	var band := Polygon2D.new()
	band.polygon = PackedVector2Array([Vector2(stage.size.x * 0.22, 0), Vector2(stage.size.x * 0.78, 0), Vector2(stage.size.x * 0.62, stage.size.y), Vector2(stage.size.x * 0.06, stage.size.y)])
	band.color = Color(1.0, 0.79, 0.3, 0.2)
	band.name = "Band"
	_cutin.add_child(band)
	_cutin_tex = TextureRect.new()
	_cutin_tex.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_cutin_tex.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	_cutin_tex.size = stage.size
	_cutin.add_child(_cutin_tex)
	_cutin_label = _label("", 44, Color.WHITE, NetsuUI.sans(4, true))
	_cutin_label.position = Vector2(34, stage.size.y - 120)
	_cutin_label.size = Vector2(600, 60)
	_cutin.add_child(_cutin_label)
	_loading = _label("LOADING…", 26, Color(0.62, 0.8, 1.0), _raj)
	_loading.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_loading.size = stage.size
	clip.add_child(_loading)
	_panel(stage, _box(Color(0, 0, 0, 0), Color(0.62, 0.8, 1.0, 0.45)))
	var dot := ColorRect.new()
	dot.color = Color(1.0, 0.16, 0.3)
	dot.position = stage.position + Vector2(16, 20)
	dot.size = Vector2(9, 9)
	add_child(dot)
	_badge = _label("", 17, Color(0.87, 0.94, 1.0), _raj)
	_badge.position = stage.position + Vector2(34, 8)
	_badge.size = Vector2(400, 32)
	add_child(_badge)
	# move info
	_name = _label("", 40, Color.WHITE, NetsuUI.sans(1, true))
	_name.position = Vector2(1104, 640)
	_name.size = Vector2(750, 54)
	_name.clip_text = true
	add_child(_name)
	_tags = HBoxContainer.new()
	_tags.position = Vector2(1104, 698)
	_tags.size = Vector2(750, 28)
	_tags.add_theme_constant_override("separation", 8)
	add_child(_tags)
	_glyphs = NetsuInputGlyphs.new()
	_glyphs.glyph_height = 38.0
	_glyphs.position = Vector2(1104, 734)
	_glyphs.size = Vector2(750, 40)
	add_child(_glyphs)
	_desc = _label("", 19, Color(0.86, 0.89, 0.97), NetsuUI.body())
	_desc.vertical_alignment = VERTICAL_ALIGNMENT_TOP
	_desc.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_desc.position = Vector2(1104, 784)
	_desc.size = Vector2(750, 92)
	_desc.max_lines_visible = 3
	add_child(_desc)
	_grid = GridContainer.new()
	_grid.columns = 6
	_grid.position = Vector2(1104, 884)
	_grid.size = Vector2(750, 70)
	_grid.add_theme_constant_override("h_separation", 8)
	add_child(_grid)
	# footer
	if footer_override.is_empty():
		_own_footer = NetsuUI.footer(self, false, 849.0, 87.0, 885.0, 1600.0, 889.0, overlay)
	_footer_set()


func _radial(col: Color) -> GradientTexture2D:
	var g := Gradient.new()
	g.set_color(0, col)
	g.set_color(1, Color(col, 0.0))
	var t := GradientTexture2D.new()
	t.gradient = g
	t.fill = GradientTexture2D.FILL_RADIAL
	t.fill_from = Vector2(0.5, 0.5)
	t.fill_to = Vector2(1.0, 0.5)
	return t


func _footer() -> Dictionary:
	return footer_override if not footer_override.is_empty() else _own_footer


func _footer_set() -> void:
	var f := _footer()
	if f.is_empty():
		return
	f["prompts"].text = PROMPTS_CHARS if TABS[_tab][0] == "characters" else PROMPTS
	f["text"].text = HINTS[TABS[_tab][0]]


# --- Tabs ------------------------------------------------------------------------------------

func _sub_items() -> Array:
	var out: Array = []
	match TABS[_tab][0]:
		"system":
			for p in NetsuMoveCatalog.system_pages():
				out.append({"label": p["title"], "icon": null})
		"characters":
			for i in MatchSetup.fighter_count():
				var prof = MatchSetup.fighter_profile(i)
				var icon = prof.get("Portrait") if prof.get("Portrait") != null else prof.get("OnlineIcon")
				out.append({"label": str(prof.get("ShortName") if prof.get("ShortName") else prof.get("FighterName")).to_upper(), "icon": icon})
		"assists":
			for i in MatchSetup.assist_count():
				out.append({"label": MatchSetup.assist_name(i).to_upper(), "icon": MatchSetup.assist_icon(i)})
	return out


func _build_tabs() -> void:
	for c in _tabs_box.get_children():
		c.queue_free()
	var x := 0.0
	x = _pill_key(_tabs_box, "LB", x)
	for i in TABS.size():
		var on := i == _tab
		var tab := Control.new()
		tab.position = Vector2(x, 4)
		tab.size = Vector2(300, 54)
		tab.mouse_filter = Control.MOUSE_FILTER_STOP
		var shape := NetsuUI.para(286, 50, 14)
		if on:
			var glow := Polygon2D.new()
			glow.polygon = NetsuUI.para(294, 58, 15)
			glow.position = Vector2(-4, -4)
			glow.color = Color(0.62, 0.8, 1.0, 0.75)
			tab.add_child(glow)
		var body := NetsuUI.poly(shape, Color(0.2, 0.5, 1.0) if on else Color(0.047, 0.078, 0.25, 0.9))
		tab.add_child(body)
		if not on:
			var edge := Line2D.new()
			edge.points = PackedVector2Array([shape[0], shape[1], shape[2], shape[3], shape[0]])
			edge.width = 1.0
			edge.default_color = Color(0.62, 0.8, 1.0, 0.35)
			tab.add_child(edge)
		var l := _label(TABS[i][1], 25, Color.WHITE if on else Color(0.69, 0.73, 0.88), NetsuUI.sans(5, true))
		l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		l.size = Vector2(300, 50)
		tab.add_child(l)
		tab.gui_input.connect(_on_tab_click.bind(i))
		_tabs_box.add_child(tab)
		x += 306
	x = _pill_key(_tabs_box, "RB", x + 4)
	_tabs_box.add_child(NetsuUI.hairline(Vector2(x + 16, 31), 1792 - x - 16, Color(0.62, 0.8, 1.0, 0.7), 2.0, "right"))


func _pill_key(parent: Control, text: String, x: float) -> float:
	var p := PanelContainer.new()
	p.add_theme_stylebox_override("panel", _box(Color(0.97, 0.97, 1.0), Color(0.97, 0.97, 1.0), 17, 0))
	p.position = Vector2(x, 14)
	p.custom_minimum_size = Vector2(52, 34)
	var l := _label(text, 20, Color(0.16, 0.19, 0.42), _raj)
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	p.add_child(l)
	parent.add_child(p)
	return x + 64


func _build_subs() -> void:
	for c in _subs_box.get_children():
		c.queue_free()
	var items := _sub_items()
	var cur: int = _sub[_tab]
	for i in items.size():
		var on := i == cur
		var pill := PanelContainer.new()
		var sb := _box(Color(0.16, 0.52, 1.0, 0.3) if on else Color(0.04, 0.06, 0.18, 0.75),
			Color(0.62, 0.8, 1.0) if on else Color(0.62, 0.8, 1.0, 0.22), 26, 2)
		sb.content_margin_left = 8 if items[i]["icon"] != null else 18
		sb.content_margin_right = 18
		pill.add_theme_stylebox_override("panel", sb)
		pill.custom_minimum_size = Vector2(0, 52)
		pill.mouse_filter = Control.MOUSE_FILTER_STOP
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 10)
		row.mouse_filter = Control.MOUSE_FILTER_IGNORE
		pill.add_child(row)
		if items[i]["icon"] != null:
			var icon := TextureRect.new()
			icon.texture = items[i]["icon"]
			icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
			icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
			icon.custom_minimum_size = Vector2(40, 40)
			icon.size_flags_vertical = Control.SIZE_SHRINK_CENTER
			icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
			row.add_child(icon)
		var l := _label(items[i]["label"], 20, Color.WHITE if on else Color(0.69, 0.73, 0.88), _raj)
		row.add_child(l)
		pill.gui_input.connect(_on_sub_click.bind(i))
		_subs_box.add_child(pill)


func _on_tab_click(event: InputEvent, i: int) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		_set_tab(i)


func _on_sub_click(event: InputEvent, i: int) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		_set_sub(i)


func _set_tab(i: int) -> void:
	i = posmod(i, TABS.size())
	if i == _tab:
		return
	_tab = i
	_audio(0)
	_refresh()


func _set_sub(i: int) -> void:
	var n := _sub_items().size()
	if n == 0:
		return
	i = posmod(i, n)
	if i == _sub[_tab]:
		return
	_sub[_tab] = i
	if TABS[_tab][0] == "characters":
		_system_fighter = i
	_audio(0)
	_refresh()


func _set_cat(i: int) -> void:
	if TABS[_tab][0] != "characters":
		return
	var f: int = _sub[1]
	i = posmod(i, CATS.size())
	# skip categories this fighter has nothing in
	for _n in CATS.size():
		if _cat_count(i) > 0:
			break
		i = posmod(i + (1 if i >= _cat.get(f, 0) else -1), CATS.size())
	if i == _cat.get(f, 0):
		return
	_cat[f] = i
	_audio(0)
	_fill()


func _cat_count(i: int) -> int:
	var n := 0
	for r in _all_rows:
		if r.get("section", "") == CATS[i][0]:
			n += 1
	return n


func _build_cats() -> void:
	for c in _cats_box.get_children():
		c.queue_free()
	var chars: bool = TABS[_tab][0] == "characters"
	_cats_box.visible = chars
	for l in _head_labels:
		l.visible = not chars
	if not chars:
		return
	var cur: int = _cat.get(_sub[1], 0)
	for i in CATS.size():
		var n := _cat_count(i)
		var on := i == cur
		var tab := Control.new()
		tab.custom_minimum_size = Vector2(178, 44)
		tab.mouse_filter = Control.MOUSE_FILTER_STOP
		if on:
			var bg := NetsuUI.gradient_rect(Color(0.16, 0.52, 1.0, 0.05), Color(0.16, 0.52, 1.0, 0.35), true)
			bg.size = Vector2(178, 44)
			tab.add_child(bg)
			var bar := ColorRect.new()
			bar.color = Color(0.45, 0.8, 1.0)
			bar.position = Vector2(10, 41)
			bar.size = Vector2(158, 3)
			tab.add_child(bar)
		var col := Color.WHITE if on else (Color(0.69, 0.73, 0.88) if n > 0 else Color(0.69, 0.73, 0.88, 0.35))
		var l := _label("%s  %d" % [CATS[i][1], n], 18, col, _raj)
		l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		l.size = Vector2(178, 44)
		tab.add_child(l)
		tab.gui_input.connect(_on_cat_click.bind(i))
		_cats_box.add_child(tab)


func _on_cat_click(event: InputEvent, i: int) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT and _cat_count(i) > 0:
		_cat[_sub[1]] = i
		_audio(0)
		_fill()


# --- Content ---------------------------------------------------------------------------------

func _key() -> String:
	return "%d:%d:%d" % [_tab, _sub[_tab], _cat.get(_sub[1], 0) if TABS[_tab][0] == "characters" else 0]


## The fighter the previews put the move against.
func _opp_index() -> int:
	var n := MatchSetup.fighter_count()
	if n <= 0:
		return -1
	if start_opponent >= 0 and start_opponent < n:
		return start_opponent
	var shown: int = _sub[1] if TABS[_tab][0] == "characters" else _system_fighter
	return (shown + 1) % n if n > 1 else 0


## The DataContainers the current page needs: [shown, opponent, caller]. Loaded on threads first if they aren't yet.
func _wanted_paths() -> Array:
	var main := ""
	match TABS[_tab][0]:
		"characters":
			main = NetsuMoveCatalog.fighter_data_path(_sub[1])
		"assists":
			main = NetsuMoveCatalog.assist_data_path(_sub[2])
		_:
			main = NetsuMoveCatalog.fighter_data_path(_system_fighter)
	var opp := NetsuMoveCatalog.fighter_data_path(_opp_index())
	var caller := NetsuMoveCatalog.fighter_data_path(_system_fighter)
	return [main, opp, caller]


func _refresh() -> void:
	_build_tabs()
	_build_subs()
	_footer_set()
	_pending.clear()
	for path in _wanted_paths():
		if path == "" or NetsuMoveCatalog._data_cache.has(path) or path in _pending:
			continue
		if ResourceLoader.has_cached(path):
			NetsuMoveCatalog._data_cache[path] = load(path)
		else:
			_pending.append(path)
			ResourceLoader.load_threaded_request(path)
	_take_data()
	_fill()


func _take_data() -> void:
	var paths := _wanted_paths()
	_data = NetsuMoveCatalog._data_cache.get(paths[0], null)
	_opp = NetsuMoveCatalog._data_cache.get(paths[1], null)
	_caller = NetsuMoveCatalog._data_cache.get(paths[2], null)
	# no other fighter to load (a one-fighter roster, a missing data file): a mirror match
	if _opp == null and not (paths[1] in _pending):
		_opp = _caller if TABS[_tab][0] == "assists" else _data


func _process(_delta: float) -> void:
	if _pending.is_empty():
		return
	var done := false
	for path in _pending.duplicate():
		var status := ResourceLoader.load_threaded_get_status(path)
		if status == ResourceLoader.THREAD_LOAD_LOADED:
			NetsuMoveCatalog._data_cache[path] = ResourceLoader.load_threaded_get(path)
			_pending.erase(path)
			done = true
		elif status == ResourceLoader.THREAD_LOAD_FAILED or status == ResourceLoader.THREAD_LOAD_INVALID_RESOURCE:
			push_warning("Command list: couldn't load " + path)
			_pending.erase(path)
			done = true
	if done and _pending.is_empty():
		_take_data()
		_fill()


func _fill() -> void:
	for c in _list.get_children():
		c.queue_free()
	_row_nodes.clear()
	_rows.clear()
	var who := ""
	match TABS[_tab][0]:
		"system":
			var pages := NetsuMoveCatalog.system_pages()
			if _sub[0] < pages.size():
				_rows = pages[_sub[0]]["rows"]
			if MatchSetup.fighter_count() > _system_fighter:
				who = "SYSTEM · SHOWN WITH " + str(MatchSetup.fighter_profile(_system_fighter).FighterName).to_upper()
		"characters":
			_all_rows = []
			if _data != null:
				_all_rows = NetsuMoveCatalog.fighter_rows(_data, NetsuMoveCatalog.fighter_notes(_sub[1]))
			var f: int = _sub[1]
			if not _cat.has(f) or _cat_count(_cat[f]) == 0:
				_cat[f] = 0
				for i in CATS.size():
					if _cat_count(i) > 0:
						_cat[f] = i
						break
			for r in _all_rows:
				if r["section"] == CATS[_cat[f]][0]:
					_rows.append(r)
			if MatchSetup.fighter_count() > _sub[1]:
				who = str(MatchSetup.fighter_profile(_sub[1]).FighterName).to_upper()
				var aura = MatchSetup.fighter_profile(_sub[1]).get("NetsuAuraColor")
				_glow.texture = _radial(Color(aura, 0.24) if aura is Color and aura.a > 0.01 else Color(0.16, 0.52, 1.0, 0.2))
		"assists":
			var section := ""
			for r in NetsuMoveCatalog.assist_rows(_sub[2]):
				if r["section"] != section:
					section = r["section"]
					_rows.append({"heading": section.to_upper()})
				_rows.append(r)
			who = "ASSIST · " + MatchSetup.assist_name(_sub[2]).to_upper()
	if TABS[_tab][0] != "characters":
		_glow.texture = _radial(Color(0.37, 0.88, 0.63, 0.16) if TABS[_tab][0] == "assists" else Color(0.16, 0.52, 1.0, 0.2))
	_who.text = who + "   ·   PLAYER %d" % (side + 1)
	var moves := 0
	for i in _rows.size():
		var r: Dictionary = _rows[i]
		if r.has("heading"):
			_list.add_child(_heading_node(r["heading"]))
			_row_nodes.append(null)
		else:
			moves += 1
			var node := _row_node(r, i)
			_list.add_child(node)
			_row_nodes.append(node)
	_count.text = ("%d TOPICS" if TABS[_tab][0] == "system" else "%d MOVES") % moves
	_build_cats()
	_count.visible = TABS[_tab][0] != "characters"
	_loading.visible = not _pending.is_empty()
	var sel: int = _sel.get(_key(), _first_move())
	_select(sel, false)
	_scroll.scroll_vertical = 0
	if _row_nodes.size() > sel and _row_nodes[sel] != null:
		_scroll_later(sel)


func _first_move() -> int:
	for i in _rows.size():
		if not _rows[i].has("heading"):
			return i
	return 0


func _heading_node(text: String) -> Control:
	var c := Control.new()
	c.custom_minimum_size = Vector2(966, 48)
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var d := NetsuUI.diamond(5.0, Color(0.55, 0.86, 1.0), Color(0.3, 0.82, 1.0))
	d.position = Vector2(20, 30)
	c.add_child(d)
	var l := _label(text, 20, Color(0.45, 0.8, 1.0), NetsuUI.sans(4))
	l.position = Vector2(36, 12)
	l.size = Vector2(600, 36)
	c.add_child(l)
	var w := NetsuUI.sans(4).get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, 20).x
	c.add_child(NetsuUI.hairline(Vector2(48 + w, 30), 900 - w, Color(0.5, 0.78, 1.0, 0.8), 1.0, "right"))
	return c


func _tag_chip(text: String, fs: int = 14) -> PanelContainer:
	var col: Color = TAG_COLORS.get(text, Color(0.79, 0.84, 1.0))
	if text.contains("BAR"):
		col = TAG_COLORS["SUPER"] if text.contains("BARS") else TAG_COLORS["EX"]
	elif text.contains("INVINCIBLE"):
		col = TAG_COLORS["INVINCIBLE"]
	var p := PanelContainer.new()
	var sb := _box(Color(col, 0.14), col, 3, 1)
	sb.content_margin_left = 8
	sb.content_margin_right = 8
	sb.content_margin_top = 1
	sb.content_margin_bottom = 1
	p.add_theme_stylebox_override("panel", sb)
	p.mouse_filter = Control.MOUSE_FILTER_IGNORE
	p.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	p.add_child(_label(text, fs, col, _raj))
	return p


func _row_tags(r: Dictionary) -> Array:
	var tags: Array = []
	var cost := int(r.get("cost", 0))
	if cost > 0:
		tags.append("%d BAR%s" % [cost, "S" if cost > 1 else ""])
	for t in r.get("tags", []):
		if t != "EX" or cost == 0:
			tags.append(str(t))
	return tags


func _row_node(r: Dictionary, index: int) -> Control:
	var follow: bool = r.get("follow", false)
	var indent := 34.0 if follow else 0.0
	var c := Control.new()
	c.custom_minimum_size = Vector2(966, 96 if follow else 112)
	c.mouse_filter = Control.MOUSE_FILTER_STOP
	var hl := NetsuUI.gradient_rect(Color(0.16, 0.52, 1.0, 0.4), Color(0.16, 0.52, 1.0, 0.04), false)
	hl.name = "Highlight"
	hl.size = Vector2(966, c.custom_minimum_size.y - 4)
	hl.position = Vector2(0, 2)
	hl.visible = false
	c.add_child(hl)
	var edge := ColorRect.new()
	edge.name = "Edge"
	edge.color = Color(0.45, 0.8, 1.0)
	edge.position = Vector2(0, 10)
	edge.size = Vector2(4, c.custom_minimum_size.y - 20)
	edge.visible = false
	c.add_child(edge)
	var line := ColorRect.new()
	line.color = Color(0.62, 0.8, 1.0, 0.1)
	line.position = Vector2(0, c.custom_minimum_size.y - 1)
	line.size = Vector2(966, 1)
	c.add_child(line)
	if follow:
		var hook := Line2D.new()
		hook.points = PackedVector2Array([Vector2(22, 0), Vector2(22, 46), Vector2(34, 46)])
		hook.width = 2.0
		hook.default_color = Color(0.62, 0.8, 1.0, 0.45)
		c.add_child(hook)
	var th_h := 84.0 if follow else 100.0
	var frame := Panel.new()
	frame.add_theme_stylebox_override("panel", _box(Color(0.08, 0.125, 0.33, 0.55), Color(0.62, 0.8, 1.0, 0.3), 3))
	frame.position = Vector2(18 + indent, (c.custom_minimum_size.y - th_h) / 2.0)
	frame.size = Vector2(150 if not follow else 126, th_h)
	frame.mouse_filter = Control.MOUSE_FILTER_IGNORE
	frame.clip_contents = true
	c.add_child(frame)
	var anims := _row_anims(r)
	if not anims.is_empty():
		var still := NetsuAnimPreview.new()
		still.size = frame.size
		var t := NetsuMoveCatalog.timing(anims[0])
		still.still(anims, t["first"] + 1 if t["has"] else -1)
		frame.add_child(still)
	else:
		var glyph := _label(_illus_glyph(r), 30, Color(0.62, 0.8, 1.0, 0.75), NetsuUI.sans(1, true))
		glyph.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		glyph.size = frame.size
		frame.add_child(glyph)
	var x := frame.position.x + frame.size.x + 22
	var top := HBoxContainer.new()
	top.position = Vector2(x, 12 if not follow else 8)
	top.size = Vector2(966 - x - 40, 36)
	top.add_theme_constant_override("separation", 10)
	top.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var name_l := _label(r["name"], 29 if not follow else 25, Color(0.89, 0.91, 0.98), _raj)
	name_l.name = "Name"
	top.add_child(name_l)
	for t in _row_tags(r):
		top.add_child(_tag_chip(t))
	c.add_child(top)
	var gl := NetsuInputGlyphs.new()
	gl.glyph_height = 30.0 if not follow else 26.0
	gl.text = r.get("input", "")
	gl.position = Vector2(x, 60 if not follow else 52)
	gl.size = Vector2(700, gl.glyph_height)
	c.add_child(gl)
	var chev := _label("›", 30, Color(0.62, 0.8, 1.0, 0.25), NetsuUI.sans(0))
	chev.name = "Chev"
	chev.position = Vector2(924, 0)
	chev.size = Vector2(30, c.custom_minimum_size.y)
	c.add_child(chev)
	c.gui_input.connect(_on_row_input.bind(index))
	return c


func _illus_glyph(r: Dictionary) -> String:
	var p: Dictionary = r.get("preview", {})
	match str(p.get("illustration", "")):
		"gauge":
			return "CP"
		"scaling":
			return "%"
		"levels":
			return "LV"
		"overdrive":
			return "OD"
		"juggle":
			return "J"
	if p.has("cutin"):
		return "EX" if str(p["cutin"]) == "ex" else "S"
	return "◆"


## What a row plays: {"data", "states", "air", "assist"}. Its states in the fighter's / assist's data, or a system
## topic's / calling row's move, played by the fighter. Empty data = nothing to play.
func _row_source(r: Dictionary) -> Dictionary:
	var p: Dictionary = r.get("preview", {})
	if p.has("illustration") or p.has("cutin"):
		return {"data": null, "states": [], "air": false, "assist": false, "plan": [], "move": null}
	var src := _data
	var assist: bool = TABS[_tab][0] == "assists"
	if (p.has("move") or p.has("moves") or p.has("state")) and assist:
		src = _caller   # a calling row: played by the fighter, not the assist
		assist = false
	var states: Array = r.get("states", [])
	var air: bool = r.get("air", false) and not r.has("play")
	var plan: Array = r.get("play", [])
	var mv = r.get("move", null)
	if src != null and (p.has("move") or p.has("moves")):
		# Nov 2: System topics play the move the way the game gets there (a jump before an air dash, ...);
		# "moves" plays several one after another
		var names: Array = p["moves"] if p.has("moves") else [p["move"]]
		plan = []
		states = []
		for n in names:
			var m := NetsuMoveCatalog.move_named(src, str(n))
			if m == null:
				continue
			var part := NetsuMoveCatalog.preview_plan(src, m)
			for e in plan:
				e.erase("show")
			plan.append_array(part)
			mv = m
			states.append_array(NetsuMoveCatalog.states_of_move(src, str(n)))
		air = false
	elif src != null and p.has("state"):
		var s := NetsuMoveCatalog.state_by_name(src, str(p["state"]))
		states = [s] if s >= 0 else []
		plan = []
	if plan.is_empty():
		for i in states.size():
			plan.append({"state": int(states[i]), "show": i == 0})
	return {"data": src, "states": states, "air": air, "assist": assist, "plan": plan, "move": mv}


## The AnimationData list a row's still comes from.
func _row_anims(r: Dictionary) -> Array:
	var src := _row_source(r)
	if src["data"] == null:
		return []
	return NetsuMoveCatalog.anim_list(src["data"], src["states"])


## Plays a row on the stage: the move against the opponent (an assist with its caller beside her).
func _play_row(r: Dictionary) -> bool:
	var src := _row_source(r)
	if src["data"] == null or ((src["states"] as Array).is_empty() and (src["plan"] as Array).is_empty()):
		_stage.clear()
		return false
	var sim := NetsuMoveSim.new()
	sim.spawn_resolver = _spawn_list
	if src["assist"]:
		var spawn: Vector2i = r.get("spawn", Vector2i(-9000, 0))
		sim.setup(src["data"], src["states"], _opp, false, -1, spawn.x)
		if _caller != null:
			var call := NetsuMoveCatalog.state_by_name(_caller, "Assist Call")
			sim.add_extra(_caller, call if call >= 0 else 0, Vector2i(0, 0), 1)
	else:
		sim.setup(src["data"], src["plan"], _opp, src["air"], -1, 0, {"move": src["move"], "name": str(r.get("name", ""))})
	sim.record()
	_stage.show_sim(sim)
	return true


## A fighter's (or assist's) SpawnablesList, read from its scene's root (the engine's ObjectPool uses the same).
func _spawn_list(data: Resource) -> Resource:
	if data == null:
		return null
	var key := str(data.resource_path)
	if _spawn_lists.has(key):
		return _spawn_lists[key]
	var scene: PackedScene = null
	for i in MatchSetup.fighter_count():
		if NetsuMoveCatalog.fighter_data_path(i) == key:
			scene = MatchSetup.palette_scene(i, 0)
	if scene == null:
		var list = MatchSetup.assists()
		for i in MatchSetup.assist_count():
			if NetsuMoveCatalog.assist_data_path(i) == key:
				scene = list.Assists[i].get("Instance")
	var out: Resource = null
	if scene != null:
		var st := scene.get_state()
		for pi in st.get_node_property_count(0):
			if st.get_node_property_name(0, pi) == "SpawnablesList":
				out = st.get_node_property_value(0, pi)
	_spawn_lists[key] = out
	return out


func _on_row_input(event: InputEvent, index: int) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		if index == _sel.get(_key(), -1):
			_stage.restart()
		else:
			_select(index)


func _select(index: int, sound: bool = true) -> void:
	if _rows.is_empty():
		_show_row({})
		return
	index = clampi(index, 0, _rows.size() - 1)
	if _rows[index].has("heading"):
		index = _first_move()
	_sel[_key()] = index
	for i in _row_nodes.size():
		var n: Control = _row_nodes[i]
		if n == null:
			continue
		var on := i == index
		n.get_node("Highlight").visible = on
		n.get_node("Edge").visible = on
		(n.get_node("Chev") as Label).add_theme_color_override("font_color", Color(0.62, 0.8, 1.0) if on else Color(0.62, 0.8, 1.0, 0.25))
	_show_row(_rows[index])
	if sound:
		_audio(0)


## After a page is rebuilt: wait for the new rows to be laid out, then bring the picked one into view.
func _scroll_later(index: int) -> void:
	await get_tree().process_frame
	await get_tree().process_frame
	if is_inside_tree():
		_scroll_to(index)


func _scroll_to(index: int) -> void:
	if index < 0 or index >= _row_nodes.size() or _row_nodes[index] == null or not is_instance_valid(_row_nodes[index]):
		return
	var n: Control = _row_nodes[index]
	var top := n.position.y
	var bottom := top + n.size.y
	var view := _scroll.size.y
	var cur := float(_scroll.scroll_vertical)
	if top - 48.0 < cur:
		cur = top - 48.0   # keep the section heading above it in view
	elif bottom + 8.0 > cur + view:
		cur = bottom + 8.0 - view
	_scroll.scroll_vertical = int(maxf(0.0, cur))


func _step(dir: int) -> void:
	var cur: int = _sel.get(_key(), _first_move())
	var n := _rows.size()
	if n == 0:
		return
	var i := cur
	for _k in n:
		i = posmod(i + dir, n)
		if not _rows[i].has("heading"):
			break
	_select(i)
	_scroll_to(i)


func _show_row(r: Dictionary) -> void:
	_name.text = r.get("name", "")
	for c in _tags.get_children():
		c.queue_free()
	for t in _row_tags(r):
		_tags.add_child(_tag_chip(t, 16))
	_glyphs.text = r.get("input", "")
	_desc.text = r.get("desc", "")
	_desc.add_theme_color_override("font_color", Color(0.66, 0.7, 0.83) if r.get("auto_desc", false) else Color(0.86, 0.89, 0.97))
	for c in _grid.get_children():
		c.queue_free()
	for d in r.get("data", []).slice(0, 6):
		var cell := PanelContainer.new()
		var sb := _box(Color(0.04, 0.06, 0.18, 0.85), Color(0.62, 0.8, 1.0, 0.25), 4)
		sb.content_margin_left = 10
		sb.content_margin_top = 6
		sb.content_margin_bottom = 6
		cell.add_theme_stylebox_override("panel", sb)
		cell.custom_minimum_size = Vector2(118, 64)
		var v := VBoxContainer.new()
		v.add_theme_constant_override("separation", 0)
		v.add_child(_label(str(d[0]), 14, Color(0.56, 0.64, 0.84), _raj))
		var val := str(d[1])
		var col := Color.WHITE
		if val.begins_with("−") or val.begins_with("-"):
			col = Color(1.0, 0.56, 0.63)
		elif val.begins_with("+"):
			col = Color(0.49, 0.94, 0.7)
		var vl := _label(val, 22 if val.length() < 9 else 17, col, NetsuUI.sans(0))
		vl.clip_text = true
		v.add_child(vl)
		cell.add_child(v)
		_grid.add_child(cell)
	# the preview
	var p: Dictionary = r.get("preview", {})
	_stage.visible = false
	_illus.visible = false
	_cutin.visible = false
	_illus.kind = ""
	if p.has("illustration"):
		_illus.kind = str(p["illustration"])
		if _data != null and _data.get("MaxSuperGauge") != null:
			_illus.bars = maxi(1, int(_data.get("MaxSuperGauge")) / NetsuMoveCatalog.BAR)
		_illus.visible = true
		_badge.text = "EXAMPLE"
	elif p.has("cutin"):
		var path := NetsuMoveCatalog.fighter_dir(_system_fighter).path_join("Artwork/CutIn_%s.png" % ("EX" if str(p["cutin"]) == "ex" else "Super"))
		_cutin_tex.texture = load(path) if ResourceLoader.exists(path) else null
		_cutin_label.text = "EX CRAFT" if str(p["cutin"]) == "ex" else "S-CRAFT"
		(_cutin.get_node("Band") as Polygon2D).color = Color(1.0, 0.79, 0.3, 0.22) if str(p["cutin"]) == "ex" else Color(1.0, 0.16, 0.3, 0.24)
		_cutin.visible = true
		_badge.text = "CUT-IN"
	else:
		_stage.visible = true
		if _play_row(r):
			_badge.text = "THOR'S HALL · LIVE PREVIEW" + ("" if _opp != null else " · NO OPPONENT")
		else:
			_badge.text = "NO PREVIEW"
	_loading.visible = not _pending.is_empty()


# --- Input -----------------------------------------------------------------------------------

func _input(event: InputEvent) -> void:
	if not is_visible_in_tree():
		return
	var handled := true
	var tab_dir := _tab_event(event)
	var trigger_dir := _trigger_event(event)
	if event.is_action_pressed("ui_cancel"):
		_audio(1)
		closed.emit()
	elif event.is_action_pressed("ui_down", true):
		_step(1)
	elif event.is_action_pressed("ui_up", true):
		_step(-1)
	elif event.is_action_pressed("ui_left", true):
		if TABS[_tab][0] == "characters":
			_set_cat(_cat.get(_sub[1], 0) - 1)
		else:
			_set_sub(_sub[_tab] - 1)
	elif event.is_action_pressed("ui_right", true):
		if TABS[_tab][0] == "characters":
			_set_cat(_cat.get(_sub[1], 0) + 1)
		else:
			_set_sub(_sub[_tab] + 1)
	elif event.is_action_pressed("ui_accept"):
		_stage.restart()
		_audio(1)
	elif tab_dir != 0:
		_set_tab(_tab + tab_dir)
	elif trigger_dir != 0:
		_set_sub(_sub[_tab] + trigger_dir)
	else:
		handled = event.is_action("ui_up") or event.is_action("ui_down") or event.is_action("ui_left") \
			or event.is_action("ui_right") or event.is_action("ui_accept") or event.is_action("ui_cancel") or event.is_action("pause")
	if handled:
		get_viewport().set_input_as_handled()


## -1 / +1 for "previous / next tab": LB / RB, Q / E, Shift+Tab / Tab.
func _tab_event(event: InputEvent) -> int:
	if event is InputEventJoypadButton and event.pressed:
		if event.button_index == JOY_BUTTON_LEFT_SHOULDER:
			return -1
		if event.button_index == JOY_BUTTON_RIGHT_SHOULDER:
			return 1
	if event is InputEventKey and event.pressed and not event.echo:
		match event.physical_keycode:
			KEY_Q:
				return -1
			KEY_E:
				return 1
			KEY_TAB:
				return -1 if event.shift_pressed else 1
	return 0


## -1 / +1 for LT / RT pulled past halfway (each pull counts once), or Page Up / Page Down.
func _trigger_event(event: InputEvent) -> int:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.physical_keycode == KEY_PAGEUP:
			return -1
		if event.physical_keycode == KEY_PAGEDOWN:
			return 1
	if not event is InputEventJoypadMotion:
		return 0
	var i := -1
	if event.axis == JOY_AXIS_TRIGGER_LEFT:
		i = 0
	elif event.axis == JOY_AXIS_TRIGGER_RIGHT:
		i = 1
	if i < 0:
		return 0
	var down: bool = event.axis_value > 0.6
	if down and not _trigger[i]:
		_trigger[i] = true
		return -1 if i == 0 else 1
	if event.axis_value < 0.3:
		_trigger[i] = false
	return 0


func _audio(index: int) -> void:
	var audio := get_node_or_null("/root/AudioManager")
	if audio and audio.has_method("PlayMenuClip"):
		audio.call("PlayMenuClip", index)
