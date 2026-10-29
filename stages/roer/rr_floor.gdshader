// Roer - the Upper Level plaza paving, fully procedural, times the baked light map (sun, lamps, fill).
//   * big granite slabs in two tones with fine speckle and thin joints, polished steel expansion strips
//   * a dark granite band along the railing at the drop
//   * an inlaid orbal-gear medallion behind the fighters: brass rings and ticks, a wedge rose, a gear at its heart
//   * the low sun glints off the polished stone (a soft sheen toward the sunset, only where the sun reaches)
shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_opaque, cull_back, shadows_disabled;

uniform sampler2D light_tex : hint_default_white, filter_linear, repeat_disable;
uniform float light_max = 4.0;
uniform float floor_gain = 1.0;
uniform float light_saturation = 0.8;
uniform vec2 floor_x = vec2(-40.0, 40.0);
uniform vec2 floor_z = vec2(-12.5, 22.0);
uniform vec2 center = vec2(0.0, -4.5);

group_uniforms colours;
uniform vec3 granite_a : source_color = vec3(0.6, 0.58, 0.55);
uniform vec3 granite_b : source_color = vec3(0.47, 0.46, 0.45);
uniform vec3 granite_dark : source_color = vec3(0.2, 0.2, 0.22);
uniform vec3 joint_color : source_color = vec3(0.25, 0.24, 0.24);
uniform vec3 steel : source_color = vec3(0.55, 0.58, 0.64);
uniform vec3 brass : source_color = vec3(0.86, 0.64, 0.32);
uniform float tile = 1.6;
uniform float strip_every = 8.0;

group_uniforms medallion;
uniform float med_r = 4.2;

group_uniforms sheen;
uniform vec3 sun_dir = vec3(0.06, 0.14, -0.99);
uniform vec3 sheen_color : source_color = vec3(1.0, 0.72, 0.46);
uniform float sheen = 0.45;

group_uniforms look;      // keep in sync with src/bake_roer.py
uniform float exposure = 0.2;
uniform float shoulder = 0.8;
uniform float saturation = 1.1;
uniform vec3 shadow_tint = vec3(0.84, 0.86, 1.16);
uniform vec3 highlight_tint = vec3(1.14, 0.98, 0.84);
uniform float tint_amount = 0.55;

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
float line(float d, float w) { return 1.0 - smoothstep(w * 0.5, w * 0.5 + 0.015, abs(d)); }

void fragment() {
	vec2 p = wpos.xz;
	vec2 luv = vec2((p.x - floor_x.x) / (floor_x.y - floor_x.x), 1.0 - (p.y - floor_z.x) / (floor_z.y - floor_z.x));
	vec3 light = pow(texture(light_tex, luv).rgb, vec3(2.2)) * light_max * floor_gain;
	float ll = dot(light, vec3(0.2126, 0.7152, 0.0722));
	light = vec3(ll) + (light - vec3(ll)) * light_saturation;
	// --- granite slabs: a 4 x 4 block pattern of two tones ---
	vec2 tc = floor(p / tile), tf = fract(p / tile);
	float joint = 1.0 - smoothstep(0.0, 0.012, min(min(tf.x, 1.0 - tf.x), min(tf.y, 1.0 - tf.y)));
	vec2 blk = mod(tc, 4.0);
	float ring = step(0.5, min(min(blk.x, 3.0 - blk.x), min(blk.y, 3.0 - blk.y)));   // inner 2 x 2 of each block
	vec3 alb = mix(granite_a, granite_b, ring);
	alb *= 0.94 + 0.1 * hash(tc) + 0.08 * (fbm(p * 0.6) - 0.5);
	float speck = step(0.83, hash(floor(p * 38.0)));
	alb = mix(alb, alb * 0.55, speck * 0.6);
	alb = mix(alb, joint_color, joint * 0.8);
	// polished steel expansion strips running toward the drop
	float sx = abs(fract(p.x / strip_every + 0.5) - 0.5) * strip_every;
	float strip = 1.0 - smoothstep(0.05, 0.07, sx);
	alb = mix(alb, steel, strip);
	// dark granite band along the railing
	alb = mix(alb, granite_dark * (0.9 + 0.2 * fbm(p * 2.0)), step(p.y, floor_z.x + 1.25));
	alb = mix(alb, brass, line(p.y - (floor_z.x + 1.3), 0.06));
	// --- the medallion ---
	vec2 q = p - center;
	float r = length(q), a = atan(q.y, q.x);
	if (r < med_r + 0.2) {
		float wedge = step(0.5, fract(a / 6.2831853 * 16.0));
		vec3 m = mix(granite_dark, granite_a * 1.05, wedge);
		m = mix(m, granite_dark * 1.2, step(med_r - 0.8, r));
		float tick = step(med_r - 0.75, r) * step(r, med_r - 0.15) * line(fract(a / 6.2831853 * 32.0) - 0.5, 0.08 * 6.2831853 / 32.0 / max(r, 0.1) * 3.0);
		m = mix(m, brass, tick);
		// the gear at the heart
		float teeth = 1.05 + 0.18 * step(0.0, sin(a * 12.0));
		float gear = step(r, teeth) * step(0.55, r);
		m = mix(m, brass * 0.9, gear);
		m = mix(m, granite_a, step(r, 0.42));
		m = mix(m, brass, line(r - 0.42, 0.05));
		alb = mix(alb, m, step(r, med_r));
		float rings = max(max(line(r - med_r, 0.08), line(r - (med_r - 0.15), 0.04)), line(r - (med_r - 0.8), 0.05));
		alb = mix(alb, brass, rings);
	}
	vec3 lin = alb * light;
	// sunset sheen on the polished stone where the sun reaches
	vec3 v = normalize(wpos - CAMERA_POSITION_WORLD);
	vec3 rv = vec3(v.x, -v.y, v.z);
	float s = pow(max(dot(rv, normalize(sun_dir)), 0.0), 36.0);
	float sunlit = smoothstep(0.25, 0.7, ll);
	lin += sheen_color * s * sheen * sunlit * (0.6 + 0.4 * strip + 0.3 * (1.0 - speck));
	ALBEDO = grade(lin);
}
