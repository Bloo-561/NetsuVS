// The GeoFront (vault) - every glowing strip, line and lamp (card group "Glow").
// Blender UV.y = 2 * id + t (t 0..1 along the line); glTF flips v, so v = 1 - UV.y. The id picks colour + motion:
//   0 wall light strips (blue, a slow sweep runs around the room)
//   1 vault circuit lines (blue, energy pulses running out along each trace)
//   2 pillar rib glow (blue, waves climbing the ribbed sections)
//   3 amber lamps (warm, steady)        4 vault slot lines (blue, breathing)
// Colours > 1 feed the WorldEnvironment glow. Visual only.
shader_type spatial;
render_mode unshaded, cull_disabled, shadows_disabled, fog_disabled;

uniform vec3 blue : source_color = vec3(0.25, 0.65, 1.0);
uniform vec3 amber : source_color = vec3(1.0, 0.62, 0.26);
uniform float intensity = 1.6;
uniform float pulse_speed = 1.0;
uniform float alert = 0.0;               // 1 = red alert: everything blue turns red and pulses faster

varying vec3 wpos;
void vertex() { wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz; }

void fragment() {
	float v = 1.0 - UV.y;
	float id = floor(v * 0.5 + 1e-4);
	float s = clamp(v - 2.0 * id, 0.0, 1.0);
	float t = TIME * pulse_speed * (1.0 + alert);
	vec3 c = mix(blue, vec3(1.0, 0.15, 0.1), alert);
	float k = 1.0;
	if (id < 0.5) {
		float a = atan(wpos.x, -(wpos.z + 6.0));
		k = 0.8 + 1.2 * pow(0.5 + 0.5 * cos(a - t * 0.5), 18.0);
	} else if (id < 1.5) {
		k = 0.95 + 1.5 * pow(fract(s * 1.5 - t * 0.35), 10.0) + 0.15 * sin(t * 1.3);
	} else if (id < 2.5) {
		k = 0.6 + 0.8 * pow(0.5 + 0.5 * sin(wpos.y * 1.6 - t * 3.0 + wpos.x), 4.0);
	} else if (id < 3.5) {
		c = amber; k = 1.05 + 0.03 * sin(t * 9.0 + wpos.x * 3.0);
	} else {
		k = 0.75 + 0.35 * sin(t * 1.1 + wpos.x * 0.6);
	}
	ALBEDO = c * k * intensity;
}
