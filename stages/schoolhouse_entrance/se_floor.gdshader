// Old Schoolhouse -Entrance- - the polished slate floor, procedural, times the baked light map
// (which holds the moonlight patches under the windows and the warm pools under the lanterns).
//   * big square slate tiles, blue-grey and mottled, each a little different, with dark grooves
//   * a worn, uneven polish: drawn semi-transparent over the mirrored "Reflection" copy, more on some tiles
// Visual only.
shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_opaque, cull_back, shadows_disabled;

uniform sampler2D light_tex : hint_default_white, filter_linear, repeat_disable;
uniform float light_max = 4.0;
uniform float floor_gain = 1.0;
uniform float light_saturation = 0.9;
uniform vec2 floor_x = vec2(-18.0, 18.0);
uniform vec2 floor_z = vec2(-24.5, 16.0);

group_uniforms slate;
uniform vec3 slate_dark : source_color = vec3(0.22, 0.25, 0.3);
uniform vec3 slate_light : source_color = vec3(0.4, 0.44, 0.51);
uniform vec3 groove_color : source_color = vec3(0.07, 0.08, 0.1);
uniform float tile = 2.2;
uniform float groove = 0.028;

group_uniforms look;      // keep in sync with src/bake_schoolhouse_entrance.py
uniform float exposure = 0.2;
uniform float shoulder = 0.8;
uniform float saturation = 1.0;
uniform vec3 shadow_tint = vec3(0.86, 0.92, 1.2);
uniform vec3 highlight_tint = vec3(1.08, 1.0, 0.9);
uniform float tint_amount = 0.55;

group_uniforms reflection;
uniform float alpha_near : hint_range(0.0, 1.0) = 0.62;
uniform float alpha_far : hint_range(0.0, 1.0) = 0.34;
uniform float polish_variation = 0.12;   // some tiles shine more than others

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
	for (int i = 0; i < 5; i++) { s += vnoise(p) * a; p = p * 2.03 + 1.7; a *= 0.5; }
	return s / 0.97;
}

void fragment() {
	vec2 p = wpos.xz;
	vec2 luv = vec2((p.x - floor_x.x) / (floor_x.y - floor_x.x), 1.0 - (p.y - floor_z.x) / (floor_z.y - floor_z.x));
	vec3 light = pow(texture(light_tex, luv).rgb, vec3(2.2)) * light_max * floor_gain;
	float ll = dot(light, vec3(0.2126, 0.7152, 0.0722));
	light = vec3(ll) + (light - vec3(ll)) * light_saturation;
	vec2 q = p / tile + vec2(0.5, 0.0);
	vec2 tc = floor(q), tf = fract(q);
	float edge = min(min(tf.x, 1.0 - tf.x), min(tf.y, 1.0 - tf.y)) * tile;
	float aa = fwidth(edge) * 1.2;
	float gr = (1.0 - smoothstep(groove * 0.5 - aa, groove * 0.5 + aa, edge)) * mix(1.0, 0.45, smoothstep(0.02, 0.12, aa));
	float bevel = smoothstep(groove, groove * 2.5, edge) * (1.0 - smoothstep(groove * 2.5, groove * 5.0, edge));
	// mottled slate: cloudy patches, lighter worn areas, dark flecks
	float h = hash(tc);
	float m = fbm(p * 0.9 + h * 13.0);
	float worn = smoothstep(0.55, 0.8, fbm(p * 0.35 + 7.0 + h * 3.0));
	vec3 alb = mix(slate_dark, slate_light, smoothstep(0.3, 0.75, m)) * (0.88 + 0.24 * h);
	alb = mix(alb, slate_light * 1.15, worn * 0.35);
	alb *= 1.0 - step(0.93, vnoise(p * 14.0)) * 0.35;
	alb += vec3(0.05) * bevel;
	alb = mix(alb, groove_color, gr);
	vec3 col = grade(alb * light);
	ALBEDO = col;
	float ndv = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	float polish = (hash(tc + 5.3) - 0.5) * 2.0 * polish_variation + (m - 0.5) * 0.12;
	ALPHA = clamp(mix(alpha_near, alpha_far, pow(1.0 - ndv, 3.0)) + polish + gr, 0.0, 1.0);
}
