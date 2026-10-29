shader_type spatial;
// Alternate-colour outfit for fighter sprites: shifts strongly-coloured REDS to
// another hue (0.62 = blue) and leaves skin, hair and everything else alone.
// Used by actors/cecilia/Palettes/Color2/CEC_Palette_Alt1_MAT.tres.
// The engine fills in albedo_texture with the current sprite every frame.
render_mode blend_mix, cull_disabled, unshaded, specular_disabled, depth_prepass_alpha;

uniform sampler2D albedo_texture : source_color, filter_linear_mipmap;
uniform float hue_shift : hint_range(0.0, 1.0) = 0.62;
uniform float min_saturation : hint_range(0.0, 1.0) = 0.45;
uniform float red_range : hint_range(0.0, 0.2) = 0.05;

vec3 rgb2hsv(vec3 c) {
	vec4 K = vec4(0.0, -1.0 / 3.0, 2.0 / 3.0, -1.0);
	vec4 p = mix(vec4(c.bg, K.wz), vec4(c.gb, K.xy), step(c.b, c.g));
	vec4 q = mix(vec4(p.xyw, c.r), vec4(c.r, p.yzx), step(p.x, c.r));
	float d = q.x - min(q.w, q.y);
	float e = 1.0e-10;
	return vec3(abs(q.z + (q.w - q.y) / (6.0 * d + e)), d / (q.x + e), q.x);
}

vec3 hsv2rgb(vec3 c) {
	vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
	vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
	return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

void fragment() {
	vec4 tex = texture(albedo_texture, UV);
	vec3 hsv = rgb2hsv(tex.rgb);
	float dist_to_red = min(hsv.x, 1.0 - hsv.x);
	float is_red = (1.0 - smoothstep(red_range, red_range + 0.02, dist_to_red)) * step(min_saturation, hsv.y);
	hsv.x = fract(hsv.x + hue_shift * is_red);
	// COLOR = the sprite's modulate (the super flash darkens / brightens fighters with it)
	ALBEDO = hsv2rgb(hsv) * COLOR.rgb;
	ALPHA = tex.a * COLOR.a;
}
