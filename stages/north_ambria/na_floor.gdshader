// North Ambria - the snowfield floor, procedural, times the baked light map.
//   * soft wind-shaped dunes and ripples (shaded from a fake height field, lit from the bright gap behind)
//   * glittering ice sparkles that twinkle as the camera moves
//   * streaks of loose snow blowing across the ground with the wind, in gusts
// The floor stays flat; this is shading only (the fighters always stand on y = 0). Visual only.
shader_type spatial;
render_mode unshaded, cull_back, shadows_disabled;

uniform sampler2D light_tex : hint_default_white, filter_linear, repeat_disable;
uniform float light_max = 4.0;
uniform float floor_gain = 1.15;
uniform float light_saturation = 0.35;  // the baked light is quite blue; keep the snow mostly white
uniform vec2 floor_x = vec2(-40.0, 40.0);
uniform vec2 floor_z = vec2(-58.0, 22.0);

group_uniforms snow;
uniform vec3 snow_lit : source_color = vec3(0.95, 0.96, 0.99);
uniform vec3 snow_shade : source_color = vec3(0.72, 0.76, 0.84);
uniform float dune_scale = 0.22;       // dunes per metre
uniform float dune_strength = 0.7;
uniform float ripple_strength = 0.35;
uniform vec3 light_dir = vec3(0.0, 0.55, -1.0);   // toward the bright gap (behind the mound)
uniform float lane_calm = 0.5;         // dunes are softer right under the fighters

group_uniforms sparkle;
uniform float sparkle_density = 0.04;
uniform float sparkle_strength = 1.4;

group_uniforms wind;
uniform vec2 wind_dir = vec2(1.0, 0.25);
uniform float wind_speed = 4.0;        // metres per second
uniform float drift_strength = 0.35;
uniform float gust_period = 7.0;

group_uniforms look;      // keep in sync with src/bake_north_ambria.py
uniform float exposure = 0.0;
uniform float shoulder = 0.82;
uniform float saturation = 0.95;
uniform vec3 shadow_tint = vec3(0.86, 0.92, 1.14);
uniform vec3 highlight_tint = vec3(0.98, 1.0, 1.04);
uniform float tint_amount = 0.55;

varying vec3 wpos;
void vertex() { wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz; }

vec3 grade(vec3 lin) {
	vec3 c = max(lin, vec3(0.0)) * exp2(exposure);
	vec3 over = max(c - vec3(shoulder), vec3(0.0));
	vec3 soft = vec3(shoulder) + (1.0 - shoulder) * (1.0 - exp(-over / (1.0 - shoulder)));
	c = mix(c, soft, step(vec3(shoulder), c));
	float lum = dot(c, vec3(0.2126, 0.7152, 0.0722));
	c = vec3(lum) + (c - vec3(lum)) * saturation;
	float sh = pow(clamp(1.0 - lum / 0.45, 0.0, 1.0), 1.5) * tint_amount;
	float hi = clamp((lum - 0.5) / 0.5, 0.0, 1.0) * tint_amount;
	c *= (1.0 - sh) + sh * shadow_tint;
	c *= (1.0 - hi) + hi * highlight_tint;
	return clamp(c, 0.0, 1.0);
}
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vnoise(vec2 p) {
	vec2 i = floor(p), f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}
float height(vec2 p, float calm) {
	// big rounded dunes, stretched across the wind, plus small ripples
	vec2 q = vec2(p.x * 0.55, p.y) * dune_scale;
	float h = vnoise(q) * 0.6 + vnoise(q * 2.1 + 3.0) * 0.3 + vnoise(q * 4.3 + 7.0) * 0.1;
	float rip = sin(p.y * 2.2 + vnoise(p * 0.6) * 4.0) * 0.5 + 0.5;
	return h * dune_strength * calm + rip * ripple_strength * 0.15 * calm;
}

void fragment() {
	vec2 p = wpos.xz;
	vec2 luv = vec2((p.x - floor_x.x) / (floor_x.y - floor_x.x), 1.0 - (p.y - floor_z.x) / (floor_z.y - floor_z.x));
	vec3 light = pow(texture(light_tex, luv).rgb, vec3(2.2)) * light_max * floor_gain;
	float ll = dot(light, vec3(0.2126, 0.7152, 0.0722));
	light = vec3(ll) + (light - vec3(ll)) * light_saturation;
	float calm = 1.0 - lane_calm * (1.0 - smoothstep(2.0, 6.0, abs(p.y))) * (1.0 - smoothstep(12.0, 16.0, abs(p.x)));
	// fake normal from the height field
	float e = 0.15;
	float h0 = height(p, calm);
	float hx = height(p + vec2(e, 0.0), calm);
	float hz = height(p + vec2(0.0, e), calm);
	vec3 n = normalize(vec3(-(hx - h0) / e, 1.0, -(hz - h0) / e));
	float shade = clamp(0.55 + 0.6 * dot(n, normalize(light_dir)), 0.0, 1.2);
	vec3 alb = mix(snow_shade, snow_lit, shade);
	vec3 col = grade(alb * light);
	// blowing snow streaks drifting with the wind, in gusts
	float gust = 0.55 + 0.45 * sin(TIME * 6.2832 / gust_period) * sin(TIME * 6.2832 / (gust_period * 0.37));
	vec2 wd = normalize(wind_dir);
	vec2 wq = vec2(dot(p, wd), dot(p, vec2(-wd.y, wd.x)));
	float streak = vnoise(vec2(wq.x * 0.25 - TIME * wind_speed * 0.25, wq.y * 2.2)) * vnoise(vec2(wq.x * 0.6 - TIME * wind_speed * 0.6, wq.y * 4.0 + 5.0));
	col = mix(col, vec3(1.0, 1.0, 1.05), smoothstep(0.25, 0.6, streak) * drift_strength * gust);
	// sparkles: tiny glints that twinkle with the view direction
	vec2 cell = floor(p * 7.0);
	float sp = step(1.0 - sparkle_density, hash(cell));
	vec2 f = fract(p * 7.0) - vec2(hash(cell + 1.3), hash(cell + 2.7)) * 0.6 - 0.2;
	float tw = pow(max(0.0, sin(dot(VIEW, vec3(hash(cell + 4.0), hash(cell + 5.0), hash(cell + 6.0))) * 40.0 + TIME * 2.0)), 16.0);
	col += vec3(0.9, 0.95, 1.0) * sp * tw * (1.0 - smoothstep(0.02, 0.08, length(f))) * sparkle_strength;
	ALBEDO = col;
}
