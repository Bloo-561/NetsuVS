// Old Schoolhouse -Entrance- - the moonlit night sky seen through the windows (visual only), drawn from the
// VIEW DIRECTION so it sits at infinity: a glowing blue sky with bright moonlit clouds drifting past and a
// few stars between them. Card group "Window": UV.x across, UV.y = window id + height (glTF flips v).
//   mirror = true  for the copy under the floor (Reflection): the view is flipped up/down
shader_type spatial;
render_mode unshaded, cull_disabled, shadows_disabled, fog_disabled;

uniform bool mirror = false;
uniform float brightness = 1.25;
uniform vec3 sky_low : source_color = vec3(0.42, 0.56, 0.9);
uniform vec3 sky_high : source_color = vec3(0.16, 0.26, 0.6);
uniform vec3 cloud_lit : source_color = vec3(0.86, 0.92, 1.0);
uniform vec3 cloud_shade : source_color = vec3(0.36, 0.46, 0.74);
uniform vec2 wind = vec2(0.004, 0.0);
uniform float stars = 0.8;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vnoise(vec2 p) {
	vec2 i = floor(p), f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}
float fbm(vec2 p) {
	float s = 0.0, a = 0.5;
	for (int i = 0; i < 6; i++) { s += vnoise(p) * a; p = p * 2.02 + vec2(3.1, 1.7); a *= 0.5; }
	return s / 0.98;
}

varying vec3 wpos;
void vertex() { wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz; }

void fragment() {
	vec3 d = normalize(wpos - CAMERA_POSITION_WORLD);
	if (mirror) { d.y = -d.y; }
	float y = max(d.y + 0.15, 0.02);
	vec3 col = mix(sky_low, sky_high, smoothstep(0.1, 0.7, d.y + 0.15));
	// stars twinkling in the gaps
	vec2 sp = vec2(atan(d.x, -d.z) * 60.0, d.y * 60.0);
	float st = step(0.985, hash(floor(sp))) * (0.5 + 0.5 * sin(TIME * 2.0 + hash(floor(sp) + 3.0) * 6.28));
	col += vec3(0.8, 0.86, 1.0) * st * stars * 0.6;
	// big moonlit clouds on a curved layer, drifting
	vec2 cp = d.xz / y * 0.5 + wind * TIME * 10.0;
	float n = fbm(cp + vec2(fbm(cp * 0.5 + TIME * 0.003), 0.0) * 0.7);
	float c = smoothstep(0.42, 0.66, n);
	float shade = clamp((n - fbm(cp + vec2(0.06, -0.08))) * 5.0 + 0.6, 0.0, 1.0);
	col = mix(col, mix(cloud_shade, cloud_lit, shade), c);
	ALBEDO = col * brightness;
}
