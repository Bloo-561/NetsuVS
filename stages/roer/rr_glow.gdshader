// Roer - everything that glows (visual only). Card group "Glow"; the id (UV.y) picks what it is:
//   0 orbal lamp globes (warm)       1 orbal sign strips (cyan, a soft pulse)   2 the ROER letters (a shimmer sweeps across)
//   3 turbine rings (green, a chase runs round)   4 escalator skirt lights (dashes running with the steps)
//   5 the Reinford RF emblem / red signs          6 red aircraft beacons (blinking)   7 the cathedral rose window
shader_type spatial;
render_mode unshaded, cull_disabled, shadows_disabled, fog_disabled;

uniform vec3 lamp_color : source_color = vec3(1.0, 0.84, 0.6);
uniform vec3 sign_color : source_color = vec3(0.5, 0.9, 1.0);
uniform vec3 green_color : source_color = vec3(0.4, 1.0, 0.68);
uniform vec3 red_color : source_color = vec3(1.0, 0.22, 0.16);
uniform float energy = 1.0;
uniform float esc_speed = 0.5;          // m/s, same as the steps
uniform vec3 haze_color : source_color = vec3(0.7, 0.5, 0.48);
uniform vec2 haze_range = vec2(90.0, 320.0);
uniform float haze_max = 0.45;

varying vec3 wpos;
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
void vertex() { wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz; }

vec3 rose(vec2 q) {
	// q: -1..1 across the rose window. Returns colour, black outside (discarded by the caller).
	float r = length(q), a = atan(q.y, q.x);
	vec3 blue = vec3(0.2, 0.36, 1.0), red = vec3(1.0, 0.25, 0.2), gold = vec3(1.0, 0.78, 0.36), green = vec3(0.3, 0.8, 0.5);
	float pet = cos(a * 12.0);
	vec3 c = mix(blue, red, step(0.0, cos(a * 6.0 + 0.5)));
	c = mix(c, gold, smoothstep(0.24, 0.2, r));
	c = mix(c, green, step(0.62, r) * step(0.0, pet));
	float lead = max(step(abs(fract(a * 12.0 / 6.2831853 + 0.5) - 0.5), 0.04) * step(0.22, r),
	                 max(step(abs(r - 0.22), 0.03), max(step(abs(r - 0.6), 0.025), step(abs(r - 0.92), 0.04))));
	c *= 1.0 - lead * 0.85;
	return c * (1.3 - r * 0.4);
}

void fragment() {
	int id = int(-floor(UV.y) + 0.5);
	float h = 1.0 - fract(UV.y);
	float u = UV.x;
	float t = TIME;
	float ph = hash(floor(wpos.xz * 0.7)) * 6.2831853;
	vec3 col;
	if (id == 0) {
		col = lamp_color * 2.2 * (1.0 + 0.04 * sin(t * 9.0 + ph));
	} else if (id == 1) {
		col = sign_color * 1.9 * (0.88 + 0.12 * sin(t * 1.3 + ph));
	} else if (id == 2) {
		float sweep = exp(-pow(fract(wpos.x * 0.12 - t * 0.25) - 0.5, 2.0) * 60.0);
		col = mix(sign_color, vec3(0.9, 1.0, 1.0), 0.35) * (2.3 + 1.6 * sweep);
	} else if (id == 3) {
		float chase = smoothstep(0.75, 1.0, fract(u * 4.0 - t * 0.35));
		col = green_color * (1.5 + 1.8 * chase) * smoothstep(0.0, 0.25, h) * smoothstep(1.0, 0.75, h);
	} else if (id == 4) {
		float dir = wpos.x < 0.0 ? 1.0 : -1.0;               // left escalator runs down (away), right one up
		float dash = step(0.45, fract(u * 34.0 - dir * t * esc_speed * 2.0));
		col = sign_color * (1.0 + 1.4 * dash);
	} else if (id == 5) {
		col = red_color * 2.2 * (0.95 + 0.05 * sin(t * 60.0 + ph) * step(0.97, hash(vec2(floor(t * 3.0), ph))));
	} else if (id == 6) {
		float blink = step(0.72, fract(t * 0.5 + ph * 0.159));
		col = red_color * mix(0.25, 3.0, blink);
	} else {
		vec2 q = vec2(u, h) * 2.0 - 1.0;
		if (length(q) > 1.0) { discard; }
		col = rose(q) * 1.15 * (0.92 + 0.08 * sin(t * 0.8));
	}
	float dist = length(wpos - CAMERA_POSITION_WORLD);
	col = mix(col, haze_color, smoothstep(haze_range.x, haze_range.y, dist) * haze_max);
	ALBEDO = col * energy;
}
