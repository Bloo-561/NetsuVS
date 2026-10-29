// Celdic - the strings of festival pennants from the arch. Each flag picks a colour from a small palette
// (by its id in UV.y) and flutters: the tip swings more than the top edge. Visual only.
shader_type spatial;
render_mode unshaded, cull_disabled, shadows_disabled;

uniform vec3 tint : source_color = vec3(1.0, 1.0, 1.0);    // day: white; burning: dim firelit orange
uniform float flutter = 0.12;                                // metres at the tip
uniform float speed = 2.2;

varying float fid;
varying float fv;

void vertex() {
	fid = -floor(UV.y);                                      // glTF flips v: Blender v = id + f  ->  1 - id - f
	fv = 1.0 - fract(UV.y);                                  // 0 = top edge, 1 = tip
	vec3 w = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float ph = fid * 1.7 + w.x * 0.4;
	VERTEX.z += sin(TIME * speed + ph) * flutter * fv;
	VERTEX.x += sin(TIME * speed * 1.3 + ph * 1.3) * flutter * 0.4 * fv;
}

void fragment() {
	int k = int(mod(fid * 7.0 + floor(fid / 5.0), 6.0));
	vec3 c = vec3(0.85, 0.22, 0.18);
	if (k == 1) { c = vec3(0.95, 0.7, 0.15); }
	if (k == 2) { c = vec3(0.2, 0.55, 0.3); }
	if (k == 3) { c = vec3(0.2, 0.42, 0.8); }
	if (k == 4) { c = vec3(0.85, 0.45, 0.15); }
	if (k == 5) { c = vec3(0.55, 0.25, 0.6); }
	c *= 0.85 + 0.15 * (1.0 - fv);
	ALBEDO = c * tint;
}
