// Crimson Abyss - giant shadow tendrils circling the crater (energy orbiting the fight). Visual only.
// Mesh: UV.x runs root (0) -> tip (1); the ribbon id is encoded in UV.y (glTF flips V):
// id = -floor(UV.y) - 1, across = fract(UV.y).
shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled;

uniform sampler2D tendril_tex : source_color, filter_linear_mipmap, repeat_disable;
uniform float pivot_z = -8.0;           // crater centre (x = 0)
uniform float orbit_speed = 0.045;      // radians per second around the crater
uniform float sway = 3.5;               // metres at the tip
uniform float speed = 0.45;
uniform float edge_glow = 0.6;
uniform vec3 pulse_color : source_color = vec3(1.0, 0.35, 0.7);
uniform float pulse_gain = 1.3;
uniform float pulse_speed = 0.35;
uniform float opacity = 0.9;

varying float v_id;

float hash(float x) { return fract(sin(x * 91.3) * 43758.5453); }
float vnoise(vec2 p) {
	vec2 i = floor(p), f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	float a = fract(sin(dot(i, vec2(127.1, 311.7))) * 43758.5453);
	float b = fract(sin(dot(i + vec2(1, 0), vec2(127.1, 311.7))) * 43758.5453);
	float c = fract(sin(dot(i + vec2(0, 1), vec2(127.1, 311.7))) * 43758.5453);
	float d = fract(sin(dot(i + vec2(1, 1), vec2(127.1, 311.7))) * 43758.5453);
	return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
}

void vertex() {
	float id = -floor(UV.y) - 1.0;
	v_id = id;
	float u = UV.x;
	float w = u * u;
	float t = TIME * speed + id * 1.7;
	vec2 p = VERTEX.xz - vec2(0.0, pivot_z);
	vec2 tang = normalize(vec2(-p.y, p.x));
	p += tang * (sin(u * 4.0 - t * 1.3) * 0.7 + sin(u * 9.0 - t * 2.1) * 0.3) * sway * w;
	VERTEX.y += cos(u * 3.0 - t) * 0.6 * sway * 0.6 * w;
	float a = TIME * orbit_speed * (0.75 + 0.5 * hash(id + 3.0));
	float ca = cos(a), sa = sin(a);
	p = vec2(p.x * ca - p.y * sa, p.x * sa + p.y * ca);
	VERTEX.xz = p + vec2(0.0, pivot_z);
	NORMAL.xz = vec2(NORMAL.x * ca - NORMAL.z * sa, NORMAL.x * sa + NORMAL.z * ca);
}

void fragment() {
	vec2 uv = vec2(UV.x, fract(UV.y));
	vec4 tex = texture(tendril_tex, uv);
	float n = vnoise(vec2(uv.x * 9.0 - TIME * 0.35 + v_id * 3.0, uv.y * 4.0));
	float a = tex.a * smoothstep(0.1, 0.45, n * 0.6 + tex.a * 0.7);
	a *= smoothstep(0.0, 0.07, uv.x) * smoothstep(1.0, 0.85, uv.x);
	a *= smoothstep(0.08, 0.35, abs(dot(NORMAL, VIEW)));      // ribbons seen edge-on fade out
	float pink = clamp(tex.r - tex.b * 0.6, 0.0, 1.0);
	float flick = 0.75 + 0.25 * sin(TIME * 2.7 + uv.x * 14.0 + v_id * 2.0);
	// pulses of energy running from root to tip
	float e = 0.0;
	for (int k = 0; k < 2; k++) {
		float x = fract(uv.x * 0.8 - TIME * pulse_speed + v_id * 0.37 + float(k) * 0.5) - 0.5;
		e += exp(-x * x * 120.0);
	}
	float edge = smoothstep(0.25, 0.9, abs(uv.y * 2.0 - 1.0)) + pink;
	vec3 col = tex.rgb + vec3(1.0, 0.25, 0.6) * pink * edge_glow * flick + pulse_color * e * edge * pulse_gain;
	ALBEDO = col;
	ALPHA = clamp(a * opacity + e * edge * 0.3 * tex.a, 0.0, 1.0);
}
