// Depths of the Old Schoolhouse - the sky around the floating platform (visual only).
// Drawn on the "Sky" cylinder but computed from the VIEW DIRECTION, so it behaves like a sky at
// infinity: no seams, no parallax. Layers, bottom to top:
//   * a sea of clouds below the horizon, drifting, lit cyan-white, with a bright horizon haze
//   * a bank of clouds rising just above the horizon (slowly sliding sideways)
//   * deep blue night gradient with a teal milky way and dark dust lanes
//   * twinkling stars (denser in the milky way)
//   * glowing light rings arcing across the sky: they slowly breathe and turn, and pulses of light
//     run along them
// The Reflection copy uses `mirrored = true` (only the part under the floor is drawn).
shader_type spatial;
render_mode unshaded, cull_disabled, shadows_disabled, fog_disabled, depth_draw_opaque;

uniform bool mirrored = false;
uniform vec3 zenith_color : source_color = vec3(0.012, 0.05, 0.16);
uniform vec3 sky_color : source_color = vec3(0.03, 0.17, 0.4);
uniform vec3 horizon_color : source_color = vec3(0.3, 0.72, 0.92);
uniform float brightness = 1.0;

group_uniforms milky_way;
uniform vec3 mw_normal = vec3(-0.92, 0.0, -0.3);       // band runs up through the zenith, slightly right of centre          // the band is the great circle around this axis
uniform vec3 mw_color : source_color = vec3(0.25, 0.85, 0.95);
uniform float mw_strength = 0.65;
uniform float mw_width = 0.32;

group_uniforms stars;
uniform float star_density = 0.08;
uniform float star_brightness = 1.4;
uniform float twinkle_speed = 2.0;

group_uniforms rings;
uniform vec3 ring_axis = vec3(0.0, 0.866, -0.5);         // rings are circles around this direction (60 degrees up, ahead)
uniform vec4 ring_angles = vec4(0.74, 0.82, 0.89, 0.97); // radians from the axis: dip low in the middle, rise to the corners
uniform vec3 ring_color : source_color = vec3(0.55, 0.95, 1.0);
uniform float ring_strength = 0.9;
uniform float ring_width = 0.0035;
uniform float ring_glow = 0.022;
uniform float ring_turn_speed = 0.01;                    // radians per second (the whole set turns)
uniform float pulse_speed = 0.35;

group_uniforms clouds;
uniform vec3 cloud_lit : source_color = vec3(0.85, 0.97, 1.0);
uniform vec3 cloud_shade : source_color = vec3(0.22, 0.48, 0.75);
uniform float cloud_speed = 0.012;
uniform float bank_height = 0.10;                        // how far the cloud bank rises above the horizon

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vnoise(vec2 p) {
	vec2 i = floor(p), f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}
float fbm(vec2 p) {
	float s = 0.0, a = 0.5;
	for (int i = 0; i < 5; i++) { s += vnoise(p) * a; p = p * 2.03 + vec2(1.7, 9.2); a *= 0.5; }
	return s / 0.97;
}
vec3 rot_y(vec3 v, float a) {
	float c = cos(a), s = sin(a);
	return vec3(c * v.x + s * v.z, v.y, -s * v.x + c * v.z);
}

varying vec3 wpos;
void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

float stars(vec3 d, float scale, float density, float seed) {
	// cells on (azimuth, elevation); one possible star per cell
	vec2 sp = vec2(atan(d.x, -d.z) * 0.15915 + 0.5, asin(clamp(d.y, -1.0, 1.0)) * 0.3183 + 0.5) * scale;
	sp.x *= 2.0;
	vec2 c = floor(sp), f = fract(sp);
	float h = hash(c + seed);
	if (h > density) { return 0.0; }
	vec2 pos = vec2(hash(c + 3.1 + seed), hash(c + 7.7 + seed)) * 0.7 + 0.15;
	float r = length((f - pos) * vec2(1.0, 1.0));
	float sz = 0.06 + 0.12 * hash(c + 11.0 + seed);
	float tw = 0.6 + 0.4 * sin(TIME * twinkle_speed * (0.5 + hash(c + 5.0)) + h * 60.0);
	return smoothstep(sz, 0.0, r) * tw * (0.4 + 0.6 * hash(c + 13.0 + seed));
}

void fragment() {
	if (mirrored && wpos.y > 0.0) { discard; }
	vec3 d = normalize(wpos - CAMERA_POSITION_WORLD);
	if (mirrored) { d.y = -d.y; }
	float y = d.y;
	float t = TIME;
	float az = atan(d.x, -d.z);

	// ---- night gradient
	vec3 col = mix(horizon_color, sky_color, smoothstep(0.0, 0.25, y));
	col = mix(col, zenith_color, smoothstep(0.2, 0.85, y));

	// ---- milky way
	float band = dot(d, normalize(mw_normal));
	float mw = exp(-pow(band / mw_width, 2.0));
	vec2 mp = vec2(az * 3.0, y * 6.0 + band * 4.0);
	float mwn = fbm(mp * 1.5 + vec2(t * 0.002, 0.0));
	float dust = smoothstep(0.45, 0.75, fbm(mp * 3.0 + 4.0));
	col += mw_color * mw * mw_strength * (0.35 + 0.9 * mwn) * (1.0 - 0.7 * dust) * smoothstep(-0.05, 0.25, y);

	// ---- stars
	float st = stars(d, 180.0, star_density, 0.0) + stars(d, 90.0, star_density * 0.5, 17.0) * 1.3
		+ stars(d, 320.0, star_density * (1.0 + 4.0 * mw), 31.0) * 0.6;
	col += vec3(0.85, 0.95, 1.0) * st * star_brightness * smoothstep(0.0, 0.15, y);

	// ---- light rings
	vec3 ax = normalize(rot_y(ring_axis, t * ring_turn_speed));
	float ang = acos(clamp(dot(d, ax), -1.0, 1.0));
	vec3 ref = normalize(cross(ax, vec3(1.0, 0.0, 0.0)));
	vec3 ref2 = cross(ax, ref);
	float phi = atan(dot(d, ref2), dot(d, ref));
	float rings = 0.0;
	for (int i = 0; i < 4; i++) {
		float fi = float(i);
		float a0 = ring_angles[i] + 0.012 * sin(t * 0.07 + fi * 1.9);           // breathing
		float dd = abs(ang - a0);
		float core = smoothstep(ring_width * (1.0 + 0.5 * fi), 0.0, dd);
		float glow = exp(-dd / (ring_glow * (0.7 + 0.2 * fi)));
		float pulse = 0.55 + 0.45 * sin(phi * (3.0 + fi) - t * pulse_speed * (1.0 + 0.3 * fi) + fi * 2.1);
		pulse = pow(pulse, 3.0) * 1.6 + 0.35;
		float fade = smoothstep(-0.02, 0.12, y) * (0.55 + 0.45 * sin(phi * 1.3 + fi));   // rings fade in and out
		rings += (core * 1.5 + glow * 0.22) * pulse * fade * (1.0 - 0.15 * fi);
	}
	col += ring_color * rings * ring_strength;

	// ---- cloud bank just above the horizon (behind the islands)
	float bn = fbm(vec2(az * 4.0 + t * cloud_speed * 0.6, y * 9.0));
	float bank_top = bank_height * (0.45 + 0.9 * fbm(vec2(az * 2.5 - t * cloud_speed * 0.3, 3.0)));
	float bank = (1.0 - smoothstep(bank_top - 0.03, bank_top + 0.01, y)) * smoothstep(-0.02, 0.0, y);
	vec3 bankc = mix(cloud_shade, cloud_lit, smoothstep(0.3, 0.8, bn) * (0.5 + 0.5 * smoothstep(bank_top, 0.0, y)));
	col = mix(col, mix(bankc, horizon_color, 0.25), bank * smoothstep(0.25, 0.55, bn + 0.25));

	// ---- sea of clouds below
	if (y < 0.02) {
		vec2 p = d.xz / (max(-y, 0.0) + 0.04) * 0.35 + vec2(t * cloud_speed * 6.0, t * cloud_speed * 2.0);
		float n = fbm(p);
		float n2 = fbm(p * 2.3 + 5.0 - t * cloud_speed * 3.0);
		float puff = smoothstep(0.35, 0.75, n * 0.7 + n2 * 0.4);
		vec3 sea = mix(cloud_shade, cloud_lit, puff);
		sea = mix(sea, horizon_color * 1.1, smoothstep(-0.25, 0.0, y) * 0.65);       // haze toward the horizon
		col = mix(col, sea, smoothstep(0.02, -0.01, y));
	}
	// bright horizon line
	col += horizon_color * 0.25 * exp(-abs(y) * 30.0);
	ALBEDO = col * brightness;
}
