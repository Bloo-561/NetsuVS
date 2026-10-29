// Depths of the Old Schoolhouse - the green glowing glyph panels on the pillars and obelisks.
// glyph.png (white knotwork on black) is coloured green; the panels breathe and waves of energy
// climb up the pillars. Values above 1 feed the WorldEnvironment glow. Visual only.
shader_type spatial;
render_mode unshaded, cull_disabled, shadows_disabled, fog_disabled;

uniform sampler2D glyph_tex : hint_default_black, filter_linear_mipmap, repeat_disable;
uniform vec3 glow_color : source_color = vec3(0.24, 1.0, 0.58);
uniform vec3 core_color : source_color = vec3(0.85, 1.0, 0.9);
uniform float base_level = 0.35;       // panel brightness between the lines
uniform float line_gain = 1.6;
uniform float breathe = 0.18;          // slow brightness pulse
uniform float breathe_speed = 0.9;
uniform float wave_gain = 0.8;         // energy waves climbing the pillars
uniform float wave_speed = 0.6;        // metres per second
uniform float wave_spacing = 9.0;      // metres between waves

varying vec3 wpos;
void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	float g = texture(glyph_tex, UV).r;
	float ph = wpos.x * 0.37 + wpos.z * 0.21;
	float b = 1.0 - breathe + breathe * sin(TIME * breathe_speed + ph);
	float w = fract((abs(wpos.y) - TIME * wave_speed) / wave_spacing + ph * 0.1);
	float wave = pow(smoothstep(0.0, 0.08, w) * (1.0 - smoothstep(0.08, 0.3, w)), 1.5) * wave_gain;
	float edge = smoothstep(0.5, 0.0, min(min(UV.x, 1.0 - UV.x), min(UV.y, 1.0 - UV.y)) * 6.0) * 0.25;
	vec3 c = glow_color * (base_level + edge) + mix(glow_color, core_color, 0.4) * g * line_gain;
	ALBEDO = c * (b + wave);
}
