// Septian Chapel - the ground, fully procedural, times the baked light map (sun, shade of the oak and buildings).
//   * a meadow: two greens in soft patches, fine blades, wildflowers, gusts of wind rolling across as lighter bands
//   * the cobbled churchyard square in front of the chapel (rounded setts, mossy joints, worn edges)
//   * a flagstone path to the chapel steps, dirt paths to the rectory gate and the lychgate
//   * dark soil in the statue's flower ring, a worn patch under the oak, straw by the hay bales
shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_opaque, cull_back, shadows_disabled;

uniform sampler2D light_tex : hint_default_white, filter_linear, repeat_disable;
uniform float light_max = 4.0;
uniform float floor_gain = 1.0;
uniform float light_saturation = 0.85;
uniform vec2 floor_x = vec2(-60.0, 60.0);
uniform vec2 floor_z = vec2(-80.0, 22.0);

group_uniforms layout;
uniform vec2 square_center = vec2(0.0, -6.0);
uniform vec2 square_radii = vec2(13.5, 10.5);
uniform vec2 statue = vec2(-6.6, -17.0);
uniform vec2 oak = vec2(-15.5, -6.5);
uniform float facade_z = -28.0;

group_uniforms colours;
uniform vec3 grass_a : source_color = vec3(0.3, 0.46, 0.17);
uniform vec3 grass_b : source_color = vec3(0.42, 0.56, 0.22);
uniform vec3 grass_dry : source_color = vec3(0.58, 0.58, 0.3);
uniform vec3 cobble_a : source_color = vec3(0.56, 0.53, 0.48);
uniform vec3 cobble_b : source_color = vec3(0.44, 0.42, 0.39);
uniform vec3 joint_color : source_color = vec3(0.2, 0.24, 0.14);
uniform vec3 flag_color : source_color = vec3(0.64, 0.6, 0.53);
uniform vec3 dirt : source_color = vec3(0.44, 0.35, 0.24);
uniform vec3 soil : source_color = vec3(0.24, 0.17, 0.11);
uniform vec3 straw : source_color = vec3(0.78, 0.66, 0.36);
uniform float sett = 0.24;

group_uniforms wind;
uniform vec2 wind_dir = vec2(1.0, 0.35);
uniform float gusts = 0.12;

group_uniforms look;      // keep in sync with src/bake_septian_chapel.py
uniform float exposure = 0.0;
uniform float shoulder = 0.82;
uniform float saturation = 1.05;
uniform vec3 shadow_tint = vec3(0.88, 0.94, 1.12);
uniform vec3 highlight_tint = vec3(1.06, 1.0, 0.9);
uniform float tint_amount = 0.5;

varying vec3 wpos;
void vertex() { wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz; }

vec3 grade(vec3 lin) {
	vec3 c = max(lin, vec3(0.0)) * exp2(exposure);
	vec3 over = max(c - vec3(shoulder), vec3(0.0));
	vec3 soft = vec3(shoulder) + (1.0 - shoulder) * (1.0 - exp(-over / (1.0 - shoulder)));
	c = mix(c, soft, step(vec3(shoulder), c));
	float lum = dot(c, vec3(0.2126, 0.7152, 0.0722));
	c = vec3(lum) + (c - vec3(lum)) * saturation;
	float sh = pow(clamp(1.0 - lum / 0.45, 0.0, 1.0), 1.5) * tint_amount;
	float hi = clamp((lum - 0.5) / 0.5, 0.0, 1.0) * tint_amount;
	c *= (1.0 - sh) + sh * shadow_tint;
	c *= (1.0 - hi) + hi * highlight_tint;
	return clamp(c, 0.0, 1.0);
}
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
vec2 hash2(vec2 p) { return fract(sin(vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)))) * 43758.5453); }
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
// Voronoi: x = distance to the nearest centre, y = distance to the edge, zw = cell id
vec4 voro(vec2 p) {
	vec2 i = floor(p), f = fract(p);
	float d1 = 8.0, d2 = 8.0; vec2 id = vec2(0.0);
	for (int y = -1; y <= 1; y++) for (int x = -1; x <= 1; x++) {
		vec2 g = vec2(float(x), float(y));
		vec2 o = 0.2 + 0.6 * hash2(i + g);
		float d = length(g + o - f);
		if (d < d1) { d2 = d1; d1 = d; id = i + g; } else if (d < d2) { d2 = d; }
	}
	return vec4(d1, d2 - d1, id);
}
float seg_dist(vec2 p, vec2 a, vec2 b) {
	vec2 pa = p - a, ba = b - a;
	float t = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
	return length(pa - ba * t);
}

void fragment() {
	vec2 p = wpos.xz;
	vec2 luv = vec2((p.x - floor_x.x) / (floor_x.y - floor_x.x), 1.0 - (p.y - floor_z.x) / (floor_z.y - floor_z.x));
	vec3 light = pow(texture(light_tex, luv).rgb, vec3(2.2)) * light_max * floor_gain;
	float ll = dot(light, vec3(0.2126, 0.7152, 0.0722));
	light = vec3(ll) + (light - vec3(ll)) * light_saturation;
	float edge_n = fbm(p * 0.45) - 0.5;
	// --- meadow ---
	float patch = fbm(p * 0.12);
	vec3 alb = mix(grass_a, grass_b, smoothstep(0.3, 0.7, patch));
	alb = mix(alb, grass_dry, smoothstep(0.62, 0.8, fbm(p * 0.05 + 7.0)) * 0.5);
	float blades = vnoise(p * vec2(26.0, 9.0) + vec2(vnoise(p * 3.0) * 2.0, 0.0));
	alb *= 0.82 + 0.3 * blades;
	float gust = smoothstep(0.55, 1.0, sin(dot(p, normalize(wind_dir)) * 0.3 - TIME * 1.3) * 0.5 + 0.5) * smoothstep(0.35, 0.7, fbm(p * 0.08 - normalize(wind_dir) * TIME * 0.4));
	alb = mix(alb, alb * 1.25 + vec3(0.03, 0.03, 0.0), gust * gusts * 4.0 * 0.25);
	vec2 fc = floor(p * 3.0);
	float fl = hash(fc);
	vec2 fo = fract(p * 3.0) - 0.5 - (hash2(fc + 3.0) - 0.5) * 0.6;
	if (fl > 0.94 && length(fo) < 0.08) {
		alb = fl > 0.985 ? vec3(0.6, 0.42, 0.8) : (fl > 0.965 ? vec3(0.95, 0.82, 0.25) : vec3(0.93, 0.92, 0.88));
	}
	// --- worn patch under the oak, straw by the hay ---
	float od = length(p - oak);
	alb = mix(alb, mix(dirt, grass_a, smoothstep(0.3, 0.7, fbm(p * 1.3))), (1.0 - smoothstep(1.6, 3.2, od + edge_n * 1.5)) * 0.7);
	float hay = 1.0 - smoothstep(2.0, 4.0, length((p - vec2(17.0, 5.2)) * vec2(0.8, 1.0)) + edge_n * 1.5);
	alb = mix(alb, straw * (0.8 + 0.3 * vnoise(p * vec2(30.0, 6.0))), hay * 0.65);
	// --- dirt paths: to the rectory gate and to the lychgate ---
	float dp = min(min(seg_dist(p, vec2(-8.6, -11.5), vec2(-15.2, -13.4)), seg_dist(p, vec2(-15.2, -13.4), vec2(-15.2, -17.0))),
	               seg_dist(p, vec2(9.0, -10.5), vec2(16.0, -13.8)));
	float path = 1.0 - smoothstep(0.6, 0.95, dp + edge_n * 0.35);
	alb = mix(alb, dirt * (0.85 + 0.3 * fbm(p * 2.5)) * (0.9 + 0.2 * vnoise(p * 12.0)), path);
	// --- the cobbled square ---
	vec2 e = (p - square_center) / square_radii;
	float sq = 1.0 - smoothstep(0.97, 1.03, length(e) + edge_n * 0.08);
	// flagstone path to the steps
	float fp = step(abs(p.x), 2.3 + edge_n * 0.1) * step(p.y, -13.0) * step(facade_z + 0.4, p.y);
	vec4 v = voro(p / sett);
	vec3 cob = mix(cobble_b, cobble_a, hash(v.zw)) * (0.9 + 0.15 * fbm(p * 0.7));
	cob *= 0.82 + 0.25 * smoothstep(0.0, 0.5, 1.0 - v.x);                  // rounded, polished tops
	float gap = 1.0 - smoothstep(0.03, 0.09, v.y);
	cob = mix(cob, mix(joint_color, dirt * 0.6, fbm(p * 2.0)), gap);
	// flagstones: big rectangular slabs
	vec2 fs = p / vec2(1.15, 0.8); vec2 fsi = floor(fs + vec2(0.5 * mod(floor(fs.y), 2.0), 0.0));
	vec2 fsf = fract(fs + vec2(0.5 * mod(floor(fs.y), 2.0), 0.0));
	vec3 flag = flag_color * (0.85 + 0.2 * hash(fsi)) * (0.92 + 0.12 * fbm(p * 1.5));
	flag = mix(flag, joint_color, 1.0 - smoothstep(0.0, 0.04, min(min(fsf.x, 1.0 - fsf.x), min(fsf.y, 1.0 - fsf.y))));
	alb = mix(alb, cob, sq * (1.0 - fp));
	alb = mix(alb, flag, fp);
	// grass creeping into the joints near the edge of the square
	alb = mix(alb, grass_a * 0.9, sq * gap * smoothstep(0.75, 1.0, length(e)) * 0.8);
	// --- soil of the statue's flower ring ---
	float sr = length(p - statue);
	alb = mix(alb, soil * (0.8 + 0.3 * fbm(p * 4.0)), 1.0 - step(2.36, sr));
	alb = mix(alb, alb * 0.6, (1.0 - smoothstep(2.6, 3.0, sr)) * step(2.36, sr) * 0.5);
	ALBEDO = grade(alb * light);
}
