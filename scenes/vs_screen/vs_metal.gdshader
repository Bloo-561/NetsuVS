shader_type canvas_item;
// The big "VS": a silver gradient over the letters (scenes/vs_screen/vs_screen.gd).
// top / bottom are the letters' top and bottom in the Label's own pixels.

uniform float top = 0.0;
uniform float bottom = 200.0;
uniform vec4 color_top : source_color = vec4(1.0, 1.0, 1.0, 1.0);
uniform vec4 color_mid : source_color = vec4(0.62, 0.7, 0.9, 1.0);
uniform vec4 color_bottom : source_color = vec4(0.97, 0.98, 1.0, 1.0);
uniform float mid = 0.56;
uniform float shine = 0.0;                               // a bright band sweeping across (0..1 = left..right)

varying vec2 local_pos;

void vertex() {
	local_pos = VERTEX;
}

void fragment() {
	vec4 c = texture(TEXTURE, UV) * COLOR;
	float t = clamp((local_pos.y - top) / max(bottom - top, 1.0), 0.0, 1.0);
	vec3 g = t < mid ? mix(color_top.rgb, color_mid.rgb, t / mid) : mix(color_mid.rgb, color_bottom.rgb, (t - mid) / (1.0 - mid));
	// thin bright line where the two halves meet, like polished metal
	g += vec3(0.35) * (1.0 - smoothstep(0.0, 0.035, abs(t - mid)));
	float band = 1.0 - smoothstep(0.0, 0.08, abs(local_pos.x / 330.0 - shine + (t - 0.5) * 0.25));
	g += vec3(0.6) * band * step(0.001, shine) * (1.0 - step(0.999, shine));
	COLOR = vec4(g, c.a);
}
