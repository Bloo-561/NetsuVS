shader_type canvas_item;
// Animated menu background: dark diagonal pin stripes, a colored glow around
// the edges, and thin light beams sliding across (Persona 4 Arena style).
// Every "uniform" below shows up in the Inspector under
// Material > Shader Parameters, so you can tweak it without touching code.
//
// Edge glow colors: the glow cycles between hue_min and hue_min + hue_range.
//   Hue is 0..1 around the color wheel: 0 red, 0.08 orange, 0.16 yellow,
//   0.33 green, 0.5 cyan, 0.6 blue, 0.75 purple.
//   Default = cyan to purple (matches the NETSU VS logo).
//   hue_range = 1.0 gives a full rainbow like Persona 4 Arena.

uniform vec3 base_color : source_color = vec3(0.02, 0.03, 0.08);
uniform float stripe_density = 140.0;
uniform float stripe_strength : hint_range(0.0, 1.0) = 0.35;
uniform float edge_glow : hint_range(0.0, 1.0) = 0.85;
uniform float hue_min : hint_range(0.0, 1.0) = 0.5;
uniform float hue_range : hint_range(0.0, 1.0) = 0.25;
uniform float glow_speed = 0.25;
uniform vec3 beam_color_a : source_color = vec3(0.35, 0.75, 1.0);
uniform vec3 beam_color_b : source_color = vec3(1.0, 1.0, 1.0);
uniform float beam_speed = 0.15;
uniform float aspect = 1.7778; // screen width / height

vec3 hue_to_rgb(float h) {
	vec3 k = abs(fract(vec3(h) + vec3(0.0, 2.0 / 3.0, 1.0 / 3.0)) * 6.0 - 3.0) - 1.0;
	return clamp(k, 0.0, 1.0);
}

// A thin bright line with a soft glow around it.
float beam(vec2 p, vec2 origin, vec2 dir, float width) {
	vec2 n = normalize(vec2(-dir.y, dir.x));
	float d = abs(dot(p - origin, n));
	return exp(-d / width) + exp(-d / (width * 12.0)) * 0.25;
}

void fragment() {
	vec2 uv = UV;
	vec2 p = vec2(uv.x * aspect, uv.y);
	vec3 col = base_color;

	// Slightly lighter slanted panel through the middle.
	float panel_dist = abs(dot(p - vec2(aspect * 0.5, 0.5), normalize(vec2(0.55, 1.0))));
	col += vec3(0.04, 0.05, 0.09) * (1.0 - smoothstep(0.38, 0.42, panel_dist));

	// Diagonal pin stripes.
	float s = fract((p.x - p.y) * stripe_density * 0.5);
	col *= 1.0 - stripe_strength * step(0.55, s);

	// Colored glow around the edges.
	vec2 c = (uv - 0.5) * vec2(1.0, 1.15);
	float edge = smoothstep(0.38, 0.75, length(c));
	float wave = 0.5 + 0.5 * sin(atan(c.y, c.x) * 2.0 + TIME * glow_speed * 6.28318);
	float hue = hue_min + hue_range * wave;
	col = mix(col, hue_to_rgb(hue) * 0.95, edge * edge_glow);

	// Two light beams drifting across.
	float t = TIME * beam_speed;
	col += beam_color_a * beam(p, vec2(aspect * (0.3 + 0.25 * sin(t)), 0.0), vec2(0.7, 1.0), 0.0015) * 0.9;
	col += beam_color_b * beam(p, vec2(aspect * (0.75 + 0.2 * cos(t * 0.8)), 0.0), vec2(-0.9, 1.0), 0.0012) * 0.7;

	COLOR = vec4(col, 1.0);
}
