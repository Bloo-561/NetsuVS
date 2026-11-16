// Septian Chapel - Trails variant ground (Trails in the Sky / Crossbell look), times the baked light map.
// Each surface = a CC0 photo texture (textures/trails/, Poly Haven) used as DETAIL and recoloured to a painted
// palette, so the colours stay art-directed while the texture gives real, varied surface detail.
//   * meadow: two grass textures in big soft patches, lush yellow-green, darker clumps, flower clusters
//   * tan dirt paths with soft, ragged edges and a darker grass lip (the Trails "worn path" look)
//   * Crossbell fan-pattern cobble square with a pale dressed-stone border
//   * forest floor under the oak, flower-strewn soil in the statue's ring
shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_opaque, cull_back, shadows_disabled;

uniform sampler2D light_tex : hint_default_white, filter_linear, repeat_disable;
uniform float light_max = 4.0;
uniform float floor_gain = 1.0;
uniform float light_saturation = 0.85;
uniform vec2 floor_x = vec2(-60.0, 60.0);
uniform vec2 floor_z = vec2(-80.0, 22.0);

group_uniforms textures;
uniform sampler2D tex_grass : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D tex_grass2 : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D tex_dirt : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D tex_forest : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D tex_cobble : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D tex_flowers : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform float grass_tile = 3.2;       // metres per texture repeat
uniform float dirt_tile = 3.5;
uniform float cobble_tile = 4.2;
uniform float cobble_contrast = 2.2;

group_uniforms layout;
uniform vec2 square_center = vec2(0.0, -6.0);
uniform vec2 square_radii = vec2(13.5, 10.5);
uniform float border_width = 0.45;
uniform float emblem = 1.0;                 // the Septian rune circle inlaid in the square (0 = off)
uniform vec2 emblem_center = vec2(0.0, -6.0);
uniform float emblem_radius = 3.4;
uniform vec3 bronze : source_color = vec3(0.62, 0.48, 0.28);
uniform vec2 statue = vec2(-6.6, -17.0);
uniform vec2 oak = vec2(-15.5, -6.5);
uniform float facade_z = -28.0;

group_uniforms palette;
uniform vec3 grass_a : source_color = vec3(0.33, 0.50, 0.15);
uniform vec3 grass_b : source_color = vec3(0.50, 0.62, 0.20);
uniform vec3 grass_dark : source_color = vec3(0.20, 0.34, 0.12);
uniform vec3 grass_dry : source_color = vec3(0.66, 0.62, 0.30);
uniform vec3 dirt_col : source_color = vec3(0.70, 0.56, 0.38);
uniform vec3 cobble_col : source_color = vec3(0.60, 0.56, 0.50);
uniform vec3 border_col : source_color = vec3(0.80, 0.74, 0.64);
uniform vec3 forest_col : source_color = vec3(0.40, 0.34, 0.20);
uniform float detail = 0.85;          // how much of the photo's light/dark detail survives the recolour
uniform float photo_colour = 0.25;    // how much of the photo's own hue is kept

group_uniforms wind;
uniform vec2 wind_dir = vec2(1.0, 0.35);
uniform float gusts = 0.10;

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
float seg_dist(vec2 p, vec2 a, vec2 b) {
	vec2 pa = p - a, ba = b - a;
	float t = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
	return length(pa - ba * t);
}
float lum(vec3 c) { return dot(c, vec3(0.2126, 0.7152, 0.0722)); }
// sample a texture twice (rotated, offset) and blend by noise -> no visible tiling
vec3 untiled(sampler2D t, vec2 p, float tile) {
	vec2 uv = p / tile;
	vec2 uv2 = mat2(vec2(0.8, 0.6), vec2(-0.6, 0.8)) * uv * 0.73 + vec2(0.37, 0.71);
	float m = smoothstep(0.35, 0.65, vnoise(p * 0.18));
	return mix(texture(t, uv).rgb, texture(t, uv2).rgb, m);
}
// recolour a photo to a painted target colour, keeping its relative light/dark detail
vec3 paint_c(vec3 photo, vec3 target, float avg, float k) {
	float d = mix(1.0, pow(lum(photo) / max(avg, 1e-3), k), detail);
	return mix(target * d, photo * (lum(target) / max(avg, 1e-3)), photo_colour);
}
vec3 paint(vec3 photo, vec3 target, float avg) {
	float d = mix(1.0, lum(photo) / max(avg, 1e-3), detail);
	vec3 painted = target * d;
	return mix(painted, photo * (lum(target) / max(avg, 1e-3)), photo_colour);
}

float avg_of(sampler2D t) { return max(lum(textureLod(t, vec2(0.5), 12.0).rgb), 1e-3); }   // smallest mip = texture average

void fragment() {
	vec2 p = wpos.xz;
	vec2 luv = vec2((p.x - floor_x.x) / (floor_x.y - floor_x.x), 1.0 - (p.y - floor_z.x) / (floor_z.y - floor_z.x));
	vec3 light = pow(texture(light_tex, luv).rgb, vec3(2.2)) * light_max * floor_gain;
	float ll = lum(light);
	light = vec3(ll) + (light - vec3(ll)) * light_saturation;
	float edge_n = fbm(p * 0.55) - 0.5;
	float rag = vnoise(p * 3.1) - 0.5;            // fine raggedness of the grass edges

	// --- meadow: two textures, big soft painted patches ---
	vec3 g1 = untiled(tex_grass, p, grass_tile);
	vec3 g2 = untiled(tex_grass2, p + 11.0, grass_tile * 1.2);
	float patch = smoothstep(0.32, 0.68, fbm(p * 0.09));
	vec3 gcol = mix(grass_a, grass_b, patch);
	gcol = mix(gcol, grass_dry, smoothstep(0.62, 0.82, fbm(p * 0.045 + 7.0)) * 0.55);
	float clump = smoothstep(0.55, 0.75, fbm(p * 0.6 + 3.0));
	gcol = mix(gcol, grass_dark, clump * 0.45);
	vec3 alb = mix(paint(g1, gcol, avg_of(tex_grass)), paint(g2, gcol, avg_of(tex_grass2)), smoothstep(0.4, 0.6, vnoise(p * 0.11 + 5.0)));
	float gust = smoothstep(0.55, 1.0, sin(dot(p, normalize(wind_dir)) * 0.3 - TIME * 1.3) * 0.5 + 0.5)
	           * smoothstep(0.35, 0.7, fbm(p * 0.08 - normalize(wind_dir) * TIME * 0.4));
	alb = mix(alb, alb * 1.2 + vec3(0.02, 0.025, 0.0), gust * gusts);
	// flower clusters (white / yellow / lilac), clumped like the painted meadows
	vec2 fc = floor(p * 1.4);
	float fl = hash(fc);
	vec2 fo = fract(p * 1.4) - 0.5 - (hash2(fc + 3.0) - 0.5) * 0.5;
	float cl = 1.0 - smoothstep(0.12, 0.26, length(fo) + rag * 0.12);
	float dots = step(0.72, vnoise(p * 22.0));
	vec3 fcol = fl > 0.975 ? vec3(0.62, 0.50, 0.86) : (fl > 0.955 ? vec3(0.98, 0.86, 0.30) : vec3(0.96, 0.95, 0.90));
	alb = mix(alb, fcol, step(0.935, fl) * cl * dots * smoothstep(0.3, 0.6, fbm(p * 0.2 + 9.0)));

	// --- forest floor under the oak ---
	float od = length(p - oak);
	float under = 1.0 - smoothstep(2.0, 4.2, od + edge_n * 2.0 + rag * 0.6);
	alb = mix(alb, paint(untiled(tex_forest, p, 3.0), forest_col, avg_of(tex_forest)), under * 0.85);

	// --- dirt paths (rectory gate, lychgate, and round the back of the square) ---
	float dp = min(min(seg_dist(p, vec2(-8.6, -11.5), vec2(-15.2, -13.4)), seg_dist(p, vec2(-15.2, -13.4), vec2(-15.2, -17.0))),
	               seg_dist(p, vec2(9.0, -10.5), vec2(16.0, -13.8)));
	dp = min(dp, seg_dist(p, vec2(-12.5, 2.0), vec2(-26.0, 9.0)) + 0.25);
	dp = min(dp, seg_dist(p, vec2(12.5, 2.0), vec2(26.0, 7.0)) + 0.25);
	float pw = 1.05 + edge_n * 0.7 + rag * 0.35;
	float path = 1.0 - smoothstep(pw - 0.12, pw + 0.12, dp);
	float lip = (1.0 - smoothstep(pw + 0.05, pw + 0.55, dp)) * (1.0 - path);
	vec3 dirt = paint(untiled(tex_dirt, p, dirt_tile), dirt_col * (0.92 + 0.16 * fbm(p * 0.7)), avg_of(tex_dirt));
	alb = mix(alb, alb * 0.72, lip * 0.8);                                  // darker, denser grass lip
	alb = mix(alb, dirt, path);

	// --- the Crossbell fan-cobble square with a pale stone border ---
	vec2 e = (p - square_center) / square_radii;
	float r = length(e) + edge_n * 0.015;
	float rm = 1.0 - border_width / min(square_radii.x, square_radii.y);
	float sq = 1.0 - smoothstep(0.995, 1.005, r);
	float border = sq * smoothstep(rm - 0.005, rm + 0.005, r);
	float fp = step(abs(p.x), 2.4) * step(p.y, -13.0) * step(facade_z + 0.4, p.y);     // walk to the steps
	float fpb = fp * step(2.4 - border_width, abs(p.x));
	vec3 cob = paint_c(texture(tex_cobble, p / cobble_tile).rgb, cobble_col * (0.9 + 0.18 * fbm(p * 0.4)), avg_of(tex_cobble), cobble_contrast);
	// worn, lighter centre and grime near the edge
	cob *= mix(1.08, 0.88, smoothstep(0.3, 0.95, r));
	float seg = atan(e.y, e.x) / 6.2832 * 64.0 * (min(square_radii.x, square_radii.y) / 10.5);
	float jnt = 1.0 - smoothstep(0.0, 0.05, min(fract(seg), 1.0 - fract(seg)));
	vec3 bst = border_col * (0.86 + 0.14 * hash(vec2(floor(seg), 1.0))) * (0.92 + 0.1 * fbm(p * 2.0));
	bst = mix(bst, bst * 0.55, jnt);
	bst = mix(bst, bst * 0.6, 1.0 - smoothstep(0.0, 0.004, abs(r - rm)));         // inner joint line
	alb = mix(alb, alb * 0.75, (1.0 - smoothstep(1.0, 1.06, r)) * (1.0 - sq));   // shadowed grass at the kerb
	alb = mix(alb, cob, max(sq, fp));
	alb = mix(alb, bst, max(border, fpb));
	// --- the Septian rune circle (Crossbell plaza): pale stone rings, seven bronze rays, a bronze hub ---
	if (emblem > 0.0) {
		vec2 q = p - emblem_center; float d = length(q) / emblem_radius; float a = atan(q.y, q.x);
		float aa = 0.012;
		float ring_o = smoothstep(0.90 - aa, 0.90, d) * (1.0 - smoothstep(1.0, 1.0 + aa, d));
		float ring_i = smoothstep(0.64 - aa, 0.64, d) * (1.0 - smoothstep(0.69, 0.69 + aa, d));
		float inside = 1.0 - smoothstep(0.90 - aa, 0.90, d);
		float ray_w = 0.06 * (1.0 - d * 0.6);
		float ray = (1.0 - smoothstep(ray_w, ray_w + 0.015, abs(fract(a / 6.2832 * 7.0 + 0.25) - 0.5) * 2.0 * d * 3.2))
		          * smoothstep(0.17, 0.2, d) * (1.0 - smoothstep(0.62, 0.64, d));
		float hub = 1.0 - smoothstep(0.15, 0.15 + aa, d);
		float hub_ring = smoothstep(0.17, 0.18, d) * (1.0 - smoothstep(0.21, 0.22, d));
		float glyph = step(0.7, d) * step(d, 0.88) * step(0.55, fract(a / 6.2832 * 28.0)) * step(fract(a / 6.2832 * 28.0), 0.8)
		            * step(0.74, d) * step(d, 0.84);
		vec3 pale = border_col * 1.12;
		vec3 inner = mix(cob, cob * 1.12 + vec3(0.02), 0.6);
		vec3 em = mix(alb, inner, inside);
		float edge = max(ring_o, ring_i);
		float line = (1.0 - smoothstep(0.0, 0.006, abs(d - 0.90))) + (1.0 - smoothstep(0.0, 0.006, abs(d - 1.0)))
		           + (1.0 - smoothstep(0.0, 0.005, abs(d - 0.64))) + (1.0 - smoothstep(0.0, 0.005, abs(d - 0.69)));
		em = mix(em, pale, edge);
		em = mix(em, em * 0.55, clamp(line, 0.0, 1.0));      // dark joints outline the rings
		em = mix(em, bronze * (0.85 + 0.25 * fbm(p * 3.0)), max(max(ray, hub), max(hub_ring, glyph * 0.8)));
		alb = mix(alb, em, emblem);
	}

	// --- statue ring: flower-strewn soil ---
	float sr = length(p - statue);
	alb = mix(alb, paint(texture(tex_flowers, p / 2.0).rgb, vec3(0.36, 0.26, 0.17), avg_of(tex_flowers)) * 1.0, 1.0 - step(2.36, sr));
	alb = mix(alb, alb * 0.65, (1.0 - smoothstep(2.6, 3.0, sr)) * step(2.36, sr) * 0.5);
	ALBEDO = grade(alb * light);
}
