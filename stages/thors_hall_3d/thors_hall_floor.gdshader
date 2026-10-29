// Thors Training Hall 3D - polished floor.
// Tiling marble (albedo_tex) x baked light map (light_tex), graded exactly like the baked atlases
// (same curve as grade() in src/bake_thors_hall.py), then drawn semi-transparent over the
// mirrored copy of the room ("Reflection" node) for the polished-stone reflection.
// Works in the Compatibility renderer: no SSR, no screen textures.
shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_opaque, cull_back, shadows_disabled;

uniform sampler2D albedo_tex : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D light_tex : hint_default_white, filter_linear, repeat_disable;
uniform float tile_m = 6.0;
uniform float light_max = 6.0;
uniform vec2 floor_x = vec2(-15.5, 15.5);
uniform vec2 floor_z = vec2(-27.1, 6.0);

group_uniforms court_lines;
uniform float court_x = 8.0;
uniform float court_z = -17.5;
uniform float court_w = 0.26;
uniform vec3 court_color : source_color = vec3(0.91, 0.54, 0.21);

group_uniforms look;      // keep in sync with src/bake_thors_hall.py
uniform float exposure = 0.55;
uniform float shoulder = 0.78;
uniform float saturation = 1.12;
uniform vec3 shadow_tint = vec3(0.86, 0.88, 1.10);
uniform vec3 highlight_tint = vec3(1.07, 1.0, 0.90);
uniform float tint_amount = 0.55;

group_uniforms fight_line;   // calmer floor right behind the fighters (sprites read better)
uniform float fight_calm : hint_range(0.0, 1.0) = 0.25;
uniform float calm_level = 0.9;          // light level the floor is eased toward near z = 0
uniform float calm_half_depth = 3.0;     // metres in front of / behind the fight line

group_uniforms reflection;
uniform float alpha_near : hint_range(0.0, 1.0) = 0.80;  // floor opacity looking down
uniform float alpha_far : hint_range(0.0, 1.0) = 0.45;   // floor opacity at grazing angles

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
	return clamp(c, 0.0, 1.0);   // display-referred, already "sRGB-graded" but kept linear-light here
}

float court_mask(vec2 p) {
	float hw = court_w * 0.5;
	float aa = fwidth(p.x) + fwidth(p.y);
	float side = (1.0 - smoothstep(hw - aa, hw + aa, abs(abs(p.x) - court_x))) * step(court_z - hw, p.y);
	float back = 1.0 - smoothstep(hw - aa, hw + aa, abs(p.y - court_z));
	return max(side, back);
}

void fragment() {
	vec2 p = wpos.xz;
	vec2 luv = vec2((p.x - floor_x.x) / (floor_x.y - floor_x.x),
	                1.0 - (p.y - floor_z.x) / (floor_z.y - floor_z.x));
	vec3 light = pow(texture(light_tex, luv).rgb, vec3(2.2)) * light_max;
	float calm = fight_calm * (1.0 - smoothstep(calm_half_depth, calm_half_depth + 4.0, abs(p.y)));
	light = mix(light, vec3(calm_level) * normalize(light + 1e-4) * 1.732, calm);
	vec3 alb = texture(albedo_tex, p / tile_m).rgb;
	vec3 line_lin = court_color;   // source_color -> already linear
	float m = court_mask(p);
	float wear = 0.85 + 0.15 * dot(alb, vec3(0.333));
	alb = mix(alb, line_lin * wear, m);
	ALBEDO = grade(alb * light);
	float ndv = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	ALPHA = mix(alpha_near, alpha_far, pow(1.0 - ndv, 3.0));
}
