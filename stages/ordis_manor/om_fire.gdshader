// Ordis Royal Manor (Ruined) - flames on crossed quads. UV.x across the flame, UV.y = flame id + height (0 = base).
// Licking tongues from scrolling noise, white-yellow core -> orange -> red -> gone. Additive. Visual only.
shader_type spatial;
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled;

uniform vec3 core_color : source_color = vec3(1.0, 0.92, 0.6);
uniform vec3 mid_color : source_color = vec3(1.0, 0.45, 0.1);
uniform vec3 edge_color : source_color = vec3(0.7, 0.1, 0.02);
uniform float intensity = 1.6;
uniform float speed = 1.6;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vnoise(vec2 p) {
	vec2 i = floor(p), f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}
float fbm(vec2 p) {
	float s = 0.0, a = 0.5;
	for (int i = 0; i < 4; i++) { s += vnoise(p) * a; p = p * 2.1 + 3.7; a *= 0.5; }
	return s / 0.94;
}

void fragment() {
	float id = -floor(UV.y);            // glTF flips v (Blender v = id + h)
	float h = 1.0 - fract(UV.y);
	float x = UV.x * 2.0 - 1.0;
	float t = TIME * speed + id * 3.17;
	// two layers of rising noise make separate licking tongues
	float n1 = fbm(vec2(UV.x * 3.5 + id, h * 2.6 - t));
	float n2 = fbm(vec2(UV.x * 7.0 - id * 1.3, h * 5.5 - t * 1.7));
	float tongues = n1 * 0.62 + n2 * 0.38;
	float sway = (vnoise(vec2(t * 0.7, id)) - 0.5) * 0.4 * h;
	float width = (1.0 - h) * 0.9 + 0.1;
	float shape = 1.0 - smoothstep(width * 0.35, width, abs(x - sway) + (tongues - 0.5) * 0.95);
	shape *= smoothstep(0.0, 0.05, h);
	shape *= smoothstep(0.0, 0.22, tongues - h * 0.78 + 0.18);       // the top breaks up into licks
	float heat = shape * (1.2 - h) * (0.7 + 0.5 * tongues);
	vec3 c = mix(edge_color, mid_color, smoothstep(0.08, 0.42, heat));
	c = mix(c, core_color, smoothstep(0.5, 0.95, heat));
	float flick = 0.85 + 0.3 * vnoise(vec2(TIME * 8.0, id));
	ALBEDO = c * shape * intensity * flick;
}
