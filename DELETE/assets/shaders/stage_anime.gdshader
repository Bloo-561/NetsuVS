// Netsu stage "anime background" filter (TRIAL, 2026-11-09). Full-screen QuadMesh in a STAGE scene, node AnimeFX,
// render_priority -128, no depth test: drawn first in the transparent pass, so it restyles only the stage (the
// opaque pass); fighters, effects and UI draw crisp on top.
//   1. edge-preserving smoothing (bilateral 5x5): removes photo grain, keeps shapes crisp
//   2. cel light: luminance pulled into a few soft bands; shadows shift toward blue-violet, lights toward warm
//   3. thin outlines: depth silhouettes + colour edges, drawn in a darker shade of the local colour
//   4. vivid grade + a soft glow on bright areas
// GPU only, no effect on gameplay / rollback.
shader_type spatial;
render_mode unshaded, depth_test_disabled, depth_draw_never, cull_disabled, shadows_disabled, blend_mix, fog_disabled;

uniform sampler2D screen_tex : hint_screen_texture, filter_linear, repeat_disable;
uniform sampler2D depth_tex : hint_depth_texture, filter_nearest, repeat_disable;

group_uniforms clean;
uniform float smooth_sigma = 0.22;          // colour similarity for the bilateral (lower = keeps more detail)
uniform float smooth_px = 2.6;              // sample spacing (pixels at 1080p)
uniform float detail_keep : hint_range(0.0, 1.0) = 0.08;
group_uniforms cel;
uniform float cel_bands : hint_range(2.0, 8.0) = 3.0;
uniform float cel_soft : hint_range(0.0, 0.5) = 0.18;
uniform float cel_amount : hint_range(0.0, 1.0) = 0.6;
uniform vec3 shadow_tint : source_color = vec3(0.78, 0.82, 1.0);
uniform vec3 light_tint : source_color = vec3(1.0, 0.98, 0.94);
group_uniforms lines;
uniform float line_amount : hint_range(0.0, 1.0) = 0.85;
uniform float line_dark = 0.42;             // line = local colour x this
uniform float depth_threshold = 0.025;
uniform float colour_threshold = 0.45;
uniform float line_fade_far = 120.0;
group_uniforms grade;
uniform float saturation = 1.22;
uniform float contrast = 1.0;
uniform float glow = 0.35;
uniform float glow_threshold = 0.72;
uniform int debug = 0;

void vertex() { POSITION = vec4(VERTEX.xy * 2.0, 0.0, 1.0); }

float lin_depth(vec2 uv, mat4 ip) {
	float d = textureLod(depth_tex, uv, 0.0).r;
	vec4 v = ip * vec4(uv * 2.0 - 1.0, d * 2.0 - 1.0, 1.0);
	return -v.z / v.w;
}
float luma(vec3 c) { return dot(c, vec3(0.299, 0.587, 0.114)); }

void fragment() {
	vec2 px = 1.0 / VIEWPORT_SIZE;
	float rs = max(VIEWPORT_SIZE.y / 1080.0, 0.5);
	vec2 uv = SCREEN_UV;
	vec3 c0 = textureLod(screen_tex, uv, 0.0).rgb;
	// --- 1. bilateral smoothing ---
	vec3 acc = vec3(0.0); float wsum = 0.0;
	for (int j = -2; j <= 2; j++) for (int i = -2; i <= 2; i++) {
		vec3 c = textureLod(screen_tex, uv + vec2(float(i), float(j)) * px * smooth_px * rs, 0.0).rgb;
		vec3 dc = c - c0;
		float w = exp(-dot(dc, dc) / (2.0 * smooth_sigma * smooth_sigma)) * exp(-float(i * i + j * j) / 8.0);
		acc += c * w; wsum += w;
	}
	vec3 sm = acc / wsum;
	vec3 col = mix(sm, c0, detail_keep);
	// --- 2. cel light bands with hue-shifted shadows ---
	float L = luma(sm);
	float q = L * cel_bands; float f = fract(q);
	float Lq = (floor(q) + smoothstep(0.5 - cel_soft, 0.5 + cel_soft, f)) / cel_bands;
	vec3 cel = col * (Lq / max(L, 1e-3));
	float shade = 1.0 - smoothstep(0.25, 0.6, Lq);
	cel *= mix(light_tint, shadow_tint, shade);
	col = mix(col, cel, cel_amount);
	// --- 3. outlines ---
	vec2 o = px * rs * 1.25;
	float d0 = lin_depth(uv, INV_PROJECTION_MATRIX);
	float dj = 0.0; float cj = 0.0;
	for (int k = 0; k < 4; k++) {
		vec2 dir = k == 0 ? vec2(1, 0) : k == 1 ? vec2(-1, 0) : k == 2 ? vec2(0, 1) : vec2(0, -1);
		dj = max(dj, abs(lin_depth(uv + dir * o, INV_PROJECTION_MATRIX) - d0));
		cj = max(cj, length(textureLod(screen_tex, uv + dir * o, 0.0).rgb - c0));
	}
	float far_fade = 1.0 - smoothstep(line_fade_far * 0.5, line_fade_far, d0);
	float line = max(smoothstep(depth_threshold, depth_threshold * 2.5, dj / max(d0, 0.1)),
	                 smoothstep(colour_threshold, colour_threshold * 1.8, cj) * 0.7) * far_fade;
	col = mix(col, col * line_dark, line * line_amount);
	// --- 4. grade + glow ---
	vec3 gl = vec3(0.0);
	for (int k = 0; k < 8; k++) {
		float a = 6.2832 * float(k) / 8.0;
		vec3 c = textureLod(screen_tex, uv + vec2(cos(a), sin(a)) * px * rs * 9.0, 0.0).rgb;
		gl += max(c - vec3(glow_threshold), vec3(0.0));
	}
	col += gl / 8.0 * glow;
	float l2 = luma(col);
	col = vec3(l2) + (col - vec3(l2)) * saturation;
	col = (col - 0.5) * contrast + 0.5;
	if (debug == 1) col = vec3(line);
	ALBEDO = clamp(col, 0.0, 1.0);
}
