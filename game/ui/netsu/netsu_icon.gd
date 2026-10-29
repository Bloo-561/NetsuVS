class_name NetsuIcon
extends Control
## Small white line icons for the pause menu (drawn, no image files):
## close, commands, sound, pad, keyboard, restart, chars, menu, training.
## The icon fills a square of `box` px centred in the control.

var kind := "close"
var box := 32.0
var color := Color(0.92, 0.94, 1.0)


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE


func _draw() -> void:
	var c := size / 2.0
	var s := box / 2.0
	var w := maxf(2.0, box * 0.08)
	match kind:
		"close":   # door with an arrow out
			draw_rect(Rect2(c + Vector2(-s * 0.7, -s * 0.9), Vector2(s * 1.0, s * 1.8)), color, false, w)
			draw_rect(Rect2(c + Vector2(-s * 0.2, -s * 0.9), Vector2(s * 0.5, s * 1.8)), color, false, w)
			draw_circle(c + Vector2(s * 0.12, 0), w * 0.8, color)
			draw_line(c + Vector2(s * 0.45, 0), c + Vector2(s * 0.95, 0), color, w)
			draw_line(c + Vector2(s * 0.95, 0), c + Vector2(s * 0.7, -s * 0.25), color, w)
			draw_line(c + Vector2(s * 0.95, 0), c + Vector2(s * 0.7, s * 0.25), color, w)
		"commands":   # clipboard with lines
			draw_rect(Rect2(c + Vector2(-s * 0.7, -s * 0.8), Vector2(s * 1.4, s * 1.75)), color, false, w)
			draw_rect(Rect2(c + Vector2(-s * 0.3, -s * 0.98), Vector2(s * 0.6, s * 0.3)), color)
			for i in 4:
				var y := -s * 0.35 + i * s * 0.32
				draw_rect(Rect2(c + Vector2(-s * 0.45, y - w * 0.4), Vector2(w, w)), color)
				draw_line(c + Vector2(-s * 0.2, y), c + Vector2(s * 0.45, y), color, w * 0.8)
		"sound":   # speaker + waves
			draw_colored_polygon(PackedVector2Array([c + Vector2(-s * 0.9, -s * 0.3), c + Vector2(-s * 0.45, -s * 0.3),
				c + Vector2(s * 0.05, -s * 0.8), c + Vector2(s * 0.05, s * 0.8), c + Vector2(-s * 0.45, s * 0.3),
				c + Vector2(-s * 0.9, s * 0.3)]), color)
			draw_arc(c + Vector2(s * 0.1, 0), s * 0.45, -0.9, 0.9, 12, color, w)
			draw_arc(c + Vector2(s * 0.1, 0), s * 0.8, -0.9, 0.9, 16, color, w)
		"pad":   # controller
			var body := Color(color)
			draw_circle(c + Vector2(-s * 0.55, s * 0.15), s * 0.42, body)
			draw_circle(c + Vector2(s * 0.55, s * 0.15), s * 0.42, body)
			draw_rect(Rect2(c + Vector2(-s * 0.6, -s * 0.45), Vector2(s * 1.2, s * 0.75)), body)
			var ink := Color(0.04, 0.06, 0.2)
			draw_rect(Rect2(c + Vector2(-s * 0.72, -s * 0.12), Vector2(s * 0.42, s * 0.12)), ink)
			draw_rect(Rect2(c + Vector2(-s * 0.57, -s * 0.27), Vector2(s * 0.12, s * 0.42)), ink)
			for p: Vector2 in [Vector2(0.55, -0.22), Vector2(0.4, -0.06), Vector2(0.7, -0.06), Vector2(0.55, 0.1)]:
				draw_circle(c + p * s, s * 0.07, ink)
		"keyboard":
			draw_rect(Rect2(c + Vector2(-s, -s * 0.6), Vector2(s * 2.0, s * 1.2)), color, false, w)
			for row in 3:
				for k in 7 - (1 if row == 2 else 0):
					draw_rect(Rect2(c + Vector2(-s * 0.82 + k * s * 0.25 + row * s * 0.06, -s * 0.42 + row * s * 0.3),
						Vector2(s * 0.16, s * 0.16)), color)
		"restart":   # circular arrow
			draw_arc(c, s * 0.75, 0.6, TAU - 0.3, 28, color, w * 1.2)
			var tip := c + Vector2(cos(0.6), sin(0.6)) * s * 0.75
			draw_colored_polygon(PackedVector2Array([tip + Vector2(-s * 0.35, -s * 0.05), tip + Vector2(s * 0.12, -s * 0.15),
				tip + Vector2(-s * 0.05, s * 0.32)]), color)
		"chars":   # three people
			for p: Vector2 in [Vector2(-0.6, 0.1), Vector2(0.6, 0.1), Vector2(0.0, -0.05)]:
				var big := p.x == 0.0
				var r := s * (0.3 if big else 0.24)
				var head := c + Vector2(p.x * s, p.y * s - s * 0.35)
				draw_circle(head, r, color)
				var shoulders := PackedVector2Array()
				for i in 13:
					var a := PI + PI * i / 12.0
					shoulders.append(head + Vector2(0, r * 2.6) + Vector2(cos(a), sin(a) * 0.9) * r * 1.6)
				draw_colored_polygon(shoulders, color)
		"training":   # a target: rings and a cross
			draw_arc(c, s * 0.85, 0.0, TAU, 32, color, w)
			draw_arc(c, s * 0.48, 0.0, TAU, 24, color, w)
			draw_circle(c, s * 0.16, color)
			for d: Vector2 in [Vector2.UP, Vector2.DOWN, Vector2.LEFT, Vector2.RIGHT]:
				draw_line(c + d * s * 0.62, c + d * s * 1.05, color, w)
		"menu":   # house
			draw_colored_polygon(PackedVector2Array([c + Vector2(0, -s * 0.95), c + Vector2(s * 0.95, -s * 0.05),
				c + Vector2(s * 0.7, -s * 0.05), c + Vector2(s * 0.7, s * 0.85), c + Vector2(s * 0.18, s * 0.85),
				c + Vector2(s * 0.18, s * 0.3), c + Vector2(-s * 0.18, s * 0.3), c + Vector2(-s * 0.18, s * 0.85),
				c + Vector2(-s * 0.7, s * 0.85), c + Vector2(-s * 0.7, -s * 0.05), c + Vector2(-s * 0.95, -s * 0.05)]), color)
