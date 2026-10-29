// Crimson Abyss - cracked obsidian arena floor.
// Tiling stone (albedo_tex) x baked light map, graded like the baked atlases (grade() in
// src/bake_crimson_abyss.py), plus glowing magenta cracks that pulse in slow waves.
// Drawn semi-transparent over the mirrored "Reflection" copy for the wet-obsidian look.
// Compatibility-renderer friendly (no screen textures, no SSR). Visual only.
shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_opaque, cull_back, shadows_disabled;

uniform sampler2D albedo_tex : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D crack_tex : hint_default_black, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D halo_tex : hint_default_black, filter_linear_mipmap, repeat_enable;
uniform sampler2D region_tex : hint_default_white, filter_linear, repeat_enable;
uniform sampler2D light_tex : hint_default_white, filter_linear, repeat_disable;
uniform float tile_m = 8.0;
uniform float region_m = 64.0;
uniform float light_max = 4.0;
uniform vec2 floor_x = vec2(-56.0, 56.0);
uniform vec2 floor_z = vec2(-64.0, 48.0);

group_uniforms cracks;
uniform vec3 crack_color : source_color = vec3(1.0, 0.32, 0.66);
uniform float crack_gain = 1.9;
uniform float halo_gain = 0.35;
uniform float pulse_speed = 1.3;
uniform float pulse_depth = 0.45;
uniform float fight_line_dim = 0.35;    // crack glow is reduced this much right under the fighters

group_uniforms look;      // keep in sync with src/bake_crimson_abyss.py
uniform float exposure = 0.15;
uniform float shoulder = 0.8;
uniform float saturation = 1.05;
uniform vec3 shadow_tint = vec3(0.96, 0.86, 1.10);
uniform vec3 highlight_tint = vec3(1.06, 0.94, 1.0);
uniform float tint_amount = 0.6;

group_uniforms reflection;
uniform float alpha_near : hint_range(0.0, 1.0) = 0.86;
uniform float alpha_far : hint_range(0.0, 1.0) = 0.55;

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
	vec2 luv = vec2((p.x - floor_x.x) / (floor_x.y - floor_x.x),
	                1.0 - (p.y - floor_z.x) / (floor_z.y - floor_z.x));
	vec3 light = pow(texture(light_tex, luv).rgb, vec3(2.2)) * light_max;
	vec3 alb = texture(albedo_tex, p / tile_m).rgb;
	vec3 col = grade(alb * light);
	float crack = texture(crack_tex, p / tile_m).r;
	float halo = texture(halo_tex, p / tile_m).r;
	float region = texture(region_tex, p / region_m).r;
	// slow waves of light running outward through the cracks
	float d = length(p * vec2(1.0, 1.6));
	float wave = 0.5 + 0.5 * sin(TIME * pulse_speed - d * 0.35 + region * 5.0);
	float pulse = 1.0 - pulse_depth + pulse_depth * wave;
	float dim = 1.0 - fight_line_dim * (1.0 - smoothstep(2.0, 6.0, abs(p.y)));
	float glow = (crack * crack_gain + halo * halo_gain) * (0.15 + 0.85 * region) * pulse * dim;
	ALBEDO = min(col + crack_color * glow, vec3(1.0));
	float ndv = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	ALPHA = mix(alpha_near, alpha_far, pow(1.0 - ndv, 3.0));
}
