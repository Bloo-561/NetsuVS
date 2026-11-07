class_name NetsuCustomize
extends Control
## CUSTOMIZE (Main Menu > CUSTOMIZE, Nov 4 2026). How you look to the others online, and who greets you on the main
## menu. Opens over the whole main menu (like the command list) and uses the main menu's footer.
##
##   left:   your PROFILE CARD (NetsuProfileCard: icon, name, title; what the others see in online lobbies; while
##           you browse it previews what's under the cursor), the three rows ICON / TITLE / MENU CHARACTER with what's
##           set, and a box about the thing under the cursor.
##   right:  the picker of the row you're on: ICON and TITLE are paged grids, MENU CHARACTER a list (RANDOM SELECT,
##           then every fighter) next to the fighter's render.
##
##   rows:    Up / Down  row        A  into its picker              B  back to the main menu
##   picker:  directions  move      Left / Right past the edge, LB / RB (Q / E, Page Up / Down, LT / RT)  page
##            A  set it (it's saved at once)                         B  back to the rows
## Works with the keyboard and controllers through Godot's ui_ actions (Controls adds every player's keys and buttons
## to them: J / K, Numpad 4 / 5, X / Y...). Nothing is typed here, so the ui_cancel keys (K, L, Backspace...) just go
## back. The name on the card is ONLINE > NAME.
## What's set lives in GameSettings "profile" ("icon", "title", "menu_character"); the icons and titles are listed in
## ProfileCatalog (game/ui/profile/profile_catalog.gd: how to add some is at its top).
## Emits closed(menu_character_changed) when you back out; the main menu frees it.

signal closed(menu_character_changed: bool)

const TABS := [["icon", "ICON"], ["title", "TITLE"], ["menu", "MENU CHARACTER"]]
const CARD := Rect2(80, 150, 570, 280)
const ROWS_Y := 470.0
const ROW_H := 70.0
const ROW_STEP := 78.0
const INFO := Rect2(80, 712, 570, 228)
const PANEL := Rect2(690, 150, 1150, 790)
const GRID_TOP := 244.0
const GRID_BOTTOM := 872.0
const ICON_COLS := 6
const ICON_ROWS := 3
const ICON_CELL := 150.0
const TITLE_COLS := 2
const TITLE_ROWS := 5
const TITLE_SIZE := Vector2(470, 66)
const LIST_ROWS := 6
const GOLD := Color(1.0, 0.84, 0.4)

## Set by the host before add_child: the main menu's footer ({"text", "prompts"}); {} = this screen makes its own.
var footer_override: Dictionary = {}

var _tab := 0
var _in_picker := false
var _cursor := {0: 0, 1: 0, 2: 0}   # tab -> index into that tab's items
var _set := {}                      # tab -> what's set (icon id, title id, "random" / fighter index)
var _mc_at_open = null
var _footer: Dictionary
var _card: NetsuProfileCard
var _rows: Array = []               # [{"root", "bar", "label", "value", "diamond"}]
var _info := {}
var _content: Control               # the picker (rebuilt on a new tab / page)
var _cells: Array = []              # the picker's cells on this page: [{"index", "rect", "node"...}]
var _cursor_frame: Node2D
var _page_label: Label
var _arrows: Array = []
var _pager: Array = []              # the page line and arrows (hidden when there's only one page)
var _caption: Label
var _big := {}                      # MENU CHARACTER: the render and name on the right
var _flash_t := 0.0
var _trigger := [false, false]


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	mouse_filter = Control.MOUSE_FILTER_STOP
	size = Vector2(1920, 1080)
	_set = {0: ProfileCatalog.my_icon(), 1: ProfileCatalog.my_title(), 2: ProfileCatalog.my_menu_character()}
	_mc_at_open = _set[2]
	for t in 3:
		_cursor[t] = maxi(0, _items(t).find(_set[t]))
	_build()
	_show_tab(0)
	NetsuUI.cascade(self, 3)


func _process(delta: float) -> void:
	if _flash_t > 0.0:
		_flash_t = maxf(0.0, _flash_t - delta)
		if _flash_t == 0.0:
			_refresh_footer()


# --- What each tab lists ------------------------------------------------------------------------------------

## The tab's entries: icon ids, title ids, or "random" then fighter indices.
func _items(tab: int) -> Array:
	var out := []
	match tab:
		0:
			for e in ProfileCatalog.ICONS:
				out.append(e["id"])
		1:
			for e in ProfileCatalog.TITLES:
				out.append(e["id"])
		2:
			out.append("random")
			for i in MatchSetup.fighter_count():
				out.append(i)
	return out


func _per_page(tab: int) -> int:
	return [ICON_COLS * ICON_ROWS, TITLE_COLS * TITLE_ROWS, LIST_ROWS][tab]


func _cols(tab: int) -> int:
	return [ICON_COLS, TITLE_COLS, 1][tab]


func _pages(tab: int) -> int:
	return maxi(1, ceili(float(_items(tab).size()) / _per_page(tab)))


func _page(tab: int) -> int:
	return int(_cursor[tab]) / _per_page(tab)


func _unlocked(tab: int, item) -> bool:
	match tab:
		0:
			return ProfileCatalog.is_unlocked(ProfileCatalog.icon(str(item)))
		1:
			return ProfileCatalog.is_unlocked(ProfileCatalog.title(str(item)))
	return true


func _fighter_name(i: int, full := false) -> String:
	if i < 0 or i >= MatchSetup.fighter_count():
		return "?"
	var prof = MatchSetup.fighter_profile(i)
	return String(prof.FighterName if full else prof.ShortName) if prof else "?"


## What a row says is set.
func _value_text(tab: int) -> String:
	var v = _set[tab]
	match tab:
		0:
			var e := ProfileCatalog.icon(str(v))
			return str(e["name"]) if str(e.get("group", "")) in ["GAME", "ASSIST", "ART"] \
				else "%s · %s" % [str(e["group"]).capitalize(), str(e["name"])]
		1:
			return str(ProfileCatalog.title(str(v)).get("text", ""))
	return _fighter_name(v) if v is int else "Random Select"


## A fighter's face: their select-screen Portrait as a square from its top middle (like the select screen's slots).
func _face(i: int) -> Texture2D:
	if i < 0 or i >= MatchSetup.fighter_count():
		return null
	var prof = MatchSetup.fighter_profile(i)
	var portrait = prof.get("Portrait") if prof else null
	if portrait is Texture2D:
		var ts: Vector2 = portrait.get_size()
		var side := minf(ts.x, ts.y * 0.885)
		var crop := AtlasTexture.new()
		crop.atlas = portrait
		crop.region = Rect2((ts.x - side) / 2.0, ts.y * 0.03, side, side)
		return crop
	return prof.get("OnlineIcon") if prof and prof.get("OnlineIcon") is Texture2D else null


# --- Building -------------------------------------------------------------------------------------------------

func _build() -> void:
	NetsuUI.picture(self, NetsuUI.MENU_BG)
	var shade := ColorRect.new()
	shade.color = Color(0.02, 0.03, 0.12, 0.6)
	shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(shade)
	NetsuUI.full_rect(shade)
	var p1 := NetsuUI.gradient_rect(Color(NetsuUI.BLUE, 0.16), Color(NetsuUI.BLUE, 0.0), false)   # player 1's light
	p1.size = Vector2(760, 1080)
	add_child(p1)
	NetsuUI.header(self, "CUSTOMIZE")
	# the profile card
	_card = NetsuProfileCard.new()
	_card.position = CARD.position
	_card.size = CARD.size
	add_child(_card)
	# the rows
	for t in TABS.size():
		var r := {}
		var root := Control.new()
		root.mouse_filter = Control.MOUSE_FILTER_IGNORE
		root.position = Vector2(CARD.position.x, ROWS_Y + t * ROW_STEP)
		root.size = Vector2(CARD.size.x, ROW_H)
		add_child(root)
		r["root"] = root
		r["bar"] = NetsuUI.row_bar(Vector2(CARD.size.x, ROW_H))
		root.add_child(r["bar"])
		root.add_child(NetsuUI.hairline(Vector2(10, ROW_H + 4), CARD.size.x - 20, Color(0.55, 0.75, 1.0, 0.3), 1.0))
		r["label"] = _lbl(root, TABS[t][1], 32, NetsuUI.DIM, NetsuUI.serif(600, 1), Rect2(52, 0, 300, ROW_H))
		r["value"] = _lbl(root, "", 19, NetsuUI.DIM, NetsuUI.sans(2), Rect2(300, 0, CARD.size.x - 324, ROW_H), HORIZONTAL_ALIGNMENT_RIGHT)
		r["value"].clip_text = true
		r["value"].text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
		r["diamond"] = Vector2(28, ROW_H / 2.0)
		_rows.append(r)
	# the info box (what's under the cursor)
	NetsuUI.frame_panel(self, INFO)
	_info["group"] = _lbl(self, "", 19, NetsuUI.CYAN, NetsuUI.sans(6), Rect2(INFO.position.x + 28, INFO.position.y + 18, INFO.size.x - 56, 28))
	_info["name"] = _lbl(self, "", 40, Color.WHITE, NetsuUI.serif(700, 1), Rect2(INFO.position.x + 28, INFO.position.y + 48, INFO.size.x - 56, 56))
	_info["name"].clip_text = true
	_info["name"].text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	NetsuUI.glow(_info["name"], Color(0.25, 0.5, 1.0, 0.35), 6)
	_info["about"] = _lbl(self, "", 21, NetsuUI.TEXT, NetsuUI.body(), Rect2(INFO.position.x + 28, INFO.position.y + 108, INFO.size.x - 56, 64),
		HORIZONTAL_ALIGNMENT_LEFT, VERTICAL_ALIGNMENT_TOP)
	_info["about"].autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_info["state"] = _lbl(self, "", 19, GOLD, NetsuUI.sans(5), Rect2(INFO.position.x + 28, INFO.end.y - 46, INFO.size.x - 56, 28))
	# the picker's frame
	NetsuUI.frame_panel(self, PANEL)
	_caption = _lbl(self, "", 22, NetsuUI.CYAN, NetsuUI.sans(6), Rect2(PANEL.position.x + 40, PANEL.position.y + 18, 700, 36))
	NetsuUI.divider(self, PANEL.position.x + 30, PANEL.end.x - 30, PANEL.position.y + 64)
	_content = Control.new()
	_content.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_content)
	NetsuUI.full_rect(_content)
	_cursor_frame = Node2D.new()
	add_child(_cursor_frame)
	# page: —— PAGE 1 / 2 ——  and the arrows at the edges
	var py := PANEL.end.y - 38.0
	_page_label = _lbl(self, "", 20, NetsuUI.TEXT, NetsuUI.sans(5), Rect2(PANEL.get_center().x - 120, py - 16, 240, 32), HORIZONTAL_ALIGNMENT_CENTER)
	_pager.append(_page_label)
	for s: float in [-1.0, 1.0]:
		var hl := NetsuUI.hairline(Vector2(PANEL.get_center().x + (s * 130.0 if s > 0 else -230.0), py), 100, Color(0.6, 0.8, 1.0, 0.7), 1.5,
			"left" if s < 0 else "right")
		add_child(hl)
		_pager.append(hl)
	for s in [-1, 1]:
		var a := NetsuUI.arrow(Vector2(PANEL.position.x + 34 if s < 0 else PANEL.end.x - 34, (GRID_TOP + GRID_BOTTOM) / 2.0), 46.0, s,
			Color(0.85, 0.93, 1.0), 4.0)
		add_child(a)
		_arrows.append(a)
		_pager.append(a)
	if footer_override.is_empty():
		_footer = NetsuUI.footer(self, true)
	else:
		_footer = footer_override


func _lbl(parent: Node, text: String, fs: int, col: Color, font: Font, rect: Rect2,
		al := HORIZONTAL_ALIGNMENT_LEFT, val := VERTICAL_ALIGNMENT_CENTER) -> Label:
	var l := NetsuUI.label(text, fs, col, font)
	l.position = rect.position
	l.size = rect.size
	l.horizontal_alignment = al
	l.vertical_alignment = val
	parent.add_child(l)
	return l


## The gold SET tag (what's set now), its right edge at `right`.
func _set_tag(parent: Node, right: Vector2, small := false) -> void:
	var w := 58.0 if small else 70.0
	var h := 24.0 if small else 28.0
	var pts := NetsuUI.para(w, h, 8.0)
	var tag := Node2D.new()
	tag.position = right - Vector2(w + 8.0, 0)
	tag.add_child(NetsuUI.poly(pts, Color(GOLD, 0.95)))
	tag.add_child(NetsuUI.outline(pts, Color(1.0, 0.96, 0.8), 1.5))
	parent.add_child(tag)
	var l := _lbl(parent, "SET", 15 if small else 17, Color(0.16, 0.1, 0.02), NetsuUI.sans(4), Rect2(tag.position, Vector2(w + 8.0, h)),
		HORIZONTAL_ALIGNMENT_CENTER)
	l.add_theme_constant_override("outline_size", 0)


# --- The tabs and pages ---------------------------------------------------------------------------------------

func _show_tab(t: int) -> void:
	_tab = wrapi(t, 0, TABS.size())
	_flash_t = 0.0
	_build_page()
	_refresh()


## The picker for the current tab and page.
func _build_page() -> void:
	for c in _content.get_children():
		c.queue_free()
	_cells = []
	_big = {}
	var items := _items(_tab)
	var per := _per_page(_tab)
	var first := _page(_tab) * per
	var count := mini(per, items.size() - first)
	match _tab:
		0:
			_build_icons(items, first, count)
		1:
			_build_titles(items, first, count)
		2:
			_build_list(items, first, count)


func _grid_origin(cols: int, rows: int, cell: Vector2, gap: Vector2) -> Vector2:
	var w := cols * cell.x + (cols - 1) * gap.x
	var h := rows * cell.y + (rows - 1) * gap.y
	return Vector2(PANEL.get_center().x - w / 2.0, (GRID_TOP + GRID_BOTTOM) / 2.0 - h / 2.0)


func _build_icons(items: Array, first: int, count: int) -> void:
	var cell := Vector2(ICON_CELL, ICON_CELL + 30.0)
	var gap := Vector2(24, 26)
	var o := _grid_origin(ICON_COLS, ICON_ROWS, cell, gap)
	for k in count:
		var id: String = items[first + k]
		var e := ProfileCatalog.icon(id)
		var pos := o + Vector2((k % ICON_COLS) * (cell.x + gap.x), (k / ICON_COLS) * (cell.y + gap.y))
		var r := Rect2(pos, Vector2(ICON_CELL, ICON_CELL))
		var base := ColorRect.new()
		base.color = Color(0.04, 0.05, 0.14, 0.95)
		base.position = r.position
		base.size = r.size
		base.mouse_filter = Control.MOUSE_FILTER_IGNORE
		_content.add_child(base)
		var open := ProfileCatalog.is_unlocked(e)
		if open:
			var pic := TextureRect.new()
			pic.position = r.position
			pic.size = r.size
			pic.mouse_filter = Control.MOUSE_FILTER_IGNORE
			ProfileCatalog.apply_icon(pic, id)
			_content.add_child(pic)
		else:
			_lbl(_content, "?", 84, Color(0.6, 0.66, 0.85, 0.7), NetsuUI.serif(700), r, HORIZONTAL_ALIGNMENT_CENTER)
		_content.add_child(NetsuUI.outline(_corners(r), Color(0.92, 0.94, 1.0, 0.75), 1.5))
		var name := str(e["name"]) if open else "? ? ?"
		if open and not str(e.get("group", "")) in ["GAME", "ASSIST", "ART"]:
			name = "%s · %s" % [str(e["group"]).capitalize(), name]
		var l := _lbl(_content, name, 16, NetsuUI.DIM, NetsuUI.sans(1), Rect2(pos.x - 8, r.end.y + 4, ICON_CELL + 16, 24), HORIZONTAL_ALIGNMENT_CENTER)
		_shrink(l, 16, 12)
		if id == str(_set[0]):
			_set_tag(_content, Vector2(r.end.x + 4, r.position.y - 10), true)
		_cells.append({"index": first + k, "rect": r.grow(6), "label": l})


func _build_titles(items: Array, first: int, count: int) -> void:
	var gap := Vector2(44, 40)
	var o := _grid_origin(TITLE_COLS, TITLE_ROWS, TITLE_SIZE, gap)
	for k in count:
		var id: String = items[first + k]
		var pos := o + Vector2((k % TITLE_COLS) * (TITLE_SIZE.x + gap.x), (k / TITLE_COLS) * (TITLE_SIZE.y + gap.y))
		var plate := NetsuTitlePlate.new()
		plate.position = pos
		plate.size = TITLE_SIZE
		plate.title_id = id
		_content.add_child(plate)
		if id == str(_set[1]):
			_set_tag(_content, Vector2(pos.x + TITLE_SIZE.x - 30, pos.y - 14), true)
		_cells.append({"index": first + k, "rect": Rect2(pos, TITLE_SIZE).grow_individual(4, 8, 4, 8), "plate": plate})


func _build_list(items: Array, first: int, count: int) -> void:
	var x0 := PANEL.position.x + 70.0
	var w := 520.0
	var h := 86.0
	var step := 100.0
	var y0 := GRID_TOP + 6.0
	for k in count:
		var item = items[first + k]
		var y := y0 + k * step
		var skew := 22.0
		var shape := NetsuUI.para(w, h, skew)
		var slot := Node2D.new()
		slot.position = Vector2(x0, y)
		var fill := Polygon2D.new()
		fill.polygon = shape
		fill.vertex_colors = PackedColorArray([Color(0.06, 0.1, 0.32, 0.92), Color(0.05, 0.08, 0.26, 0.85),
			Color(0.03, 0.05, 0.18, 0.88), Color(0.03, 0.05, 0.2, 0.95)])
		slot.add_child(fill)
		var glow := NetsuUI.outline(shape, Color(0.35, 0.7, 1.0, 0.35), 9.0)
		slot.add_child(glow)
		var edge := NetsuUI.outline(shape, Color(0.62, 0.8, 1.0, 0.55), 1.5)
		slot.add_child(edge)
		_content.add_child(slot)
		var face_r := Rect2(x0 + w - 104, y + 6, 74, 74)
		var base := ColorRect.new()
		base.color = Color(0.04, 0.05, 0.12, 0.95)
		base.position = face_r.position
		base.size = face_r.size
		base.mouse_filter = Control.MOUSE_FILTER_IGNORE
		_content.add_child(base)
		var label := ""
		if item is int:
			var pic := TextureRect.new()
			pic.texture = _face(item)
			pic.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
			pic.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
			pic.position = face_r.position
			pic.size = face_r.size
			pic.mouse_filter = Control.MOUSE_FILTER_IGNORE
			_content.add_child(pic)
			label = _fighter_name(item).to_upper()
		else:
			_lbl(_content, "?", 50, Color(0.75, 0.82, 1.0, 0.85), NetsuUI.serif(700), face_r, HORIZONTAL_ALIGNMENT_CENTER)
			label = "RANDOM SELECT"
		_content.add_child(NetsuUI.outline(_corners(face_r), Color(0.92, 0.94, 1.0, 0.8), 1.5))
		var l := _lbl(_content, label, 34, NetsuUI.TEXT, NetsuUI.serif(700, 2), Rect2(x0 + 40, y, w - 170, h))
		if _same(item, _set[2]):
			_set_tag(_content, Vector2(face_r.end.x + 12, face_r.end.y - 16), true)
		_cells.append({"index": first + k, "rect": Rect2(x0 - 6, y - 6, w + skew + 12, h + 12), "label": l, "fill": fill, "edge": edge,
			"glow": glow})
	# the big picture on the right: the fighter's render, or RANDOM SELECT
	var area := Rect2(PANEL.position.x + 640, GRID_TOP - 20, PANEL.end.x - 30 - (PANEL.position.x + 640), GRID_BOTTOM - GRID_TOP + 40)
	var clip := Control.new()
	clip.clip_contents = true
	clip.position = area.position
	clip.size = area.size
	clip.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_content.add_child(clip)
	var glow := NetsuUI.gradient_rect(Color(NetsuUI.BLUE, 0.0), Color(NetsuUI.BLUE, 0.22), true)
	glow.size = area.size
	clip.add_child(glow)
	var render := TextureRect.new()
	render.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	render.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	render.mouse_filter = Control.MOUSE_FILTER_IGNORE
	clip.add_child(render)
	var rnd := _lbl(clip, "RANDOM\nSELECT", 92, Color.WHITE, NetsuUI.serif(700, 4), Rect2(0, 60, area.size.x, 300), HORIZONTAL_ALIGNMENT_CENTER)
	NetsuUI.glow(rnd, Color(0.3, 0.5, 1.0, 0.55), 12)
	rnd.add_theme_constant_override("line_spacing", -10)
	var faces := Control.new()
	faces.mouse_filter = Control.MOUSE_FILTER_IGNORE
	clip.add_child(faces)
	var n := MatchSetup.fighter_count()
	var fw := 84.0
	for i in n:
		var fr := Rect2(area.size.x / 2.0 - (n * (fw + 14) - 14) / 2.0 + i * (fw + 14), 390, fw, fw)
		var b := ColorRect.new()
		b.color = Color(0.04, 0.05, 0.12, 0.95)
		b.position = fr.position
		b.size = fr.size
		faces.add_child(b)
		var f := TextureRect.new()
		f.texture = _face(i)
		f.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		f.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
		f.position = fr.position
		f.size = fr.size
		faces.add_child(f)
		faces.add_child(NetsuUI.outline(_corners(fr), Color(0.92, 0.94, 1.0, 0.8), 1.5))
	var shade := NetsuUI.gradient_rect(Color(0.02, 0.03, 0.12, 0.0), Color(0.02, 0.03, 0.12, 0.9), true)
	shade.position = Vector2(0, area.size.y - 200)
	shade.size = Vector2(area.size.x, 200)
	clip.add_child(shade)
	var name := _lbl(clip, "", 64, Color.WHITE, NetsuUI.serif(700, 3), Rect2(0, area.size.y - 140, area.size.x, 76), HORIZONTAL_ALIGNMENT_CENTER)
	NetsuUI.glow(name, Color(0.3, 0.5, 1.0, 0.5), 10)
	var full := _lbl(clip, "", 20, NetsuUI.CYAN, NetsuUI.sans(6), Rect2(0, area.size.y - 64, area.size.x, 30), HORIZONTAL_ALIGNMENT_CENTER)
	_big = {"area": area, "render": render, "random": rnd, "faces": faces, "name": name, "full": full}


func _corners(r: Rect2) -> PackedVector2Array:
	return PackedVector2Array([r.position, Vector2(r.end.x, r.position.y), r.end, Vector2(r.position.x, r.end.y)])


func _shrink(l: Label, from: int, to: int) -> void:
	var f: Font = l.get_theme_font("font")
	var fs := from
	while fs > to and f.get_string_size(l.text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x > l.size.x:
		fs -= 1
	l.add_theme_font_size_override("font_size", fs)


func _same(a, b) -> bool:
	return typeof(a) == typeof(b) and a == b


# --- Showing the state ----------------------------------------------------------------------------------------

func _refresh() -> void:
	var items := _items(_tab)
	var hovered = items[_cursor[_tab]] if not items.is_empty() else null
	# the rows
	for t in _rows.size():
		var r: Dictionary = _rows[t]
		var on := t == _tab
		r["bar"].visible = on
		r["bar"].modulate.a = 0.5 if on and _in_picker else 1.0
		r["label"].add_theme_color_override("font_color", NetsuUI.TEXT if on else NetsuUI.DIM)
		r["value"].text = _value_text(t)
		_shrink(r["value"], 19, 14)
		r["value"].add_theme_color_override("font_color", Color.WHITE if on else NetsuUI.DIM)
		for c in r["root"].get_children():
			if c.has_meta("diamond"):
				c.queue_free()
		var d := NetsuUI.diamond(9.0, Color.WHITE if on else Color(0.62, 0.64, 0.78, 0.9), Color(0.05, 0.2, 0.6, 0.9) if on
			else Color(0.16, 0.18, 0.32, 0.9), NetsuUI.CYAN if on else Color(0, 0, 0, 0))
		d.position = r["diamond"]
		d.set_meta("diamond", true)
		r["root"].add_child(d)
	# the card: what's set, or (browsing icons / titles) what's under the cursor
	var icon_id := str(_set[0])
	var title_id := str(_set[1])
	var preview := false
	if _in_picker and hovered != null and _unlocked(_tab, hovered):
		if _tab == 0 and str(hovered) != icon_id:
			icon_id = str(hovered)
			preview = true
		elif _tab == 1 and str(hovered) != title_id:
			title_id = str(hovered)
			preview = true
	_card.caption = "PREVIEW" if preview else "YOUR PROFILE"
	_card.show_profile(ProfileCatalog.my_name(), icon_id, title_id)
	_card.note = "How the others see you in online lobbies." if ProfileCatalog.my_name() != "" \
		else "No name yet: set it in ONLINE > NAME."
	# the picker
	_caption.text = "CUSTOMIZE   ‹ %s ›" % TABS[_tab][1]
	var pages := _pages(_tab)
	_page_label.text = "PAGE  %d / %d" % [_page(_tab) + 1, pages]
	for n in _pager:
		n.visible = pages > 1
	for i in _arrows.size():
		_arrows[i].modulate.a = 1.0 if _in_picker else 0.45
	_content.modulate.a = 1.0 if _in_picker else 0.8
	_draw_cursor()
	_fill_info(hovered if _in_picker else _set[_tab])
	if _tab == 2:
		_fill_big(hovered if _in_picker else _set[2])
	_refresh_footer()


## The cursor: a cyan glowing frame around the cell (only in the picker); the set one has the gold SET tag.
func _draw_cursor() -> void:
	for c in _cursor_frame.get_children():
		c.queue_free()
	_light_rows()
	for cell in _cells:
		if cell.has("label") and cell["label"] is Label and _tab == 0:
			cell["label"].add_theme_color_override("font_color", NetsuUI.DIM)
	if not _in_picker:
		return
	for cell in _cells:
		if int(cell["index"]) != int(_cursor[_tab]):
			continue
		var r: Rect2 = cell["rect"]
		var pts := _corners(r)
		if cell.has("fill"):
			continue   # (list rows light up themselves: _light_rows)
		_cursor_frame.add_child(NetsuUI.outline(pts, Color(0.3, 0.75, 1.0, 0.3), 12.0))
		_cursor_frame.add_child(NetsuUI.outline(pts, Color(0.55, 0.9, 1.0, 1.0), 3.0))
		for k in 4:   # the kit's bright corner triangles
			var c: Vector2 = pts[k]
			var dx := 1.0 if k in [0, 3] else -1.0
			var dy := 1.0 if k in [0, 1] else -1.0
			_cursor_frame.add_child(NetsuUI.poly(PackedVector2Array([c, c + Vector2(dx * 18, 0), c + Vector2(0, dy * 18)]),
				Color(0.85, 0.96, 1.0)))
		if cell.has("label") and _tab == 0:
			cell["label"].add_theme_color_override("font_color", Color.WHITE)


## MENU CHARACTER: the row under the cursor gets the menus' selected-row look (blue fill, bright edge).
func _light_rows() -> void:
	for cell in _cells:
		if not cell.has("fill"):
			continue
		var on := _in_picker and int(cell["index"]) == int(_cursor[_tab])
		var fill: Polygon2D = cell["fill"]
		fill.vertex_colors = PackedColorArray([Color(0.1, 0.4, 0.95, 0.9), Color(0.05, 0.2, 0.6, 0.65),
			Color(0.04, 0.16, 0.5, 0.65), Color(0.08, 0.34, 0.88, 0.9)]) if on else PackedColorArray([Color(0.06, 0.1, 0.32, 0.92),
			Color(0.05, 0.08, 0.26, 0.85), Color(0.03, 0.05, 0.18, 0.88), Color(0.03, 0.05, 0.2, 0.95)])
		cell["edge"].default_color = Color(0.6, 0.88, 1.0, 1.0) if on else Color(0.62, 0.8, 1.0, 0.55)
		cell["edge"].width = 2.5 if on else 1.5
		cell["glow"].visible = on
		cell["label"].add_theme_color_override("font_color", Color.WHITE if on else NetsuUI.TEXT)


func _fill_info(item) -> void:
	var state := ""
	if item == null:
		return
	var is_set := _same(item, _set[_tab])
	match _tab:
		0:
			var e := ProfileCatalog.icon(str(item))
			var open := ProfileCatalog.is_unlocked(e)
			_info["group"].text = "ICON  ·  %s" % str(e.get("group", ""))
			_info["name"].text = str(e["name"]) if open else "? ? ?"
			_info["about"].text = "Shown next to your name in online lobbies (and on your profile card)." if open \
				else "Locked. Keep playing to find out how to get it."
			state = "SET" if is_set else ("" if open else "LOCKED")
		1:
			var e := ProfileCatalog.title(str(item))
			var open := ProfileCatalog.is_unlocked(e)
			_info["group"].text = "TITLE"
			_info["name"].text = str(e.get("text", "")) if open else "? ? ?"
			_info["about"].text = str(e.get("about", "")) if open else "Locked. Keep playing to find out how to get it."
			state = "SET" if is_set else ("" if open else "LOCKED")
		2:
			_info["group"].text = "MENU CHARACTER"
			if item is int:
				_info["name"].text = _fighter_name(item, true)
				_info["about"].text = "%s greets you on the main menu and talks you through it." % _fighter_name(item)
			else:
				_info["name"].text = "Random Select"
				_info["about"].text = "A different fighter greets you each time the main menu opens."
			state = "SET" if is_set else ""
	if state == "" and _in_picker:
		state = "A  TO SET"
	_info["state"].text = state
	_info["state"].add_theme_color_override("font_color", GOLD if state == "SET" else (Color(1.0, 0.5, 0.55) if state == "LOCKED"
		else NetsuUI.CYAN))


func _fill_big(item) -> void:
	if _big.is_empty():
		return
	var rnd := not (item is int)
	_big["random"].visible = rnd
	_big["faces"].visible = rnd
	_big["render"].visible = not rnd
	var area: Rect2 = _big["area"]
	if rnd:
		_big["name"].text = ""
		_big["full"].text = "A NEW FACE EVERY TIME"
		return
	var prof = MatchSetup.fighter_profile(item)
	var tex: Texture2D = prof.Render if prof else null
	var r: TextureRect = _big["render"]
	r.texture = tex
	if tex:
		# as wide as the area, from the top: head and body, the legs run under the name
		var w := area.size.x * 1.05
		var h := w * tex.get_size().y / tex.get_size().x
		r.size = Vector2(w, h)
		r.position = Vector2((area.size.x - w) / 2.0, 0)
	_big["name"].text = _fighter_name(item).to_upper()
	_big["full"].text = _fighter_name(item, true).to_upper()


func _refresh_footer() -> void:
	if _footer.is_empty():
		return
	var text := ""
	var prompts := ""
	if _in_picker:
		var paged := _pages(_tab) > 1
		match _tab:
			0:
				text = "Pick the icon shown next to your name online."
			1:
				text = "Pick the title shown with your name online."
			2:
				text = "Pick who greets you on the main menu."
		prompts = "SELECT     " + ("LB / RB  PAGE     " if paged else "") + "A  SET     B  BACK"
	else:
		text = ["Your profile icon: the game's logo, the fighters, the assists.",
			"Your title: a name plate shown with your name online.",
			"The fighter on the main menu: Random Select, or your favourite."][_tab]
		prompts = "UP / DOWN  SELECT     A  CHOOSE     B  BACK"
	if _flash_t > 0.0:
		text = str(get_meta("flash", text))
	_footer["text"].text = text
	_footer["prompts"].text = prompts


func _flash(text: String) -> void:
	set_meta("flash", text)
	_flash_t = 2.5
	_refresh_footer()


# --- Doing things ---------------------------------------------------------------------------------------------

func _move(dx: int, dy: int) -> void:
	var items := _items(_tab)
	var n := items.size()
	if n == 0:
		return
	var per := _per_page(_tab)
	var cols := _cols(_tab)
	var cur: int = _cursor[_tab]
	var page := cur / per
	var k := cur - page * per
	var on_page := mini(per, n - page * per)
	var col := k % cols
	var row := k / cols
	var rows := ceili(float(on_page) / cols)
	var old_page := page
	if dx != 0:
		if cols == 1:
			_turn_page(dx)
			return
		col += dx
		if col < 0 or col >= cols:
			# past the edge: the next / previous page, same row
			page = wrapi(page + dx, 0, _pages(_tab))
			on_page = mini(per, n - page * per)
			col = 0 if dx > 0 else cols - 1
			row = mini(row, ceili(float(on_page) / cols) - 1)
	if dy != 0:
		row = wrapi(row + dy, 0, rows)
	var idx := page * per + row * cols + col
	idx = mini(idx, page * per + on_page - 1)
	_cursor[_tab] = clampi(idx, 0, n - 1)
	_audio(0)
	if page != old_page:
		_build_page()
	_refresh()


func _turn_page(dir: int) -> void:
	var pages := _pages(_tab)
	if pages <= 1:
		return
	var per := _per_page(_tab)
	var cur: int = _cursor[_tab]
	var k := cur % per
	var page := wrapi(cur / per + dir, 0, pages)
	_cursor[_tab] = mini(page * per + k, _items(_tab).size() - 1)
	_audio(0)
	_build_page()
	_refresh()


func _set_current() -> void:
	var item = _items(_tab)[_cursor[_tab]]
	if not _unlocked(_tab, item):
		_flash("That one is locked.")
		_audio(1)
		return
	_set[_tab] = item
	match _tab:
		0:
			GameSettings.set_value("profile", "icon", str(item))
		1:
			GameSettings.set_value("profile", "title", str(item))
		2:
			GameSettings.set_value("profile", "menu_character", item)
	_audio(2)
	_build_page()   # (the SET tag moves)
	_refresh()
	_flash("Set!  %s" % _value_text(_tab))


func _close() -> void:
	_audio(1)
	closed.emit(not _same(_set[2], _mc_at_open))


func _input(event: InputEvent) -> void:
	if not is_visible_in_tree():
		return
	var handled := true
	var page_dir := _page_event(event)
	if event.is_action_pressed("ui_cancel"):
		if _in_picker:
			_in_picker = false
			_flash_t = 0.0
			_cursor[_tab] = maxi(0, _items(_tab).find(_set[_tab]))
			_audio(1)
			_build_page()
			_refresh()
		else:
			_close()
	elif event.is_action_pressed("ui_accept"):
		if _in_picker:
			_set_current()
		else:
			_in_picker = true
			_audio(2)
			_refresh()
	elif event.is_action_pressed("ui_down", true):
		if _in_picker:
			_move(0, 1)
		else:
			_audio(0)
			_show_tab(_tab + 1)
	elif event.is_action_pressed("ui_up", true):
		if _in_picker:
			_move(0, -1)
		else:
			_audio(0)
			_show_tab(_tab - 1)
	elif event.is_action_pressed("ui_left", true):
		if _in_picker:
			_move(-1, 0)
	elif event.is_action_pressed("ui_right", true):
		if _in_picker:
			_move(1, 0)
	elif page_dir != 0:
		if _in_picker:
			_turn_page(page_dir)
		else:
			_audio(0)
			_show_tab(_tab + page_dir)
	else:
		handled = event.is_action("ui_up") or event.is_action("ui_down") or event.is_action("ui_left") \
			or event.is_action("ui_right") or event.is_action("ui_accept") or event.is_action("ui_cancel") or event.is_action("pause")
	if handled:
		get_viewport().set_input_as_handled()


## -1 / +1: LB / RB, LT / RT (pulled past halfway), Q / E, Page Up / Page Down. (In the rows: the tab before / after.)
func _page_event(event: InputEvent) -> int:
	if event is InputEventJoypadButton and event.pressed:
		if event.button_index == JOY_BUTTON_LEFT_SHOULDER:
			return -1
		if event.button_index == JOY_BUTTON_RIGHT_SHOULDER:
			return 1
	if event is InputEventKey and event.pressed and not event.echo:
		match event.physical_keycode:
			KEY_Q, KEY_PAGEUP:
				return -1
			KEY_E, KEY_PAGEDOWN:
				return 1
	if event is InputEventJoypadMotion:
		var i := -1
		if event.axis == JOY_AXIS_TRIGGER_LEFT:
			i = 0
		elif event.axis == JOY_AXIS_TRIGGER_RIGHT:
			i = 1
		if i >= 0:
			if event.axis_value > 0.6 and not _trigger[i]:
				_trigger[i] = true
				return -1 if i == 0 else 1
			if event.axis_value < 0.3:
				_trigger[i] = false
	return 0


func _audio(index: int) -> void:
	var audio := get_node_or_null("/root/AudioManager")
	if audio and audio.has_method("PlayMenuClip"):
		audio.call("PlayMenuClip", index)


# --- For tests ------------------------------------------------------------------------------------------------

func test_state() -> Dictionary:
	var items := _items(_tab)
	return {"tab": TABS[_tab][0], "picker": _in_picker, "cursor": _cursor[_tab], "hovered": items[_cursor[_tab]] if not items.is_empty() else null,
		"page": _page(_tab), "pages": _pages(_tab), "set": _set.duplicate(), "card_caption": _card.caption,
		"card_icon": _card.icon_id, "card_title": _card.title_id, "info": _info["name"].text,
		"footer": _footer["text"].text if not _footer.is_empty() else "", "prompts": _footer["prompts"].text if not _footer.is_empty() else ""}
