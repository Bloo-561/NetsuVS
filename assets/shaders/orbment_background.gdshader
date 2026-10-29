shader_type canvas_item;
// Character select background, Trails of Cold Steel style: deep navy with
// slowly turning gold rings like an ARCUS orbment. Seven small rings orbit
// the inner circle (one for each member of Class VII).
// Every "uniform" shows up in the Inspector under Material > Shader Parameters.

uniform vec3 top_color : source_color = vec3(0.04, 0.06, 0.14);
uniform vec3 bottom_color : source_color = vec3(0.01, 0.015, 0.045);
uniform vec3 ring_color : source_color = vec3(0.86, 0.72, 0.4);
uniform float ring_strength : hint_range(0.0, 1.0) = 0.22;
uniform vec2 ring_center = vec2(0.5, 0.45);
uniform float spin_speed = 0.02;
uniform float aspect = 1.7778; // screen width / height

// A thin circle outline of the given radius.
float ring(float dist, float radius, float width) {
	return 1.0 - smoothstep(width * 0.5, width * 0.5 + 0.0015, abs(dist - radius));
}

void fragment() {
	vec2 uv = UV;
	vec3 col = mix(top_color, bottom_color, uv.y);

	vec2 p = (uv - ring_center) * vec2(aspect, 1.0);
	float r = length(p);
	float a = atan(p.y, p.x);
	float t = TIME * spin_speed * 6.28318;

	float lines = 0.0;
	lines += ring(r, 0.26, 0.004);
	lines += ring(r, 0.40, 0.0025);
	lines += ring(r, 0.445, 0.007) * 0.6;
	lines += ring(r, 0.62, 0.003);

	// Tick marks between the two middle rings, turning clockwise.
	float ticks = step(0.5, fract((a + t) / 6.28318 * 96.0));
	lines += ticks * step(0.405, r) * step(r, 0.44) * 0.45;

	// Dashed outer ring turning the other way.
	float dashes = step(0.55, fract((a - t * 0.7) / 6.28318 * 28.0));
	lines += dashes * ring(r, 0.53, 0.004);

	// Seven quartz rings orbiting the inner circle.
	for (int i = 0; i < 7; i++) {
		float angle = -t * 0.5 + float(i) * 6.28318 / 7.0;
		vec2 c = vec2(cos(angle), sin(angle)) * 0.26;
		lines += ring(length(p - c), 0.034, 0.003);
	}

	col += ring_color * lines * ring_strength;
	col += ring_color * 0.06 * exp(-r * 3.0); // soft glow in the middle

	vec2 v = uv - 0.5;
	col *= 1.0 - dot(v, v) * 0.9; // darker corners

	COLOR = vec4(col, 1.0);
}
