// Septian Chapel - swallows wheeling around the bell tower (visual only). Card group "Birds": a small card per bird,
// flown in circles by the vertex shader and drawn as a flapping silhouette.
shader_type spatial;
render_mode unshaded, cull_disabled, shadows_disabled, fog_disabled;

uniform vec3 bird_color : source_color = vec3(0.14, 0.13, 0.16);
uniform float speed = 0.45;

varying float bid;
void vertex() {
	bid = -floor(UV.y);
	float a = TIME * speed * (1.0 + 0.1 * bid) + bid * 0.9;
	float R = 4.0 + bid * 0.7;
	VERTEX += vec3(cos(a) * R, sin(TIME * 0.6 + bid) * 0.9, sin(a) * R * 0.6);
}
float seg(vec2 p, vec2 a, vec2 b) {
	vec2 pa = p - a, ba = b - a;
	float t = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
	return length(pa - ba * t);
}
void fragment() {
	vec2 p = vec2(UV.x, 1.0 - fract(UV.y)) * vec2(2.25, 1.0);
	float flap = sin(TIME * 9.0 + bid * 2.3);
	vec2 c = vec2(1.125, 0.45);
	vec2 lt = c + vec2(-0.95, 0.38 * flap), rt = c + vec2(0.95, 0.38 * flap);
	vec2 lm = c + vec2(-0.45, 0.15 + 0.12 * flap), rm = c + vec2(0.45, 0.15 + 0.12 * flap);
	float d = min(min(seg(p, c, lm), seg(p, lm, lt)), min(seg(p, c, rm), seg(p, rm, rt)));
	float body = length((p - c) * vec2(1.0, 1.6));
	if (d > 0.06 && body > 0.11) { discard; }
	ALBEDO = bird_color;
}
