// Celdic - sky above the town (visual only), computed from the VIEW DIRECTION (a sky at infinity).
// One shader for both variants:
//   Day:     blue gradient with big drifting cumulus clouds (bright tops, soft grey undersides)
//   Burning: heavy dark storm clouds lit red-orange from below by the fires, a glowing horizon,
//            and the cloud undersides pulse with the firelight
shader_type spatial;
render_mode unshaded, cull_disabled, shadows_disabled, fog_disabled, depth_draw_opaque;

uniform vec3 zenith_color : source_color = vec3(0.1, 0.3, 0.76);
uniform vec3 sky_color : source_color = vec3(0.28, 0.54, 0.9);
uniform vec3 horizon_color : source_color = vec3(0.86, 0.92, 0.96);
uniform vec3 cloud_lit : source_color = vec3(1.0, 1.0, 1.0);
uniform vec3 cloud_shade : source_color = vec3(0.62, 0.68, 0.78);
uniform float cloud_cover : hint_range(0.0, 1.0) = 0.38;
uniform float cloud_softness = 0.07;
uniform float cloud_scale = 0.7;
uniform vec2 wind = vec2(0.010, 0.003);
uniform float brightness = 1.0;

group_uniforms fire_glow;              // Burning variant
uniform vec3 glow_color : source_color = vec3(1.0, 0.35, 0.1);
uniform float glow_strength = 0.0;     // red light on the cloud undersides
uniform float glow_height = 0.25;      // how high the glow reaches (direction-y)
uniform float glow_pulse = 0.25;
uniform float flash_strength = 0.0;    // Burning: sudden distant flashes on the horizon
uniform float flash_rate = 0.35;       // flashes per second (roughly)

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vnoise(vec2 p) {
	vec2 i = floor(p), f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}
float fbm(vec2 p) {
	float s = 0.0, a = 0.5;
	for (int i = 0; i < 6; i++) { s += vnoise(p) * a; p = p * 2.02 + vec2(3.1, 1.7); a *= 0.5; }
	return s / 0.98;
}

varying vec3 wpos;
void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec3 d = normalize(wpos - CAMERA_POSITION_WORLD);
	float y = d.y;
	float t = TIME;
	vec3 col = mix(horizon_color, sky_color, smoothstep(0.0, 0.2, y));
	col = mix(col, zenith_color, smoothstep(0.15, 0.7, y));
	// clouds on a flat sky plane (puffy: two fbm layers, darker where thick)
	// a curved cloud layer (not a flat plane): clouds near the horizon stay big and puffy instead of streaking
	vec2 p = d.xz / (max(y, 0.0) + 0.3) * cloud_scale + wind * t * 10.0;
	// puffy cumulus: a low-frequency mass, eroded by finer billows; shaded darker underneath / inside
	float big = fbm(p * 0.6);
	float n = fbm(p * 1.7 + 3.0);
	float n2 = fbm(p * 4.3 + 5.0 + wind * t * 6.0);
	float dens = big * 0.7 + n * 0.3 + (n2 - 0.5) * 0.18;
	float c = smoothstep(1.0 - cloud_cover - cloud_softness, 1.0 - cloud_cover + cloud_softness, dens);
	float core = smoothstep(1.0 - cloud_cover, 1.0 - cloud_cover + 0.25, dens);
	float lit = clamp(0.55 + (n2 - n) * 1.4 + (1.0 - core) * 0.45, 0.0, 1.0);
	float thick = 1.0 - lit;
	vec3 cc = mix(cloud_shade, cloud_lit, lit);
	// fire glow on the undersides (strongest low in the sky), flickering
	float low = 1.0 - smoothstep(0.0, glow_height, y);
	float pulse = 1.0 - glow_pulse + glow_pulse * vnoise(vec2(t * 1.3, d.x * 3.0));
	cc += glow_color * glow_strength * low * pulse * (0.4 + 0.6 * thick);
	col += glow_color * glow_strength * 0.5 * low * low * pulse;
	// distant flashes: a random spot on the horizon lights up briefly every few seconds
	float slot = floor(TIME * flash_rate);
	float ph = fract(TIME * flash_rate);
	float fx = hash(vec2(slot, 3.7)) * 2.0 - 1.0;
	float fl = exp(-ph * 10.0) * step(0.35, hash(vec2(slot, 9.1)));
	float spot = exp(-pow((atan(d.x, -d.z) - fx * 1.2) * 2.5, 2.0)) * (1.0 - smoothstep(0.0, 0.35, y));
	vec3 flash = glow_color * 1.8 * fl * spot * flash_strength;
	cc += flash * 1.2; col += flash * 0.6;
	float fade = smoothstep(-0.02, 0.06, y);
	col = mix(col, mix(horizon_color, cc, smoothstep(0.0, 0.12, y) * 0.8 + 0.2), c * fade);
	ALBEDO = col * brightness;
}
