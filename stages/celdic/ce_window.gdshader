// Celdic - window panes. Day: dark glass with a soft sky sheen. Burning: fire glowing inside, flickering.
shader_type spatial;
render_mode unshaded, cull_back, shadows_disabled;

uniform vec3 glass_color : source_color = vec3(0.12, 0.14, 0.17);
uniform vec3 sheen_color : source_color = vec3(0.55, 0.65, 0.75);
uniform vec3 fire_color : source_color = vec3(1.0, 0.55, 0.2);
uniform float fire = 0.0;            // 0 day, ~1.8 burning
uniform float flicker_speed = 7.0;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vnoise(vec2 p) {
	vec2 i = floor(p), f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}

varying vec3 wpos;
void vertex() { wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz; }

void fragment() {
	float sheen = smoothstep(0.3, 0.9, UV.y) * 0.35 + 0.15 * smoothstep(0.6, 0.0, abs(UV.x - UV.y + 0.2));
	vec3 c = mix(glass_color, sheen_color, sheen);
	float fl = 0.75 + 0.5 * vnoise(vec2(TIME * flicker_speed, wpos.x + wpos.z));
	vec3 f = fire_color * fire * fl * (0.6 + 0.4 * (1.0 - UV.y));
	ALBEDO = c * (1.0 - min(fire, 1.0) * 0.8) + f;
}
