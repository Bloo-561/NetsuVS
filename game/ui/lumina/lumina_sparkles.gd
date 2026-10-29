class_name LuminaSparkles
extends Node2D
## Little four-point stars that fade in and out across the screen.
## Used by LuminaUI.backdrop(). Change count / area / colors freely.

@export var count: int = 26
@export var area: Rect2 = Rect2(0, 0, 1920, 1080)
@export var colors: Array[Color] = [Color(1, 1, 1), Color(0.8, 0.74, 0.96), Color(0.62, 0.55, 0.92)]

var _stars: Array = []
var _time := 0.0


func _ready() -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	for i in count:
		_stars.append({
			"pos": Vector2(rng.randf_range(area.position.x, area.end.x), rng.randf_range(area.position.y, area.end.y)),
			"size": rng.randf_range(4.0, 13.0),
			"speed": rng.randf_range(0.6, 1.6),
			"phase": rng.randf() * TAU,
			"color": colors[rng.randi() % colors.size()],
			"drift": rng.randf_range(-6.0, 6.0),
		})


func _process(delta: float) -> void:
	_time += delta
	queue_redraw()


func _draw() -> void:
	for s in _stars:
		var a: float = pow(maxf(sin(_time * s["speed"] + s["phase"]), 0.0), 3.0)
		if a < 0.02:
			continue
		var p: Vector2 = s["pos"] + Vector2(0, sin(_time * 0.3 + s["phase"]) * s["drift"])
		var c: Color = s["color"]
		draw_colored_polygon(_shift(LuminaUI.sparkle_points(s["size"] * (0.7 + 0.3 * a)), p), Color(c, a))
		draw_circle(p, s["size"] * 0.9, Color(c, a * 0.15))


func _shift(points: PackedVector2Array, by: Vector2) -> PackedVector2Array:
	var out := PackedVector2Array()
	for q in points:
		out.append(q + by)
	return out
