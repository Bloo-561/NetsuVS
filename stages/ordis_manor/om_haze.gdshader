// Ordis Royal Manor (Ruined) - smoke gathering under the ceiling and a low haze at the back of the hall.
// Wide camera-facing quads: UV.x in 20 m units across, UV.y = layer id + height (glTF flips v).
// Thick at the bottom, ragged and wispy at the top, lit warm from the fires below. Alpha blended.
shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled;

uniform vec3 haze_color : source_color = vec3(0.3, 0.28, 0.27);
uniform vec3 lit_color : source_color = vec3(0.42, 0.24, 0.14);
uniform float opacity = 0.38;
uniform float drift = 0.04;           // 20 m units per second (sideways, with the wind)
uniform float layer_fade = 0.12;      // nearer layers are thinner (they cover more of the screen)

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vnoise(vec2 p) {
	vec2 i = floor(p), f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}
float fbm(vec2 p) {
	float s = 0.0, a = 0.5;
	for (int i = 0; i < 5; i++) { s += vnoise(p) * a; p = p * 2.03 + 1.3; a *= 0.5; }
	return s / 0.97;
}

void fragment() {
	float id = -floor(UV.y);
	float h = 1.0 - fract(UV.y);
	float t = TIME * drift * (1.0 + id * 0.25);
	vec2 q = vec2(UV.x * 1.6 + t + id * 3.1, h * 2.2 - TIME * 0.02);
	float n = fbm(q + vec2(fbm(q * 0.8 - t * 0.5), 0.0) * 0.9);
	float top = 0.45 + 0.5 * fbm(vec2(UV.x * 0.8 + t * 0.6, id));          // ragged upper edge
	float a = smoothstep(0.25, 0.6, n) * (1.0 - smoothstep(top - 0.3, top, h)) * smoothstep(0.0, 0.08, h);
	a *= 1.0 - layer_fade * (4.0 - id);
	ALBEDO = mix(lit_color, haze_color, smoothstep(0.0, 0.5, h)) * (0.6 + 0.7 * n);
	ALPHA = clamp(a * opacity, 0.0, 1.0);
}
