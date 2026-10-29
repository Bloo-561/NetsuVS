// Septian Chapel - a thin wisp of smoke from the rectory chimney (visual only). Card group "Smoke".
shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled;

uniform vec3 smoke_color : source_color = vec3(0.86, 0.86, 0.88);
uniform float density = 0.55;
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
	float h = 1.0 - fract(UV.y);
	float x = (UV.x - 0.5) * 2.0;
	float n = fbm(vec2(x * 1.5 + sin(h * 5.0 - TIME * 0.7) * 0.4, h * 3.5 - TIME * 0.35));
	float body = 1.0 - smoothstep(0.15, 0.7 + 0.2 * h, abs(x + sin(h * 6.0 - TIME * 0.9) * 0.25 * h) + (n - 0.5) * 0.7);
	ALBEDO = smoke_color * (0.85 + 0.2 * n);
	ALPHA = clamp(body * smoothstep(0.0, 0.08, h) * (1.0 - smoothstep(0.35, 1.0, h)) * density * smoothstep(0.25, 0.55, n + 0.15), 0.0, 1.0);
}
