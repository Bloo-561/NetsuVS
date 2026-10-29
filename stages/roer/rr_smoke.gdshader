// Roer - chimney smoke (visual only). Card group "Smoke": crossed quads rising from each stack and leaning with the
// wind; UV.x across, UV.y = chimney id + height up the plume. Soot-brown, lit warm on the sunset side.
shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled;

uniform vec3 smoke_dark : source_color = vec3(0.3, 0.26, 0.28);
uniform vec3 smoke_lit : source_color = vec3(0.86, 0.6, 0.5);
uniform float density = 0.9;
uniform float rise = 0.12;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vnoise(vec2 p) {
	vec2 i = floor(p), f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}
float fbm(vec2 p) {
	float s = 0.0, a = 0.5;
	for (int i = 0; i < 5; i++) { s += vnoise(p) * a; p = p * 2.03 + 1.7; a *= 0.5; }
	return s / 0.97;
}

void fragment() {
	float id = -floor(UV.y);
	float h = 1.0 - fract(UV.y);
	float x = (UV.x - 0.5) * 2.0;
	float n = fbm(vec2(x * 1.6 + id * 3.7, h * 3.0 - TIME * rise) + vec2(0.0, fbm(vec2(x, h * 2.0 - TIME * rise * 0.6) + id)));
	float w = 0.55 + 0.4 * h;
	float body = 1.0 - smoothstep(w * 0.4, w, abs(x) + (n - 0.5) * 0.9);
	float a = body * smoothstep(0.0, 0.05, h) * (1.0 - smoothstep(0.45, 1.0, h)) * smoothstep(0.3, 0.6, n + 0.2) * density;
	vec3 col = mix(smoke_dark, smoke_lit, clamp(n * 1.2 - 0.15 + x * 0.25, 0.0, 1.0));
	ALBEDO = col;
	ALPHA = clamp(a, 0.0, 1.0);
}
