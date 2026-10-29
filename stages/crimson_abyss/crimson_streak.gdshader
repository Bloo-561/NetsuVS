// Crimson Abyss - white light streaks shooting down through the clouds (like the painting).
// Each quad: UV.x along (1 = head), streak id in UV.y (id = -floor(UV.y) - 1). Visual only.
shader_type spatial;
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled;

uniform sampler2D streak_tex : filter_linear, repeat_disable;
uniform vec3 color : source_color = vec3(1.0, 0.9, 0.97);
uniform float intensity = 0.85;
uniform float period = 5.5;
uniform float travel_time = 0.9;

float hash(float x) { return fract(sin(x * 91.3) * 43758.5453); }

void fragment() {
	float id = -floor(UV.y) - 1.0;
	float across = fract(UV.y);
	float per = period + id * 1.37;
	float tt = TIME + hash(id) * per;
	float ph = mod(tt, per);
	float p = clamp(ph / travel_time, 0.0, 1.6);                 // head position along the streak
	float trail = smoothstep(p - 0.55, p, UV.x) * (1.0 - smoothstep(p, p + 0.03, UV.x));
	float fade = 1.0 - smoothstep(1.0, 1.6, p);
	float prof = texture(streak_tex, vec2(0.9, across)).a;
	ALBEDO = color * trail * fade * prof * intensity;
}
