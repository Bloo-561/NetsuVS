extends Control
## SIDE SELECT  (Versus -> Game Settings -> Start Game; Oct 19 2026 mockup)
##
## Two controllers and two keyboards sit in the middle column. Each player
## moves THEIR OWN device left (Player 1 side) or right (Player 2 side) with
## their left / right, then presses A to start. A side with nobody on it is
## the CPU. B moves your device back to the middle; B in the middle goes back.
##
## Runs inside the main menu (scenes/main_menu/main_menu.gd), like Options.
## The result goes to Controls.assign_sides(): from then on whichever device
## is on the Player 1 side drives player 1's buttons ("p1_a" ...).

signal confirmed(p1_device: String, p2_device: String)
signal cancelled

## The main menu's footer ({"root", "text", "prompts"}), set before adding.
var footer_override: Dictionary = {}

## Layout in mockup pixels (1672 x 941), converted with NetsuUI.m().
@export var column_x: Vector2 = Vector2(406, 1266)   ## centre of the Player 1 / Player 2 side
@export var side_y: float = 475.0                    ## where a device sits once it's on a side
@export var middle_x: float = 836.0
@export var first_row_y: float = 292.0
@export var row_step: float = 127.0
@export var card_size: Vector2 = Vector2(272, 110)

const MOVE_REPEAT := 0.18   # seconds between moves while a stick is held

var _side := {}        # device -> -1 (Player 1), 0 (middle), 1 (Player 2)
var _cards := {}       # device -> DeviceCard
var _arrows := {}      # device -> [left Label, right Label]
var _cooldown := {}    # device -> seconds until it may move again
var _cpu_labels: Array[Node2D] = []   # the CPU circles
var _footer: Dictionary
var _done := false


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	size = Vector2(1920, 1080)
	_footer = footer_override
	_build()
	for d in Controls.DEVICES:
		_side[d] = 0
		_cooldown[d] = 0.0
	_refresh(false)
	if not _footer.is_empty():
		_footer["text"].text = "Move your controller or keyboard to a side. An empty side is the CPU."
		_footer["prompts"].text = "LEFT / RIGHT  MOVE     A  START     B  BACK"
	# entrance: the hall fades up, then everything slides in from top to bottom
	var back: CanvasItem = get_child(0)
	back.modulate.a = 0.0
	create_tween().tween_property(back, "modulate:a", 1.0, 0.22)
	NetsuUI.cascade(self, 1, 0.08)


func _process(delta: float) -> void:
	for d in _cooldown:
		_cooldown[d] = maxf(_cooldown[d] - delta, 0.0)


func _unhandled_input(event: InputEvent) -> void:
	if _done or SceneRouter.is_busy():
		return
	var device := Controls.device_from_event(event)
	if device == "" or not _side.has(device):
		return
	if Controls.device_pressed(event, device, "left"):
		_move(device, -1)
	elif Controls.device_pressed(event, device, "right"):
		_move(device, 1)
	elif Controls.device_pressed(event, device, "confirm"):
		_confirm(device)
	elif Controls.device_pressed(event, device, "back"):
		_back(device)
	else:
		return
	get_viewport().set_input_as_handled()


func _move(device: String, dir: int) -> void:
	if _cooldown[device] > 0.0:
		return
	_cooldown[device] = MOVE_REPEAT
	var target := clampi(_side[device] + dir, -1, 1)
	if target == _side[device]:
		return
	if target != 0 and _who(target) != "":
		_shake(device)   # someone is already on that side
		return
	_side[device] = target
	_audio("PlayMenuClip", 0)
	_refresh(true)


func _confirm(device: String) -> void:
	if _side[device] == 0:
		_footer["text"].text = "Move left or right to pick a side first."
		_shake(device)
		return
	_done = true
	_audio("PlayMenuClip", 3)
	var card: Control = _cards[device]
	var pop := create_tween()
	pop.tween_property(card, "scale", Vector2(1.08, 1.08), 0.07)
	pop.tween_property(card, "scale", Vector2.ONE, 0.1)
	await pop.finished
	confirmed.emit(_who(-1), _who(1))


func _back(device: String) -> void:
	_audio("PlayMenuClip", 2)
	if _side[device] != 0:
		_side[device] = 0
		_refresh(true)
		return
	close()


## Fades out, then emits `cancelled` and frees itself.
func close() -> void:
	if _done:
		return
	_done = true
	var t := create_tween().set_parallel(true).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_IN)
	t.tween_property(self, "modulate:a", 0.0, 0.18)
	t.tween_property(self, "position:y", 16.0, 0.18)
	t.chain().tween_callback(_finish_close)


func _finish_close() -> void:
	cancelled.emit()
	queue_free()


## The device on a side (-1 = Player 1, 1 = Player 2), or "" for none.
func _who(side: int) -> String:
	for d in _side:
		if _side[d] == side:
			return d
	return ""


# --- Drawing ----------------------------------------------------------------------------

const P_COLORS := [Color(0.35, 0.72, 1.0), Color(1.0, 0.3, 0.4)]   # Player 1 blue, Player 2 crimson


func _build() -> void:
	var k := NetsuUI.K
	NetsuUI.settings_backdrop(self, 0.45)
	NetsuUI.header(self, "VERSUS")
	NetsuUI.page_title(self, "SIDE SELECT", 136.0, 50)
	for s in [0, 1]:
		var cx: float = column_x[s] * k
		var col: Color = P_COLORS[s]
		var head := NetsuUI.label("PLAYER %d SIDE" % (s + 1), 32, col, NetsuUI.sans(9))
		NetsuUI.glow(head, Color(col.darkened(0.5), 0.5), 6)
		head.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		head.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		head.position = Vector2(cx - 300, 222 * k - 30)
		head.size = Vector2(600, 60)
		add_child(head)
		add_child(NetsuUI.hairline(Vector2(cx - 240 * k, 248 * k), 480 * k, Color(col, 0.75), 1.5, "both"))
		var d := NetsuUI.diamond(6.0, col, Color(0.03, 0.05, 0.15))
		d.position = Vector2(cx, 248 * k)
		add_child(d)
		var ring := Node2D.new()
		ring.position = Vector2(cx, side_y * k)
		var r := 140.0 * k
		for a in 4:
			var arc := Line2D.new()
			var start := a * PI / 2.0 + 0.2
			var pts := PackedVector2Array()
			for i in 17:
				var t := start + (PI / 2.0 - 0.4) * i / 16.0
				pts.append(Vector2(cos(t), sin(t)) * r)
			arc.points = pts
			arc.width = 1.5
			arc.default_color = Color(0.75, 0.82, 1.0, 0.55)
			ring.add_child(arc)
			var gem := NetsuUI.diamond(11.0, Color(0.85, 0.9, 1.0, 0.8), Color(0.03, 0.05, 0.15, 0.8))
			gem.position = Vector2(cos(a * PI / 2.0), sin(a * PI / 2.0)) * r
			ring.add_child(gem)
		var cpu := NetsuUI.label("CPU", 96, Color(0.55, 0.6, 0.75, 0.55), NetsuUI.sans(4, true))
		cpu.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		cpu.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		cpu.position = Vector2(-200, -70)
		cpu.size = Vector2(400, 140)
		ring.add_child(cpu)
		add_child(ring)
		_cpu_labels.append(ring)
	for x in [646.0, 1026.0]:
		var line := NetsuUI.gradient_rect(Color(0.65, 0.8, 1.0, 0.75), Color(0.65, 0.8, 1.0, 0.2), true)
		line.position = Vector2(x * k, 205 * k)
		line.size = Vector2(1.5, 565 * k)
		add_child(line)
	for i in Controls.DEVICES.size():
		var device: String = Controls.DEVICES[i]
		var card := DeviceCard.new()
		card.device = device
		card.size = card_size * k
		card.pivot_offset = card.size / 2.0
		card.position = Vector2(middle_x * k - card.size.x / 2.0, (first_row_y + i * row_step) * k - card.size.y / 2.0)
		card.set_meta("home_y", card.position.y)
		add_child(card)
		_cards[device] = card
		var pair: Array = []
		for dir in [-1, 1]:
			var a := NetsuUI.arrow(Vector2.ZERO, 30, dir, Color(0.9, 0.93, 1.0), 3.0)
			add_child(a)
			pair.append(a)
		_arrows[device] = pair


func _refresh(animate: bool) -> void:
	var k := NetsuUI.K
	for device in _cards:
		var card: DeviceCard = _cards[device]
		var s: int = _side[device]
		card.side = s
		card.connected = Controls.device_connected(device)
		card.queue_redraw()
		var cx: float = (middle_x if s == 0 else column_x[0 if s < 0 else 1]) * k
		var cy: float = card.get_meta("home_y") + card.size.y / 2.0 if s == 0 else side_y * k
		var target := Vector2(cx - card.size.x / 2.0, cy - card.size.y / 2.0)
		var grow := Vector2.ONE * (1.15 if s != 0 else 1.0)
		if animate:
			var t := create_tween().set_parallel(true).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
			t.tween_property(card, "position", target, 0.18)
			t.tween_property(card, "scale", grow, 0.18)
		else:
			card.position = target
			card.scale = grow
		var arrows: Array = _arrows[device]
		var half := card.size.x * grow.x / 2.0
		arrows[0].position = Vector2(cx - half - 30 * k, cy)
		arrows[1].position = Vector2(cx + half + 30 * k, cy)
		var can_left := s > -1 and card.connected and (s == 1 or _who(-1) == "")
		var can_right := s < 1 and card.connected and (s == -1 or _who(1) == "")
		arrows[0].modulate.a = 1.0 if can_left else 0.25
		arrows[1].modulate.a = 1.0 if can_right else 0.25
	for i in 2:
		_cpu_labels[i].visible = _who(-1 if i == 0 else 1) == ""


func _shake(device: String) -> void:
	var card: Control = _cards[device]
	var x := card.position.x
	var t := create_tween()
	for dx in [10.0, -10.0, 6.0, 0.0]:
		t.tween_property(card, "position:x", x + dx, 0.04)


func _audio(method: String, index: int) -> void:
	var audio := get_node_or_null("/root/AudioManager")
	if audio and audio.has_method(method):
		audio.call(method, index)


## One device: a controller or keyboard drawing with its name, in a cut-corner box.
class DeviceCard extends Control:
	var device := "pad1"
	var side := 0          # -1 Player 1, 0 middle, 1 Player 2
	var connected := true

	func _ready() -> void:
		mouse_filter = Control.MOUSE_FILTER_IGNORE

	func _draw() -> void:
		var accent := Color(0.4, 0.75, 1.0)
		if side < 0:
			accent = Color(0.35, 0.72, 1.0)
		elif side > 0:
			accent = Color(1.0, 0.3, 0.4)
		var lit := side != 0 or (connected and device == "pad1")
		var alpha := 1.0 if connected else 0.45
		var cut := 16.0
		var w := size.x
		var h := size.y
		var shape := PackedVector2Array([Vector2(cut, 0), Vector2(w - cut, 0), Vector2(w, cut), Vector2(w, h - cut),
			Vector2(w - cut, h), Vector2(cut, h), Vector2(0, h - cut), Vector2(0, cut)])
		draw_colored_polygon(shape, Color(0.03, 0.05, 0.16, 0.85))
		var closed := shape.duplicate()
		closed.append(shape[0])
		if lit:
			draw_polyline(closed, Color(accent, 0.3 * alpha), 9.0, true)
			draw_polyline(closed, Color(accent.lightened(0.3), alpha), 2.5, true)
			for p in [Vector2(6, 6), Vector2(w - 6, 6), Vector2(6, h - 6), Vector2(w - 6, h - 6)]:
				draw_colored_polygon(PackedVector2Array([p + Vector2(0, -4), p + Vector2(4, 0), p + Vector2(0, 4), p + Vector2(-4, 0)]),
					Color(accent.lightened(0.4), alpha))
		else:
			draw_polyline(closed, Color(0.85, 0.88, 1.0, 0.7 * alpha), 1.5, true)
		var ink := Color(0.93, 0.95, 1.0, alpha)
		var c := Vector2(w / 2.0, h * 0.4)
		if device.begins_with("pad"):
			_draw_pad(c, ink)
		else:
			_draw_keyboard(c, ink)
		var font: Font = NetsuUI.sans(1)
		var text := Controls.device_label(device).to_upper()
		var fs := 20
		var tw := font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x
		draw_string(font, Vector2((w - tw) / 2.0, h * 0.86 - (8 if not connected else 0)), text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, ink)
		if not connected:
			var note := "Not connected"
			var nf: Font = NetsuUI.body()
			var nw := nf.get_string_size(note, HORIZONTAL_ALIGNMENT_LEFT, -1, 15).x
			draw_string(nf, Vector2((w - nw) / 2.0, h * 0.97), note, HORIZONTAL_ALIGNMENT_LEFT, -1, 15, Color(0.75, 0.8, 0.95, 0.8))

	func _draw_pad(c: Vector2, ink: Color) -> void:
		var outline_pts := PackedVector2Array()
		# rounded controller silhouette as an outline
		for i in 41:
			var t := TAU * i / 40.0
			var x := cos(t) * 62.0
			var y := sin(t) * 26.0
			if sin(t) > 0.0:
				y += 10.0 * absf(cos(t))   # grips hang lower
			outline_pts.append(c + Vector2(x, y))
		draw_polyline(outline_pts, ink, 2.5, true)
		draw_arc(c + Vector2(-34, 0), 15, 0, TAU, 20, ink, 2.0)
		draw_arc(c + Vector2(34, 0), 15, 0, TAU, 20, ink, 2.0)
		draw_rect(Rect2(c + Vector2(-42, -2.5), Vector2(16, 5)), ink)
		draw_rect(Rect2(c + Vector2(-36.5, -8), Vector2(5, 16)), ink)
		for p in [Vector2(34, -7), Vector2(27, 0), Vector2(41, 0), Vector2(34, 7)]:
			draw_circle(c + p, 2.6, ink)

	func _draw_keyboard(c: Vector2, ink: Color) -> void:
		var r := Rect2(c + Vector2(-66, -24), Vector2(132, 48))
		var poly := PackedVector2Array([r.position + Vector2(6, 0), Vector2(r.end.x - 6, r.position.y), Vector2(r.end.x, r.end.y),
			Vector2(r.position.x, r.end.y), r.position + Vector2(6, 0)])
		draw_polyline(poly, ink, 2.5, true)
		for row in 3:
			var count := 10 - row
			var start := r.position.x + 12 + row * 5
			for kk in count:
				draw_rect(Rect2(Vector2(start + kk * 11, r.position.y + 7 + row * 10), Vector2(7, 6)), ink)
		draw_rect(Rect2(Vector2(r.position.x + 34, r.position.y + 38), Vector2(64, 4)), ink)
