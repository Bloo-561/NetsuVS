// Thors Training Hall 3D - the sky seen through the windows (visual only).
// Drawn on the "Outside" cards behind the windows, but computed from the VIEW DIRECTION, so it
// behaves like a real sky at infinity: no parallax seams, no trees, the horizon stays at eye level.
// Clouds drift with `wind`; distant hazy hills sit on the horizon. The same shader with
// `mirrored = true` goes on the Reflection copy so the polished floor reflects the sky correctly.
// Morning / dusk are just different colour sets (see thors_hall_3d.tscn / thors_hall_3d_dusk.tscn).
shader_type spatial;
render_mode unshaded, cull_back, shadows_disabled, fog_disabled, depth_draw_opaque;

uniform bool mirrored = false;
uniform vec3 zenith_color : source_color = vec3(0.36, 0.58, 0.86);
uniform vec3 sky_color : source_color = vec3(0.62, 0.76, 0.92);       // ~20 degrees up
uniform vec3 horizon_color : source_color = vec3(0.89, 0.93, 0.96);
uniform vec3 sun_glow_color : source_color = vec3(1.0, 0.94, 0.82);
uniform vec3 sun_dir = vec3(0.62, 0.17, 0.77);    // TOWARD the sun (opposite of the light travel)
uniform float sun_glow = 0.45;
uniform float sun_glow_power = 6.0;

group_uniforms clouds;
uniform vec3 cloud_lit : source_color = vec3(1.0, 1.0, 1.0);
uniform vec3 cloud_shade : source_color = vec3(0.70, 0.76, 0.86);
uniform float cloud_cover : hint_range(0.0, 1.0) = 0.48;
uniform float cloud_softness = 0.22;
uniform float cloud_opacity : hint_range(0.0, 1.0) = 0.9;
uniform float cloud_scale = 0.55;
uniform vec2 wind = vec2(0.012, 0.004);           // cloud drift (sky-plane units per second)
uniform float cloud_morph = 0.01;                 // how fast the cloud shapes change

group_uniforms hills;
uniform vec3 far_hills : source_color = vec3(0.66, 0.74, 0.82);
uniform vec3 near_hills : source_color = vec3(0.52, 0.62, 0.68);
uniform vec3 ground_color : source_color = vec3(0.50, 0.58, 0.60);
uniform float hills_height = 0.05;                // in direction-y units (about 3 degrees)
uniform float haze = 0.55;

uniform float brightness = 1.0;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vnoise(vec2 p) {
	vec2 i = floor(p), f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}
float fbm(vec2 p) {
	float s = 0.0, a = 0.5;
	for (int i = 0; i < 5; i++) { s += vnoise(p) * a; p = p * 2.02 + vec2(3.1, 1.7); a *= 0.5; }
	return s / 0.97;
}
float ridge(float az, float k, float seed) {      // 1D hill profile around the horizon, 0..1
	float s = 0.0, a = 0.5, f = k;
	for (int i = 0; i < 5; i++) { s += a * vnoise(vec2(az * f, seed + float(i) * 3.7)); f *= 2.17; a *= 0.48; }
	return s / 0.95;
}

varying vec3 wpos;
void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	// the mirrored copy of the cards pokes up above the floor (they reach below y = 0): only the part
	// under the floor belongs to the reflection
	if (mirrored && wpos.y > 0.0) { discard; }
	vec3 d = normalize(wpos - CAMERA_POSITION_WORLD);
	if (mirrored) { d.y = -d.y; }
	float y = d.y;
	vec3 sd = normalize(sun_dir);
	// sky gradient
	vec3 col = mix(horizon_color, sky_color, smoothstep(0.0, 0.18, y));
	col = mix(col, zenith_color, smoothstep(0.15, 0.6, y));
	float sdot = max(dot(d, sd), 0.0);
	col += sun_glow_color * sun_glow * pow(sdot, sun_glow_power) * (1.0 - 0.6 * smoothstep(0.0, 0.5, y));
	// drifting clouds on a flat sky plane
	float above = smoothstep(-0.01, 0.10, y);
	if (above > 0.0) {
		vec2 p = d.xz / (y + 0.10) * cloud_scale;
		float t = TIME;
		vec2 q = p + wind * t * 10.0;
		float n = fbm(q + vec2(fbm(q * 0.6 + t * cloud_morph), 0.0) * 0.6);
		float c = smoothstep(1.0 - cloud_cover - cloud_softness, 1.0 - cloud_cover + cloud_softness, n);
		// fake self-shadowing: sample a little toward the sun
		float n2 = fbm(q + normalize(sd.xz + 1e-4) * 0.12 + vec2(fbm(q * 0.6 + t * cloud_morph), 0.0) * 0.6);
		float lit = clamp(0.55 + (n - n2) * 4.0, 0.0, 1.0);
		vec3 cc = mix(cloud_shade, cloud_lit, lit);
		cc += sun_glow_color * sun_glow * 0.8 * pow(sdot, sun_glow_power * 0.5) * lit;   // silver/golden lining
		float fade = above * (1.0 - smoothstep(0.0, 1.0, length(p) * 0.02));          // thin out far away
		float hfade = mix(0.7, 1.0, smoothstep(0.0, 0.2, y));                         // hazier at the horizon
		col = mix(col, mix(horizon_color, cc, hfade), c * cloud_opacity * fade);
	}
	// distant hills on the horizon (two hazy layers) and the ground below them
	float az = atan(d.x, -d.z);
	float hf = hills_height * (0.25 + 0.75 * ridge(az, 5.0, 1.0));
	float hn = hills_height * (0.05 + 0.5 * ridge(az, 9.0, 7.0)) - 0.01;
	float aa = fwidth(y) * 1.5 + 1e-4;
	vec3 farc = mix(far_hills, horizon_color, haze * 0.6);
	col = mix(col, farc, 1.0 - smoothstep(hf - aa, hf + aa, y));
	vec3 nearc = mix(near_hills, horizon_color, haze * 0.3);
	col = mix(col, nearc, 1.0 - smoothstep(hn - aa, hn + aa, y));
	col = mix(col, mix(ground_color, horizon_color, haze * 0.25), 1.0 - smoothstep(-0.06, -0.02, y));
	ALBEDO = col * brightness;
}
