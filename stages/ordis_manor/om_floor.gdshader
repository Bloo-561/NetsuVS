// Ordis Royal Manor - the polished marble floor, fully procedural, times the baked light map.
//   * warm marble tiles with soft clouds and fine veins, thin grout lines
//   * gold inlays: a double octagon around the hall, an inner octagon band, a rosette medallion behind
//     the fighters and an ornamental band across the hall
//   * Ruined (damage = 1): impact craters of cracks with embers glowing inside, scorch, dust and grit
// Drawn semi-transparent over the mirrored "Reflection" copy for the mirror shine. Visual only.
shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_opaque, cull_back, shadows_disabled;

uniform sampler2D light_tex : hint_default_white, filter_linear, repeat_disable;
uniform float light_max = 4.0;
uniform float floor_gain = 1.0;
uniform float light_saturation = 0.7;
uniform vec2 floor_x = vec2(-26.0, 26.0);
uniform vec2 floor_z = vec2(-28.5, 18.0);
uniform vec2 center = vec2(0.0, -8.0);

group_uniforms colours;
uniform vec3 marble_a : source_color = vec3(0.6, 0.54, 0.46);
uniform vec3 marble_b : source_color = vec3(0.45, 0.4, 0.34);
uniform vec3 vein_color : source_color = vec3(0.36, 0.31, 0.27);
uniform vec3 band_fill : source_color = vec3(0.3, 0.24, 0.2);
uniform vec3 gold : source_color = vec3(0.9, 0.66, 0.28);
uniform float gold_glow = 0.12;          // gold lines catch the light (a little added shine)
uniform float tile = 2.5;

group_uniforms layout;
uniform float oct_outer = 13.0;          // apothem of the big double octagon
uniform float oct_inner = 7.0;           // inner octagon band
uniform float medallion_r = 2.0;
uniform vec2 band_z = vec2(-3.4, -2.6);  // the ornamental band across the hall

group_uniforms ruin;
uniform float damage : hint_range(0.0, 1.0) = 0.0;
uniform float ember_glow = 1.0;
uniform vec3 ember_color : source_color = vec3(1.0, 0.42, 0.12);

group_uniforms look;      // keep in sync with src/bake_ordis_manor.py
uniform float exposure = 0.25;
uniform float shoulder = 0.8;
uniform float saturation = 1.08;
uniform vec3 shadow_tint = vec3(0.92, 0.9, 1.06);
uniform vec3 highlight_tint = vec3(1.06, 1.0, 0.9);
uniform float tint_amount = 0.5;

group_uniforms reflection;
uniform float alpha_near : hint_range(0.0, 1.0) = 0.7;
uniform float alpha_far : hint_range(0.0, 1.0) = 0.42;

// impact centres (x, z, radius) and scorch spots (x, z, radius) for the Ruined hall
const vec3 IMPACTS[6] = vec3[6](vec3(-5.5, -12.5, 4.0), vec3(7.0, -10.8, 3.5), vec3(-1.5, 1.5, 3.0),
                                vec3(9.5, 3.5, 2.6), vec3(-11.0, -2.0, 3.0), vec3(2.0, -19.0, 3.5));
const vec3 SCORCH[10] = vec3[10](vec3(-14.6, -18.9, 3.5), vec3(15.0, -19.2, 3.8), vec3(-21.5, -13.4, 3.2), vec3(22.0, -14.0, 3.0),
                                 vec3(5.6, -25.2, 2.8), vec3(-9.6, -25.3, 2.6), vec3(11.3, -23.0, 3.0), vec3(-16.0, 4.4, 2.8),
                                 vec3(-6.0, -12.8, 2.4), vec3(7.2, -11.0, 2.2));

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
// distance to the nearest Voronoi edge (cracks)
float vedge(vec2 p) {
	vec2 i = floor(p), f = fract(p);
	float d1 = 8.0, d2 = 8.0;
	for (int y = -1; y <= 1; y++) for (int x = -1; x <= 1; x++) {
		vec2 g = vec2(float(x), float(y));
		vec2 o = hash2(i + g);
		float d = length(g + o - f);
		if (d < d1) { d2 = d1; d1 = d; } else if (d < d2) { d2 = d; }
	}
	return d2 - d1;
}
float oct(vec2 q) { q = abs(q); return max(max(q.x, q.y), (q.x + q.y) * 0.70710678); }
float line(float d, float w) { return 1.0 - smoothstep(w * 0.5, w * 0.5 + 0.02, abs(d)); }

void fragment() {
	vec2 p = wpos.xz;
	vec2 luv = vec2((p.x - floor_x.x) / (floor_x.y - floor_x.x), 1.0 - (p.y - floor_z.x) / (floor_z.y - floor_z.x));
	vec3 light = pow(texture(light_tex, luv).rgb, vec3(2.2)) * light_max * floor_gain;
	float ll = dot(light, vec3(0.2126, 0.7152, 0.0722));
	light = vec3(ll) + (light - vec3(ll)) * light_saturation;
	vec2 q = p - center;
	// --- marble tiles ---
	vec2 tc = floor(q / tile);
	vec2 tf = q / tile - tc;
	float grout = 1.0 - smoothstep(0.0, 0.008, min(min(tf.x, 1.0 - tf.x), min(tf.y, 1.0 - tf.y)));
	float cloud = fbm(p * 0.35 + hash(tc) * 7.0);
	vec3 alb = mix(marble_b, marble_a, smoothstep(0.25, 0.75, cloud)) * (0.96 + 0.08 * hash(tc + 3.1));
	float vn = fbm(p * vec2(0.5, 0.32) + vec2(fbm(p * 0.6) * 2.5, 0.0));
	alb = mix(alb, vein_color, (1.0 - smoothstep(0.0, 0.018, abs(vn - 0.5))) * 0.55);
	alb *= 1.0 - grout * 0.35;
	// --- gold inlays ---
	float g = 0.0, fill = 0.0;
	float o = oct(q);
	g = max(g, line(o - oct_outer, 0.1)); g = max(g, line(o - (oct_outer - 0.55), 0.06));
	g = max(g, line(o - oct_inner, 0.08)); g = max(g, line(o - (oct_inner - 0.7), 0.08));
	fill = max(fill, step(oct_inner - 0.7, o) * step(o, oct_inner) * 0.85);
	// diamonds inside the inner octagon band
	float ang = atan(q.y, q.x);
	float seg = fract(ang / 6.2831853 * 48.0) - 0.5;
	float rr = (o - (oct_inner - 0.35)) / 0.3;
	g = max(g, line(abs(seg) * 1.6 + abs(rr) - 0.45, 0.07) * step(abs(rr), 1.0));
	// the rosette medallion
	float r = length(q);
	g = max(g, line(r - medallion_r, 0.09)); g = max(g, line(r - (medallion_r - 0.18), 0.05));
	g = max(g, step(r, 0.32));
	float ray = abs(fract(ang / 6.2831853 * 16.0) - 0.5);
	float petal = smoothstep(0.0, 0.5, ray) * 1.8;
	g = max(g, line(r - (0.5 + petal * (medallion_r - 0.75)), 0.06) * step(r, medallion_r - 0.2));
	g = max(g, line(ray, 0.025 * 16.0 / max(r, 0.4)) * step(0.4, r) * step(r, medallion_r - 0.2) * 0.9);
	fill = max(fill, step(r, medallion_r - 0.18) * 0.35);
	// the band across the hall: border lines, dark fill and a chain of gold diamonds
	float bz = (p.y - band_z.x) / (band_z.y - band_z.x);
	float inband = step(0.0, bz) * step(bz, 1.0);
	g = max(g, (line(bz, 0.12) + line(bz - 1.0, 0.12)) * step(-0.2, bz) * step(bz, 1.2));
	fill = max(fill, inband);
	float bx = fract(p.x / 0.9) - 0.5;
	g = max(g, inband * line(abs(bx) * 1.8 + abs(bz - 0.5) * 1.1 - 0.42, 0.09));
	g = max(g, inband * step(abs(bx) * 1.8 + abs(bz - 0.5) * 1.1, 0.16));
	alb = mix(alb, band_fill * (0.85 + 0.3 * cloud), fill * (1.0 - g));
	alb = mix(alb, gold * (0.85 + 0.3 * vnoise(p * 3.0)), clamp(g, 0.0, 1.0));
	vec3 col = grade(alb * light) + gold * clamp(g, 0.0, 1.0) * gold_glow * (0.6 + 0.4 * ll);
	float alpha_add = g * 0.12;
	// --- Ruined: cracks, embers, scorch, grit ---
	if (damage > 0.0) {
		float crack = 0.0, glowm = 0.0;
		for (int k = 0; k < 6; k++) {
			vec2 d = p - IMPACTS[k].xy; float R = IMPACTS[k].z;
			float fall = 1.0 - smoothstep(R * 0.35, R, length(d) + (fbm(p * 0.7 + float(k)) - 0.5) * R * 0.6);
			vec2 w = p * 0.9 + vec2(fbm(p * 1.3 + float(k)), fbm(p * 1.3 - float(k))) * 1.2;
			float e = vedge(w);
			float c = (1.0 - smoothstep(0.015, 0.05, e)) * fall;
			float sa = atan(d.y, d.x) / 6.2831853 * 11.0 + fbm(d * 0.8 + float(k)) * 0.7;
			float rad = abs(fract(sa) - 0.5);
			float reach = R * (0.45 + 0.7 * hash(vec2(floor(sa), float(k))));
			c = max(c, (1.0 - smoothstep(0.012, 0.035, rad * length(d) * 0.57)) * (1.0 - smoothstep(reach * 0.6, reach, length(d))));
			crack = max(crack, c);
			glowm = max(glowm, c * (1.0 - smoothstep(0.0, R * 0.55, length(d))));
		}
		float soot = 0.0;
		for (int k = 0; k < 10; k++) {
			float dd = length(p - SCORCH[k].xy) / SCORCH[k].z;
			soot = max(soot, (1.0 - smoothstep(0.3, 1.0, dd + (fbm(p * 0.9 + float(k) * 3.0) - 0.5) * 0.7)));
		}
		soot = max(soot, smoothstep(0.62, 0.85, fbm(p * 0.18 + 4.0)) * 0.6);
		float grit = step(0.985, hash(floor(p * 9.0))) * (0.5 + 0.5 * hash(floor(p * 9.0) + 1.7));
		col = mix(col, vec3(0.04, 0.03, 0.025), soot * 0.82 * damage);
		col = mix(col, vec3(0.08, 0.06, 0.05), grit * 0.7 * damage);
		col = mix(col, vec3(0.03, 0.02, 0.015), crack * 0.95 * damage);
		float pulse = 0.65 + 0.35 * sin(TIME * 2.2 + p.x * 1.3) * sin(TIME * 1.3 + p.y);
		float hot = glowm * smoothstep(0.35, 0.75, fbm(p * 0.5 + TIME * 0.05));
		col += ember_color * hot * ember_glow * pulse * damage * 1.6;
		alpha_add += (soot * 0.5 + crack * 0.6 + grit * 0.4) * damage;
	}
	ALBEDO = col;
	float ndv = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	ALPHA = clamp(mix(alpha_near, alpha_far, pow(1.0 - ndv, 3.0)) + alpha_add, 0.0, 1.0);
}
