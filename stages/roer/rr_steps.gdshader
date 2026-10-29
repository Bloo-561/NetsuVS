// Roer - the moving steps of the two giant escalators (visual only). Card group "Steps": UV.x across the step
// width, UV.y = id + position along the run (0 at the plaza, 1 at the Lower Level).  id 0 runs down, id 1 runs up.
shader_type spatial;
render_mode unshaded, cull_disabled, shadows_disabled, fog_disabled;

uniform float run_length = 17.13;      // metres from the top landing to the bottom one
uniform float speed = 0.5;             // m/s
uniform float step_depth = 0.4;
uniform vec3 tread_dark : source_color = vec3(0.13, 0.135, 0.15);
uniform vec3 tread_light : source_color = vec3(0.3, 0.31, 0.34);
uniform vec3 edge_color : source_color = vec3(0.95, 0.74, 0.2);
uniform vec3 glow_color : source_color = vec3(0.5, 0.9, 1.0);

void fragment() {
	float id = -floor(UV.y);
	float t = 1.0 - fract(UV.y);
	float dir = id < 0.5 ? 1.0 : -1.0;
	float s = t * run_length - dir * TIME * speed;
	float f = fract(s / step_depth);
	float groove = step(0.45, fract(UV.x * 46.0));
	vec3 col = mix(tread_dark, tread_light, groove * 0.8);
	col = mix(col, edge_color, smoothstep(0.86, 0.9, f) * (1.0 - smoothstep(0.96, 0.99, f)));   // yellow step nosing
	col = mix(col, edge_color * 0.9, step(UV.x, 0.035) + step(0.965, UV.x));                      // yellow side margins
	col *= mix(0.35, 1.0, smoothstep(0.0, 0.06, f));                                             // the gap between steps
	// the comb plates at both landings, and the blue skirt light spilling onto the edges
	col = mix(col, tread_light * 1.2, step(t, 0.012) + step(0.988, t));
	col += glow_color * 0.18 * (smoothstep(0.12, 0.0, UV.x) + smoothstep(0.88, 1.0, UV.x));
	col *= mix(1.05, 0.62, smoothstep(0.1, 0.95, t));                                             // darker down in the drop
	ALBEDO = col;
}
