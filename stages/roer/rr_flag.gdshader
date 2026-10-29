// Roer - the two red banners on the gateway arch (visual only). Card group "Flag": UV.x across, UV.y = id + height.
// Deep red with a gold border and a white gear emblem, a swallowtail hem, ripples running down the cloth.
shader_type spatial;
render_mode unshaded, cull_disabled, shadows_disabled, fog_disabled;

uniform vec3 cloth : source_color = vec3(0.58, 0.07, 0.08);
uniform vec3 trim : source_color = vec3(0.86, 0.66, 0.3);
uniform vec3 emblem : source_color = vec3(0.92, 0.9, 0.86);
uniform float light = 1.0;

void fragment() {
	float id = -floor(UV.y);
	float h = 1.0 - fract(UV.y);
	float u = UV.x;
	float wave = sin(h * 9.0 - TIME * 2.4 + id * 1.3) * (1.0 - h) * 0.03;
	u += wave;
	// swallowtail hem
	float cut = 0.1 * (1.0 - abs(u - 0.5) * 2.0);
	if (h < cut || u < 0.0 || u > 1.0) { discard; }
	vec3 col = cloth;
	float border = 1.0 - step(0.07, u) * step(u, 0.93) * step(cut + 0.06, h) * step(h, 0.92);
	col = mix(col, trim, border);
	// gear emblem
	vec2 q = (vec2(u, h) - vec2(0.5, 0.62)) * vec2(1.0, 3.3 / 1.4);
	float r = length(q), a = atan(q.y, q.x);
	float teeth = 0.34 + 0.05 * step(0.0, sin(a * 10.0));
	float gear = step(r, teeth) * step(0.22, r);
	float core = step(r, 0.13);
	float bar = step(abs(q.x), 0.045) * step(abs(q.y), 0.22);
	col = mix(col, emblem, max(max(gear, core), bar));
	col = mix(col, trim, step(abs(h - 0.3), 0.012) * step(0.12, u) * step(u, 0.88));
	// folds catch the light
	col *= light * (0.82 + 0.3 * sin(h * 9.0 - TIME * 2.4 + id * 1.3 + 1.2) * (1.0 - h) + 0.12 * sin(u * 18.0));
	ALBEDO = col;
}
