// Ordis Royal Manor (Ruined) - grey-black smoke rising from the fires up to the ceiling.
// Crossed quads: UV.x across, UV.y = column id + height (0 = base). Billowing noise scrolls upward;
// the base glows with firelight. Alpha blended. Visual only.
shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled;

uniform vec3 smoke_color : source_color = vec3(0.3, 0.28, 0.27);
uniform vec3 lit_color : source_color = vec3(0.6, 0.26, 0.1);
uniform float opacity = 0.6;
uniform float rise_speed = 0.06;
uniform float count = 99.0;          // only columns with id < count are drawn (Day: the smouldering ruins)

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vnoise(vec2 p) {
	vec2 i = floor(p), f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}
float fbm(vec2 p) {
	float s = 0.0, a = 0.5;
	for (int i = 0; i < 5; i++) { s += vnoise(p) * a; p = p * 2.03 + 1.3; a *= 0.5; }
	return s / 0.97;
}

void fragment() {
	float id = -floor(UV.y);            // glTF flips v (Blender v = id + h)
	float h = 1.0 - fract(UV.y);
	float t = TIME * rise_speed;
	// billowing puffs: isotropic noise (the card is ~1:1.4), domain-warped in both axes, scrolling up
	vec2 q = vec2(UV.x * 2.2 + id * 7.1, h * 3.0 - t * 4.0);
	vec2 w = vec2(fbm(q * 0.9 + vec2(0.0, t)), fbm(q * 0.9 + vec2(5.2, -t))) - 0.5;
	float n = fbm(q + w * 1.6);
	float x = abs(UV.x * 2.0 - 1.0 + w.x * 0.6);
	float width = 0.35 + 0.55 * h;                       // the plume widens as it rises
	float body = 1.0 - smoothstep(width * 0.55, width, x);
	float dens = body * (n + 0.25 * (1.0 - h)) ;
	float a = smoothstep(0.42, 0.6, dens) * smoothstep(0.0, 0.06, h) * (1.0 - smoothstep(0.65, 1.0, h));
	// shading: darker in the thick core, a lit rim on the puffs' lower edges, firelight only at the base
	float rim = smoothstep(0.42, 0.5, dens) - smoothstep(0.5, 0.62, dens);
	vec3 c = smoke_color * (0.75 + 0.5 * n);
	c += lit_color * (rim * 0.35 + (1.0 - smoothstep(0.0, 0.22, h)) * 0.9) ;
	ALBEDO = c;
	ALPHA = clamp(a * opacity, 0.0, 1.0) * step(id, count - 0.5);
}
