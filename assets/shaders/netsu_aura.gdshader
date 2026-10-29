shader_type spatial;
// Netsu (Oct 24): the aura around a fighter during her EX move or super (Under Night In-Birth style).
// AnimationViewer.SetAura draws eight copies of the body sprite with this material, nudged a few pixels
// in every direction just behind the real sprite, so only a coloured rim shows around her.
// The engine fills in tex (the current sprite) and aura (colour; alpha = strength) every frame.
render_mode blend_mix, cull_disabled, unshaded, specular_disabled, depth_draw_never;

uniform sampler2D tex : source_color, filter_linear_mipmap;
uniform vec4 aura : source_color = vec4(1.0, 0.3, 0.4, 0.8);

void fragment() {
	float a = texture(tex, UV).a;
	// a hot core where the copies stack up, the aura colour towards the outside
	ALBEDO = mix(aura.rgb, vec3(1.0), 0.18);
	ALPHA = smoothstep(0.05, 0.6, a) * aura.a;
}
