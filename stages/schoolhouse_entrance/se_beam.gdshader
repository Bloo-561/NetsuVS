// Old Schoolhouse -Entrance- - the moonbeams slanting down from the windows (visual only).
// Each beam is the window swept along the moonlight to the floor (4 sheets): UV.x across a sheet,
// UV.y = beam id + distance (0 at the window, 1 at the floor; glTF flips v). Additive, very soft,
// with dust drifting in it; the light swells and fades as clouds pass the moon.
shader_type spatial;
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled;

uniform vec3 beam_color : source_color = vec3(0.55, 0.68, 1.0);
uniform float strength = 0.18;
uniform float dust = 0.6;
uniform float cloud_pass = 0.35;         // how much passing clouds dim the beams

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vnoise(vec2 p) {
	vec2 i = floor(p), f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}
float fbm(vec2 p) {
	float s = 0.0, a = 0.5;
	for (int i = 0; i < 4; i++) { s += vnoise(p) * a; p = p * 2.1 + 3.7; a *= 0.5; }
	return s / 0.94;
}

void fragment() {
	float id = -floor(UV.y);
	float s = 1.0 - fract(UV.y);
	float u = UV.x;
	float body = smoothstep(0.0, 0.35, u) * smoothstep(0.0, 0.35, 1.0 - u);
	float along = smoothstep(0.0, 0.06, s) * (1.0 - smoothstep(0.45, 1.0, s)) * (1.0 - 0.4 * s);
	float motes = 0.55 + dust * (fbm(vec2(u * 3.0 + id * 1.7, s * 7.0 - TIME * 0.04)) - 0.3);
	float cloud = 1.0 - cloud_pass * smoothstep(0.35, 0.75, vnoise(vec2(TIME * 0.06 + id * 0.37, 2.0)));
	float facing = pow(abs(dot(normalize(NORMAL), normalize(VIEW))), 0.6);
	ALBEDO = beam_color * strength * body * along * motes * cloud * facing;
}
