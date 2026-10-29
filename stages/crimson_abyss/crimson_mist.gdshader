// Crimson Abyss - drifting mist bands at the plateau edge and between the mountain ranges.
// UV.x tiles along the band; band id in UV.y (id = -floor(UV.y) - 1). Visual only.
shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled;

uniform sampler2D mist_tex : filter_linear_mipmap, repeat_enable;
uniform vec3 near_color : source_color = vec3(0.78, 0.5, 0.98);
uniform vec3 far_color : source_color = vec3(0.55, 0.28, 0.72);
uniform float near_alpha = 0.55;
uniform float far_alpha = 0.75;
uniform float drift = 0.006;

void fragment() {
	float id = -floor(UV.y) - 1.0;
	float v = fract(UV.y);
	float dir = mod(id, 2.0) < 0.5 ? 1.0 : -1.0;
	float a1 = texture(mist_tex, vec2(UV.x + TIME * drift * dir, v)).a;
	float a2 = texture(mist_tex, vec2(UV.x * 1.7 - TIME * drift * 1.6 * dir + 0.37, v)).a;
	float a = clamp(a1 * 0.65 + a2 * 0.55, 0.0, 1.0);
	float k = clamp(id / 2.0, 0.0, 1.0);
	ALBEDO = mix(near_color, far_color, k) * (0.9 + 0.2 * a2);
	ALPHA = a * mix(near_alpha, far_alpha, k);
}
