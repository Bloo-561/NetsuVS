// Depths of the Old Schoolhouse - the teleport circle on the dais: a ring of runes that slowly turns,
// with a second, counter-turning echo and a soft pulse. UV.x runs around the ring (4 repeats),
// UV.y across it (0 = inner edge). Additive. Visual only.
shader_type spatial;
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled;

uniform sampler2D rune_tex : hint_default_black, filter_linear_mipmap, repeat_enable;
uniform vec3 color : source_color = vec3(0.4, 0.95, 1.0);
uniform float intensity = 1.4;
uniform float turn_speed = 0.02;       // ring units per second
uniform float pulse_speed = 1.2;

void fragment() {
	float a = texture(rune_tex, vec2(UV.x + TIME * turn_speed, UV.y)).r;
	float b = texture(rune_tex, vec2(-UV.x * 0.5 + TIME * turn_speed * 1.7 + 0.37, 1.0 - UV.y)).r;
	float pulse = 0.75 + 0.25 * sin(TIME * pulse_speed);
	float edge = smoothstep(0.0, 0.08, UV.y) * smoothstep(1.0, 0.92, UV.y);
	ALBEDO = color * (a + 0.35 * b + 0.08) * pulse * edge * intensity;
}
