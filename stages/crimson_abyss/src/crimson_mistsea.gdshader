// Crimson Abyss - glowing sea of mist below the plateau edge (horizontal plane). Visual only.
// Hides the mountain feet; brighter toward the horizon like the painting's violet ground glow.
shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled;

uniform sampler2D noise_tex : hint_default_white, filter_linear_mipmap, repeat_enable;
uniform vec3 deep_color : source_color = vec3(0.16, 0.08, 0.22);
uniform vec3 glow_color : source_color = vec3(0.62, 0.36, 0.86);
uniform float glow_start = 25.0;
uniform float glow_end = 120.0;
uniform float drift = 0.004;
uniform float opacity = 0.9;

varying vec3 wpos;
void vertex() { wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz; }

void fragment() {
	vec2 p = wpos.xz;
	float n1 = texture(noise_tex, p / 90.0 + vec2(TIME * drift, 0.0)).r;
	float n2 = texture(noise_tex, p / 37.0 + vec2(-TIME * drift * 1.7, TIME * drift * 0.6)).r;
	float n = n1 * 0.6 + n2 * 0.4;
	float d = clamp((-p.y - glow_start) / (glow_end - glow_start), 0.0, 1.0);
	vec3 c = mix(deep_color, glow_color, d * (0.7 + 0.5 * n));
	ALBEDO = c;
	ALPHA = clamp(opacity * (0.75 + 0.35 * n), 0.0, 1.0) * smoothstep(0.0, 6.0, -p.y - 16.0);
}
