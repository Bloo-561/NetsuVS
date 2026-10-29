// Septian Chapel - the stained glass seen from outside in daylight (visual only). Card group "Glass":
//   id 0 the rose window (round)     id 1 the lancets on the facade and tower     id 2 the lancets along the nave
// Jewel colours in lead cames, dimmed as seen from the bright outdoors, with the sky reflected in the panes and a
// soft candle glow from within that breathes slowly.
shader_type spatial;
render_mode unshaded, cull_disabled, shadows_disabled, fog_disabled;

uniform float spring = 0.76;            // where the pointed arch springs (fraction of the lancet card height)
uniform float dim = 0.55;
uniform vec3 candle : source_color = vec3(1.0, 0.7, 0.4);
uniform float candle_glow = 0.12;
uniform vec3 sky_tint : source_color = vec3(0.7, 0.8, 0.95);

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
vec3 jewel(float r) {
	if (r < 0.28) return vec3(0.12, 0.24, 0.72);
	if (r < 0.48) return vec3(0.72, 0.1, 0.12);
	if (r < 0.62) return vec3(0.92, 0.7, 0.2);
	if (r < 0.76) return vec3(0.16, 0.5, 0.28);
	if (r < 0.88) return vec3(0.46, 0.2, 0.6);
	return vec3(0.86, 0.84, 0.7);
}
varying vec3 wpos;
void vertex() { wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz; }

void fragment() {
	float id = -floor(UV.y);
	float h = 1.0 - fract(UV.y);
	vec2 q = vec2(UV.x, h) * 2.0 - 1.0;
	vec3 col; float lead = 0.0;
	if (id < 0.5) {
		float r = length(q), a = atan(q.y, q.x);
		if (r > 1.0) { discard; }
		float sec = floor(a / 6.2831853 * 12.0 + 6.0);
		float band = floor(r * 4.0);
		col = jewel(hash(vec2(sec * (band > 1.5 ? 1.0 : 0.5), band)));
		if (r < 0.3) { col = vec3(0.95, 0.75, 0.3); }
		lead = max(step(abs(fract(a / 6.2831853 * 12.0) - 0.5), 0.05) * step(0.3, r),
		           max(step(abs(fract(r * 4.0) - 0.5), 0.06), step(0.94, r)));
		lead = max(lead, step(abs(r - 0.3), 0.03));
	} else {
		// pointed arch outline
		if (h > spring) {
			float yy = (h - spring) / (1.0 - spring) * 1.732;
			if ((q.x - 1.0) * (q.x - 1.0) + yy * yy > 4.0 || (q.x + 1.0) * (q.x + 1.0) + yy * yy > 4.0) { discard; }
		}
		// diamond quarries with a coloured medallion in the middle and a border
		vec2 dq = vec2(UV.x * 4.0 + h * 9.0, UV.x * 4.0 - h * 9.0);
		vec2 cell = floor(dq);
		col = mix(vec3(0.8, 0.82, 0.7), jewel(hash(cell + id * 7.0)), 0.55);
		float med = step(length(vec2(q.x, (h - 0.5) * 4.0)), 0.75);
		col = mix(col, jewel(hash(vec2(id, floor(h * 3.0)))) * 1.1, med);
		float border = 1.0 - step(0.12, UV.x) * step(UV.x, 0.88) * step(0.04, h);
		col = mix(col, vec3(0.7, 0.12, 0.12), border);
		vec2 f = fract(dq);
		lead = max(step(min(min(f.x, 1.0 - f.x), min(f.y, 1.0 - f.y)), 0.06) * (1.0 - med) * (1.0 - border), step(abs(length(vec2(q.x, (h - 0.5) * 4.0)) - 0.75), 0.06));
	}
	col *= dim;
	vec3 v = normalize(wpos - CAMERA_POSITION_WORLD);
	col += sky_tint * 0.16 * smoothstep(-0.4, 0.4, -v.y + h * 0.3);
	col += candle * candle_glow * (0.85 + 0.15 * sin(TIME * 1.3 + id * 2.0)) * (0.6 + 0.4 * sin(TIME * 7.0 + h * 3.0) * 0.1);
	col = mix(col, vec3(0.08, 0.08, 0.09), lead);
	ALBEDO = col;
}
