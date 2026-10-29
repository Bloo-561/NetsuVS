// Thors Training Hall 3D - soft sun shafts through the right-hand windows (visual only).
// The "Shafts" mesh is a set of crossed ribbons: UV.x runs along the beam (0 = window),
// UV.y across it. Additive, unshaded, no depth write.
shader_type spatial;
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled;

uniform vec3 shaft_color : source_color = vec3(1.0, 0.86, 0.66);
uniform float intensity : hint_range(0.0, 1.0) = 0.10;
uniform float length_falloff = 1.6;
uniform float pulse_speed = 0.25;
uniform float dust_scale = 7.0;

varying vec3 wpos;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vnoise(vec2 p) {
	vec2 i = floor(p), f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);
}

void fragment() {
	float along = clamp(UV.x, 0.0, 1.0);
	float across = abs(UV.y * 2.0 - 1.0);
	float a = pow(1.0 - along, length_falloff) * smoothstep(0.0, 0.08, along);
	a *= 1.0 - smoothstep(0.35, 1.0, across);
	a *= pow(abs(dot(NORMAL, VIEW)), 0.6);          // hide edge-on ribbons
	float t = TIME * pulse_speed;
	float n = vnoise(vec2(UV.x * dust_scale - t, UV.y * 3.0 + wpos.y * 0.2));
	a *= 0.75 + 0.25 * sin(t * 2.0 + wpos.z * 0.15) * 0.5 + 0.35 * n;
	ALBEDO = shaft_color * a * intensity;
}
