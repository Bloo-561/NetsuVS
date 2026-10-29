// Septian Chapel - the summer afternoon sky (visual only), drawn from the VIEW DIRECTION so it sits at infinity.
// Pale and hazy at the horizon, deep blue overhead, big fair-weather cumulus drifting slowly: bright sunlit tops
// (the sun is behind the camera, on the right), soft blue-grey bases, a warmer glow on the sunny side.
shader_type spatial;
render_mode unshaded, cull_disabled, shadows_disabled, fog_disabled, depth_draw_opaque;

uniform vec3 sun_dir = vec3(0.45, 0.62, 0.64);            // toward the sun (opposite of the bake's light travel)
uniform vec3 horizon_color : source_color = vec3(0.86, 0.9, 0.95);
uniform vec3 low_color : source_color = vec3(0.62, 0.77, 0.94);
uniform vec3 high_color : source_color = vec3(0.3, 0.5, 0.86);
uniform vec3 cloud_lit : source_color = vec3(1.0, 0.98, 0.94);
uniform vec3 cloud_shade : source_color = vec3(0.6, 0.68, 0.82);
uniform vec2 wind = vec2(0.0025, 0.0006);
uniform float coverage = 0.5;
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
	float y = d.y;
	vec3 col = mix(horizon_color, low_color, smoothstep(0.0, 0.1, y));
	col = mix(col, high_color, smoothstep(0.08, 0.5, y));
	float sunward = 0.5 + 0.5 * dot(normalize(d.xz + vec2(0.0001)), normalize(sun_dir.xz));
	col *= mix(vec3(1.0), vec3(1.04, 1.01, 0.96), sunward * (1.0 - smoothstep(0.0, 0.25, y)));
	// cumulus on a curved layer: heaped shapes, sunlit tops, flat shaded bases
	float yy = max(y, 0.0) + 0.06;
	vec2 cp = d.xz / yy * 0.42 + wind * TIME * 10.0;
	float n = fbm(cp * 1.1 + vec2(fbm(cp * 0.6) * 0.8, 0.0));
	float shape = smoothstep(1.0 - coverage, 1.0 - coverage + 0.18, n);
	float n2 = fbm(cp * 1.1 + vec2(0.05, 0.09) + vec2(fbm(cp * 0.6) * 0.8, 0.0));
	float lit = clamp(0.55 + (n - n2) * 6.0, 0.0, 1.0);
	vec3 cc = mix(cloud_shade, cloud_lit, lit);
	cc = mix(cc, horizon_color, (1.0 - smoothstep(0.0, 0.12, y)) * 0.55);       // distant clouds sink into the haze
	col = mix(col, cc, shape * smoothstep(0.0, 0.03, y));
	col = mix(col, horizon_color * 0.98, 1.0 - smoothstep(-0.05, 0.01, y));
	ALBEDO = col * brightness;
}
