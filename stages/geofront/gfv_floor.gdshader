// The GeoFront (vault) - the steel floor, fully procedural, times the baked light map.
//   * diamond-plate steel: big plates (polar around the grate, a grid further out), seams and rivets,
//     the raised tread catching the light
//   * the round grate behind the fighters: diamond mesh over a blue glow that breathes up from below,
//     six red spokes, a yellow / black hazard ring and a steel rim
//   * a band of vents and a hazard stripe across the front
// Drawn semi-transparent over the mirrored "Reflection" copy; the raised tread breaks the reflection up.
// Visual only.
shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_opaque, cull_back, shadows_disabled;

uniform sampler2D light_tex : hint_default_white, filter_linear, repeat_disable;
uniform float light_max = 4.0;
uniform float floor_gain = 1.0;
uniform float light_saturation = 0.42;
uniform vec2 floor_x = vec2(-26.0, 26.0);
uniform vec2 floor_z = vec2(-31.5, 18.0);

group_uniforms colours;
uniform vec3 steel : source_color = vec3(0.47, 0.5, 0.55);
uniform vec3 seam_color : source_color = vec3(0.05, 0.06, 0.07);
uniform vec3 hole_color : source_color = vec3(0.015, 0.02, 0.035);
uniform vec3 under_glow : source_color = vec3(0.12, 0.38, 1.0);
uniform vec3 hazard_yellow : source_color = vec3(0.86, 0.63, 0.12);
uniform vec3 red_line : source_color = vec3(0.55, 0.1, 0.07);

group_uniforms layout;
uniform vec2 grate_c = vec2(0.0, -10.0);
uniform float grate_r = 6.2;
uniform float ring_w = 0.65;
uniform float rim_w = 0.3;
uniform vec2 vent_z = vec2(0.85, 1.5);
uniform vec2 stripe_z = vec2(1.62, 2.3);

group_uniforms animation;
uniform float glow_strength = 0.8;
uniform float glow_speed = 1.2;

group_uniforms look;      // keep in sync with src/bake_geofront.py (LOOKS["vault"])
uniform float exposure = 0.3;
uniform float shoulder = 0.8;
uniform float saturation = 0.78;
uniform vec3 shadow_tint = vec3(0.88, 0.94, 1.12);
uniform vec3 highlight_tint = vec3(1.08, 1.0, 0.9);
uniform float tint_amount = 0.5;

group_uniforms reflection;
uniform float alpha_near : hint_range(0.0, 1.0) = 0.8;
uniform float alpha_far : hint_range(0.0, 1.0) = 0.58;

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
float aline(float d, float w, float aa) { return 1.0 - smoothstep(w * 0.5 - aa, w * 0.5 + aa, abs(d)); }

void fragment() {
	vec2 p = wpos.xz;
	float aa = max(fwidth(p.x), fwidth(p.y));
	vec2 luv = vec2((p.x - floor_x.x) / (floor_x.y - floor_x.x), 1.0 - (p.y - floor_z.x) / (floor_z.y - floor_z.x));
	vec3 light = pow(texture(light_tex, luv).rgb, vec3(2.2)) * light_max * floor_gain;
	float ll = dot(light, vec3(0.2126, 0.7152, 0.0722));
	light = vec3(ll) + (light - vec3(ll)) * light_saturation;
	vec2 q = p - grate_c;
	float r = length(q);
	float ang = atan(q.x, -q.y);                         // 0 = toward the vault
	// --- plates and seams ---
	float seam = 0.0; float plate_id = 0.0;
	float r_rim = grate_r + ring_w + rim_w;
	if (r < 12.0) {
		float a12 = ang / 6.2831853 * 12.0 + 0.5;
		float aseam = abs(fract(a12) - 0.5) / 12.0 * 6.2831853 * r;           // distance to a radial seam (m)
		seam = max(aline(r - 9.4, 0.035, aa), aline(r - 12.0, 0.035, aa));
		seam = max(seam, aline(aseam, 0.035, aa) * step(r_rim, r));
		plate_id = floor(a12) + floor(r / 9.4) * 17.0;
	} else {
		vec2 g = vec2(p.x / 2.4 + 0.5, p.y / 1.8);
		vec2 gf = abs(fract(g) - 0.5) * vec2(2.4, 1.8);
		seam = max(aline(gf.x - 1.2, 0.035, aa), aline(gf.y - 0.9, 0.035, aa));
		plate_id = dot(floor(g), vec2(1.0, 31.0));
	}
	// diamond tread: little raised lozenges, alternating direction in a checker
	vec2 tp = p / 0.105;
	vec2 tc = floor(tp), tf = fract(tp) - 0.5;
	float o = mod(tc.x + tc.y, 2.0) < 1.0 ? 1.0 : -1.0;
	vec2 rp = vec2(tf.x + o * tf.y, tf.y - o * tf.x) * 0.70710678;
	float lz = length(rp / vec2(0.36, 0.085));
	float raised = 1.0 - smoothstep(0.75, 1.0, lz);
	float lit_edge = raised * clamp(dot(normalize(rp + 1e-4), normalize(vec2(0.3 * o, -1.0))) * 0.5 + 0.5, 0.0, 1.0);
	float tread_vis = 1.0 - smoothstep(0.008, 0.03, aa);                  // fade the tread out in the distance
	vec3 alb = steel * (0.86 + 0.16 * vnoise(p * 0.6) + 0.06 * (hash(vec2(plate_id, 3.0)) - 0.5));
	alb *= (0.88 + (raised * 0.22 + lit_edge * 0.45) * tread_vis) * tread_vis + (1.0 - tread_vis) * 1.0;
	alb = mix(alb, seam_color, seam);
	float alpha_add = seam * 0.5 + raised * 0.12 * tread_vis;
	vec3 emit = vec3(0.0);
	// --- the grate ---
	if (r < r_rim) {
		if (r < grate_r) {
			vec2 m = q / 0.32;
			float g1 = abs(fract(m.x + m.y) - 0.5), g2 = abs(fract(m.x - m.y) - 0.5);
			float bar = 1.0 - smoothstep(0.07 - aa * 2.0, 0.07 + aa * 2.0, min(g1, g2));
			float pulse = 0.55 + 0.45 * sin(TIME * glow_speed - r * 0.9) * (0.7 + 0.3 * sin(TIME * 0.37 + ang * 3.0));
			vec3 hole = hole_color;
			emit += under_glow * glow_strength * pulse * (1.0 - bar) * (0.35 + 0.65 * (1.0 - r / grate_r)) * 0.5;
			vec3 galb = mix(hole, steel * 0.55, bar);
			// six red spokes and a red hexagon around the centre
			float sp = abs(fract(ang / 6.2831853 * 6.0) - 0.5) / 6.0 * 6.2831853 * r;
			float spoke = aline(sp, 0.18, aa) * step(0.9, r);
			float hex = abs(cos(mod(ang, 1.0471976) - 0.5235988) * r - 1.15);
			spoke = max(spoke, aline(hex, 0.14, aa));
			galb = mix(galb, red_line, spoke);
			emit *= 1.0 - spoke;
			alb = galb;
			alpha_add = 1.0 - spoke * 0.6;
		} else if (r < grate_r + ring_w) {
			float st = step(0.5, fract((ang * grate_r + (r - grate_r) * 1.0) / 0.55));
			alb = mix(vec3(0.03), hazard_yellow, st);
			alb = mix(alb, seam_color, aline(r - grate_r, 0.04, aa) + aline(r - grate_r - ring_w, 0.04, aa));
			alpha_add = 0.25;
		} else {
			alb = steel * 1.15;
			alb = mix(alb, seam_color, aline(r - r_rim, 0.04, aa));
			float bolt = 1.0 - smoothstep(0.03, 0.05, length(vec2(fract(ang / 6.2831853 * 96.0) - 0.5, 0.0) * 6.2831853 * r / 96.0 + vec2(0.0, r - (grate_r + ring_w + rim_w * 0.5))));
			alb = mix(alb, vec3(0.75, 0.78, 0.82), bolt);
			alpha_add = 0.1;
		}
	}
	// --- vents and the hazard stripe across the front ---
	if (p.y > vent_z.x && p.y < vent_z.y) {
		float slat = 1.0 - smoothstep(0.32 - aa * 8.0, 0.32 + aa * 8.0, abs(fract(p.x / 0.16) - 0.5));
		vec3 v = mix(hole_color * 2.0, steel * 0.7, slat);
		float fr = max(aline(p.y - vent_z.x, 0.06, aa), aline(p.y - vent_z.y, 0.06, aa));
		alb = mix(v, steel * 1.1, fr); alpha_add = 0.6;
	} else if (p.y > stripe_z.x && p.y < stripe_z.y) {
		float st = step(0.5, fract((p.x + p.y) / 0.6));
		alb = mix(vec3(0.03), hazard_yellow, st) * (0.9 + 0.2 * vnoise(p * 3.0));
		alpha_add = 0.3;
	}
	vec3 col = grade(alb * light) + emit;
	ALBEDO = col;
	float ndv = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	ALPHA = clamp(mix(alpha_near, alpha_far, pow(1.0 - ndv, 3.0)) + alpha_add, 0.0, 1.0);
}
