class_name NetsuProfileCard
extends Control
## PROFILE CARD (Nov 4 2026): how a player looks to the others online: their icon, their name and their title plate,
## in a kit frame_panel. Main Menu > CUSTOMIZE shows yours (with what you're browsing); made to be reused (ranked
## matches, a results screen...).
##
##   var card := NetsuProfileCard.new()
##   card.position = Vector2(80, 160)
##   card.size = Vector2(560, 260)          # set the size BEFORE add_child: the layout is built from it
##   add_child(card)
##   card.show_profile("Tama", "cec_smile", "cecilia_main")
##   card.show_mine()                       # this computer's own (GameSettings "online" / "profile")

## The caption over the name ("YOUR PROFILE", "PREVIEW"...). "" = none.
var caption := "YOUR PROFILE":
	set(value):
		caption = value
		if _caption:
			_caption.text = value
## The panel's light (NetsuUI blue for player 1, red for player 2...).
var accent := Color(0.3, 0.62, 1.0)
## Shown under the plate (small, dim). "" = none.
var note := "":
	set(value):
		note = value
		if _note:
			_note.text = value

var player_name := ""
var icon_id := ""
var title_id := ""

var _icon: TextureRect
var _name: Label
var _caption: Label
var _note: Label
var _plate: NetsuTitlePlate


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_build()
	_refresh()


func show_profile(who: String, icon: String, title: String) -> void:
	player_name = who
	icon_id = icon
	title_id = title
	_refresh()


func show_mine() -> void:
	show_profile(ProfileCatalog.my_name(), ProfileCatalog.my_icon(), ProfileCatalog.my_title())


func _build() -> void:
	var w := size.x
	var h := size.y
	NetsuUI.frame_panel(self, Rect2(Vector2.ZERO, size), accent)
	var light := NetsuUI.gradient_rect(Color(accent, 0.22), Color(accent, 0.0), false)
	light.position = Vector2(8, 8)
	light.size = Vector2(w * 0.6, h - 16)
	add_child(light)
	# [icon] caption / name / note, and the title plate across the bottom
	var pad := maxf(14.0, h * 0.075)
	var side := h * 0.6
	var base := ColorRect.new()
	base.color = Color(0.04, 0.05, 0.12, 0.92)
	base.position = Vector2(pad, pad)
	base.size = Vector2(side, side)
	base.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(base)
	_icon = TextureRect.new()
	_icon.position = base.position
	_icon.size = base.size
	_icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_icon)
	var r := Rect2(base.position, base.size)
	add_child(NetsuUI.outline(PackedVector2Array([r.position, Vector2(r.end.x, r.position.y), r.end, Vector2(r.position.x, r.end.y)]),
		Color(0.92, 0.94, 1.0, 0.9), 2.0))
	var x := pad * 2.0 + side
	var tw := w - x - pad
	_caption = NetsuUI.label(caption, int(clampf(h * 0.07, 13, 22)), accent.lightened(0.45), NetsuUI.sans(6))
	_caption.position = Vector2(x, pad - 2)
	_caption.size = Vector2(tw, h * 0.11)
	_caption.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	add_child(_caption)
	NetsuUI.divider(self, x, x + tw, pad + h * 0.135, false)
	_name = NetsuUI.label("", int(clampf(h * 0.14, 18, 44)), Color.WHITE, NetsuUI.sans(3))
	_name.position = Vector2(x, pad + h * 0.16)
	_name.size = Vector2(tw, h * 0.2)
	_name.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_name.clip_text = true
	_name.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	NetsuUI.glow(_name, Color(0.02, 0.03, 0.12, 0.7), 5)
	add_child(_name)
	_note = NetsuUI.label(note, int(clampf(h * 0.06, 12, 19)), NetsuUI.DIM, NetsuUI.sans(2))
	_note.position = Vector2(x, pad + h * 0.38)
	_note.size = Vector2(tw, side - h * 0.38)
	_note.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	add_child(_note)
	var top := pad + side + h * 0.035
	_plate = NetsuTitlePlate.new()
	var inset := maxf(pad, 40.0)   # (clear of the panel's corner triangles)
	_plate.position = Vector2(inset, top)
	_plate.size = Vector2(w - inset * 2.0, h - top - pad * 0.7)
	add_child(_plate)


func _refresh() -> void:
	if _icon == null:
		return
	ProfileCatalog.apply_icon(_icon, icon_id if icon_id != "" else ProfileCatalog.DEFAULT_ICON)
	_name.text = (player_name if player_name != "" else "PLAYER").to_upper()
	_plate.title_id = title_id
