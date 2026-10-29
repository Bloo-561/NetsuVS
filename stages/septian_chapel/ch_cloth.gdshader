// Septian Chapel - washing on the line, stirring in the breeze (visual only). Card group "Cloth": UV.x across,
// UV.y = item + height.  0 a white sheet, 1 a pale blue shirt, 2 a striped tea towel.
shader_type spatial;
render_mode unshaded, cull_disabled, shadows_disabled, fog_disabled;

uniform float light = 1.0;
varying float cid;
void vertex() {
	cid = -floor(UV.y);
	float h = 1.0 - fract(UV.y);
	float w = (1.0 - h);
	VERTEX.z += (sin(TIME * 1.9 + cid * 1.7) * 0.5 + 0.5) * 0.22 * w;
	VERTEX.x += sin(TIME * 1.3 + cid) * 0.04 * w;
}
void fragment() {
	float h = 1.0 - fract(UV.y);
	float u = UV.x;
	float hem = 0.03 * sin(u * 12.0 + TIME * 2.0 + cid);
	if (h < hem + 0.02) { discard; }
	vec3 col = vec3(0.95, 0.94, 0.9);
	if (cid > 0.5 && cid < 1.5) {
		col = vec3(0.66, 0.78, 0.92);
		if (h < 0.75 && (u < 0.08 || u > 0.92)) { discard; }        // the shirt's shape: no sleeves below the shoulders
		col *= 1.0 - 0.15 * step(abs(u - 0.5), 0.01);
	}
	if (cid > 1.5) { col = mix(vec3(0.94, 0.9, 0.8), vec3(0.72, 0.22, 0.2), step(0.5, fract(u * 6.0)) * step(0.7, h) * step(h, 0.85)); }
	float fold = 0.86 + 0.14 * sin(u * 22.0 + sin(TIME * 1.5 + cid) * 2.0);
	col *= fold * (0.9 + 0.1 * h);
	col *= 1.0 - step(0.97, h) * 0.3;                                // shadow under the pegs
	ALBEDO = col * light;
}
