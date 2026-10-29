class_name NetsuLights
extends Node2D
## Diagonal light beams (blue on the left, crimson on the right) and, optionally,
## slowly drifting glowing petals. Drawn additively over the background.
##
## Each beam is [x_at_top, width, alpha, color] in MOCKUP pixels (1672 x 941);
## beams lean like "/" (they move `slope` px left for every px down).

@export var slope: float = 0.51
@export var beams: Array = []
@export var petals: int = 0
## How much the beams breathe (0 = still).
@export var shimmer: float = 0.12

var _time := 0.0
var _petals: Array = []


static func preset(name: String) -> Array:
	var b := Color(0.18, 0.5, 1.0)
	var c := Color(0.45, 0.8, 1.0)
	var r := Color(1.0, 0.16, 0.28)
	var p := Color(1.0, 0.45, 0.55)
	match name:
		"menu":
			return [[60.0, 70.0, 0.2, b], [150.0, 4.0, 0.6, c], [250.0, 150.0, 0.13, b], [330.0, 3.0, 0.4, c],
				[1000.0, 3.0, 0.18, c],
				[1590.0, 70.0, 0.14, r], [1705.0, 3.0, 0.5, p], [1810.0, 120.0, 0.12, r], [1960.0, 4.0, 0.35, p]]
		"select":
			return [[150.0, 70.0, 0.14, b], [250.0, 3.0, 0.45, c], [560.0, 170.0, 0.12, b], [640.0, 3.0, 0.4, c],
				[1100.0, 3.0, 0.3, Color(0.75, 0.5, 1.0)], [1180.0, 150.0, 0.1, r], [1660.0, 3.0, 0.55, p],
				[1880.0, 110.0, 0.14, r]]
		"title":
			return [[180.0, 60.0, 0.1, b], [260.0, 3.0, 0.35, c], [1700.0, 3.0, 0.35, p], [1790.0, 80.0, 0.1, r]]
	return []


func _ready() -> void:
	var mat := CanvasItemMaterial.new()
	mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	material = mat
	var rng := RandomNumberGenerator.new()
	rng.seed = 11
	for i in petals:
		var left := i % 2 == 0
		_petals.append({
			"pos": Vector2(rng.randf_range(0, 760) if left else rng.randf_range(1160, 1920), rng.randf_range(0, 1080)),
			"vel": Vector2(rng.randf_range(4, 14), rng.randf_range(10, 26)),
			"size": rng.randf_range(5.0, 12.0),
			"rot": rng.randf() * TAU,
			"spin": rng.randf_range(-0.6, 0.6),
			"phase": rng.randf() * TAU,
			"color": Color(0.35, 0.65, 1.0) if left else Color(1.0, 0.3, 0.38),
		})


func _process(delta: float) -> void:
	_time += delta
	for pt in _petals:
		pt["pos"] += pt["vel"] * delta
		pt["rot"] += pt["spin"] * delta
		if pt["pos"].y > 1100:
			pt["pos"].y = -20
		if pt["pos"].x > 1940:
			pt["pos"].x = -20
	queue_redraw()


func _draw() -> void:
	var k := NetsuUI.K
	for i in beams.size():
		var beam: Array = beams[i]
		var x0: float = beam[0] * k
		var w: float = beam[1] * k
		var a: float = beam[2] * (1.0 + shimmer * sin(_time * 0.7 + i * 1.7))
		var col: Color = beam[3]
		var dx := slope * 1080.0
		var soft := minf(w * 0.5, 40.0)
		# soft edge | core | soft edge, top to bottom
		var xs := [x0 - soft, x0, x0 + w, x0 + w + soft]
		var alphas := [0.0, a, a, 0.0]
		for s in 3:
			var pts := PackedVector2Array([Vector2(xs[s], 0), Vector2(xs[s + 1], 0),
				Vector2(xs[s + 1] - dx, 1080), Vector2(xs[s] - dx, 1080)])
			var cols := PackedColorArray([Color(col, alphas[s]), Color(col, alphas[s + 1]),
				Color(col, alphas[s + 1]), Color(col, alphas[s])])
			draw_polygon(pts, cols)
	for pt in _petals:
		var a: float = 0.25 + 0.2 * sin(_time * 1.3 + pt["phase"])
		var pts := PackedVector2Array()
		for j in 10:
			var t := TAU * j / 10.0
			var v := Vector2(cos(t) * pt["size"], sin(t) * pt["size"] * 0.42).rotated(pt["rot"])
			pts.append(pt["pos"] + v)
		draw_colored_polygon(pts, Color(pt["color"], a))
