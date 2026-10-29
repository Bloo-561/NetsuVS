// Roer - layers of smog over the factory district (visual only). Card group "Haze": wide cards, UV.x along
// (metres / 20), UV.y = id + height. Thick at the bottom, thinning upward, drifting, glowing toward the sun.
shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled;

uniform vec3 sun_dir = vec3(0.06, 0.14, -0.99);
uniform vec3 haze_color : source_color = vec3(0.74, 0.5, 0.46);
uniform vec3 glow_color : source_color = vec3(1.0, 0.7, 0.46);
uniform float density = 0.55;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vnoise(vec2 p) {
	vec2 i = floor(p), f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}
float fbm(vec2 p) {
	float s = 0.0, a = 0.5;
	for (int i = 0; i < 4; i++) { s += vnoise(p) * a; p = p * 2.03 + 1.7; a *= 0.5; }
	return s / 0.94;
}
varying vec3 wpos;
void vertex() { wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz; }

void fragment() {
	float id = -floor(UV.y);
	float h = 1.0 - fract(UV.y);
	float n = fbm(vec2(UV.x * 0.5 + TIME * 0.004 * (1.0 + id), h * 2.0 + id * 5.0));
	float a = pow(1.0 - h, 1.6) * (0.55 + 0.6 * n) * density * smoothstep(0.0, 0.08, h + 0.04);
	vec3 d = normalize(wpos - CAMERA_POSITION_WORLD);
	float sun = pow(max(dot(d, normalize(sun_dir)), 0.0), 8.0);
	ALBEDO = mix(haze_color, glow_color, sun * 0.8) * (0.9 + 0.2 * n);
	ALPHA = clamp(a, 0.0, 0.92);
}
