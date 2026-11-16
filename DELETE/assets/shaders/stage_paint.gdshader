// Netsu stage "painted illustration" filter (E's Laf look). Put it on a QuadMesh in a STAGE scene
// (see stages/septian_chapel/septian_chapel_trails.tscn, node PaintFX). It is drawn first in the transparent pass
// (render_priority -128, no depth test), so it repaints only what the opaque pass drew - the stage - and the
// fighters, effects and UI are drawn crisp on top.
//   1. Kuwahara (4 sectors): flattens detail into painted brush patches, keeps the edges sharp
//   2. ink lines where the depth jumps (silhouettes of buildings, props, trees against what is behind)
//   3. soft value banding, a colour grade (saturation, split tone), a faint canvas grain
// GPU only, no effect on gameplay / rollback.
shader_type spatial;
render_mode unshaded, depth_test_disabled, depth_draw_never, cull_disabled, shadows_disabled, blend_mix, fog_disabled;

uniform sampler2D screen_tex : hint_screen_texture, filter_nearest, repeat_disable;
uniform sampler2D depth_tex : hint_depth_texture, filter_nearest, repeat_disable;

group_uniforms paint;
uniform int radius : hint_range(1, 6) = 5;          // brush size in pixels (at 1080p); 0-cost knob for low-end GPUs
uniform float strength : hint_range(0.0, 1.0) = 1.0;
uniform float spread : hint_range(1.0, 3.0) = 1.35;    // sample spacing: a wider brush for the same cost
uniform int debug = 0;                               // 1 = show depth, 2 = show the ink mask
group_uniforms ink;
uniform float ink_amount : hint_range(0.0, 1.0) = 0.9;
uniform vec3 ink_color : source_color = vec3(0.12, 0.10, 0.14);
uniform float ink_threshold = 0.02;                 // relative depth jump that draws a line
uniform float ink_fade_far = 140.0;                  // lines fade out with distance (metres)
group_uniforms grade;
uniform float bands : hint_range(0.0, 32.0) = 9.0;  // soft value banding (0 = off)
uniform float band_softness : hint_range(0.0, 1.0) = 0.55;
uniform float saturation = 1.2;
uniform float contrast = 1.08;
uniform vec3 shadow_tint : source_color = vec3(0.86, 0.88, 1.0);
uniform vec3 highlight_tint : source_color = vec3(1.0, 0.98, 0.93);
uniform float grain = 0.025;

void vertex() {
	POSITION = vec4(VERTEX.xy * 2.0, 0.0, 1.0);      // full-screen quad (QuadMesh 1 x 1)
}

float lin_depth(vec2 uv, mat4 inv_proj) {
	float d = textureLod(depth_tex, uv, 0.0).r;
	vec4 v = inv_proj * vec4(uv * 2.0 - 1.0, d * 2.0 - 1.0, 1.0);
	return -v.z / v.w;
}
float luma(vec3 c) { return dot(c, vec3(0.299, 0.587, 0.114)); }
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vnoise(vec2 p) {
	vec2 i = floor(p), f = fract(p); vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);
}

void fragment() {
	vec2 px = 1.0 / VIEWPORT_SIZE;
	vec2 uv = SCREEN_UV;
	vec3 src = textureLod(screen_tex, uv, 0.0).rgb;
	// scale the brush with resolution so 720p and 1080p look alike
	float rs = VIEWPORT_SIZE.y / 1080.0;
	vec2 st = px * max(rs, 0.5) * spread;
	vec2 st1 = px * max(rs, 0.5);
	// --- 1. Kuwahara ---
	float ang = (vnoise(FRAGCOORD.xy / (90.0 * max(rs, 0.5))) - 0.5) * 2.6;
	mat2 R = mat2(vec2(cos(ang), sin(ang)), vec2(-sin(ang), cos(ang)));
	vec3 m[4]; vec3 s[4];
	for (int k = 0; k < 4; k++) { m[k] = vec3(0.0); s[k] = vec3(0.0); }
	float n = float((radius + 1) * (radius + 1));
	for (int j = 0; j <= radius; j++) {
		for (int i = 0; i <= radius; i++) {
			vec3 c;
			c = textureLod(screen_tex, uv + R * vec2(-float(i), -float(j)) * st, 0.0).rgb; m[0] += c; s[0] += c * c;
			c = textureLod(screen_tex, uv + R * vec2( float(i), -float(j)) * st, 0.0).rgb; m[1] += c; s[1] += c * c;
			c = textureLod(screen_tex, uv + R * vec2(-float(i),  float(j)) * st, 0.0).rgb; m[2] += c; s[2] += c * c;
			c = textureLod(screen_tex, uv + R * vec2( float(i),  float(j)) * st, 0.0).rgb; m[3] += c; s[3] += c * c;
		}
	}
	vec3 col = src; float best = 1e9;
	for (int k = 0; k < 4; k++) {
		vec3 mu = m[k] / n;
		vec3 va = abs(s[k] / n - mu * mu);
		float v = va.r + va.g + va.b;
		if (v < best) { best = v; col = mu; }
	}
	col = mix(src, col, strength);
	// --- 2. ink lines on depth discontinuities ---
	float d0 = lin_depth(uv, INV_PROJECTION_MATRIX);
	float dl = lin_depth(uv - vec2(st1.x, 0.0) * 2.0, INV_PROJECTION_MATRIX);
	float dr = lin_depth(uv + vec2(st1.x, 0.0) * 2.0, INV_PROJECTION_MATRIX);
	float du = lin_depth(uv - vec2(0.0, st1.y) * 2.0, INV_PROJECTION_MATRIX);
	float dd = lin_depth(uv + vec2(0.0, st1.y) * 2.0, INV_PROJECTION_MATRIX);
	float jump = max(max(abs(dl - d0), abs(dr - d0)), max(abs(du - d0), abs(dd - d0))) / max(d0, 0.1);
	float ink = smoothstep(ink_threshold, ink_threshold * 2.5, jump) * (1.0 - smoothstep(ink_fade_far * 0.5, ink_fade_far, d0));
	col = mix(col, ink_color, ink * ink_amount);
	// --- 3. banding, grade, grain ---
	if (bands > 0.0) {
		float l = luma(col);
		float q = l * bands; float f = fract(q);
		float qs = (floor(q) + smoothstep(0.5 - band_softness * 0.5, 0.5 + band_softness * 0.5, f)) / bands;
		col *= qs / max(l, 1e-3);
	}
	float l2 = luma(col);
	col = vec3(l2) + (col - vec3(l2)) * saturation;
	col = (col - 0.5) * contrast + 0.5;
	col *= mix(shadow_tint, highlight_tint, smoothstep(0.15, 0.85, l2));
	col += (hash(floor(FRAGCOORD.xy / 2.0)) - 0.5) * grain;
	if (debug == 1) col = vec3(fract(d0 / 20.0), textureLod(depth_tex, uv, 0.0).r, 0.0);
	if (debug == 2) col = vec3(ink);
	ALBEDO = clamp(col, 0.0, 1.0);
}
