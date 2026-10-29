shader_type canvas_item;
// Character select renders fade toward the bottom of the screen (their legs
// melt into the floor behind the name plates, like the mockup).

uniform float fade_start : hint_range(0.0, 1.0) = 0.62;
uniform float fade_end : hint_range(0.0, 1.0) = 0.98;
uniform float min_alpha : hint_range(0.0, 1.0) = 0.12;

void fragment() {
	COLOR.a *= mix(1.0, min_alpha, smoothstep(fade_start, fade_end, SCREEN_UV.y));
}
