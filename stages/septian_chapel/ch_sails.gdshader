// Septian Chapel - the windmill's four sails turning slowly (visual only). Card group "Sails": one square card.
// Wooden spars, a lattice frame with canvas on one side of each arm; hazed by the distance.
shader_type spatial;
render_mode unshaded, cull_disabled, shadows_disabled, fog_disabled;

uniform float speed = 0.32;
uniform vec3 wood : source_color = vec3(0.36, 0.26, 0.18);
uniform vec3 canvas : source_color = vec3(0.86, 0.82, 0.72);
uniform vec3 haze_color : source_color = vec3(0.72, 0.79, 0.88);
uniform float haze = 0.32;

void fragment() {
	vec2 q = vec2(UV.x, 1.0 - fract(UV.y)) * 2.0 - 1.0;
	float r = length(q);
	if (r > 1.0) { discard; }
	float a = atan(q.y, q.x) - TIME * speed;
	float m = 0.0; vec3 col = wood;
	for (int k = 0; k < 4; k++) {
		float ak = a - float(k) * 1.5707963;
		vec2 p = vec2(cos(ak), sin(ak)) * r;          // p.x along the arm, p.y across
		if (p.x > 0.0) {
			if (abs(p.y) < 0.022) { m = 1.0; col = wood; }
			if (p.x > 0.2 && p.x < 0.97 && p.y > 0.02 && p.y < 0.2) {
				float lat = step(abs(fract(p.x * 14.0) - 0.5), 0.42) * step(abs(fract(p.y * 18.0) - 0.5), 0.36);
				m = 1.0; col = mix(wood * 1.1, canvas * (0.9 + 0.1 * p.y * 5.0), lat * step(p.x, 0.92));
			}
		}
	}
	if (r < 0.06) { m = 1.0; col = wood * 0.8; }
	if (m < 0.5) { discard; }
	ALBEDO = mix(col, haze_color, haze);
}
