// Celdic - the ground, fully procedural, times the baked light map (sun, shade, firelight).
//   * warm golden cobbles over the whole square: irregular rounded stones, dark joints with grass in them
//   * the round well plaza: concentric rings of dressed paving slabs inside the curb (Refs 2, 6, 8)
//   * a worn, lighter path through the middle and toward the gate; packed dirt in the Grand Market (Ref 4)
//   * grass and dirt outside the fences and at the edges of the square
//   * burning: soot patches, blast marks, embers glowing in the joints, the firelight flickering
shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_opaque, cull_back, shadows_disabled;

uniform sampler2D light_tex : hint_default_white, filter_linear, repeat_disable;
uniform float light_max = 4.0;
uniform float floor_gain = 0.8;
uniform vec3 floor_ambient : source_color = vec3(0.0);
uniform float light_saturation = 0.9;
uniform vec2 floor_x = vec2(-50.0, 50.0);
uniform vec2 floor_z = vec2(-72.0, 22.0);

group_uniforms layout;
uniform vec2 ring_centre = vec2(0.0, -19.0);
uniform float ring_radius = 8.5;
uniform float gate_z = -33.0;

group_uniforms colours;
uniform vec3 cobble_a : source_color = vec3(0.66, 0.58, 0.46);
uniform vec3 cobble_b : source_color = vec3(0.52, 0.5, 0.46);
uniform vec3 cobble_c : source_color = vec3(0.64, 0.62, 0.57);
uniform vec3 joint_color : source_color = vec3(0.4, 0.36, 0.28);
uniform vec3 slab_color : source_color = vec3(0.7, 0.64, 0.52);
uniform vec3 dirt : source_color = vec3(0.5, 0.4, 0.28);
uniform vec3 grass_a : source_color = vec3(0.3, 0.44, 0.17);
uniform vec3 grass_b : source_color = vec3(0.44, 0.54, 0.22);
uniform float sett = 0.15;
uniform float grass_amount = 1.0;

group_uniforms damage;
uniform float scorch = 0.0;
uniform vec3 soot_color : source_color = vec3(0.06, 0.05, 0.05);
uniform float ember_glow = 0.0;
uniform vec3 ember_color : source_color = vec3(1.0, 0.35, 0.08);
uniform float crater_strength = 0.0;
const vec4 CRATERS[5] = vec4[5](vec4(-9.5, -13.5, 2.4, 1.0), vec4(10.5, -24.0, 2.8, 1.0), vec4(-17.5, -3.0, 2.2, 1.0),
                                vec4(18.0, -8.0, 2.0, 1.0), vec4(5.0, -38.5, 3.0, 1.0));

group_uniforms fire;
uniform float flicker = 0.0;
uniform float flicker_speed = 9.0;

group_uniforms look;      // keep in sync with LOOKS in src/bake_celdic.py
uniform float exposure = 0.35;
uniform float shoulder = 0.8;
uniform float saturation = 1.1;
uniform vec3 shadow_tint = vec3(0.9, 0.92, 1.1);
uniform vec3 highlight_tint = vec3(1.06, 1.0, 0.92);
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
	for (int i = 0; i < 5; i++) { s += vnoise(p) * a; p = mat2(vec2(0.8, 0.6), vec2(-0.6, 0.8)) * p * 2.03 + 1.7; a *= 0.5; }
	return s / 0.97;
}
// Voronoi: x = distance to the nearest centre, y = distance to the edge, zw = cell id
vec4 voro(vec2 p) {
	vec2 i = floor(p), f = fract(p);
	float d1 = 8.0, d2 = 8.0; vec2 id = vec2(0.0);
	for (int y = -1; y <= 1; y++) for (int x = -1; x <= 1; x++) {
		vec2 g = vec2(float(x), float(y));
		vec2 o = 0.15 + 0.7 * hash2(i + g);
		float d = length(g + o - f);
		if (d < d1) { d2 = d1; d1 = d; id = i + g; } else if (d < d2) { d2 = d; }
	}
	return vec4(d1, d2 - d1, id);
}

void fragment() {
	vec2 p = wpos.xz;
	vec2 luv = vec2((p.x - floor_x.x) / (floor_x.y - floor_x.x), 1.0 - (p.y - floor_z.x) / (floor_z.y - floor_z.x));
	vec3 light = pow(texture(light_tex, luv).rgb, vec3(2.2)) * light_max * floor_gain + floor_ambient;
	float ll = dot(light, vec3(0.2126, 0.7152, 0.0722));
	light = vec3(ll) + (light - vec3(ll)) * light_saturation;
	float en = fbm(p * 0.35) - 0.5;
	// --- cobbles ---
	vec2 cp = p / sett + vec2(fbm(p * 0.45), fbm(p * 0.45 + 4.0)) * 0.7 + vec2(fbm(p * 2.2), fbm(p * 2.2 + 7.0)) * 0.25;
	vec4 v = voro(cp);
	float hv = hash(v.zw);
	vec3 cob = hv < 0.45 ? mix(cobble_b, cobble_a, hv / 0.45) : mix(cobble_a, cobble_c, (hv - 0.45) / 0.55);
	cob *= 0.88 + 0.18 * fbm(p * 0.5) + 0.08 * (hash(v.zw + 3.0) - 0.5);
	cob = mix(cob, cob * vec3(0.92, 0.88, 0.8), smoothstep(0.5, 0.75, fbm(p * 0.18 + 3.0)) * 0.6);      // patches of dirt
	cob *= 0.9 + 0.12 * smoothstep(0.0, 0.55, 1.0 - v.x);                         // softly rounded tops
	vec4 vl = voro(cp + vec2(-0.09, -0.07));                                     // bevelled edges: lit on the sun side,
	float bev = (hash(vl.zw) == hash(v.zw)) ? clamp((vl.x - v.x) * 2.2, -1.0, 1.0) : -0.6;   // shaded on the far side
	cob *= 1.0 + 0.12 * bev * (1.0 - smoothstep(0.0, 0.25, v.y) * 0.0);
	float gap = 1.0 - smoothstep(0.02, 0.07, v.y);
	vec3 jc = mix(joint_color * (0.85 + 0.3 * fbm(p * 3.0)), grass_a * 0.8, smoothstep(0.55, 0.75, fbm(p * 0.7 + 2.0)) * grass_amount * 0.8);
	cob = mix(cob, mix(cob, grass_a, 0.35), smoothstep(0.7, 0.85, fbm(p * 0.5 + 11.0)) * smoothstep(0.2, 0.6, v.x) * grass_amount * 0.5);   // a little moss
	vec3 alb = mix(cob, jc, gap);
	float far_aa = clamp(length(fwidth(cp)) * 1.6 - 0.35, 0.0, 1.0);          // fade the stones to their average in the distance (no shimmer)
	alb = mix(alb, mix(cobble_b, cobble_a, 0.55) * 0.9, far_aa * 0.85);
	// a worn lighter path: across the lane and on toward the gate
	float worn = (1.0 - smoothstep(4.0, 9.0, abs(p.y + 1.0) + en * 3.0)) * 0.5
	           + (1.0 - smoothstep(2.5, 5.0, abs(p.x) + en * 2.0)) * step(p.y, -10.0) * step(gate_z, p.y) * 0.35;
	alb = mix(alb, alb * 1.08 + vec3(0.03, 0.025, 0.01), clamp(worn, 0.0, 1.0) * (1.0 - gap));
	// --- the well plaza: rings of dressed slabs inside the curb ---
	vec2 d = p - ring_centre;
	float r = length(d);
	float ang = atan(d.x, d.y);
	float rw = 0.9;                                                               // ring width
	float ri = floor(r / rw);
	float seg = max(6.0, floor(6.2831 * (ri + 0.5) * rw / 1.1));                 // slabs about 1.1 m long
	float a01 = fract(ang / 6.2831 + hash(vec2(ri, 1.0)));
	float si = floor(a01 * seg);
	float fr = fract(r / rw), fa = fract(a01 * seg);
	float jr = min(fr, 1.0 - fr) * rw, ja = min(fa, 1.0 - fa) * 6.2831 * max(r, 0.5) / seg;
	float sj = 1.0 - smoothstep(0.025, 0.06, min(jr, ja));
	vec3 slab = slab_color * (0.88 + 0.18 * hash(vec2(ri, si))) * (0.9 + 0.14 * fbm(p * 1.4));
	if (mod(ri, 3.0) > 1.5) { slab *= vec3(1.02, 0.96, 0.9); }
	slab = mix(slab, joint_color * 1.1, sj);
	float inside = 1.0 - smoothstep(ring_radius - 0.05, ring_radius + 0.05, r);
	alb = mix(alb, slab, inside);
	// --- the Grand Market: packed dirt with stones showing through ---
	float mk = smoothstep(gate_z - 0.4, gate_z - 1.6, p.y);
	vec3 dr = dirt * (0.82 + 0.3 * fbm(p * 0.8)) * (0.92 + 0.1 * vnoise(p * 9.0));
	dr = mix(dr, cob * 0.9, smoothstep(0.55, 0.75, fbm(p * 0.4 + 9.0)) * 0.6);
	alb = mix(alb, dr, mk);
	// --- grass outside the fences and at the edges ---
	float gz = smoothstep(14.0, 15.2, abs(p.x) + en * 1.4) * step(-11.5, p.y)
	         + smoothstep(26.0, 29.0, abs(p.x) + en * 3.0)
	         + smoothstep(-60.0, -64.0, p.y + en * 3.0)
	         + smoothstep(12.0, 14.0, abs(p.x) + en * 2.0) * mk;
	vec3 gr = mix(grass_a, grass_b, smoothstep(0.3, 0.7, fbm(p * 0.15))) * (0.82 + 0.3 * vnoise(p * vec2(26.0, 9.0)));
	alb = mix(alb, gr, clamp(gz, 0.0, 1.0) * grass_amount);
	alb = mix(alb, mix(gr, dirt, 0.5), clamp(gz, 0.0, 1.0) * (1.0 - grass_amount));
	// --- fire flicker: only where the baked light is warm (near the flames) ---
	float warm = clamp((light.r - light.b) * 1.2, 0.0, 1.0);
	float t = TIME * flicker_speed;
	float fl = (vnoise(vec2(t, p.x * 0.05)) * 0.6 + vnoise(vec2(t * 2.3, p.y * 0.05 + 7.0)) * 0.4 - 0.5) * 2.0;
	light *= 1.0 + flicker * warm * fl;
	// --- soot, blast marks, embers (burning) ---
	float sn = fbm(p * 0.2);
	float burn = smoothstep(0.7 - scorch * 0.3, 0.76 - scorch * 0.2, sn) * step(0.001, scorch);
	burn *= 1.0 - 0.6 * (1.0 - smoothstep(1.5, 4.0, abs(p.y)));
	for (int i = 0; i < 5; i++) {
		vec2 c = CRATERS[i].xy; float rad = CRATERS[i].z;
		float dd = length(p - c) / rad;
		float ray = 0.75 + 0.25 * sin(atan(p.y - c.y, p.x - c.x) * 9.0 + float(i) * 2.0);
		burn = max(burn, (1.0 - smoothstep(0.4 * ray, 1.0 * ray, dd)) * CRATERS[i].w * crater_strength);
	}
	vec3 col = grade(alb * light);
	col = mix(col, soot_color * (0.7 + 0.6 * vnoise(p * 3.0)), burn * 0.85);
	float em = gap * burn * ember_glow * (0.55 + 0.45 * vnoise(vec2(TIME * 2.5, p.x * 2.0 + p.y)));
	col += ember_color * em;
	ALBEDO = col;
}
