// North Ambria - storm haze and snow-fog (visual only). Card group "Mist": UV.x along (metres / 40),
// UV.y = id + height.  0 rising out of the gulf past the plateau edge, 1-4 veils in front of each cliff layer
// (each farther one denser), 5 a thin veil of driven snow across the back of the plateau.
shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled;

uniform vec3 mist_color : source_color = vec3(0.7, 0.74, 0.81);
uniform vec3 bright_color : source_color = vec3(0.84, 0.87, 0.92);
uniform vec3 gap_dir = vec3(0.05, 0.07, -1.0);
uniform float wind_speed = 0.06;
uniform bool sea = false;        // the horizontal mist sea filling the gulf (node "Fog")

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
varying vec3 wpos;
void vertex() { wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz; }

void fragment() {
	float id = -floor(UV.y);
	if (sea) {
		float hs = 1.0 - fract(UV.y);
		float ns = fbm(vec2(UV.x * 0.8 - TIME * wind_speed * 2.0, hs * 30.0) + vec2(fbm(vec2(UV.x * 0.3, hs * 12.0 + TIME * 0.01)), 0.0));
		vec3 ds = normalize(wpos - CAMERA_POSITION_WORLD);
		float tw = pow(max(dot(ds, normalize(gap_dir)), 0.0), 5.0);
		ALBEDO = mix(mist_color * (0.9 + 0.14 * ns), bright_color, tw * 0.25);
		ALPHA = clamp((0.72 + 0.3 * ns) * smoothstep(0.0, 0.07, hs), 0.0, 0.97);
	} else {
	float h = 1.0 - fract(UV.y);
	float u = UV.x;
	float dens = id < 0.5 ? 0.6 : (id < 1.5 ? 0.3 : (id < 2.5 ? 0.36 : (id < 3.5 ? 0.46 : (id < 4.5 ? 0.62 : 0.08))));
	float spd = id > 4.5 ? 6.0 : 1.0 + id * 0.2;
	float n = fbm(vec2(u * 1.2 - TIME * wind_speed * spd, h * 2.2 + id * 3.7) + vec2(fbm(vec2(u * 0.5, h + TIME * 0.02)) * 1.2, 0.0));
	float n2 = fbm(vec2(u * 3.0 - TIME * wind_speed * spd * 1.8, h * 5.0 + id));
	float prof = id > 4.5 ? (1.0 - smoothstep(0.1, 1.0, h)) : pow(1.0 - h, 1.3);
	float a = prof * smoothstep(0.0, 0.08, h) * (0.45 + 0.75 * n + 0.2 * n2) * dens;
	vec3 d = normalize(wpos - CAMERA_POSITION_WORLD);
	float toward = pow(max(dot(d, normalize(gap_dir)), 0.0), 6.0);
	ALBEDO = mix(mist_color, bright_color, toward * 0.7 + n2 * 0.15);
	ALPHA = clamp(a, 0.0, 0.94);
	}
}
