// Ordis Royal Manor - candle flames on the chandeliers (crossed quads, UV.x across, UV.y = flame id + height).
// A small teardrop that sways and flickers, white-yellow core, orange rim. Additive. Visual only.
shader_type spatial;
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled;

uniform vec3 core_color : source_color = vec3(1.0, 0.95, 0.75);
uniform vec3 rim_color : source_color = vec3(1.0, 0.55, 0.15);
uniform float intensity = 1.8;
uniform float sway = 0.12;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vnoise(vec2 p) {
	vec2 i = floor(p), f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}

void fragment() {
	float id = -floor(UV.y);
	float h = 1.0 - fract(UV.y);
	float t = TIME * 3.0 + id * 2.37;
	float x = UV.x * 2.0 - 1.0 - (vnoise(vec2(t, id)) - 0.5) * sway * 2.0 * h;
	// teardrop: round at the bottom, pointed at the top
	float w = (h < 0.3) ? sqrt(max(0.0, 1.0 - pow((0.3 - h) / 0.3, 2.0))) : pow(max(0.0, 1.0 - (h - 0.3) / 0.7), 1.3);
	w *= 0.8;
	float shape = 1.0 - smoothstep(w * 0.55, w, abs(x));
	shape *= step(0.02, h);
	float core = 1.0 - smoothstep(w * 0.1, w * 0.55, abs(x));
	core *= 1.0 - smoothstep(0.15, 0.6, h);
	vec3 c = mix(rim_color, core_color, core);
	float flick = 0.85 + 0.3 * vnoise(vec2(TIME * 9.0, id * 3.1));
	ALBEDO = c * shape * intensity * flick;
}
