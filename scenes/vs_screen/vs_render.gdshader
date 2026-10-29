shader_type canvas_item;
// VS screen fighter render (scenes/vs_screen/vs_screen.gd): fades out toward the bottom of the screen
// and past the slanted seam in the middle (so the two renders never pile up on each other), with a
// coloured rim light on the edges that face away from the middle.

uniform float side = 0.0;                                // 0 = player 1 (left), 1 = player 2 (right)
uniform float seam_x = 0.5;                              // where the seam crosses mid-height (0..1 of the screen)
uniform float seam_slant = 0.22;                         // how much the seam leans (like "/")
uniform float seam_soft = 0.09;
uniform float bottom_start : hint_range(0.0, 1.0) = 0.66;
uniform float bottom_end : hint_range(0.0, 1.0) = 0.99;
uniform vec4 rim_color : source_color = vec4(0.3, 0.6, 1.0, 1.0);
uniform float rim = 0.9;
uniform float rim_px = 7.0;                              // rim width in picture pixels
uniform float flash = 0.0;                               // 1 = solid white (entrance / VS slam)
uniform float shade = 0.0;                               // darken toward navy

void fragment() {
	vec4 c = texture(TEXTURE, UV);
	vec2 s = SCREEN_UV;
	// the seam leans like "/": further right at the top
	float x = s.x - (0.5 - s.y) * seam_slant;
	float keep = side < 0.5
		? 1.0 - smoothstep(seam_x - seam_soft * 0.2, seam_x + seam_soft, x)
		: smoothstep(seam_x - seam_soft, seam_x + seam_soft * 0.2, x);
	float fade = 1.0 - smoothstep(bottom_start, bottom_end, s.y);
	// rim light: picture edges whose outer side (toward the screen edge) is empty
	float dir = side < 0.5 ? -1.0 : 1.0;
	vec2 o = TEXTURE_PIXEL_SIZE * rim_px;
	float outside = texture(TEXTURE, UV + vec2(dir * o.x, -o.y * 0.4)).a;
	float edge = clamp(c.a - outside, 0.0, 1.0);
	vec3 col = c.rgb;
	col = mix(col, vec3(0.05, 0.07, 0.2), shade);
	col += rim_color.rgb * edge * rim;
	col = mix(col, vec3(1.0), flash);
	COLOR = vec4(col, c.a * keep * fade) * COLOR;
}
