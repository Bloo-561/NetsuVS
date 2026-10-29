// Roer - the dusk sky (visual only), drawn from the VIEW DIRECTION so it sits at infinity.
// The sun is setting just to the right of the Reinford tower: a hot disc and a wide golden glow, long streaks
// of cloud lit orange and pink from below, the sky deepening to violet and indigo overhead with the first stars.
shader_type spatial;
render_mode unshaded, cull_disabled, shadows_disabled, fog_disabled, depth_draw_opaque;

uniform vec3 sun_dir = vec3(0.06, 0.14, -0.99);          // toward the sun (matches the bake)
uniform vec3 horizon_color : source_color = vec3(1.0, 0.66, 0.4);
uniform vec3 low_color : source_color = vec3(0.95, 0.5, 0.44);
uniform vec3 mid_color : source_color = vec3(0.56, 0.4, 0.6);
uniform vec3 high_color : source_color = vec3(0.17, 0.18, 0.38);
uniform vec3 sun_color : source_color = vec3(1.0, 0.86, 0.6);
uniform vec3 cloud_lit : source_color = vec3(1.0, 0.62, 0.42);
uniform vec3 cloud_dark : source_color = vec3(0.34, 0.26, 0.38);
uniform vec3 haze_color : source_color = vec3(0.78, 0.52, 0.48);
uniform vec2 wind = vec2(0.0035, 0.0);
uniform float brightness = 1.0;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vnoise(vec2 p) {
	vec2 i = floor(p), f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}
float fbm(vec2 p) {
	float s = 0.0, a = 0.5;
	for (int i = 0; i < 6; i++) { s += vnoise(p) * a; p = p * 2.03 + vec2(3.1, 1.7); a *= 0.5; }
	return s / 0.98;
}

varying vec3 wpos;
void vertex() { wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz; }

void fragment() {
	vec3 d = normalize(wpos - CAMERA_POSITION_WORLD);
	vec3 sd = normalize(sun_dir);
	float y = d.y;
	float t = TIME;
	// the fight cams see y ~ -0.27 .. 0.27 (the high cams a little more): the gradient is packed into that band
	vec3 col = mix(horizon_color, low_color, smoothstep(0.0, 0.08, y));
	col = mix(col, mid_color, smoothstep(0.06, 0.22, y));
	col = mix(col, high_color, smoothstep(0.18, 0.5, y));
	// sun: disc, glow and a broad warm halo that tints the whole low sky toward it
	float cs = dot(d, sd);
	float ang = acos(clamp(cs, -1.0, 1.0));
	float disc = 1.0 - smoothstep(0.016, 0.02, ang);
	float glow = exp(-ang * ang / 0.0016) * 1.2 + exp(-ang * ang / 0.03) * 0.45;
	float halo = pow(max(cs, 0.0), 6.0);
	col = mix(col, horizon_color * 1.08, halo * (1.0 - smoothstep(0.0, 0.3, y)) * 0.6);
	// long cloud streaks on a curved layer, drifting
	float yy = max(y, 0.0) + 0.05;
	vec2 cp = vec2(d.x / yy * 0.35, 1.0 / yy * 0.6) + wind * t * 10.0;
	float n = fbm(vec2(cp.x * 0.6, cp.y * 3.2) + vec2(fbm(cp * 0.4 + t * 0.002) * 1.5, 0.0));
	float n2 = fbm(vec2(cp.x * 1.6, cp.y * 7.0) + 11.0);
	float cl = smoothstep(0.48, 0.7, n * 0.85 + n2 * 0.25) * smoothstep(0.015, 0.05, y) * (1.0 - smoothstep(0.32, 0.5, y));
	// undersides lit by the sun below them: brightest toward the sun and low down
	float under = clamp(0.35 + (n - n2) * 1.2, 0.0, 1.0);
	float sunside = 0.35 + 0.65 * pow(max(cs, 0.0), 3.0);
	vec3 cc = mix(cloud_dark, cloud_lit, under * sunside * (1.0 - smoothstep(0.1, 0.4, y) * 0.5));
	cc = mix(cc, mid_color * 0.8, smoothstep(0.2, 0.45, y) * 0.5);
	col = mix(col, cc, cl * 0.92);
	// the sun shines through the thin parts of the clouds
	col += sun_color * (disc * 3.2 + glow * (1.0 - cl * 0.6));
	// first stars high up
	vec2 sp = vec2(atan(d.x, -d.z) * 90.0, y * 90.0);
	float st = step(0.992, hash(floor(sp))) * smoothstep(0.22, 0.45, y) * (1.0 - cl);
	col += vec3(0.85, 0.9, 1.0) * st * (0.4 + 0.3 * sin(t * 1.7 + hash(floor(sp) + 4.0) * 6.28));
	// below the horizon: the smog haze of the factory district
	col = mix(col, haze_color, 1.0 - smoothstep(-0.03, 0.015, y));
	ALBEDO = col * brightness;
}
