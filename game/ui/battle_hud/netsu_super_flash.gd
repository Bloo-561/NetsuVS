extends Control
## EX / SUPER FLASH (Oct 24 2026)
##
## When a fighter spends Craft Gauge on a big move, the fight shows it:
##   EX move (1 bar) or super (3 bars) -> the stage goes dark for as long as the move's flash
##       freezes the opponent, and a burst of light (spinning rays, a glow, a ring that opens
##       out) goes off at the fighter's chest. The frozen opponent (and its assist) is darkened:
##       that part is the engine (SakugaActor.NetsuSuperFlashLook, C#).
##   Assist Cancel (S during your attack, 1 bar) -> a small white burst, no dark screen.
##   Any other move with a flash (cost under 1 bar) -> a burst, no dark screen.
## The engine calls MatchSetup.netsu_super_flash() as the flash starts; this node listens to
## MatchSetup.super_flash. netsu_hud.gd adds it to the battle's CanvasLayer, right above the
## fighters' layer (ViewportContainer), and puts a full-screen dark rect at the bottom of that
## layer: over the stage, under the fighters and the HUD.
## Oct 24 (evening): EX moves and supers also get a streak of light through the fighter and sparks
## drifting off her in her colour (MatchSetup.side_color); the close-up / smoke / big picture are
## netsu_cut_in.gd and the outline around her is the engine (AnimationViewer.SetAura).
## Presentation only: nothing in the match depends on it. Rollback can report a flash twice;
## repeats within repeat_guard seconds are ignored.
## Oct 24 (late): EX moves and supers first stop the whole fight for a moment (the engine's pause,
## GameManager.NetsuPause: the camera closes in on her, FighterCamera). While it lasts the stage is
## darker still (pause_ex_dim / pause_super_dim); it eases back to ex_dim / super_dim as the fight goes on.
## Oct 25: for the fight's first frames (still black) one burst and a spark are drawn nearly transparent, so this
## layer's additive material is compiled then and not at the first EX move (which stalled for a moment).
## Nov 4: the defensive Burst has its own look (see "THE BURST'S LOOK" below). Nov 4 (evening): redone after Million
## Arthur: Arcana Blood (a ring of fire round a torn blue void, the screen washed gold); the Persona 4 Arena Ultimax
## whirlwind of the morning is gone. Nov 4 (night, TamaDeez): the red fiery stage after it is gone too (blue wisps stay),
## the timing is DFCI's Escape Blast (it goes off on frame 4), and the powered-up Burst (in Overdrive) is bigger.

@export_group("Dark screen")
@export var ex_dim: float = 0.55           ## darkness for EX moves (0-1)
@export var super_dim: float = 0.65        ## darkness for supers
@export var dim_color: Color = Color(0.016, 0.008, 0.04)
@export var dim_in: float = 0.05           ## seconds to go dark
@export var dim_out: float = 0.3           ## seconds to fade back after the freeze
@export var pause_ex_dim: float = 0.86     ## darkness while an EX move's pause holds the fight
@export var pause_super_dim: float = 0.9   ## darkness while a super's pause holds the fight
@export var pause_out: float = 0.18        ## seconds to ease from the pause's darkness to the flash's
@export var overdrive_dim: float = 0.28    ## Oct 26 evening: the stage's tint while anyone's Overdrive runs (MatchSetup.overdrive_hud)

@export_group("Burst")
@export var burst_time: float = 0.55       ## seconds
@export var ray_count: int = 14
@export var ray_length: float = 1.7        ## metres in the fight (a fighter is about 1.4 m tall)
@export var ray_width: float = 0.035       ## metres, at the centre
@export var ray_spin: float = 3.0          ## radians per second
@export var glow_radius: float = 0.75      ## metres
@export var ring_from: float = 0.27        ## metres
@export var ring_to: float = 1.45          ## metres
@export var ring_width: float = 4.0        ## screen pixels
@export var p1_color: Color = Color(0.55, 0.8, 1.0)     ## glow colour, player 1 side
@export var p2_color: Color = Color(1.0, 0.55, 0.62)    ## glow colour, player 2 side
@export var ray_color: Color = Color(1.0, 0.94, 0.78)
@export var cancel_scale: float = 0.55     ## Assist Cancel burst size
@export var rc_color: Color = Color(1.0, 0.1, 0.08)     ## Oct 27 c35: Roman Cancel glow (red)
@export var rc_ray_color: Color = Color(1.0, 0.45, 0.35)
@export var rc_scale: float = 1.25         ## Roman Cancel burst size
@export var rc_tint: float = 0.0          ## Roman Cancel: how red the stage goes while the fight is stopped (0-1)
@export var repeat_guard: float = 0.4      ## seconds

@export_group("Streak and sparks")
@export var streak_time: float = 0.28      ## seconds the line of light through her lasts
@export var streak_length: float = 2600.0  ## screen pixels
@export var spark_count: int = 18          ## EX (supers get half again as many)
@export var spark_time: float = 0.75       ## seconds
@export var spark_speed: float = 0.9       ## metres per second
@export var spark_size: float = 0.07       ## metres

var _dim: ColorRect
var _dim_level := 0.0
var _dim_target := 0.0
var _dim_hold := 0.0
var _bursts: Array = []      # {side, pos: Vector3, t, size, time, color, ring, big}
var _sparks: Array = []      # {pos: Vector3, vel: Vector3, t, time, size, color}
var _rng := RandomNumberGenerator.new()
var _last := {}              # "side:kind" -> msec
var _glow: GradientTexture2D
var _container: SubViewportContainer
var _viewport: SubViewport
var _camera: Camera3D
var _game: Node              # GameManager (C#): the pause (NetsuPauseInfo)
var _pause_kind := 0         # 0 EX, 1 super: the last big flash
var _warm := 0               # frames of invisible warm-up drawing left
var _rc_hold := 0.0          # Oct 27 c35: seconds of red stage tint left (Roman Cancel)
var _rc_level := 0.0


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var add := CanvasItemMaterial.new()
	add.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	material = add
	_glow = _make_glow()
	_bb_textures()   # Nov 4: the Burst's textures (made here, once a run) and its other layers
	_bb_layers()
	if MatchSetup.has_signal("super_flash"):
		MatchSetup.super_flash.connect(_on_flash)
	_place.call_deferred()


## Above the fighters' layer, and the dark rect at the very bottom of the CanvasLayer.
func _place() -> void:
	var root := get_parent()
	if root == null:
		return
	_container = root.get_node_or_null("ViewportContainer") as SubViewportContainer
	if _container:
		_viewport = _container.get_node_or_null("Viewport_Foreground") as SubViewport
		if _viewport:
			_camera = _viewport.get_node_or_null("CharacterCamera") as Camera3D
		root.move_child(self, _container.get_index() + 1)
	_dim = ColorRect.new()
	_dim.name = "NetsuStageDim"
	_dim.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_dim.color = Color(dim_color, 0.0)
	_dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_child(_dim)
	root.move_child(_dim, 0)
	_dim.add_child(_bb_under)   # Nov 4: the Burst's layers under the fighters ride on the dim (over the stage, under them)
	var battle := root.get_parent()
	if battle:
		for n in battle.get_children():
			if n.has_method("NetsuPauseInfo"):
				_game = n
	_warm = 4


func _warm_tick() -> void:
	_warm -= 1
	if _warm > 0:
		modulate.a = 0.01   # under the fight's black screen anyway
		if _bb_under:
			_bb_under.modulate.a = 0.01
		var pos := Vector3(0.0, 1.0, 0.0)
		_bursts = [{"side": -1, "pos": pos, "t": 0.05, "size": 1.0, "time": burst_time, "color": p1_color, "ring": true, "big": true}]
		_sparks = [{"side": -1, "pos": pos, "vel": Vector3.ZERO, "t": 0.05, "time": spark_time, "size": spark_size, "color": p1_color}]
		# Nov 4: and two Bursts, one pressing and one going off (every kind of thing it draws, on all five of its layers)
		var press := _bb_new(-1, pos, "stars", bb_veil_time)
		press["t"] = 0.05
		var warm := _bb_new(-1, pos, "stars", bb_veil_time)
		warm["t"] = 0.36
		warm["boom"] = 0.25
		_bb_blast(warm)
		for p in warm["bits"]:
			p["t"] = 0.05
		_bb = [press, warm]
		_redraw_bb()
	else:
		modulate.a = 1.0
		if _bb_under:
			_bb_under.modulate.a = 1.0
		_bursts = _bursts.filter(func(b): return b["side"] != -1)
		_sparks = _sparks.filter(func(p): return p["side"] != -1)
		_bb = _bb.filter(func(b): return b["side"] != -1)
		_redraw_bb()


func _make_glow() -> GradientTexture2D:
	var g := Gradient.new()
	g.offsets = PackedFloat32Array([0.0, 0.35, 1.0])
	g.colors = PackedColorArray([Color(1, 1, 1, 1), Color(1, 1, 1, 0.55), Color(1, 1, 1, 0)])
	var tex := GradientTexture2D.new()
	tex.gradient = g
	tex.fill = GradientTexture2D.FILL_RADIAL
	tex.fill_from = Vector2(0.5, 0.5)
	tex.fill_to = Vector2(1.0, 0.5)
	tex.width = 128
	tex.height = 128
	return tex


func _on_flash(side: int, pos: Vector3, cost: int, frames: int) -> void:
	if _warm > 0:
		_warm = 1
		_warm_tick()
	if cost == -6:
		_on_burst_start(side, pos, frames)   # Nov 4: the Burst is pressed (frame 0; frames: when it goes off)
		return
	if cost == -3 or cost == -7:
		_on_burst(side, pos, frames, cost == -7)   # it goes off (frame 4; frames: how long the blast lasts; -7 powered up)
		return
	if cost == -4:
		return   # Nov 3: the PUNISH ring / text was removed
	if cost == -5:
		for b in _bb:   # Nov 3: the Burst follows the Burster while it lasts
			if b["side"] == side:
				b["pos"] = pos
		return
	# kind: 0 EX, 1 super, 2 Assist Cancel, 3 another flash, 4 Roman Cancel (cost -2; Oct 28: removed from the
	# engine, nothing sends -2 any more). Oct 29: EX moves cost 10000 (1 bar), supers 30000 (units x5).
	var kind := 4 if cost == -2 else (2 if cost < 0 else (1 if cost >= 30000 else (0 if cost >= 10000 else 3)))
	var key := "%d:%d" % [side, kind]
	var now := Time.get_ticks_msec()
	if float(now - int(_last.get(key, -100000))) < repeat_guard * 1000.0:
		return
	_last[key] = now
	var col := p1_color if side == 0 else p2_color
	if kind <= 1 and MatchSetup.has_method("side_color"):
		col = MatchSetup.side_color(side).lerp(Color(1, 1, 1), 0.25)
	if kind == 4:
		col = rc_color
		_rc_hold = float(frames) / 60.0 + 0.1
	if kind <= 1:
		_dim_target = super_dim if kind == 1 else ex_dim
		_dim_hold = maxf(_dim_hold, float(frames) / 60.0 + dim_in)
		_pause_kind = kind
	var big := kind <= 1 or kind == 4
	_bursts = _bursts.filter(func(b): return b["side"] != side)
	_bursts.append({"side": side, "pos": pos, "t": 0.0,
		"size": rc_scale if kind == 4 else (1.0 if big else (cancel_scale if kind == 2 else 0.8)),
		"time": burst_time * 1.15 if kind == 4 else (burst_time if big else burst_time * 0.6),
		"color": Color(1, 1, 1) if kind == 2 else col, "ring": kind != 2, "big": big,
		"ray": rc_ray_color if kind == 4 else ray_color})
	if big:
		_sparks = _sparks.filter(func(p): return p["side"] != side)
		var n := spark_count + (int(spark_count * 0.5) if kind == 1 else 0) + (spark_count if kind == 4 else 0)
		for i in n:
			var ang := _rng.randf() * TAU
			var dir := Vector3(cos(ang), sin(ang) * 0.8 + 0.35, 0.0).normalized()
			var start := pos + Vector3(_rng.randf_range(-0.35, 0.35), _rng.randf_range(-0.55, 0.45), 0.0)
			_sparks.append({"side": side, "pos": start, "vel": dir * spark_speed * _rng.randf_range(0.4, 1.3),
				"t": -_rng.randf_range(0.0, 0.12), "time": spark_time * _rng.randf_range(0.6, 1.1),
				"size": spark_size * _rng.randf_range(0.5, 1.3), "color": col})


## Nov 4 (evening; Million Arthur: Arcana Blood, 0:03-0:05 of TamaDeez's clip): THE BURST'S LOOK. (The morning's was
## Persona 4 Arena Ultimax's whirlwind and gold blast.) The engine (SakugaActor.NetsuBurstCue) sends:
##   cost -6 as she presses it (frame 0; frames = 4, when it goes off): she snaps into her pose (her sprite flashes pale
##           blue: the engine), a pale flash of light on her, and a dark see-through veil sweeps out from her;
##   cost -3 on frame 4 (frames = 20, how long the blast is drawn; it hits for 9): the blast, at full size at once, round
##           her chest and about 1.5 times her height across: a blazing white-gold rim with burnt orange / brown edges, a
##           torn dark-blue void inside it with blue energy swirling in it, white-hot streaks spraying out sideways and the
##           whole screen washed gold (her sprite flashes gold: the engine). Over its 20 frames the ring opens out a little
##           and frays apart and the void turns blue; then blue flame wisps rise round her and fade out over bb_after_time
##           (about half a second). (Nov 4 night: the deep red fiery stage that came with them is gone.)
##   cost -7 instead of -3 (frames = 27): the powered-up Burst (in Overdrive), drawn bb_powered_scale bigger;
##   cost -5 every other frame (frames = her state frame): where she is now, so all of it follows her.
## Each fighter adds her own touch to the blast (bb_styles, by FighterProfile.ShortName): Cecilia's lightning crackles
## round the rim; Flan's stars, Leticia's embers (and cyan tracers) and Noah's violet crystal shards burst out of it.
## Five layers, so it reads on bright stages and dark ones. Under the fighters, on the stage dim: BurstUnder (normal
## blend: the veil, the void, the burnt band, the wisps) and BurstUnderLight on it (additive: the energy in the void, the
## wisps' bright cores). Over them: this node (additive: the gold wash),
## BurstPaint (normal blend: the stars, shards and embers, the lightning's glow) and BurstLight (additive: the rim, the
## streaks, the torn edges catching the light, the pale flash, the lightning, the glints).
## Its textures (the rim, the burnt band, the swirl) are made at runtime (_bb_textures): no image files.
## Presentation only: nothing in the match reads any of it.
@export_group("Burst (the defensive Burst)")
@export var bb_ring_radius: float = 0.85       ## metres: the blazing rim's middle, round her chest (a fighter is about 1.3-1.5 m tall)
@export var bb_rim_width: float = 0.5          ## metres: how wide the blazing rim is, its glow included
@export var bb_void_radius: float = 0.46       ## metres: the dark void inside it, out to its torn edge (on average)
@export var bb_ring_grow: float = 0.12         ## how much the ring opens out over the blast (0.12 = 12 %)
@export var bb_veil_time: float = 0.117        ## seconds the veil takes to sweep out (the -6 cue's frames win)
@export var bb_blast_time: float = 0.333       ## seconds the blast lasts (the -3 / -7 cue's frames win)
@export var bb_after_time: float = 0.5         ## seconds the wisps take to fade out after the blast
@export var bb_powered_scale: float = 1.35     ## Nov 4 night: the powered-up Burst (in Overdrive) is drawn this much bigger
@export var bb_streak_count: int = 20          ## white-hot streaks spraying out sideways (half each way)
@export var bb_streak_length: float = 2.4      ## metres: the longest of them
@export var bb_wisp_count: int = 9             ## blue flame wisps rising round her after the blast
@export var bb_wash: float = 0.55              ## how strongly the screen is washed gold (0-1)
@export var bb_bloom: float = 0.6              ## the glow round the outside of the rim (0-1)
@export var bb_flash: float = 0.6              ## the pale flash on her as she presses it (0-1)
@export var bb_veil: float = 0.45              ## how dark the veil is (0-1)
@export var bb_rim_color: Color = Color(1.0, 0.96, 0.7)      ## the rim's white-hot middle, and the streaks'
@export var bb_gold: Color = Color(1.0, 0.76, 0.34)          ## the rim's glow
@export var bb_rim_paint: Color = Color(1.0, 0.86, 0.42)     ## the rim's colour under its light (so it stays gold on a bright stage)
@export var bb_wash_color: Color = Color(1.0, 0.72, 0.3)     ## the gold the screen is washed with
@export var bb_burn_color: Color = Color(0.72, 0.36, 0.16)   ## the burnt band (lit)
@export var bb_char_color: Color = Color(0.12, 0.05, 0.04)   ## its charred, torn edge
@export var bb_void_color: Color = Color(0.03, 0.05, 0.14)   ## the void as it opens
@export var bb_void_blue: Color = Color(0.12, 0.26, 0.72)    ## the void as it brightens
@export var bb_energy_color: Color = Color(0.45, 0.68, 1.0)  ## the energy swirling in it
@export var bb_veil_color: Color = Color(0.04, 0.03, 0.1)
@export var bb_flash_color: Color = Color(0.82, 0.9, 1.0)
@export var bb_wisp_color: Color = Color(0.14, 0.34, 0.95)  ## the blue flame wisps after it
@export var bb_wisp_core: Color = Color(0.62, 0.84, 1.0)    ## their bright cores
## Each fighter's touch: FighterProfile.ShortName (lower case) -> "lightning", "stars", "embers" or "shards".
@export var bb_styles: Dictionary = {"cecilia": "lightning", "flan": "stars", "leticia": "embers", "noah": "shards"}

const BB_LIGHTNING := Color(1.0, 0.9, 0.3)     # Cecilia's lightning (her burst sprite's yellow)
const BB_STAR := Color(1.0, 0.8, 0.22)         # Flan's stars
const BB_EMBER := Color(1.0, 0.5, 0.13)        # Leticia's fire
const BB_CYAN := Color(0.3, 0.86, 1.0)         # Leticia's guns
const BB_VIOLET := Color(0.62, 0.26, 1.0)      # Noah's crystal
const BB_SEGS := 72                            # points round the void's torn outline (and the band, the swirl, the wash)
const BB_RIM_SEGS := 96                        # points round the rim
const BB_TEX_W := 256                          # the ring textures: columns round the ring ...
const BB_TEX_H := 32                           # ... by rows across it

static var _bb_tex := {}   # the Burst's textures, made once a run (_bb_textures)

var _bb: Array = []          # one per Burst (_bb_new)
var _bb_paint: Control       # over the fighters: the Burst's paint (normal blend) ...
var _bb_light: Control       # ... and the light on top (additive)
var _bb_under: Control       # under the fighters: its paint (normal blend) ...
var _bb_under_light: Control # ... and its light (additive)
var _bb_idx := {}            # triangle indices of its meshes, by shape


## The Burst's other layers: two children of this one (drawn after it) and two for under the fighters (_place puts
## BurstUnder on the stage dim; BurstUnderLight is its child).
func _bb_layers() -> void:
	_bb_paint = Control.new()
	_bb_paint.name = "BurstPaint"
	_bb_light = Control.new()
	_bb_light.name = "BurstLight"
	_bb_under = Control.new()
	_bb_under.name = "BurstUnder"
	_bb_under_light = Control.new()
	_bb_under_light.name = "BurstUnderLight"
	for layer in [_bb_light, _bb_under_light]:
		var add := CanvasItemMaterial.new()
		add.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
		layer.material = add
	for layer in [_bb_paint, _bb_light, _bb_under, _bb_under_light]:
		layer.mouse_filter = Control.MOUSE_FILTER_IGNORE
		layer.texture_repeat = CanvasItem.TEXTURE_REPEAT_ENABLED   # the ring textures wrap round
		layer.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(_bb_paint)
	add_child(_bb_light)
	_bb_under.add_child(_bb_under_light)
	_bb_paint.draw.connect(func(): _draw_bb_layer(_bb_paint, 1))
	_bb_light.draw.connect(func(): _draw_bb_layer(_bb_light, 2))
	_bb_under.draw.connect(func(): _draw_bb_layer(_bb_under, 3))
	_bb_under_light.draw.connect(func(): _draw_bb_layer(_bb_under_light, 4))


func _exit_tree() -> void:
	if is_instance_valid(_bb_under) and not _bb_under.is_inside_tree():
		_bb_under.queue_free()   # (_place never ran)


## One layer: 0 light under the paint, 1 paint, 2 light on top (over the fighters); 3 paint, 4 light (under them).
func _draw_bb_layer(ci: CanvasItem, layer: int) -> void:
	for b in _bb:
		_draw_bb(ci, b, layer)


func _redraw_bb() -> void:
	queue_redraw()
	for layer in [_bb_paint, _bb_light, _bb_under, _bb_under_light]:
		if layer:
			layer.queue_redraw()


## The touch for a side's fighter ("" = just the Burst itself).
func _bb_style(side: int) -> String:
	if side < 0 or not MatchSetup.has_method("settings"):
		return ""
	var cfg = MatchSetup.settings()
	if cfg == null:
		return ""
	var index := int(cfg.P1SelectedCharacter if side == 0 else cfg.P2SelectedCharacter)
	if index < 0 or index >= MatchSetup.fighter_count():
		return ""
	var profile = MatchSetup.fighter_profile(index)
	if profile == null:
		return ""
	return String(bb_styles.get(String(profile.get("ShortName")).to_lower(), ""))


## True if this cue already came within repeat_guard (rollback can send one twice); notes it otherwise.
func _repeat(side: int, kind: String) -> bool:
	var key := "%d:%s" % [side, kind]
	var now := Time.get_ticks_msec()
	if float(now - int(_last.get(key, -100000))) < repeat_guard * 1000.0:
		return true
	_last[key] = now
	return false


func _bb_new(side: int, pos: Vector3, style: String, veil: float) -> Dictionary:
	return {"side": side, "pos": pos, "t": 0.0, "boom": -1.0, "style": style, "seed": _rng.randi() % 100000,
		"veil": veil, "blast": maxf(bb_blast_time, 0.05), "rot": _rng.randf() * TAU, "u": _rng.randf(),
		"shape": PackedFloat32Array(), "corners": [], "edges": [], "streaks": [], "wisps": [], "bits": []}


## cost -6 (frame 0): she presses it.
func _on_burst_start(side: int, pos: Vector3, frames: int) -> void:
	if _repeat(side, "burst_start"):
		return
	_bb = _bb.filter(func(b): return b["side"] != side)
	_bb.append(_bb_new(side, pos, _bb_style(side), float(frames) / 60.0 if frames > 0 else bb_veil_time))
	_redraw_bb()


## cost -3 (frame 4): it goes off; -7 = the powered-up Burst (in Overdrive), drawn bb_powered_scale bigger.
func _on_burst(side: int, pos: Vector3, frames: int, big: bool = false) -> void:
	if _repeat(side, "burst"):
		return
	var b = null
	for e in _bb:
		if e["side"] == side and float(e["boom"]) < 0.0:
			b = e
	if b == null:   # the press was missed (it came before this layer was ready): straight to the blast
		b = _bb_new(side, pos, _bb_style(side), bb_veil_time)
		b["t"] = bb_veil_time
		_bb.append(b)
	b["pos"] = pos
	b["boom"] = 0.0
	b["scale"] = bb_powered_scale if big else 1.0
	b["blast"] = maxf(float(frames) / 60.0 if frames > 0 else bb_blast_time, 0.05)
	_bb_blast(b)
	_redraw_bb()


## Everything the blast needs, rolled once as it goes off.
func _bb_blast(b: Dictionary) -> void:
	var pos: Vector3 = b["pos"]
	var torn := _bb_shape()
	b["shape"] = torn[0]
	b["corners"] = torn[1]
	var corners: Array = b["corners"]
	# three of the void's torn edges catch the light as it opens
	var edges: Array = []
	var first := _rng.randi() % corners.size()
	for i in 3:
		edges.append({"k": (first + i * 3 + _rng.randi() % 2) % corners.size(), "delay": _rng.randf_range(0.0, 0.05),
			"life": _rng.randf_range(0.14, 0.24)})
	b["edges"] = edges
	# white-hot streaks spraying out sideways, left and right
	var streaks: Array = []
	for i in bb_streak_count:
		var away := 0.0 if i % 2 == 0 else PI
		var spread := _rng.randf_range(0.0, 0.38) * (1.0 if (i / 2) % 2 == 0 else -1.0)
		streaks.append({"ang": away + spread, "len": _rng.randf_range(0.45, 1.0), "w": _rng.randf_range(0.5, 1.5),
			"delay": 0.0 if i < 6 else _rng.randf_range(0.0, 0.08), "life": _rng.randf_range(0.18, 0.34)})
	b["streaks"] = streaks
	# the blue flame wisps that rise round her after it (metres from her chest; up is +)
	var wisps: Array = []
	var bt: float = b["blast"]
	for i in bb_wisp_count:
		var side := -1.0 if i % 2 == 0 else 1.0
		wisps.append({"x": side * _rng.randf_range(0.1, 0.4), "y": _rng.randf_range(-0.7, 0.05),
			"h": _rng.randf_range(0.9, 1.6), "w": _rng.randf_range(0.2, 0.34), "lean": side * _rng.randf_range(0.05, 0.35),
			"sway": _rng.randf_range(0.04, 0.09), "freq": _rng.randf_range(7.0, 11.0), "ph": _rng.randf() * TAU,
			"born": bt * 0.65 + 0.3 * float(i) / float(maxi(bb_wisp_count, 1)) + _rng.randf_range(0.0, 0.04),
			"life": _rng.randf_range(0.3, 0.45)})
	b["wisps"] = wisps
	# her touch (in the fight: these fly free, they don't follow her)
	var ring := bb_ring_radius
	match String(b["style"]):
		"stars":
			for i in 14:   # stars bursting out of the void, spinning
				var ang := TAU * (float(i) + _rng.randf()) / 14.0
				var d := Vector3(cos(ang), sin(ang), 0.0)
				b["bits"].append({"kind": "star", "pos": pos + d * 0.2, "vel": d * _rng.randf_range(2.4, 4.6),
					"t": -_rng.randf_range(0.0, 0.04), "time": _rng.randf_range(0.45, 0.7), "size": _rng.randf_range(0.08, 0.15),
					"spin": _rng.randf_range(-9.0, 9.0), "color": BB_STAR})
			for i in 9:    # and glints twinkling on the rim
				var ang := _rng.randf() * TAU
				var r := ring * _rng.randf_range(0.95, 1.2)
				b["bits"].append({"kind": "twinkle", "pos": pos + Vector3(cos(ang) * r, sin(ang) * r, 0.0), "vel": Vector3.ZERO,
					"t": -_rng.randf_range(0.02, 0.3), "time": _rng.randf_range(0.16, 0.26), "size": _rng.randf_range(0.1, 0.18),
					"color": Color(1.0, 0.95, 0.75)})
		"embers":
			for i in 24:   # embers thrown off the burning rim, falling
				var ang := _rng.randf() * TAU
				var d := Vector3(cos(ang), sin(ang), 0.0)
				b["bits"].append({"kind": "ember", "pos": pos + d * ring * 0.85, "vel": (d + Vector3(0, 0.35, 0)) * _rng.randf_range(1.6, 4.2),
					"t": -_rng.randf_range(0.0, 0.1), "time": _rng.randf_range(0.45, 0.85), "size": _rng.randf_range(0.025, 0.05),
					"grav": 6.5, "color": BB_EMBER})
			for i in 5:    # her cyan tracers, shot out of the void
				b["bits"].append({"kind": "tracer", "pos": pos, "ang": _rng.randf() * TAU, "from": bb_void_radius * 0.9,
					"len": _rng.randf_range(1.4, 2.4), "t": -_rng.randf_range(0.0, 0.07), "time": 0.16, "color": BB_CYAN})
		"shards":
			for i in 12:   # violet crystal shards bursting out of the void, spinning
				var ang := _rng.randf() * TAU
				var d := Vector3(cos(ang), sin(ang), 0.0)
				b["bits"].append({"kind": "shard", "pos": pos + d * 0.2, "vel": d * _rng.randf_range(2.2, 4.2),
					"t": -_rng.randf_range(0.0, 0.04), "time": _rng.randf_range(0.4, 0.65), "size": _rng.randf_range(0.12, 0.24),
					"rot": ang, "spin": _rng.randf_range(-6.0, 6.0), "color": BB_VIOLET})


## The void's torn outline: 8-11 corners joined by straight edges, like torn paper.
## [PackedFloat32Array: its radius (x bb_void_radius) at each of BB_SEGS points round it, Array: the corners (Vector2)]
func _bb_shape() -> Array:
	var n := 7 + _rng.randi() % 3
	var angs := PackedFloat32Array()
	var corners: Array = []
	for k in n:
		var ang := TAU * (float(k) + _rng.randf_range(0.0, 0.6)) / float(n)
		angs.append(ang)
		corners.append(Vector2.from_angle(ang) * _rng.randf_range(0.8, 1.16))
	var shape := PackedFloat32Array()
	shape.resize(BB_SEGS)
	for i in BB_SEGS:
		var a := TAU * float(i) / float(BB_SEGS)
		var k := n - 1   # (before the first corner: the edge from the last one round to it)
		for j in n:
			if angs[j] <= a:
				k = j
		var p: Vector2 = corners[k]
		var q: Vector2 = corners[(k + 1) % n]
		var d := Vector2.from_angle(a)
		var e := q - p
		var den := d.x * e.y - d.y * e.x
		var r := (p.x * e.y - p.y * e.x) / den if absf(den) > 0.0001 else p.length()
		shape[i] = clampf(r, 0.6, 1.25) * _rng.randf_range(0.98, 1.02)
	return [shape, corners]


func _bb_tick(delta: float) -> void:
	var drag := pow(0.16, delta)
	for b in _bb:
		b["t"] += delta
		if float(b["boom"]) >= 0.0:
			b["boom"] += delta
		for p in b["bits"]:
			p["t"] += delta
			if p["t"] > 0.0 and p.has("vel"):
				var v: Vector3 = p["vel"]
				p["pos"] += v * delta
				v *= drag
				v.y -= float(p.get("grav", 0.0)) * delta
				p["vel"] = v
	_bb = _bb.filter(func(b): return (float(b["boom"]) < 0.0 and float(b["t"]) < 0.6) \
		or (float(b["boom"]) >= 0.0 and float(b["boom"]) < maxf(float(b["blast"]) + bb_after_time + 0.08, 1.0)))


## One Burst on one layer (see _draw_bb_layer).
func _draw_bb(ci: CanvasItem, b: Dictionary, layer: int) -> void:
	var pos: Vector3 = b["pos"]
	var c := _to_screen(pos)
	var metre := (_to_screen(pos + Vector3(0, 1, 0)) - c).length() * float(b.get("scale", 1.0))   # powered up: bigger
	if metre <= 0.0:
		return
	var boom: float = b["boom"]
	if boom < 0.06:
		_draw_bb_press(ci, b, c, metre, layer)
	if boom >= 0.0:
		_draw_bb_blast(ci, b, c, metre, boom, layer)
		if layer >= 3:
			_draw_bb_wisps(ci, b, c, metre, boom, layer)
		elif layer == 2:   # and the blue of it on her, while the wisps rise round her
			var bt: float = b["blast"]
			var aura := 0.16 * smoothstep(bt * 0.7, bt, boom) * (1.0 - smoothstep(bt + 0.1, bt + bb_after_time, boom))
			if aura > 0.0:
				var body := Vector2(0.9, 1.7) * metre
				var q := c + Vector2(0.0, 0.15 * metre)
				ci.draw_texture_rect(_glow, Rect2(q - body * 0.5, body), false, Color(bb_energy_color, aura))
	for p in b["bits"]:
		_draw_bb_bit(ci, p, c, metre, layer)


## The press: a pale flash on her, and a dark see-through veil sweeping out from her until it goes off.
func _draw_bb_press(ci: CanvasItem, b: Dictionary, c: Vector2, metre: float, layer: int) -> void:
	var t: float = b["t"]
	var boom: float = b["boom"]
	if layer == 2:
		if t < 0.08 and bb_flash > 0.0:
			var k := t / 0.08
			var a := bb_flash * (1.0 - k) * (1.0 - k)
			var body := Vector2(0.85, 1.75) * metre   # all of her (her chest is 0.9 m up)
			var q := c + Vector2(0.0, 0.22 * metre)
			ci.draw_texture_rect(_glow, Rect2(q - body * 0.5, body), false, Color(bb_flash_color, a))
			var core := Vector2(0.45, 1.0) * metre
			ci.draw_texture_rect(_glow, Rect2(q - core * 0.5, core), false, Color(1, 1, 1, a * 0.8))
		return
	if layer != 3 or bb_veil <= 0.0:
		return
	var vt: float = maxf(float(b["veil"]), 0.02)
	var k := clampf(t / vt, 0.0, 1.0)
	var a := bb_veil * minf(1.0, t / 0.025 + 0.25)
	if boom >= 0.0:
		a *= 1.0 - clampf(boom / 0.06, 0.0, 1.0)   # the void takes over
	elif t > vt + 0.04:
		a *= 1.0 - clampf((t - vt - 0.04) / 0.15, 0.0, 1.0)   # (it never went off)
	if a <= 0.0:
		return
	var reach := bb_ring_radius * 1.12
	var r := (0.2 + (reach - 0.2) * (1.0 - pow(1.0 - k, 2.4))) * metre
	var sd: int = b["seed"]
	var front := PackedFloat32Array()
	front.resize(48)
	for i in 48:
		var u := float(i) / 48.0
		front[i] = r * (0.84 + 0.3 * _bb_noise(u + t * 0.6, 7, sd) + 0.12 * _bb_noise(u - t * 0.4, 19, sd + 1))
	var col := bb_veil_color
	_bb_polar(ci, c, 48, float(b["rot"]) + t * 5.0, [0.0, r * 0.55, r * 0.8, front],
		[Color(col, a * 0.45), Color(col, a * 0.7), Color(col, a), Color(col, 0.0)])


## The blast and its fraying, on each layer.
func _draw_bb_blast(ci: CanvasItem, b: Dictionary, c: Vector2, metre: float, boom: float, layer: int) -> void:
	var shape: PackedFloat32Array = b["shape"]
	if shape.size() != BB_SEGS:
		return
	var bt: float = b["blast"]
	var k := boom / bt
	var kk := clampf(k, 0.0, 1.0)
	var open := 1.0 - (1.0 - kk) * (1.0 - kk)
	var ring := bb_ring_radius * metre * (1.0 + bb_ring_grow * open)   # the rim's middle (pixels)
	var wide := bb_rim_width * metre * (1.0 + 0.45 * kk)
	var hole := bb_void_radius * metre * (1.0 + 0.3 * open)             # the void's torn edge, on average
	var band_out := ring - wide * 0.3                                   # the burnt band runs out under the rim's glow
	var spin: float = b["rot"]
	var u0: float = b["u"]
	var style: String = b["style"]
	var sd: int = b["seed"]
	var band := 1.0 - smoothstep(0.6, 1.0, k)          # the burnt band burns away as the rim frays ...
	var dark := 1.0 - smoothstep(0.7, 1.05, k)         # ... the void's dark goes with it ...
	var lit := smoothstep(0.1, 0.8, k) * (1.0 - smoothstep(0.95, 1.3, k))   # ... after it has brightened to blue
	var wash := bb_wash * (1.0 - smoothstep(0.55, 1.0, k))   # the gold wash gives way to the red stage
	if boom < 0.05:
		wash = minf(1.0, wash * (1.0 + 0.5 * (1.0 - boom / 0.05)))
	var far := maxf(size.x, size.y) * 2.5
	match layer:
		0:   # light over the whole screen (so it glows on a dark stage too); none in the void
			if wash <= 0.0:
				return
			var g := bb_gold
			var w := wash * 0.35
			_bb_polar(ci, c, BB_SEGS, spin, [_bb_scaled(shape, hole * 0.95), band_out, ring + wide * 0.6, ring * 2.3, far],
				[Color(g, 0.0), Color(g, 0.4 * w), Color(g, w), Color(g, 0.7 * w), Color(g, 0.5 * w)])
		1:   # (paint) the screen washed gold (so it holds its colour on a bright stage), and Cecilia's lightning's glow
			if wash > 0.0:
				var g := bb_wash_color
				_bb_polar(ci, c, BB_SEGS, spin, [_bb_scaled(shape, hole), band_out, ring + wide * 0.62, ring * 2.4, far],
					[Color(g, 0.0), Color(g, 0.12 * wash), Color(g, wash), Color(g, 0.75 * wash), Color(g, 0.55 * wash)])
			if style == "lightning":
				_bb_lightning(ci, c, ring, metre, sd, boom, k, true)
		2:
			_draw_bb_rim(ci, b, c, metre, boom, k, ring, wide)
			_draw_bb_rays(ci, b, c, metre, boom, k, ring, hole)
			if style == "lightning":
				_bb_lightning(ci, c, ring, metre, sd, boom, k, false)
		3:   # (under her) the void, dark navy turning blue, and the burnt band round it, torn along the void
			if dark <= 0.0:
				return
			var e: float = _bb_tex.get("edge_mean", 0.3)
			var vr := PackedFloat32Array()
			var br := PackedFloat32Array()
			vr.resize(BB_SEGS)
			br.resize(BB_SEGS)
			for i in BB_SEGS:
				var inner := (hole * shape[i] - e * band_out) / (1.0 - e)   # so the band's torn edge falls on the void's
				br[i] = minf(inner, band_out - 2.0)
				vr[i] = br[i] + (band_out - br[i]) * 0.68                 # (the void runs on under the band ...
			var vc := bb_void_color.lerp(bb_void_blue, pow(kk, 1.3))
			var edge_a := 0.95 * dark * band                                # ... and fades out with it)
			_bb_polar(ci, c, BB_SEGS, spin, [0.0, _bb_scaled(shape, hole * 0.92), vr],
				[Color(vc.lightened(0.06), 0.95 * dark), Color(vc.darkened(0.3), 0.95 * dark), Color(vc.darkened(0.35), edge_a)])
			if band <= 0.0:
				return
			var vs := PackedFloat32Array([0.0, 1.0])
			_bb_polar(ci, c, BB_SEGS, spin, [br, band_out],
				[_bb_col(bb_burn_color, 0.62 + 0.3 * kk, band), _bb_col(bb_burn_color, 1.05 + 0.2 * kk, band)], _bb_tex["burn"], u0, 2.0, vs)
			_bb_polar(ci, c, BB_SEGS, spin, [br, band_out], [Color(bb_char_color, band), Color(bb_char_color, band)], _bb_tex["char"], u0, 2.0, vs)
			# the rim's gold, painted under its light (her feet stay on top of it)
			var pa := 0.75 * (1.0 - 0.2 * kk) * (1.0 - smoothstep(0.6, 1.0, k))
			if pa > 0.0:
				var rp := bb_rim_paint
				_bb_polar(ci, c, BB_RIM_SEGS, spin, [ring - wide * 0.45, ring - wide * 0.15, ring + wide * 0.15, ring + wide * 0.5],
					[Color(rp, 0.0), Color(rp, pa), Color(rp, pa), Color(rp, 0.0)])
		4:   # (under her, light) the energy swirling in the void, brighter as it goes, then it thins away
			var ea := 0.22 * dark + 0.9 * lit
			if ea <= 0.0:
				return
			var reach := 1.0 + 0.25 * smoothstep(0.8, 1.3, k)   # (spreading a little as it goes)
			var ec := bb_energy_color
			var tex: Texture2D = _bb_tex["swirl"]
			var vs := PackedFloat32Array([0.0, 0.4, 0.78, 1.0])
			var radii := [0.0, _bb_scaled(shape, hole * 0.4 * reach), _bb_scaled(shape, hole * 0.78 * reach), _bb_scaled(shape, hole * reach)]
			_bb_polar(ci, c, BB_SEGS, spin, radii, [Color(ec, 0.55 * ea), Color(ec, ea), Color(ec, 0.8 * ea), Color(ec, 0.0)],
				tex, u0 - boom * 0.55, 2.0, vs, PackedFloat32Array([0.0, 0.07, 0.16, 0.22]))
			_bb_polar(ci, c, BB_SEGS, spin, radii, [Color(ec, 0.3 * ea), Color(ec, 0.5 * ea), Color(ec, 0.4 * ea), Color(ec, 0.0)],
				tex, u0 + 0.5 + boom * 0.3, 3.0, vs, PackedFloat32Array([0.0, -0.05, -0.12, -0.16]))


## The rim: a blazing white-gold ring, ragged and burnt orange inside, flame-tipped outside; it opens out a little over
## the blast, its white-hot middle goes first and a second, wider ring frays off it.
func _draw_bb_rim(ci: CanvasItem, b: Dictionary, c: Vector2, metre: float, boom: float, k: float, ring: float, wide: float) -> void:
	var kk := clampf(k, 0.0, 1.0)
	var spin: float = b["rot"]
	var u0: float = float(b["u"]) + boom * 0.05
	var vs := PackedFloat32Array([0.0, 0.25, 0.5, 0.75, 1.0])
	var orange := bb_burn_color.lerp(bb_gold, 0.35)
	var hot := bb_gold.lerp(bb_rim_color, 0.35)
	var a := (1.0 - 0.2 * kk) * (1.0 - smoothstep(0.6, 1.0, k))
	var bloom := bb_bloom * (1.0 - smoothstep(0.5, 1.0, k))   # its glow spilling out over the stage
	if bloom > 0.0:
		var g := bb_gold
		_bb_polar(ci, c, 64, spin, [ring, ring + wide * 0.62, ring * 1.55, ring * 2.0],
			[Color(g, 0.55 * bloom), Color(g, 0.6 * bloom), Color(g, 0.18 * bloom), Color(g, 0.0)])
	if a > 0.0:
		var radii := []
		for v in vs:
			radii.append(ring - wide * 0.62 + wide * 1.24 * v)
		_bb_polar(ci, c, BB_RIM_SEGS, spin, radii, [Color(orange, a), Color(bb_gold, a), Color(hot, a), Color(bb_gold, a), Color(orange, a)],
			_bb_tex["rim_glow"], u0, 2.0, vs)
		var ca := a * 0.75 * (1.0 - 0.55 * kk)   # (pale gold-white, not pure white, once it's all added up)
		var cc := Color(bb_rim_color, ca)
		_bb_polar(ci, c, BB_RIM_SEGS, spin, radii, [cc, cc, cc, cc, cc], _bb_tex["rim_core"], u0, 2.0, vs)
	var fray := 0.65 * smoothstep(0.25, 0.6, k) * (1.0 - smoothstep(0.7, 1.05, k))
	if fray > 0.0:
		var r2 := ring * (1.0 + 0.07 * kk)
		var w2 := wide * 1.45
		var radii2 := []
		for v in vs:
			radii2.append(r2 - w2 * 0.62 + w2 * 1.24 * v)
		_bb_polar(ci, c, BB_RIM_SEGS, spin + 0.4, radii2, [Color(orange, fray), Color(bb_gold, fray), Color(bb_gold, fray), Color(orange, fray), Color(orange, 0.0)],
			_bb_tex["rim_glow"], u0 + 0.5, 2.0, vs)


## The light of the blast: the void's torn edges catching it, and the white-hot streaks spraying out sideways.
func _draw_bb_rays(ci: CanvasItem, b: Dictionary, c: Vector2, metre: float, boom: float, k: float, ring: float, hole: float) -> void:
	var spin: float = b["rot"]
	var corners: Array = b["corners"]
	var tick := int(boom * 30.0)
	for h in b["edges"]:
		var lt: float = boom - float(h["delay"])
		var life: float = h["life"]
		if lt <= 0.0 or lt >= life:
			continue
		var j: int = h["k"]
		var a := (1.0 - lt / life) * (0.7 + 0.3 * _hash(tick * 7 + j))
		var p: Vector2 = (corners[j] as Vector2).rotated(spin)
		var q: Vector2 = (corners[(j + 1) % corners.size()] as Vector2).rotated(spin)
		var pts := PackedVector2Array()
		var glow := PackedFloat32Array()
		var line := PackedFloat32Array()
		var gc := PackedColorArray()
		var lc := PackedColorArray()
		for s in 7:
			var u := float(s) / 6.0
			pts.append(c + p.lerp(q, u) * hole * 0.98)
			var prof := sqrt(sin(PI * u))
			glow.append(0.035 * metre * prof)
			line.append(0.009 * metre * prof)
			gc.append(Color(bb_gold.lerp(bb_rim_color, 0.5), 0.55 * a * prof))
			lc.append(Color(1, 1, 0.95, a * prof))
		_bb_strip(ci, pts, glow, gc)
		_bb_strip(ci, pts, line, lc)
	for s in b["streaks"]:
		var lt: float = boom - float(s["delay"])
		var life: float = s["life"]
		if lt <= 0.0 or lt >= life:
			continue
		var a := pow(1.0 - lt / life, 1.2)
		var d := Vector2.from_angle(float(s["ang"]))
		var from := ring * 0.9
		var length: float = float(s["len"]) * bb_streak_length * metre * (0.6 + 0.4 * minf(1.0, lt / 0.05))
		var w: float = float(s["w"]) * 0.045 * metre
		# (a band of light, blurred along its length: about as thick all the way, fading out)
		var pts := PackedVector2Array([c + d * from, c + d * (from + length * 0.25), c + d * (from + length * 0.6), c + d * (from + length)])
		_bb_strip(ci, pts, PackedFloat32Array([w * 3.6, w * 3.6, w * 3.0, w * 2.4]),
			PackedColorArray([Color(bb_gold, 0.42 * a), Color(bb_gold, 0.36 * a), Color(bb_gold, 0.2 * a), Color(bb_gold, 0.0)]))
		_bb_strip(ci, pts, PackedFloat32Array([w, w, w * 0.85, w * 0.6]),
			PackedColorArray([Color(bb_rim_color, a), Color(bb_rim_color, 0.9 * a), Color(bb_rim_color, 0.45 * a), Color(bb_rim_color, 0.0)]))


## After the blast: blue flame wisps rising round her, fading out with the red stage (3 their bodies, 4 their cores).
func _draw_bb_wisps(ci: CanvasItem, b: Dictionary, c: Vector2, metre: float, boom: float, layer: int) -> void:
	var bt: float = b["blast"]
	var env := 1.0 - smoothstep(bt + 0.12, bt + bb_after_time, boom)
	if env <= 0.0:
		return
	var col := bb_wisp_color if layer == 3 else bb_wisp_core
	# bodies: a wide soft one and a narrower one in it (so they're dense in the middle); cores: one thin bright line
	var passes := [[1.0, 0.5], [0.5, 0.5]] if layer == 3 else [[0.4, 0.42]]
	for w in b["wisps"]:
		var lt: float = boom - float(w["born"])
		var life: float = w["life"]
		if lt <= 0.0 or lt >= life:
			continue
		var q := lt / life
		var a := env * minf(1.0, lt / 0.05) * (1.0 - smoothstep(0.45, 1.0, q))
		if a <= 0.0:
			continue
		var grow := 1.0 - pow(1.0 - minf(1.0, lt / 0.14), 2.0)
		var tall: float = float(w["h"]) * grow
		var x0: float = w["x"]
		var y0: float = float(w["y"]) + 0.3 * q
		var lean: float = w["lean"]
		var sway: float = w["sway"]
		var ph: float = float(w["ph"]) + lt * float(w["freq"])
		var wide: float = float(w["w"]) * metre
		var pts := PackedVector2Array()
		var prof := PackedFloat32Array()
		for j in 10:
			var u := float(j) / 9.0
			var x := x0 + lean * u * u * grow + sway * (1.6 * sin(ph - u * 3.2) * pow(u, 1.2) + 0.5 * sin(ph * 1.7 - u * 7.0) * u)
			pts.append(c + Vector2(x, -(y0 + tall * u)) * metre)
			# fat most of the way up, curling to a point, its edge flickering
			prof.append(pow(sin(PI * pow(u, 0.6)), 0.6) * (1.0 - 0.3 * u) * (0.85 + 0.15 * sin(ph * 2.0 + u * 9.0)))
		for layer_pass in passes:
			var half := PackedFloat32Array()
			var cols := PackedColorArray()
			for j in 10:
				var u := float(j) / 9.0
				half.append(wide * float(layer_pass[0]) * prof[j])
				cols.append(Color(col, float(layer_pass[1]) * a * minf(1.0, prof[j] * 2.0) * (1.0 - 0.6 * u * u)))
			_bb_strip(ci, pts, half, cols)


## Cecilia: lightning crackling round the rim (hugging it inside and out) and bolts shooting out through it.
## paint = its glow (BurstPaint, so it shows on a bright stage), else its bright core (BurstLight).
func _bb_lightning(ci: CanvasItem, c: Vector2, ring: float, metre: float, sd: int, boom: float, k: float, paint: bool) -> void:
	var la := 1.0 - smoothstep(0.6, 0.95, k)
	if la > 0.0:
		_bb_rim_arcs(ci, c, ring, metre, sd, boom, 5, la, paint)
	if k < 0.55:
		_bb_bolts(ci, c, metre, sd, boom, 6, bb_void_radius * 0.9, 1.35, 2.0, 1.0 - k / 0.55, paint)


## Bolts shooting out from `from` metres (jagged), redrawn 30 times a second.
func _bb_bolts(ci: CanvasItem, c: Vector2, metre: float, sd: int, t: float, count: int, from: float, r0: float, r1: float,
		alpha: float, paint: bool) -> void:
	var tick := int(t * 30.0)
	for i in count:
		var h := sd * 31 + i * 7 + tick * 131
		var d := Vector2.from_angle(TAU * (float(i) + _hash(h)) / float(count))
		var n := Vector2(-d.y, d.x)
		var start := from * metre
		var length := lerpf(r0, r1, _hash(h + 1)) * metre
		var pts := PackedVector2Array([c + d * start])
		for j in range(1, 8):
			var u := float(j) / 7.0
			var jag := (_hash(h + 10 + j) - 0.5) * 0.28 * metre if j < 7 else 0.0
			pts.append(c + d * (start + (length - start) * u) + n * jag)
		_bolt_line(ci, pts, BB_LIGHTNING, alpha, maxf(1.5, metre * 0.009), paint)
		if _hash(h + 3) > 0.45:   # a fork off the middle
			var fork_at := pts[3]
			var fd := d.rotated((_hash(h + 4) - 0.5) * 1.6)
			var fork := PackedVector2Array([fork_at])
			for j in range(1, 4):
				fork.append(fork_at + fd * length * 0.16 * j + Vector2(-fd.y, fd.x) * (_hash(h + 20 + j) - 0.5) * 0.18 * metre)
			_bolt_line(ci, fork, BB_LIGHTNING, alpha * 0.8, maxf(1.0, metre * 0.006), paint)


## Lightning in arcs round the rim, just inside it and just outside it, redrawn 30 times a second.
func _bb_rim_arcs(ci: CanvasItem, c: Vector2, ring: float, metre: float, sd: int, t: float, count: int, alpha: float, paint: bool) -> void:
	var tick := int(t * 30.0)
	for i in count:
		var h := sd * 17 + i * 13 + tick * 97
		var a0 := TAU * _hash(h)
		var span := 0.5 + 0.8 * _hash(h + 1)
		var r := ring * ((0.74 + 0.1 * _hash(h + 2)) if i % 2 == 0 else (1.14 + 0.1 * _hash(h + 2)))
		var pts := PackedVector2Array()
		for j in 10:
			var u := float(j) / 9.0
			pts.append(c + Vector2.from_angle(a0 + span * u) * (r + (_hash(h + 30 + j) - 0.5) * 0.09 * metre))
		_bolt_line(ci, pts, BB_LIGHTNING, alpha, maxf(1.5, metre * 0.008), paint)


func _bolt_line(ci: CanvasItem, pts: PackedVector2Array, col: Color, alpha: float, width: float, paint: bool = false) -> void:
	if alpha <= 0.0:
		return
	if paint:
		ci.draw_polyline(pts, Color(col.r, col.g * 0.85, col.b * 0.4, 0.5 * alpha), width * 4.5, true)
		return
	ci.draw_polyline(pts, Color(col, 0.9 * alpha), width * 2.0, true)
	ci.draw_polyline(pts, Color(1, 1, 0.85, alpha), width * 0.8, true)


## A mesh round c: n points round it, one ring per entry of radii (a float, or a PackedFloat32Array of n radii, in
## pixels) and cols (a Color, or a PackedColorArray of n), turned by spin. With tex: u runs round it (u_rep times, from
## u0, plus twist[ring]), v across it (vs[ring]); the layers wrap the texture round (texture_repeat).
func _bb_polar(ci: CanvasItem, c: Vector2, n: int, spin: float, radii: Array, cols: Array, tex: Texture2D = null,
		u0: float = 0.0, u_rep: float = 1.0, vs: PackedFloat32Array = PackedFloat32Array(),
		twist: PackedFloat32Array = PackedFloat32Array()) -> void:
	var m := radii.size()
	var count := (n + 1) * m
	var pts := PackedVector2Array()
	pts.resize(count)
	var pc := PackedColorArray()
	pc.resize(count)
	var uv := PackedVector2Array()
	if tex:
		uv.resize(count)
	var dirs := PackedVector2Array()
	dirs.resize(n + 1)
	for i in n + 1:
		dirs[i] = Vector2.from_angle(spin + TAU * float(i) / float(n))
	for j in m:
		var rr = radii[j]
		var cc = cols[j]
		var each_r: bool = rr is PackedFloat32Array
		var each_c: bool = cc is PackedColorArray
		var tw := twist[j] if j < twist.size() else 0.0
		var v := vs[j] if j < vs.size() else float(j) / float(maxi(m - 1, 1))
		for i in n + 1:
			var at := j * (n + 1) + i
			var r: float = rr[i % n] if each_r else rr
			pts[at] = c + dirs[i] * r
			pc[at] = cc[i % n] if each_c else cc
			if tex:
				uv[at] = Vector2(u0 + tw + u_rep * float(i) / float(n), v)
	RenderingServer.canvas_item_add_triangle_array(ci.get_canvas_item(), _bb_polar_idx(n, m), pts, pc, uv,
		PackedInt32Array(), PackedFloat32Array(), tex.get_rid() if tex else RID())


func _bb_polar_idx(n: int, m: int) -> PackedInt32Array:
	var key := "p%d:%d" % [n, m]
	if _bb_idx.has(key):
		return _bb_idx[key]
	var idx := PackedInt32Array()
	for j in m - 1:
		for i in n:
			var a := j * (n + 1) + i
			var b := a + n + 1
			idx.append(a)
			idx.append(a + 1)
			idx.append(b)
			idx.append(a + 1)
			idx.append(b + 1)
			idx.append(b)
	_bb_idx[key] = idx
	return idx


## A soft line through pts: its colour down the middle, fading to nothing at its edges (half = half its width, pixels).
func _bb_strip(ci: CanvasItem, pts: PackedVector2Array, half: PackedFloat32Array, cols: PackedColorArray) -> void:
	var n := pts.size()
	if n < 2:
		return
	var vp := PackedVector2Array()
	vp.resize(n * 3)
	var vc := PackedColorArray()
	vc.resize(n * 3)
	for i in n:
		var d := pts[mini(i + 1, n - 1)] - pts[maxi(i - 1, 0)]
		var side := Vector2(-d.y, d.x).normalized() * half[i]
		var col := cols[i]
		vp[i * 3] = pts[i] + side
		vp[i * 3 + 1] = pts[i]
		vp[i * 3 + 2] = pts[i] - side
		vc[i * 3] = Color(col, 0.0)
		vc[i * 3 + 1] = col
		vc[i * 3 + 2] = Color(col, 0.0)
	var key := "s%d" % n
	if not _bb_idx.has(key):
		var idx := PackedInt32Array()
		for i in n - 1:
			var a := i * 3
			for tri in [[a, a + 1, a + 3], [a + 1, a + 4, a + 3], [a + 1, a + 2, a + 4], [a + 2, a + 5, a + 4]]:
				for v in tri:
					idx.append(v)
		_bb_idx[key] = idx
	RenderingServer.canvas_item_add_triangle_array(ci.get_canvas_item(), _bb_idx[key], vp, vc)


## A textured rect, uv in texture units (so it can wrap round).
func _bb_quad(ci: CanvasItem, r: Rect2, uv: Rect2, col: Color, tex: Texture2D) -> void:
	var pts := PackedVector2Array([r.position, Vector2(r.end.x, r.position.y), r.end, Vector2(r.position.x, r.end.y)])
	var uvs := PackedVector2Array([uv.position, Vector2(uv.end.x, uv.position.y), uv.end, Vector2(uv.position.x, uv.end.y)])
	RenderingServer.canvas_item_add_triangle_array(ci.get_canvas_item(), PackedInt32Array([0, 1, 2, 0, 2, 3]), pts,
		PackedColorArray([col, col, col, col]), uvs, PackedInt32Array(), PackedFloat32Array(), tex.get_rid())


static func _bb_scaled(a: PackedFloat32Array, s: float) -> PackedFloat32Array:
	var out := PackedFloat32Array()
	out.resize(a.size())
	for i in a.size():
		out[i] = a[i] * s
	return out


static func _bb_col(col: Color, light: float, a: float) -> Color:
	return Color(col.r * light, col.g * light, col.b * light, a)


## The Burst's textures, made once a run: white masks (coloured by the vertices they're drawn with), wrapping round.
##   rim_glow: the blazing rim across its width (rows: inside -> outside), ragged inside, flame-tipped outside, streaked;
##   rim_core: the white-hot line down its middle;
##   burn: the burnt band (rows: the void's side -> the rim's), torn along the void's side, streaked, lit toward the rim;
##   char: its charred edge along the tear; ("edge_mean": where the tear is on average, 0-1 across it)
##   swirl: arcs of energy for the void (columns round it, rows out from her);
func _bb_textures() -> void:
	if _bb_tex.has("swirl"):
		return
	var w := BB_TEX_W
	var h := BB_TEX_H
	var glow := PackedByteArray()
	glow.resize(w * h * 4)
	var core := PackedByteArray()
	core.resize(w * h * 4)
	var burn := PackedByteArray()
	burn.resize(w * h * 4)
	var charred := PackedByteArray()
	charred.resize(w * h * 4)
	var edge_sum := 0.0
	for x in w:
		var u := float(x) / float(w)
		var s := _hash(x * 3 + 101)
		var lo := _bb_noise(u, 9, 1)
		var hi := _bb_noise(u, 47, 2)
		var inside := 0.03 + 0.14 * lo + 0.16 * _bb_noise(u, 41, 5) + 0.08 * pow(_hash(x * 17 + 5), 2.0)   # burnt tongues reaching in
		var outside := 0.8 + 0.12 * hi + 0.08 * s
		var mid := 0.5 + 0.06 * (lo - 0.5)
		var thick := 0.11 + 0.06 * hi
		var lum := 0.62 + 0.38 * s
		# its torn edge: big tears and notches, smaller ragged bits on them (burnt paper, not fur)
		var blo := _bb_noise(u, 11, 3)
		var bmid := _bb_noise(u, 29, 4)
		var bhi := _bb_noise(u, 67, 14)
		var tear := smoothstep(0.72, 1.0, _bb_noise(u, 17, 15))   # now and then a wide tear into the void
		var edge := clampf(0.1 + 0.3 * blo + 0.14 * bmid + 0.08 * bhi - 0.22 * tear, 0.02, 0.6)
		edge_sum += edge
		var blum := 0.45 + 0.55 * (0.25 * pow(_hash(x * 5 + 7), 0.7) + 0.75 * _bb_noise(u, 61, 13))   # streaked, dark and bright
		var deep := 0.14 + 0.1 * bmid
		for y in h:
			var v := (float(y) + 0.5) / float(h)
			var i := (y * w + x) * 4
			var body := smoothstep(inside, inside + 0.12, v) * (1.0 - smoothstep(mid + 0.1, outside, v))
			var dd := (v - mid) / thick
			_bb_put(glow, i, 1.0, clampf(body * lum, 0.0, 1.0))
			_bb_put(core, i, 1.0, exp(-dd * dd) * (0.8 + 0.2 * s))
			var d := v - edge
			var a := clampf(d * 48.0 + 0.5, 0.0, 1.0)
			var fleck := _bb_noise2(u, v, 17, 3, 12)   # burnt blotches, drawn out toward the rim
			_bb_put(burn, i, blum * (0.45 + 0.55 * fleck) * (0.45 + 0.55 * smoothstep(edge, 1.0, v)), a)
			_bb_put(charred, i, 1.0, a * (1.0 - smoothstep(0.0, deep, d)))
	_bb_tex["edge_mean"] = edge_sum / float(w)
	var sw := 128
	var sh := 32
	var swirl := PackedByteArray()
	swirl.resize(sw * sh * 4)
	for y in sh:
		var v := (float(y) + 0.5) / float(sh)
		for x in sw:
			var u := float(x) / float(sw)
			var nz := _bb_noise2(u, v, 5, 4, 8) * 0.6 + _bb_noise2(u, v, 13, 9, 9) * 0.4
			var e := clampf((nz - 0.42) * 3.2, 0.0, 1.0)
			_bb_put(swirl, (y * sw + x) * 4, 1.0, e * e)
	for entry in [["rim_glow", glow, w, h], ["rim_core", core, w, h], ["burn", burn, w, h], ["char", charred, w, h],
			["swirl", swirl, sw, sh]]:
		var img := Image.create_from_data(entry[2], entry[3], false, Image.FORMAT_RGBA8, entry[1])
		_bb_tex[entry[0]] = ImageTexture.create_from_image(img)


static func _bb_put(data: PackedByteArray, i: int, lum: float, a: float) -> void:
	var l := int(clampf(lum, 0.0, 1.0) * 255.0)
	data[i] = l
	data[i + 1] = l
	data[i + 2] = l
	data[i + 3] = int(clampf(a, 0.0, 1.0) * 255.0)


## Smooth noise round a circle: u in [0, 1) -> 0..1, with `cells` bumps round it; sd: a seed.
static func _bb_noise(u: float, cells: int, sd: int) -> float:
	var x := fposmod(u, 1.0) * float(cells)
	var i := int(x)
	var f := x - float(i)
	f = f * f * (3.0 - 2.0 * f)
	return lerpf(_hash(sd * 977 + i % cells), _hash(sd * 977 + (i + 1) % cells), f)


## The same in two directions, wrapping round in u (cu cells) but not in v (cv cells).
static func _bb_noise2(u: float, v: float, cu: int, cv: int, sd: int) -> float:
	var x := fposmod(u, 1.0) * float(cu)
	var y := v * float(cv)
	var ix := int(x)
	var iy := int(y)
	var fx := x - float(ix)
	var fy := y - float(iy)
	fx = fx * fx * (3.0 - 2.0 * fx)
	fy = fy * fy * (3.0 - 2.0 * fy)
	var x1 := (ix + 1) % cu
	var base := sd * 7919
	var a := lerpf(_hash(base + ix * 131 + iy * 1031), _hash(base + x1 * 131 + iy * 1031), fx)
	var b := lerpf(_hash(base + ix * 131 + (iy + 1) * 1031), _hash(base + x1 * 131 + (iy + 1) * 1031), fx)
	return lerpf(a, b, fy)


static func _hash(i: int) -> float:
	var x := sin(float(i) * 12.9898 + 78.233) * 43758.5453
	return x - floorf(x)


## The little things flying about (the fighters' touches), on their layers.
func _draw_bb_bit(ci: CanvasItem, p: Dictionary, c: Vector2, metre: float, layer: int) -> void:
	if layer != 1 and layer != 2:
		return
	var t: float = p["t"]
	var time: float = p["time"]
	if t <= 0.0 or t >= time:
		return
	var k := t / time
	var col: Color = p["color"]
	match String(p["kind"]):
		"star":
			var q := _to_screen(p["pos"])
			var rad: float = float(p["size"]) * metre * (1.0 - 0.5 * k)
			if layer == 1:
				_star(ci, q, rad, float(p["spin"]) * t, col, 1.0 - k * k)
			else:
				_dot(ci, q, rad * 0.35, col, 1.0 - k)
		"twinkle":
			if layer == 2:
				_twinkle(ci, _to_screen(p["pos"]), float(p["size"]) * metre * sin(k * PI), col, sin(k * PI))
		"ember":
			var q := _to_screen(p["pos"])
			var a := 1.0 - k
			if layer == 1:
				var v: Vector3 = p["vel"]
				ci.draw_line(q - Vector2(v.x, -v.y) * 0.035 * metre, q, Color(col, 0.85 * a), maxf(1.5, float(p["size"]) * metre * 0.6), true)
			else:
				_dot(ci, q, float(p["size"]) * metre, Color(1.0, 0.85, 0.5), a)
		"tracer":
			if layer == 2:
				var q := _to_screen(p["pos"])
				var d := Vector2.from_angle(float(p["ang"]))
				var from: float = float(p.get("from", 0.0)) * metre
				var length: float = float(p["len"]) * metre * minf(1.0, k * 3.0)
				var tail := q + d * (from + length * maxf(0.0, k * 1.5 - 0.5))
				var a := 1.0 - k
				ci.draw_line(tail, q + d * (from + length), Color(col, 0.9 * a), maxf(1.5, 0.018 * metre), true)
				ci.draw_line(tail, q + d * (from + length), Color(1, 1, 1, 0.8 * a), maxf(1.0, 0.007 * metre), true)
		"shard":
			var q := _to_screen(p["pos"])
			var length: float = float(p["size"]) * metre * (1.0 - 0.4 * k)
			if layer == 1:
				_shard(ci, q, length, float(p["rot"]) + float(p["spin"]) * t, col, 1.0 - k * k)
			else:
				_dot(ci, q, length * 0.16, col, 0.7 * (1.0 - k))


func _dot(ci: CanvasItem, q: Vector2, r: float, col: Color, a: float) -> void:
	if r < 0.5 or a <= 0.0:
		return
	ci.draw_texture_rect(_glow, Rect2(q - Vector2(r, r) * 2.0, Vector2(r, r) * 4.0), false, Color(col, 0.7 * a))
	ci.draw_texture_rect(_glow, Rect2(q - Vector2(r, r) * 0.7, Vector2(r, r) * 1.4), false, Color(1, 1, 1, a))


## Flan: a four-point glint (light).
func _twinkle(ci: CanvasItem, q: Vector2, r: float, col: Color, a: float) -> void:
	if r < 1.5 or a <= 0.0:
		return
	var w := r * 0.14
	var tip := Color(col, 0.0)
	var mid := Color(1, 1, 1, a)
	ci.draw_polygon(PackedVector2Array([q + Vector2(0, -r), q + Vector2(w, -w), q + Vector2(r, 0), q + Vector2(w, w),
			q + Vector2(0, r), q + Vector2(-w, w), q + Vector2(-r, 0), q + Vector2(-w, -w)]),
		PackedColorArray([tip, mid, tip, mid, tip, mid, tip, mid]))
	_dot(ci, q, r * 0.25, col, a)


## Flan: a five-point star (paint), pale in the middle.
func _star(ci: CanvasItem, q: Vector2, r: float, spin: float, col: Color, a: float) -> void:
	if r < 1.5 or a <= 0.0:
		return
	var pts := PackedVector2Array()
	var cols := PackedColorArray()
	for j in 10:
		var ang := spin - PI * 0.5 + PI * float(j) / 5.0
		pts.append(q + Vector2.from_angle(ang) * (r if j % 2 == 0 else r * 0.45))
		cols.append(Color(col, a) if j % 2 == 0 else Color(col.lerp(Color.WHITE, 0.55), a))
	ci.draw_polygon(pts, cols)


## Noah: a long crystal shard (paint).
func _shard(ci: CanvasItem, q: Vector2, length: float, rot: float, col: Color, a: float) -> void:
	if length < 2.0 or a <= 0.0:
		return
	var d := Vector2.from_angle(rot)
	var n := Vector2(-d.y, d.x)
	var w := length * 0.22
	ci.draw_polygon(PackedVector2Array([q + d * length * 0.6, q + n * w, q - d * length * 0.4, q - n * w]),
		PackedColorArray([Color(0.95, 0.85, 1.0, a), Color(col, 0.9 * a), Color(col.darkened(0.45), 0.8 * a), Color(col, 0.9 * a)]))


func _process(delta: float) -> void:
	if not _bb.is_empty():
		_bb_tick(delta)
		_redraw_bb()
	if _warm > 0:
		_warm_tick()
		return
	var pausing := false
	if _game:
		var info = _game.call("NetsuPauseInfo")
		pausing = info is Array and info.size() > 0 and int(info[0]) > 0
	if pausing:
		var dark := pause_super_dim if _pause_kind == 1 else pause_ex_dim
		_dim_hold = maxf(_dim_hold - delta, 0.05)
		_dim_level = move_toward(_dim_level, dark, delta * dark / maxf(dim_in, 0.001))
	elif _dim_hold > 0.0:
		_dim_hold -= delta
		var rate := _dim_target / maxf(dim_in, 0.001)
		if _dim_level > _dim_target:   # coming out of the pause: ease back to the flash's darkness
			rate = maxf(pause_ex_dim, pause_super_dim) / maxf(pause_out, 0.001)
		_dim_level = move_toward(_dim_level, _dim_target, delta * rate)
	else:
		# back to no darkness, or to the Overdrive tint while one runs
		var rest := 0.0   # Oct 28: no stage tint for Overdrive any more (it's a low-health state now)
		if _dim_level > rest:
			_dim_level = move_toward(_dim_level, rest, delta * maxf(_dim_target, 0.05) / maxf(dim_out, 0.001))
		elif _dim_level < rest:
			_dim_level = move_toward(_dim_level, rest, delta * rest / maxf(dim_out, 0.001))
	if _rc_hold > 0.0:
		_rc_hold -= delta
		_rc_level = move_toward(_rc_level, rc_tint, delta * 6.0)
	else:
		_rc_level = move_toward(_rc_level, 0.0, delta * 2.0)
	if _dim:
		if _rc_level > 0.001 and _dim_level < 0.05:
			_dim.color = Color(rc_color.r * 0.55, 0.0, 0.0, _rc_level)
		else:
			_dim.color = Color(dim_color, _dim_level)
	if _bursts.is_empty() and _sparks.is_empty():
		return
	for b in _bursts:
		b["t"] += delta
	_bursts = _bursts.filter(func(b): return b["t"] < b["time"])
	for p in _sparks:
		p["t"] += delta
		if p["t"] > 0.0:
			p["pos"] += p["vel"] * delta
			p["vel"] *= 0.97
	_sparks = _sparks.filter(func(p): return p["t"] < p["time"])
	queue_redraw()


## A point of the fight (metres) on this layer: through the fighters' camera, then from its
## viewport's pixels onto the container's rect.
func _to_screen(world: Vector3) -> Vector2:
	if _camera == null or _viewport == null or _container == null:
		return size * 0.5
	var p := _camera.unproject_position(world)
	var vs := Vector2(_viewport.size)
	if vs.x <= 0.0 or vs.y <= 0.0:
		return size * 0.5
	var r := _container.get_rect()
	return r.position + p / vs * r.size


func _draw() -> void:
	for b in _bb:
		_draw_bb(self, b, 0)   # (the rest of it: BurstPaint and BurstLight over this, BurstUnder under the fighters)
	for b in _bursts:
		_draw_burst(b)
	for p in _sparks:
		_draw_spark(p)


## A spark: a small glow with a white core that grows in, then shrinks away.
func _draw_spark(p: Dictionary) -> void:
	var t: float = p["t"]
	if t <= 0.0:
		return
	var k := clampf(t / float(p["time"]), 0.0, 1.0)
	var c := _to_screen(p["pos"])
	var metre := (_to_screen(p["pos"] + Vector3(0, 1, 0)) - c).length()
	var r: float = p["size"] * metre * (0.5 + 0.5 * sin(minf(1.0, k * 4.0) * PI * 0.5)) * (1.0 - k * 0.6)
	var a := 1.0 - k
	draw_texture_rect(_glow, Rect2(c - Vector2(r, r) * 2.0, Vector2(r, r) * 4.0), false, Color(p["color"], 0.8 * a))
	draw_texture_rect(_glow, Rect2(c - Vector2(r, r) * 0.6, Vector2(r, r) * 1.2), false, Color(1, 1, 1, a))


func _draw_burst(b: Dictionary) -> void:
	var t: float = b["t"]
	var k := clampf(t / float(b["time"]), 0.0, 1.0)
	var a := 1.0 - k
	var pos: Vector3 = b["pos"]
	var c := _to_screen(pos)
	var metre := (_to_screen(pos + Vector3(0, 1, 0)) - c).length()
	if metre <= 0.0:
		return
	var s: float = b["size"] * metre
	var col: Color = b["color"]
	var rays: Color = b.get("ray", ray_color)
	# rays: grow out over the first 0.1 s and spin
	var length := ray_length * s * minf(1.0, t / 0.1)
	var half := ray_width * s
	var spin := t * ray_spin
	for i in ray_count:
		var ang := spin + TAU * float(i) / float(ray_count)
		var d := Vector2(cos(ang), sin(ang))
		var n := Vector2(-d.y, d.x)
		draw_polygon(PackedVector2Array([c + n * half, c + d * length, c - n * half]),
			PackedColorArray([Color(rays, 0.5 * a), Color(rays, 0.0), Color(rays, 0.5 * a)]))
	# glow: the side's colour, with a white core; swells in over ~5 frames
	var r := glow_radius * s * (0.6 + 0.4 * sin(minf(1.0, t / 0.083) * PI * 0.5))
	draw_texture_rect(_glow, Rect2(c - Vector2(r, r), Vector2(r, r) * 2.0), false, Color(col, 0.85 * a))
	draw_texture_rect(_glow, Rect2(c - Vector2(r, r) * 0.45, Vector2(r, r) * 0.9), false, Color(1, 1, 1, 0.9 * a))
	# a line of light straight through her (EX moves and supers)
	if b.get("big", false) and t < streak_time:
		var ks := t / streak_time
		var half_len := streak_length * 0.5 * (0.35 + 0.65 * minf(1.0, t / 0.05))
		var th := maxf(2.0, 0.05 * s * (1.0 - ks))
		var sa := 0.9 * (1.0 - ks)
		draw_polygon(PackedVector2Array([c - Vector2(half_len, 0), c - Vector2(0, th * 2.0), c + Vector2(half_len, 0), c + Vector2(0, th * 2.0)]),
			PackedColorArray([Color(col, 0.0), Color(col, sa), Color(col, 0.0), Color(col, sa)]))
		draw_polygon(PackedVector2Array([c - Vector2(half_len * 0.7, 0), c - Vector2(0, th * 0.6), c + Vector2(half_len * 0.7, 0), c + Vector2(0, th * 0.6)]),
			PackedColorArray([Color(1, 1, 1, 0.0), Color(1, 1, 1, sa), Color(1, 1, 1, 0.0), Color(1, 1, 1, sa)]))
	# ring opening out
	if b["ring"]:
		var rr := (ring_from + k * (ring_to - ring_from)) * s
		draw_arc(c, rr, 0.0, TAU, 72, Color(1, 1, 1, a), ring_width, true)
