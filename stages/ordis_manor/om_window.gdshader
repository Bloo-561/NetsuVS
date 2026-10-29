// Ordis Royal Manor - the view out of the windows (visual only), drawn from the VIEW DIRECTION so the sea
// and sky sit at infinity and shift with the camera: bright blue sky with drifting clouds, faint islands on
// the horizon and a glittering sea. Card group "Window": UV.x across, UV.y = window id + height (glTF flips v).
//   mirror = true  for the copy under the floor (Reflection): the view is flipped up/down
//   broken > 0     cracked panes (Ruined)
//   smoke > 0      smoke drifting past outside (Ruined)
shader_type spatial;
render_mode unshaded, cull_disabled, shadows_disabled, fog_disabled;

uniform bool mirror = false;
uniform float brightness = 1.15;
uniform vec3 zenith : source_color = vec3(0.24, 0.48, 0.86);
uniform vec3 sky : source_color = vec3(0.5, 0.72, 0.96);
uniform vec3 horizon : source_color = vec3(0.86, 0.92, 0.98);
uniform vec3 cloud_lit : source_color = vec3(1.0, 0.99, 0.96);
uniform vec3 cloud_shade : source_color = vec3(0.66, 0.72, 0.84);
uniform vec3 sea_far : source_color = vec3(0.42, 0.66, 0.86);
uniform vec3 sea_near : source_color = vec3(0.06, 0.3, 0.52);
uniform vec3 land : source_color = vec3(0.56, 0.66, 0.78);
uniform float horizon_y = 0.035;           // the sea's horizon, a little above eye level (the manor is on a cliff)
uniform vec2 wind = vec2(0.006, 0.0);
uniform vec3 sun_dir = vec3(-0.35, 0.3, -1.0);
uniform float broken = 0.0;
uniform float smoke = 0.0;
uniform vec3 smoke_color : source_color = vec3(0.36, 0.33, 0.32);

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
vec2 hash2(vec2 p) { return fract(sin(vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)))) * 43758.5453); }
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
float vedge(vec2 p) {
	vec2 i = floor(p), f = fract(p);
	float d1 = 8.0, d2 = 8.0;
	for (int y = -1; y <= 1; y++) for (int x = -1; x <= 1; x++) {
		vec2 g = vec2(float(x), float(y));
		float d = length(g + hash2(i + g) - f);
		if (d < d1) { d2 = d1; d1 = d; } else if (d < d2) { d2 = d; }
	}
	return d2 - d1;
}

varying vec3 wpos;
void vertex() { wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz; }

void fragment() {
	vec3 d = normalize(wpos - CAMERA_POSITION_WORLD);
	if (mirror) { d.y = -d.y; }
	float y = d.y - horizon_y;
	float az = atan(d.x, -d.z);
	vec3 sd = normalize(sun_dir);
	vec3 col;
	// distant islands and headlands along the horizon
	float hills = (fbm(vec2(az * 3.0, 1.3)) - 0.42) * 0.07 * smoothstep(0.1, 0.6, fbm(vec2(az * 0.8, 7.0)));
	if (y > 0.0) {
		col = mix(horizon, sky, smoothstep(0.0, 0.08, y));
		col = mix(col, zenith, smoothstep(0.08, 0.5, y));
		// cumulus clouds on a curved layer, drifting
		vec2 cp = d.xz / (y + 0.06) * 0.55 + wind * TIME * 10.0;
		float n = fbm(cp + vec2(fbm(cp * 0.5 + TIME * 0.004), 0.0) * 0.6);
		float c = smoothstep(0.46, 0.72, n) * smoothstep(0.0, 0.05, y);
		float shade = clamp((fbm(cp + vec2(0.05, 0.06)) - n) * 4.0 + 0.55, 0.0, 1.0);
		col = mix(col, mix(cloud_shade, cloud_lit, shade), c * 0.95);
		col += vec3(1.0, 0.96, 0.86) * pow(max(dot(d, sd), 0.0), 40.0) * 0.6;
		col = mix(col, land, step(y, hills) * 0.85 * (1.0 - c));
	} else {
		// the sea: bright toward the horizon, deep blue below, waves and sun glitter
		float depth = smoothstep(0.0, 0.18, -y);
		col = mix(sea_far, sea_near, depth);
		vec2 sp = d.xz / (-y + 0.004);
		float wv = fbm(sp * vec2(0.6, 2.2) + vec2(TIME * 0.05, TIME * 0.02));
		col *= 0.88 + 0.24 * wv;
		float glint = pow(vnoise(sp * vec2(1.4, 6.0) + vec2(TIME * 0.6, -TIME * 0.4)), 12.0);
		float sunpath = pow(max(dot(normalize(vec3(d.x, -d.y, d.z)), sd), 0.0), 6.0);
		col += vec3(1.0, 0.97, 0.9) * glint * (0.6 + 2.5 * sunpath) * (1.0 - depth * 0.6);
		col = mix(col, horizon, (1.0 - smoothstep(0.0, 0.012, -y)) * 0.6);
	}
	// Ruined: smoke blowing past outside, then the cracked glass
	if (smoke > 0.0) {
		vec2 s = vec2(az * 4.0 - TIME * 0.05, d.y * 6.0 - TIME * 0.08);
		float sm = smoothstep(0.45, 0.85, fbm(s + vec2(fbm(s * 0.7), 0.0)));
		col = mix(col, smoke_color * (0.8 + 0.4 * fbm(s * 2.0)), sm * smoke);
	}
	col *= brightness;
	if (broken > 0.0) {
		float id = -floor(UV.y);
		vec2 uv = vec2(UV.x, 1.0 - fract(UV.y)) * vec2(1.0, 2.6);
		float has = step(0.35, hash(vec2(id, 4.2)));
		vec2 c0 = vec2(hash(vec2(id, 1.0)), 0.4 + 1.8 * hash(vec2(id, 2.0)));
		vec2 dv = uv - c0;
		float a = atan(dv.y, dv.x);
		float radial = abs(fract(a / 6.2831853 * 9.0 + fbm(dv * 2.0) * 0.5) - 0.5) * length(dv);
		float web = abs(fract(length(dv) * 3.0 + fbm(uv * 3.0) * 0.6) - 0.5);
		float lines = (1.0 - smoothstep(0.0, 0.012, radial)) + (1.0 - smoothstep(0.0, 0.02, web)) * (1.0 - smoothstep(0.2, 0.9, length(dv)));
		lines = max(lines, (1.0 - smoothstep(0.01, 0.03, vedge(uv * 2.2))) * 0.6);
		lines *= has * (1.0 - smoothstep(0.5, 1.6, length(dv)));
		col = mix(col, vec3(0.92, 0.95, 1.0), clamp(lines, 0.0, 1.0) * 0.75 * broken);
		col *= 1.0 - has * broken * 0.12 * (1.0 - smoothstep(0.0, 1.2, length(dv)));
	}
	ALBEDO = col;
}
