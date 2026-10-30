// North Ambria - the snowfield (visual only), on the sculpted ground mesh, times the baked light map.
// Wind-packed powder: soft ripples running across the wind, shallow drift tails, a fine grain; blowing powder
// streams over the surface in gusts. Fully MATTE: no specular, no sparkle, no reflection of any kind.
shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_opaque, cull_back, shadows_disabled, fog_disabled;

uniform sampler2D light_tex : hint_default_white, filter_linear, repeat_disable;
uniform float light_max = 4.0;
uniform float floor_gain = 1.0;
uniform float light_saturation = 0.45;
uniform vec2 floor_x = vec2(-90.0, 90.0);
uniform vec2 floor_z = vec2(-66.0, 24.0);

group_uniforms snow;
uniform vec3 snow_color : source_color = vec3(0.88, 0.9, 0.93);
uniform vec3 shade_color : source_color = vec3(0.62, 0.69, 0.81);     // restrained blue-grey in the ripple shadows
uniform vec2 wind = vec2(0.94, 0.34);
uniform float ripple = 0.8;          // strength of the ripple shading
uniform float grain = 0.02;
uniform float packed_amount = 0.45;    // smoother, slightly brighter patches of packed snow

group_uniforms haze;
uniform vec3 haze_color : source_color = vec3(0.68, 0.72, 0.8);
uniform vec2 haze_range = vec2(22.0, 95.0);
uniform float haze_max = 0.55;

group_uniforms look;      // keep in sync with src/bake_north_ambria.py
uniform float exposure = 0.0;
uniform float shoulder = 0.85;
uniform float saturation = 0.9;
uniform vec3 shadow_tint = vec3(0.92, 0.96, 1.08);
uniform vec3 highlight_tint = vec3(1.0, 1.0, 1.02);
uniform float tint_amount = 0.45;

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
vec2 grad2(vec2 p) { float a = hash(p) * 6.2831853; return vec2(cos(a), sin(a)); }
// smooth gradient noise with a quintic fade: no lattice creases, so the relief never forms plates or a grid
float gnoise(vec2 p) {
	vec2 i = floor(p), f = fract(p);
	vec2 u = f * f * f * (f * (f * 6.0 - 15.0) + 10.0);
	float a = dot(grad2(i), f), b = dot(grad2(i + vec2(1.0, 0.0)), f - vec2(1.0, 0.0));
	float c = dot(grad2(i + vec2(0.0, 1.0)), f - vec2(0.0, 1.0)), d = dot(grad2(i + vec2(1.0, 1.0)), f - vec2(1.0, 1.0));
	return mix(mix(a, b, u.x), mix(c, d, u.x), u.y) * 0.7 + 0.5;
}
float vnoise(vec2 p) { return gnoise(p); }
float fbm(vec2 p) {                                            // every octave rotated: no repeats, no axis lines
	float s = 0.0, a = 0.5;
	for (int i = 0; i < 5; i++) { s += gnoise(p) * a; p = mat2(vec2(0.8, 0.6), vec2(-0.6, 0.8)) * p * 2.03 + 1.7; a *= 0.5; }
	return s / 0.97;
}
// height of the powder's surface: broad, soft, irregular wind-shaped swells a few metres across, a little stretched
// across the wind and warped so nothing lines up, with a gentle smaller undulation on them - smooth everywhere
float ripples(vec2 p) {
	vec2 w = normalize(wind);
	vec2 q = vec2(dot(p, w), dot(p, vec2(-w.y, w.x))) * vec2(1.0, 0.7);
	vec2 wq = q + vec2(fbm(q * 0.08), fbm(q * 0.07 + 5.0)) * 4.0;
	return fbm(wq * 0.3) * 0.9 + fbm(wq * 1.05 + 3.0) * 0.18;
}
float packed(vec2 p) {                                         // very soft, broad areas of smoother wind-packed snow
	return smoothstep(0.38, 0.75, fbm(p * 0.045 + vec2(fbm(p * 0.02) * 2.0, 0.0)));
}

void fragment() {
	vec2 p = wpos.xz;
	vec2 luv = vec2((p.x - floor_x.x) / (floor_x.y - floor_x.x), 1.0 - (p.y - floor_z.x) / (floor_z.y - floor_z.x));
	vec3 light = pow(texture(light_tex, luv).rgb, vec3(2.2)) * light_max * floor_gain;
	float ll = dot(light, vec3(0.2126, 0.7152, 0.0722));
	light = vec3(ll) + (light - vec3(ll)) * light_saturation;
	// fake-lit ripple relief from a soft light from behind-above (the storm's bright side)
	float pk = packed(p) * packed_amount;
	float e = 0.3;
	float h0 = ripples(p), hx = ripples(p + vec2(e, 0.0)), hz = ripples(p + vec2(0.0, e));
	vec2 grad = vec2(hx - h0, hz - h0) / e;
	float relief = clamp(-dot(grad, vec2(0.55, -0.6)) * ripple * (1.0 - pk * 0.5), -0.2, 0.2);
	vec3 alb = snow_color;
	alb = mix(alb, shade_color, smoothstep(0.0, 0.3, -relief) * 0.65);
	alb *= 1.0 + smoothstep(0.0, 0.3, relief) * 0.06;
	alb = mix(alb, alb * 1.03 + vec3(0.0, 0.004, 0.01), pk);                       // packed: smoother, a touch brighter
	alb *= 1.0 + ((gnoise(p * 23.0) - 0.5) * grain + (gnoise(p * 6.0) - 0.5) * grain * 1.5) * (1.0 - pk * 0.5);
	vec3 col = grade(alb * light);
	float dist = length(wpos - CAMERA_POSITION_WORLD);
	col = mix(col, haze_color, smoothstep(haze_range.x, haze_range.y, dist) * haze_max);
	ALBEDO = col;
}
