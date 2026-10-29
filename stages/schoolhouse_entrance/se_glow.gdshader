// Old Schoolhouse -Entrance- - the lantern glasses: warm and flickering, each lantern on its own
// (phase from its position). Card group "Glow". Visual only.
shader_type spatial;
render_mode unshaded, cull_disabled, shadows_disabled, fog_disabled;

uniform vec3 glow_color : source_color = vec3(1.0, 0.74, 0.4);
uniform float energy = 1.8;
uniform float flicker = 0.12;

varying vec3 wpos;
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
void vertex() { wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz; }

void fragment() {
	float ph = hash(floor(wpos.xz * 1.5)) * 6.2831853;
	float f = 1.0 + flicker * (sin(TIME * 6.1 + ph) * 0.5 + sin(TIME * 11.7 + ph * 1.7) * 0.3 + sin(TIME * 23.0 + ph * 2.3) * 0.2);
	float core = 0.85 + 0.3 * smoothstep(0.4, 1.0, abs(NORMAL.y) < 0.5 ? 1.0 : 0.0);
	ALBEDO = glow_color * energy * f * core;
}
