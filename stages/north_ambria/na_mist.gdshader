// North Ambria - banks of blowing snow and mist between the field and the mountains (card group "Mist").
// Wide camera-facing quads: UV.x in 20 m units across, UV.y = layer id + height (glTF flips v).
// The near layers blow fast and thin (snow streaming across the ground behind the fighters);
// the far ones roll slowly and thick, burying the mountains' feet. Gusts swell them. Visual only.
shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled;

uniform vec3 mist_color : source_color = vec3(0.86, 0.9, 0.96);
uniform vec3 shade_color : source_color = vec3(0.6, 0.66, 0.78);
uniform float opacity = 0.75;
uniform float wind = 0.35;            // 20 m units per second (near layer)
uniform float gust_period = 7.0;

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
	float gust = 0.7 + 0.3 * sin(TIME * 6.2832 / gust_period + id) * sin(TIME * 6.2832 / (gust_period * 0.41));
	float speed = wind / (1.0 + id * 0.9);
	float t = TIME * speed;
	vec2 q = vec2(UV.x * (2.4 - id * 0.25) - t * 2.0, h * (1.6 + id * 0.2) - TIME * 0.03);
	float n = fbm(q + vec2(fbm(q * 0.7 + vec2(t, 0.0)) * 1.2, 0.0));
	// near layers: streaky (stretched along the wind); far layers: billowy
	float streak = vnoise(vec2(UV.x * 6.0 - t * 6.0, h * 18.0 + id * 3.0));
	n = mix(n * 0.7 + streak * 0.45, n, smoothstep(0.0, 2.5, id));
	float top = 0.55 + 0.4 * fbm(vec2(UV.x * 0.9 - t * 0.7, id * 1.7));
	float a = smoothstep(0.3, 0.68, n) * (1.0 - smoothstep(top - 0.35, top, h)) * smoothstep(0.0, 0.1, h);
	a *= gust * mix(0.55, 1.0, smoothstep(0.0, 3.0, id));
	ALBEDO = mix(shade_color, mist_color, 0.55 + 0.45 * n + 0.2 * h);
	ALPHA = clamp(a * opacity, 0.0, 1.0);
}
