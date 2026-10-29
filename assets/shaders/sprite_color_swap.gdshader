shader_type spatial;
// Alternate-colour outfit for fighter sprites (made for Flan's "Polaris" colour).
// 1) "Trim" pixels: hue between trim_hue_min and trim_hue_max and saturation above
//    trim_min_sat (Flan's gold, including its darker orange shading). They get
//    target_hue, their saturation times target_sat and value times target_val.
//    Her brown hair (saturation ~0.5) and skin (~0.3) stay below the cut-off.
// 2) "Dark" pixels: saturation below dark_max_sat and value below dark_max_val
//    (black cloth and outlines). They get dark_hue / dark_sat, value times dark_lift.
//    Set dark_sat to 0 and dark_lift to 1 to leave the black (almost) alone.
// Works on the colours exactly as the texture gives them, like sprite_hue_shift does.
// With this project's Compatibility renderer those are the colours you see in an image
// editor (converting them again washed them out and missed the bright gold).
// strength (0-1) blends from the original art (0) to the recolour (1), e.g. to fade
// back to her real colours during a move (planned: Stigmata colour + Stigmata Install).
// The engine fills in albedo_texture with the current sprite every frame.
render_mode blend_mix, cull_disabled, unshaded, specular_disabled, depth_prepass_alpha;

uniform sampler2D albedo_texture : source_color, filter_linear_mipmap;
// hue_offset is added to the hue before the trim test only, so a range can wrap around red
// (Cecilia: 0.1 turns her reds at 0.93-0.05 into 0.03-0.15). 0 = old behaviour (Flan).
uniform float hue_offset : hint_range(0.0, 1.0) = 0.0;
uniform float trim_hue_min : hint_range(0.0, 1.0) = 0.06;
uniform float trim_hue_max : hint_range(0.0, 1.0) = 0.19;
uniform float trim_min_sat : hint_range(0.0, 1.0) = 0.6;
uniform float target_hue : hint_range(0.0, 1.0) = 0.57;
uniform float target_sat : hint_range(0.0, 2.0) = 0.35;
uniform float target_val : hint_range(0.0, 2.0) = 1.05;
uniform float dark_max_sat : hint_range(0.0, 1.0) = 0.3;
uniform float dark_max_val : hint_range(0.0, 1.0) = 0.45;
uniform float dark_hue : hint_range(0.0, 1.0) = 0.64;
uniform float dark_sat : hint_range(0.0, 1.0) = 0.55;
uniform float dark_lift : hint_range(0.0, 3.0) = 1.25;
uniform float strength : hint_range(0.0, 1.0) = 1.0;

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
	vec3 hsv = rgb2hsv(clamp(tex.rgb, 0.0, 1.0));
	float h = hsv.x;
	float ht = fract(h + hue_offset);
	float s = hsv.y;
	float v = hsv.z;

	float trim = smoothstep(trim_hue_min - 0.01, trim_hue_min + 0.01, ht)
		* (1.0 - smoothstep(trim_hue_max - 0.01, trim_hue_max + 0.01, ht))
		* smoothstep(trim_min_sat - 0.04, trim_min_sat + 0.04, s)
		* smoothstep(0.08, 0.15, v);
	vec3 o = hsv;
	o.x = trim > 0.0 ? target_hue : h;
	o.y = mix(s, s * target_sat, trim);
	o.z = mix(v, clamp(v * target_val, 0.0, 1.0), trim);

	float dark = (1.0 - smoothstep(dark_max_sat - 0.05, dark_max_sat + 0.05, s))
		* (1.0 - smoothstep(dark_max_val - 0.05, dark_max_val + 0.05, v))
		* (1.0 - trim);
	o.x = dark > 0.01 ? dark_hue : o.x;
	o.y = mix(o.y, dark_sat, dark);
	o.z = mix(o.z, clamp(o.z * dark_lift, 0.0, 1.0), dark);

	vec3 recoloured = clamp(hsv2rgb(clamp(o, 0.0, 1.0)), 0.0, 1.0);
	// COLOR = the sprite's modulate (the super flash darkens / brightens fighters with it)
	ALBEDO = mix(tex.rgb, recoloured, strength) * COLOR.rgb;
	ALPHA = tex.a * COLOR.a;
}
