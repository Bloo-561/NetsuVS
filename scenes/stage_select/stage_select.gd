extends Control
## STAGE SELECT  (right after the character select; Oct 19 2026 mockup)
## Two steps (either player):
##   1. STAGE:  left / right pick a stage   up / down pick its variant (Morning / Dusk ...)
##              A (or S / Start) -> music step   B (or C) -> character select
##   2. MUSIC:  left / right pick AUTO (Player 1's theme), RANDOM or any song in data/soundtrack.tres
##              Y (controller Y button, or the Y key) plays a preview   A -> FIGHT   B -> back to step 1
## Stages come from data/stage_list.tres (Name + Thumbnail). A name like
## "Thors Training Hall - Dusk" shows as THORS TRAINING HALL with DUSK under it.
## VARIANTS: entries that share the part before " - " are ONE stage on the carousel
## ("Thors Training Hall - Morning", "Thors Training Hall - Dusk"); up / down switches between them
## in list order, and small up / down arrows beside the variant name show when there is more than one.
## Each variant is still its own entry in stage_list.tres, so the battle and win screen are unchanged.
## The last card is RANDOM ("???"). The music bar shows the song, its artist and,
## for a character theme, whose theme it is. Changing it plays the song as a preview.
## Layout numbers are mockup pixels (1672 x 941), converted with NetsuUI.m().

const SFX_MOVE := "res://assets/audio/menu/mahou/NavigationSound.wav"
const SFX_BACK := "res://assets/audio/menu/mahou/CancelSound.wav"
const SFX_START := "res://assets/audio/menu/mahou/StrongConfirmSoundVers4.wav"

## Footer text per stage (matched by the start of the stage name). Add a line for each new stage.
const DESCRIPTIONS := {
	"Thors Training Hall - Dusk": "A training hall at Thors Military Academy.\nThe setting sun casts a warm light across the floor.",
	"Thors Training Hall": "A training hall at Thors Military Academy.\nMorning light pours in through the tall windows.",
	"Crimson Abyss": "A cracked crater under a burning storm sky.\nThere is no way out of this fight.",
	"Depths of the Old Schoolhouse": "Far below the old schoolhouse, a platform floats among the stars.\nGreen lanterns burn around the ancient circle.",
	"Celdic - Burning": "The market town of Celdic burns as night falls.\nSmoke and embers fill the square.",
	"Celdic": "The ruined square of Celdic, the morning after the attack.\nSmoke still rises over the broken town.",
	"The GeoFront": "A sealed vault deep beneath the city.\nEnergy runs through the great door, and the grate glows from below.",
	"North Ambria": "A frozen field in the far north, lashed by a blizzard.\nTwo lonely graves stand on the hill.",
	"Ordis Royal Manor - Ruined": "The lord's hall at the Ordis manor, torn apart in the attack.\nFire and smoke fill the room.",
	"Ordis Royal Manor - Day": "The grand office of the Ordis manor, high above the sea.\nSunlight glitters on the gold and marble.",
	"Ordis Royal Manor": "The grand office of the Ordis manor, high above the sea.\nSunlight glitters on the gold and marble.",
	"Old Schoolhouse -Entrance-": "The entrance hall of the old schoolhouse, deep in the night.\nMoonlight falls through the windows onto the cold stone floor.",
	"Roer": "The Upper Level plaza of Roer, the city of industry, at dusk.\nTrains rumble past and chimneys smoke beyond the Khemia Corp tower.",
	"Septian Chapel": "A little chapel of the Septian Church out in the countryside.\nSwallows wheel round the bell tower on a summer afternoon.",
}

@export_group("Layout (mockup pixels)")
@export var preview_rect: Rect2 = Rect2(318, 98, 1034, 418)
@export var name_y: float = 551.0
@export var cards_y: float = 653.0
@export var card_spacing: float = 283.0
@export var music_rect: Rect2 = Rect2(256, 755, 1161, 83)

var _count := 0          # entries in stage_list.tres
var _cursor := 0         # carousel position: a stage GROUP (== _groups.size() -> RANDOM)
var _groups: Array = []  # one Array[int] of stage_list indices per carousel stage (its variants)
var _var := {}           # group -> chosen variant (position in its Array)
var _var_arrows: Array[Node2D] = []
var _leaving := false
var _preview: TextureRect
var _preview_root: Control
var _random_mark: Label
var _name: Label
var _variant: Label
var _variant_lines: Array[TextureRect] = []
var _cards: Array[Dictionary] = []   # three on screen: previous, current, next
var _footer: Dictionary
var _sfx: AudioStreamPlayer

var _phase := "stage"   # "stage" or "music"
var _carousel: Control
var _music_root: Control
var _sel_style: StyleBoxFlat
var _music_glow: Node2D

const STAGE_PROMPTS := "SELECT     A  CONFIRM     B  BACK"
const VARIANT_PROMPTS := "LEFT / RIGHT  STAGE     UP / DOWN  VARIANT     A  CONFIRM     B  BACK"
const MUSIC_PROMPTS := "SELECT     Y  MUSIC PREVIEW     A  CONFIRM     B  BACK"

var _music := MatchSetup.MUSIC_AUTO
var _music_mode: Label
var _music_title: Label
var _music_artist: Label
var _music_tag: Label
var _wave: Node2D
var _time := 0.0


func _ready() -> void:
	_sfx = AudioStreamPlayer.new()
	add_child(_sfx)
	_count = MatchSetup.stage_count()
	_build_groups()
	NetsuUI.settings_backdrop(self, 0.3)
	NetsuUI.header(self, "STAGE SELECT")
	_build_matchup()
	_build_preview()
	_build_cards()
	_build_music()
	_footer = NetsuUI.footer(self, false, 857.0, 87.0, 891.0, 1600.0, 892.0)
	_footer["text"].size.y = 70
	_footer["text"].position.y = 891.0 * NetsuUI.K - 35
	_footer["prompts"].text = STAGE_PROMPTS
	_select_entry(MatchSetup.last_stage if MatchSetup.last_stage >= 0 else MatchSetup.default_stage())
	_refresh(false)
	_music = MatchSetup.music_choice
	_refresh_music(false)
	_set_phase("stage", false)
	NetsuUI.cascade(self, 2)


func _process(delta: float) -> void:
	_time += delta
	if _wave:
		_wave.queue_redraw()


func _unhandled_input(event: InputEvent) -> void:
	if _leaving or SceneRouter.is_busy():
		return
	# Y plays the music preview (checked first: the Y button is also a fighting button)
	if _phase == "music" and _is_preview(event):
		get_viewport().set_input_as_handled()
		_preview_music()
		return
	for p in ["p1_", "p2_"]:
		if event.is_action_pressed(p + "left", true):
			if _phase == "stage":
				_move(-1)
			else:
				_move_music(-1)
		elif event.is_action_pressed(p + "right", true):
			if _phase == "stage":
				_move(1)
			else:
				_move_music(1)
		elif _phase == "stage" and event.is_action_pressed(p + "up"):
			_move_variant(-1)
		elif _phase == "stage" and event.is_action_pressed(p + "down"):
			_move_variant(1)
		elif event.is_action_pressed(p + "a") or event.is_action_pressed(p + "s") \
				or event.is_action_pressed(p + "start"):
			if _phase == "stage":
				_set_phase("music")
			else:
				_confirm()
		elif event.is_action_pressed(p + "b") or event.is_action_pressed(p + "c"):
			if _phase == "music":
				_set_phase("stage")
			else:
				_back()
		else:
			continue
		get_viewport().set_input_as_handled()
		return
	if event is InputEventKey and event.pressed and not event.echo and event.physical_keycode == KEY_ESCAPE:
		get_viewport().set_input_as_handled()
		if _phase == "music":
			_set_phase("stage")
		else:
			_back()


func _is_preview(event: InputEvent) -> bool:
	if event is InputEventJoypadButton:
		return event.pressed and event.button_index == JOY_BUTTON_Y
	if event is InputEventKey:
		return event.pressed and not event.echo and event.physical_keycode == KEY_Y
	return false


## Step 1 (stage) or step 2 (music): moves the highlight between the carousel and the music bar.
func _set_phase(phase: String, animate: bool = true) -> void:
	if phase == "music" and _count == 0:
		return
	if animate and phase != _phase:
		_play(SFX_MOVE if phase == "music" else SFX_BACK)
	_phase = phase
	var music := phase == "music"
	_footer["prompts"].text = MUSIC_PROMPTS if music else _stage_prompts()
	_footer["text"].text = "Choose the battle music. Y plays a preview." if music else _description(_entry(_cursor))
	var time := 0.22 if animate else 0.0
	var t := create_tween().set_parallel(true).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	t.tween_property(_carousel, "modulate", Color(0.62, 0.64, 0.72) if music else Color.WHITE, time)
	t.tween_property(_music_root, "modulate", Color.WHITE if music else Color(0.62, 0.64, 0.72), time)
	t.tween_property(_music_glow, "modulate:a", 1.0 if music else 0.0, time)
	_sel_style.border_color = Color(0.45, 0.85, 1.0) if music else Color(0.75, 0.85, 1.0, 0.85)
	_sel_style.set_border_width_all(3 if music else 2)
	if animate and music:
		_music_root.position.y = 8
		t.tween_property(_music_root, "position:y", 0.0, time)


func _move(step: int) -> void:
	_cursor = wrapi(_cursor + step, 0, _groups.size() + 1)
	_play(SFX_MOVE)
	_refresh(true)


## Up / down: the next or previous variant of the highlighted stage (Morning <-> Dusk).
func _move_variant(step: int) -> void:
	if _cursor >= _groups.size() or _groups[_cursor].size() < 2:
		return
	_var[_cursor] = wrapi(int(_var.get(_cursor, 0)) + step, 0, _groups[_cursor].size())
	_play(SFX_MOVE)
	_refresh(true)
	var v := _variant
	v.position.y = 585 * NetsuUI.K - 20 + 10 * step
	create_tween().tween_property(v, "position:y", 585 * NetsuUI.K - 20, 0.12).set_trans(Tween.TRANS_CUBIC)


# --- Stage groups (variants) ------------------------------------------------------------

func _base_name(i: int) -> String:
	return MatchSetup.stage_name(i).split(" - ", false, 1)[0].strip_edges()


func _build_groups() -> void:
	_groups.clear()
	var by_name := {}
	for i in _count:
		var base := _base_name(i)
		if not by_name.has(base):
			by_name[base] = _groups.size()
			_groups.append([])
		_groups[by_name[base]].append(i)


## stage_list index shown for carousel position g (_count for RANDOM).
func _entry(g: int) -> int:
	if g >= _groups.size():
		return _count
	var items: Array = _groups[g]
	return items[clampi(int(_var.get(g, 0)), 0, items.size() - 1)]


## Puts the cursor on the stage and variant of stage_list index `entry`.
func _select_entry(entry: int) -> void:
	_cursor = 0
	for g in _groups.size():
		var k: int = _groups[g].find(entry)
		if k >= 0:
			_cursor = g
			_var[g] = k
			return


func _variant_count(g: int) -> int:
	return _groups[g].size() if g < _groups.size() else 0


func _stage_prompts() -> String:
	return VARIANT_PROMPTS if _variant_count(_cursor) > 1 else STAGE_PROMPTS


func _confirm() -> void:
	if _count == 0:
		return
	_leaving = true
	var stage := _entry(_cursor)
	if stage == _count:  # RANDOM: any stage, any variant
		stage = randi() % _count
		_select_entry(stage)
		_refresh(true)
	MatchSetup.last_stage = stage
	MatchSetup.music_choice = _music
	_play(SFX_START)
	var flash := create_tween()
	flash.tween_property(_preview_root, "scale", Vector2(1.02, 1.02), 0.08)
	flash.tween_property(_preview_root, "scale", Vector2.ONE, 0.12)
	await get_tree().create_timer(0.35).timeout
	MatchSetup.start_pending(stage)


func _back() -> void:
	_leaving = true
	MatchSetup.music_choice = _music
	_play(SFX_BACK)
	SceneRouter.go_to(SceneRouter.CHARACTER_SELECT)


## [base name, variant] - "Thors Training Hall - Dusk" -> ["THORS TRAINING HALL", "DUSK"].
func _split_name(i: int) -> Array:
	if i >= _count:
		return ["???", "UNKNOWN"]
	var full := MatchSetup.stage_name(i)
	var parts := full.split(" - ", false, 1)
	return [parts[0].to_upper(), parts[1].to_upper() if parts.size() > 1 else ""]


func _description(i: int) -> String:
	if i >= _count:
		return "Let fate decide the battlefield."
	var full := MatchSetup.stage_name(i)
	if DESCRIPTIONS.has(full):
		return DESCRIPTIONS[full]
	for key in DESCRIPTIONS:
		if full.begins_with(key):
			return DESCRIPTIONS[key]
	return "Fight in %s." % full


func _thumb(i: int) -> Texture2D:
	return null if i >= _count else MatchSetup.stage_thumbnail(i)


func _refresh(animate: bool) -> void:
	var e := _entry(_cursor)
	var is_random := e == _count
	_preview.texture = _thumb(e)
	_random_mark.visible = is_random
	var n := _split_name(e)
	_name.text = n[0]
	_variant.text = n[1]
	for line in _variant_lines:
		line.visible = n[1] != ""
	var many := _variant_count(_cursor) > 1
	for a in _var_arrows:
		a.visible = many
	_footer["text"].text = _description(e)
	if _phase == "stage":
		_footer["prompts"].text = _stage_prompts()
	var total := _groups.size() + 1
	for slot in 3:
		var idx := _entry(wrapi(_cursor + slot - 1, 0, total))
		var card: Dictionary = _cards[slot]
		var tex := _thumb(idx)
		var pic: Polygon2D = card["pic"]
		pic.texture = tex
		if tex:
			var ts := tex.get_size()
			var uv := PackedVector2Array()
			for p in pic.polygon:
				uv.append(p / card["size"] * ts)
			pic.uv = uv
			pic.color = Color.WHITE
		else:
			pic.color = Color(0.12, 0.13, 0.18)
		card["q"].visible = tex == null
		var cn := _split_name(idx)
		card["name"].text = cn[0]
		card["sub"].text = ("—  %s  —" % cn[1]) if slot == 1 and cn[1] != "" else cn[1]
	if animate:
		_preview.modulate.a = 0.35
		create_tween().tween_property(_preview, "modulate:a", 1.0, 0.15)
		var mid: Node2D = _cards[1]["root"]
		mid.scale = Vector2(0.94, 0.94)
		create_tween().tween_property(mid, "scale", Vector2.ONE, 0.12).set_trans(Tween.TRANS_BACK)


# --- Building --------------------------------------------------------------------------

func _build_matchup() -> void:
	var k := NetsuUI.K
	var text := MatchSetup.pending_matchup_text()   # "CECILIA  VS  FLAN"
	var parts := text.split("  VS  ")
	var who := RichTextLabel.new()
	who.bbcode_enabled = true
	who.fit_content = true
	who.scroll_active = false
	who.autowrap_mode = TextServer.AUTOWRAP_OFF
	who.mouse_filter = Control.MOUSE_FILTER_IGNORE
	who.add_theme_font_override("normal_font", NetsuUI.sans(8))
	who.add_theme_font_size_override("normal_font_size", 36)
	if parts.size() == 2:
		who.text = "[right][color=#5ab8ff]%s[/color]      VS      [color=#ff4a63]%s[/color][/right]" % [parts[0], parts[1]]
	else:
		who.text = "[right]%s[/right]" % text
	who.position = Vector2(900 * k, 48 * k - 24)
	who.size = Vector2(733 * k, 50)
	add_child(who)
	var g := Gradient.new()
	g.offsets = PackedFloat32Array([0.0, 0.15, 0.5, 0.85, 1.0])
	g.colors = PackedColorArray([Color(0.3, 0.6, 1.0, 0.0), Color(0.3, 0.6, 1.0, 0.9), Color(0.7, 0.5, 1.0, 0.9),
		Color(1.0, 0.3, 0.4, 0.9), Color(1.0, 0.3, 0.4, 0.0)])
	var tex := GradientTexture2D.new()
	tex.gradient = g
	var line := TextureRect.new()
	line.texture = tex
	line.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	line.position = NetsuUI.m(1290, 76)
	line.size = Vector2(343 * k, 1.5)
	add_child(line)


func _build_preview() -> void:
	var k := NetsuUI.K
	var r := Rect2(preview_rect.position * k, preview_rect.size * k)
	_preview_root = Control.new()
	_preview_root.position = r.position
	_preview_root.size = r.size
	_preview_root.pivot_offset = r.size / 2.0
	_preview_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_preview_root)
	var back := ColorRect.new()
	back.color = Color(0.05, 0.06, 0.12)
	back.size = r.size
	back.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_preview_root.add_child(back)
	_preview = TextureRect.new()
	_preview.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_preview.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	_preview.size = r.size
	_preview.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_preview_root.add_child(_preview)
	_random_mark = NetsuUI.label("?", 240, Color(0.75, 0.8, 0.95, 0.6), NetsuUI.sans(0, true))
	_random_mark.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_random_mark.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_random_mark.size = r.size
	_preview_root.add_child(_random_mark)
	var pts := PackedVector2Array([Vector2.ZERO, Vector2(r.size.x, 0), r.size, Vector2(0, r.size.y)])
	var edge := Node2D.new()
	_preview_root.add_child(edge)
	edge.add_child(NetsuUI.outline(pts, Color(0.35, 0.65, 1.0, 0.35), 12.0))
	edge.add_child(NetsuUI.outline(pts, Color(0.75, 0.88, 1.0, 1.0), 2.5))
	var leg := 34.0
	edge.add_child(NetsuUI.poly(PackedVector2Array([Vector2(-3, -3), Vector2(leg, -3), Vector2(-3, leg)]), Color(0.7, 0.88, 1.0)))
	edge.add_child(NetsuUI.poly(PackedVector2Array([r.size + Vector2(3, 3), r.size + Vector2(-leg, 3), r.size + Vector2(3, -leg)]),
		Color(0.7, 0.88, 1.0)))
	# stage name with lines either side, and the variant under it
	var font := NetsuUI.sans(8)
	_name = NetsuUI.label("", 52, Color.WHITE, font)
	NetsuUI.glow(_name, Color(0.25, 0.5, 1.0, 0.45), 10)
	_name.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_name.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_name.position = Vector2(0, name_y * k - 40)
	_name.size = Vector2(1920, 80)
	add_child(_name)
	for s: float in [-1.0, 1.0]:
		var x0 := 837.0 + s * 300.0
		add_child(NetsuUI.hairline(NetsuUI.m(x0 - (150.0 if s < 0 else 0.0), name_y + 3), 150 * k, Color(0.6, 0.78, 1.0, 0.8),
			1.5, "left" if s < 0 else "right"))
	_variant = NetsuUI.label("", 24, Color(0.92, 0.94, 1.0), NetsuUI.sans(9))
	_variant.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_variant.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_variant.position = Vector2(0, 585 * k - 20)
	_variant.size = Vector2(1920, 40)
	add_child(_variant)
	for s: float in [-1.0, 1.0]:
		var line := NetsuUI.hairline(NetsuUI.m(837.0 + s * 55.0 - (36.0 if s < 0 else 0.0), 586), 36 * k,
			Color(0.8, 0.88, 1.0, 0.85), 1.5, "none")
		add_child(line)
		_variant_lines.append(line)
	# up / down arrows either side of the variant name (only when the stage has variants)
	for s: float in [-1.0, 1.0]:
		var pair := Node2D.new()
		pair.position = NetsuUI.m(837.0 + s * 112.0, 588)
		for d: float in [-1.0, 1.0]:
			var a := NetsuUI.arrow(Vector2(0, d * 6.5 * k), 10, 1, Color(0.85, 0.92, 1.0), 2.5)
			a.rotation = d * PI / 2.0    # d = -1 -> points up, 1 -> points down
			pair.add_child(a)
		add_child(pair)
		_var_arrows.append(pair)


func _build_cards() -> void:
	var k := NetsuUI.K
	_carousel = Control.new()
	_carousel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_carousel.size = Vector2(1920, 1080)
	add_child(_carousel)
	for slot in 3:
		var center := slot == 1
		var w := (285.0 if center else 250.0) * k
		var h := (98.0 if center else 93.0) * k
		var skew := 16.0 * k
		var csize := Vector2(w + skew, h)
		var root := Node2D.new()
		var cx := (837.0 + (slot - 1) * card_spacing) * k
		root.position = Vector2(cx, cards_y * k)
		_carousel.add_child(root)
		var holder := Node2D.new()
		holder.position = -csize / 2.0
		root.add_child(holder)
		var shape := NetsuUI.para(w, h, skew)
		var pic := Polygon2D.new()
		pic.polygon = shape
		holder.add_child(pic)
		var q := NetsuUI.label("?", 70, Color(0.6, 0.64, 0.75, 0.8), NetsuUI.sans(0, true))
		q.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		q.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		q.size = csize
		holder.add_child(q)
		if center:
			holder.add_child(NetsuUI.outline(shape, Color(0.3, 0.6, 1.0, 0.45), 12.0))
			holder.add_child(NetsuUI.outline(shape, Color(0.55, 0.82, 1.0), 3.0))
		else:
			holder.add_child(NetsuUI.outline(shape, Color(0.85, 0.88, 1.0, 0.75), 2.0))
			root.modulate = Color(0.75, 0.75, 0.82)
		var name_label := NetsuUI.label("", 17 if center else 16, Color(0.93, 0.95, 1.0), NetsuUI.sans(2))
		name_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		name_label.position = Vector2(cx - 200, (cards_y + 63) * k - 14)
		name_label.size = Vector2(400, 28)
		_carousel.add_child(name_label)
		var sub := NetsuUI.label("", 13, Color(0.75, 0.8, 0.92), NetsuUI.sans(4))
		sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		sub.position = Vector2(cx - 200, (cards_y + 81) * k - 11)
		sub.size = Vector2(400, 22)
		_carousel.add_child(sub)
		_cards.append({"root": root, "pic": pic, "q": q, "size": csize, "name": name_label, "sub": sub})
	for s in [-1, 1]:
		_carousel.add_child(NetsuUI.arrow(NetsuUI.m(837.0 + s * 450.0, cards_y + 2), 40, s, Color(0.92, 0.95, 1.0), 4.0))


# --- Music -----------------------------------------------------------------------------

## AUTO -> RANDOM -> song 0 -> song 1 ... and round again.
func _move_music(step: int) -> void:
	var n := MatchSetup.song_count()
	if n == 0:
		return
	var order: Array = [MatchSetup.MUSIC_AUTO, MatchSetup.MUSIC_RANDOM]
	order.append_array(range(n))
	var i := maxi(order.find(_music), 0)
	_music = order[wrapi(i + step, 0, order.size())]
	_play(SFX_MOVE)
	_refresh_music(true)


## Plays the highlighted song (RANDOM keeps whatever is playing).
func _preview_music() -> void:
	if MatchSetup.song_count() == 0:
		return
	var p1: int = MatchSetup.pending.get("p1", 0)
	var song: int = MatchSetup.resolve_music(_music, p1)   # RANDOM: a random song to give an idea
	MatchSetup.prepare_music()
	var audio := get_node_or_null("/root/AudioManager")
	var clip = MatchSetup.song_info(song)["clip"]
	if audio and clip:
		audio.call("PlayBGM", clip)


func _refresh_music(animate: bool) -> void:
	var n := MatchSetup.song_count()
	if n == 0:
		_music_mode.text = "NO MUSIC"
		_music_title.text = "Add songs to data/soundtrack.tres"
		_music_artist.text = ""
		_music_tag.text = ""
		return
	var p1: int = MatchSetup.pending.get("p1", 0)
	if _music == MatchSetup.MUSIC_RANDOM:
		_music_mode.text = "RANDOM"
		_music_title.text = "A random song"
		_music_tag.text = "%d songs" % n
		_music_artist.text = ""
	else:
		var song: int = MatchSetup.resolve_music(_music, p1)
		var info := MatchSetup.song_info(song)
		_music_mode.text = "AUTO (PLAYER 1)" if _music == MatchSetup.MUSIC_AUTO else "SONG %d / %d" % [song + 1, n]
		_music_title.text = info["title"] if info["title"] != "" else "Untitled"
		_music_artist.text = info["artist"]
		var f: int = info["fighter"]
		_music_tag.text = ("%s's Theme" % str(MatchSetup.fighter_profile(f).ShortName)) if f >= 0 else "Battle Music"
	if animate:
		_music_title.modulate.a = 0.3
		create_tween().tween_property(_music_title, "modulate:a", 1.0, 0.15)


func _build_music() -> void:
	var k := NetsuUI.K
	_music_root = Control.new()
	_music_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_music_root.size = Vector2(1920, 1080)
	add_child(_music_root)
	var r := Rect2(music_rect.position * k, music_rect.size * k)
	var pts := PackedVector2Array([r.position, Vector2(r.end.x, r.position.y), r.end, Vector2(r.position.x, r.end.y)])
	var box := Node2D.new()
	_music_root.add_child(box)
	var fill := Polygon2D.new()
	fill.polygon = pts
	fill.color = Color(0.03, 0.05, 0.17, 0.85)
	box.add_child(fill)
	box.add_child(NetsuUI.outline(pts, Color(0.3, 0.6, 1.0, 0.3), 10.0))
	box.add_child(NetsuUI.outline(pts, Color(0.6, 0.82, 1.0), 2.0))
	box.add_child(NetsuUI.poly(PackedVector2Array([r.position + Vector2(-2, -2), r.position + Vector2(26, -2), r.position + Vector2(-2, 26)]),
		Color(0.6, 0.85, 1.0)))
	box.add_child(NetsuUI.poly(PackedVector2Array([r.end + Vector2(2, 2), r.end + Vector2(-26, 2), r.end + Vector2(2, -26)]),
		Color(0.6, 0.85, 1.0)))
	var cy := r.position.y + r.size.y / 2.0
	var note := NetsuUI.label("♫", 34, Color(0.75, 0.88, 1.0), NetsuUI.body())
	note.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	note.position = Vector2(286 * k, cy - 25)
	note.size = Vector2(40, 50)
	_music_root.add_child(note)
	var head := NetsuUI.label("MUSIC SELECT", 22, Color(0.4, 0.82, 1.0), NetsuUI.sans(4))
	head.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	head.position = Vector2(333 * k, cy - 20)
	head.size = Vector2(200, 40)
	_music_root.add_child(head)
	# the < AUTO (PLAYER 1) > selector
	var sel := Rect2(NetsuUI.m(512, 777), Vector2(313, 38) * k)
	# extra glow around the bar while the music step is active
	_music_glow = Node2D.new()
	_music_glow.add_child(NetsuUI.outline(pts, Color(0.35, 0.7, 1.0, 0.35), 22.0))
	_music_glow.modulate.a = 0.0
	_music_root.add_child(_music_glow)
	_music_root.move_child(_music_glow, 0)
	var style := StyleBoxFlat.new()
	_sel_style = style
	style.bg_color = Color(0.04, 0.07, 0.22, 0.9)
	style.border_color = Color(0.75, 0.85, 1.0, 0.85)
	style.set_border_width_all(2)
	style.set_corner_radius_all(6)
	var panel := Panel.new()
	panel.add_theme_stylebox_override("panel", style)
	panel.position = sel.position
	panel.size = sel.size
	panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_music_root.add_child(panel)
	_music_root.add_child(NetsuUI.arrow(Vector2(sel.position.x + 24 * k, cy), 18, -1, Color.WHITE, 3.0))
	_music_root.add_child(NetsuUI.arrow(Vector2(sel.end.x - 24 * k, cy), 18, 1, Color.WHITE, 3.0))
	_music_mode = NetsuUI.label("", 21, Color.WHITE, NetsuUI.sans(1))
	_music_mode.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_music_mode.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_music_mode.position = Vector2(sel.position.x, cy - 20)
	_music_mode.size = Vector2(sel.size.x, 40)
	_music_root.add_child(_music_mode)
	var divider := ColorRect.new()
	divider.color = Color(0.7, 0.8, 1.0, 0.5)
	divider.position = Vector2(856 * k, 762 * k)
	divider.size = Vector2(1.5, 68 * k)
	divider.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_music_root.add_child(divider)
	_music_title = NetsuUI.label("", 23, Color.WHITE, NetsuUI.sans(1))
	_music_title.position = Vector2(887 * k, 776 * k - 18)
	_music_title.size = Vector2(380 * k, 36)
	_music_title.clip_text = true
	_music_root.add_child(_music_title)
	_music_tag = NetsuUI.label("", 17, Color(0.75, 0.8, 0.92), NetsuUI.body())
	_music_tag.position = Vector2(887 * k, 800 * k - 13)
	_music_tag.size = Vector2(380 * k, 26)
	_music_root.add_child(_music_tag)
	_music_artist = NetsuUI.label("", 17, Color(0.75, 0.8, 0.92), NetsuUI.body())
	_music_artist.position = Vector2(887 * k, 820 * k - 13)
	_music_artist.size = Vector2(380 * k, 26)
	_music_root.add_child(_music_artist)
	_wave = Waveform.new()
	_wave.position = NetsuUI.m(1228, 797)
	_wave.owner_screen = self
	_music_root.add_child(_wave)


func _play(path: String) -> void:
	var stream = load(path)
	if stream:
		_sfx.stream = stream
		_sfx.play()


## The little equaliser in the music bar.
class Waveform extends Node2D:
	var owner_screen: Node
	var bars := 22

	func _draw() -> void:
		var t: float = owner_screen.get("_time") if owner_screen else 0.0
		for i in bars:
			var x := i * 6.2
			var shape := 0.35 + 0.65 * sin(PI * (i + 0.5) / bars)
			var h := (4.0 + 22.0 * shape * (0.55 + 0.45 * sin(t * 6.0 + i * 1.7) * sin(t * 2.3 + i * 0.6))) * NetsuUI.K
			var c := Color(0.35, 0.65, 1.0).lerp(Color(0.6, 0.85, 1.0), shape)
			draw_rect(Rect2(Vector2(x, -h / 2.0), Vector2(2.6, h)), c)
