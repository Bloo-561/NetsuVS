// Depths of the Old Schoolhouse - polished stone floor of the floating platform.
// Tiling slabs (tiles_tex, 4 m) + the ornate inlay (carpet_tex) in front of the dais, times the baked
// light map, graded like the baked atlases (grade() in src/bake_schoolhouse_depths.py).
// The gold filigree catches a slow travelling glint. Drawn semi-transparent over the mirrored
// "Reflection" copy for the polished look; nothing is drawn past the platform edge.
// Compatibility-renderer friendly. Visual only.
shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_opaque, cull_back, shadows_disabled;

uniform sampler2D tiles_tex : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D carpet_tex : source_color, filter_linear_mipmap_anisotropic, repeat_disable;
uniform sampler2D light_tex : hint_default_white, filter_linear, repeat_disable;
uniform float tile_m = 4.0;
uniform float light_max = 4.0;
uniform float floor_gain = 1.7;
uniform float light_saturation = 0.4;   // the sky light is very cyan; keep the stone grey-blue      // the open floor only sees the sky from above; lift it to read as pale stone
uniform vec2 floor_x = vec2(-36.0, 36.0);
uniform vec2 floor_z = vec2(-44.0, 28.0);
uniform vec4 carpet_rect = vec4(-12.0, 12.0, -17.0, -3.0);   // x0, x1, z0, z1
uniform vec2 platform_centre = vec2(0.0, -8.0);
uniform float platform_radius = 34.0;

group_uniforms inlay;
uniform float carpet_gain = 1.35;      // brighter inlay than the bare slabs (it reads like the painting)
uniform float gold_glow = 0.12;        // the gold lines glow faintly on their own
group_uniforms glint;
uniform vec3 glint_color : source_color = vec3(1.0, 0.95, 0.7);
uniform float glint_strength = 0.35;
uniform float glint_speed = 0.25;

group_uniforms look;      // keep in sync with src/bake_schoolhouse_depths.py
uniform float exposure = 0.45;
uniform float shoulder = 0.8;
uniform float saturation = 1.1;
uniform vec3 shadow_tint = vec3(0.86, 0.96, 1.16);
uniform vec3 highlight_tint = vec3(1.0, 1.04, 1.02);
uniform float tint_amount = 0.5;

group_uniforms reflection;
uniform float alpha_near : hint_range(0.0, 1.0) = 0.9;
uniform float alpha_far : hint_range(0.0, 1.0) = 0.72;

varying vec3 wpos;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

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

void fragment() {
	vec2 p = wpos.xz;
	if (length(p - platform_centre) > platform_radius) { discard; }
	vec2 luv = vec2((p.x - floor_x.x) / (floor_x.y - floor_x.x),
	                1.0 - (p.y - floor_z.x) / (floor_z.y - floor_z.x));
	vec3 light = pow(texture(light_tex, luv).rgb, vec3(2.2)) * light_max * floor_gain;
	float ll = dot(light, vec3(0.2126, 0.7152, 0.0722));
	light = mix(vec3(ll), light, light_saturation);
	vec3 alb = texture(tiles_tex, p / tile_m).rgb;
	vec2 cuv = vec2((p.x - carpet_rect.x) / (carpet_rect.y - carpet_rect.x),
	                (p.y - carpet_rect.z) / (carpet_rect.w - carpet_rect.z));
	float in_carpet = step(0.0, cuv.x) * step(cuv.x, 1.0) * step(0.0, cuv.y) * step(cuv.y, 1.0);
	vec3 car = texture(carpet_tex, clamp(cuv, 0.0, 1.0)).rgb;
	alb = mix(alb, car * carpet_gain, in_carpet);
	vec3 col = grade(alb * light);
	// glint running across the gold lines (lines = the bright, warm parts of the inlay)
	float gold = smoothstep(0.35, 0.6, car.r - car.b * 0.4) * in_carpet;
	float sweep = pow(0.5 + 0.5 * sin((p.x * 0.35 + p.y * 0.2) - TIME * glint_speed * 6.2832), 12.0);
	col += glint_color * gold * (sweep * glint_strength + gold_glow);
	ALBEDO = min(col, vec3(1.0));
	float ndv = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	ALPHA = mix(alpha_near, alpha_far, pow(1.0 - ndv, 3.0));
}
