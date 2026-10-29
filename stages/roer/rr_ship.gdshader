// Roer - airships far over the factory district (visual only). Card group "Ship": UV 0..1 over the card (id in UV.y).
// A long hull with tail fins and a gondola, backlit by the sunset (a warm rim on top), navigation lights blinking;
// they drift slowly across the sky.
shader_type spatial;
render_mode unshaded, cull_disabled, shadows_disabled, fog_disabled;

uniform vec3 hull_dark : source_color = vec3(0.3, 0.27, 0.36);
uniform vec3 hull_rim : source_color = vec3(1.0, 0.7, 0.5);
uniform float drift = 28.0;           // metres either way
uniform float drift_period = 420.0;

varying float vid;
void vertex() {
	vid = -floor(UV.y);
	VERTEX.x += sin(TIME * 6.2831853 / drift_period + vid * 2.1) * drift;
	VERTEX.y += sin(TIME * 0.31 + vid) * 0.6;
}

void fragment() {
	float id = vid;
	vec2 p = vec2(UV.x, 1.0 - fract(UV.y));
	bool flip = mod(id, 2.0) > 0.5;
	if (flip) { p.x = 1.0 - p.x; }
	// hull: an elongated ellipse, nose to the right
	vec2 q = (p - vec2(0.54, 0.6)) / vec2(0.4, 0.2);
	float hull = step(length(q), 1.0);
	// tail fins (left end), gondola underneath
	float fin = step(p.x, 0.22) * step(0.08, p.x) * step(abs(p.y - 0.6) - (0.22 - p.x) * 1.6, 0.0) * step(abs(p.y - 0.6), 0.34);
	float gon = step(0.42, p.x) * step(p.x, 0.62) * step(0.3, p.y) * step(p.y, 0.4);
	float m = max(hull, max(fin, gon));
	if (m < 0.5) { discard; }
	vec3 col = hull_dark * (0.85 + 0.25 * smoothstep(-1.0, 1.0, q.y));
	col = mix(col, hull_rim, hull * smoothstep(0.75, 1.0, length(q)) * step(0.0, q.y) * 0.8);
	col *= 1.0 - 0.18 * step(0.5, fract(p.x * 14.0)) * hull;                 // ribs
	col = mix(col, vec3(1.0, 0.8, 0.5) * 1.4, gon * step(0.33, p.y) * step(p.y, 0.37) * step(0.5, fract(p.x * 40.0)));
	float blink = step(0.8, fract(TIME * 0.7 + id * 0.37));
	col = mix(col, vec3(2.5, 0.3, 0.2), blink * step(length(p - vec2(0.12, 0.88)), 0.025));
	ALBEDO = col;
}
