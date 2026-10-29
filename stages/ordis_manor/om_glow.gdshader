// Ordis Royal Manor - everything that glows warm: lamp shades (id 0), the gold cove strips along the
// cornices (id 1) and the sconce glasses (id 2). Card group "Glow": Blender UV.y = id + h (glTF flips v).
// Each lamp flickers softly on its own (phase from its position). Visual only.
shader_type spatial;
render_mode unshaded, cull_disabled, shadows_disabled, fog_disabled;

uniform vec3 shade_color : source_color = vec3(1.0, 0.8, 0.5);
uniform vec3 cove_color : source_color = vec3(1.0, 0.72, 0.36);
uniform vec3 sconce_color : source_color = vec3(1.0, 0.86, 0.62);
uniform float shade_energy = 1.5;
uniform float cove_energy = 1.35;
uniform float sconce_energy = 1.7;
uniform float flicker = 0.08;            // Ruined: raise it (lamps sputtering)
uniform float dead = 0.0;                // Ruined: fraction of lamps that have gone out

varying vec3 wpos;
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
void vertex() { wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz; }

void fragment() {
	float id = -floor(UV.y);
	float h = 1.0 - fract(UV.y);
	vec2 cell = floor(wpos.xz * 1.5);
	float ph = hash(cell) * 6.2831853;
	float f = 1.0 + flicker * (sin(TIME * 7.3 + ph) * 0.6 + sin(TIME * 13.1 + ph * 2.0) * 0.4);
	vec3 c;
	if (id < 0.5) {
		c = shade_color * shade_energy;
	} else if (id < 1.5) {
		float core = 1.0 - smoothstep(0.0, 0.5, abs(h - 0.5));
		c = cove_color * cove_energy * (0.75 + 0.5 * core);
		f = 1.0 + flicker * 0.3 * sin(TIME * 0.7 + wpos.x * 0.4 + wpos.z * 0.3);
	} else {
		c = sconce_color * sconce_energy;
	}
	if (dead > 0.0 && hash(cell + 9.1) < dead && id > 0.5) { c *= 0.08; }
	ALBEDO = c * f;
}
