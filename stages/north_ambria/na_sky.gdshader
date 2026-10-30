// North Ambria - the storm sky (visual only), drawn from the VIEW DIRECTION so it sits at infinity.
// Heavy dark clouds churning past on the wind, paler toward the horizon where the snow haze thickens, and a
// brighter break low over the horizon behind the rise whose light glows through the thinner cloud.
shader_type spatial;
render_mode unshaded, cull_disabled, shadows_disabled, fog_disabled, depth_draw_opaque;

uniform vec3 zenith_color : source_color = vec3(0.17, 0.19, 0.24);
uniform vec3 sky_color : source_color = vec3(0.34, 0.37, 0.44);
uniform vec3 horizon_color : source_color = vec3(0.66, 0.7, 0.77);
uniform vec3 cloud_lit : source_color = vec3(0.6, 0.64, 0.72);
uniform vec3 cloud_dark : source_color = vec3(0.15, 0.17, 0.22);
uniform vec2 wind = vec2(0.02, 0.004);
uniform float cloud_scale = 0.85;

group_uniforms gap;
uniform vec3 gap_dir = vec3(0.05, 0.07, -1.0);     // the brighter break, low over the horizon behind the rise
uniform vec3 gap_color : source_color = vec3(0.88, 0.91, 0.96);
uniform float gap_size = 0.1;
uniform float gap_strength = 0.45;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vnoise(vec2 p) {
	vec2 i = floor(p), f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}
float fbm(vec2 p) {
	float s = 0.0, a = 0.5;
	for (int i = 0; i < 6; i++) { s += vnoise(p) * a; p = mat2(vec2(0.8, 0.6), vec2(-0.6, 0.8)) * p * 2.02 + vec2(3.1, 1.7); a *= 0.5; }
	return s / 0.98;
}
varying vec3 wpos;
void vertex() { wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz; }

void fragment() {
	vec3 d = normalize(wpos - CAMERA_POSITION_WORLD);
	float y = d.y, t = TIME;
	// the fight cams only see y ~ -0.27 .. 0.3 (high cams a little more): the gradient is packed into that band
	vec3 col = mix(horizon_color, sky_color, smoothstep(0.0, 0.09, y));
	col = mix(col, zenith_color, smoothstep(0.08, 0.4, y));
	float g = max(dot(d, normalize(gap_dir)), 0.0);
	float ang = acos(clamp(g, -1.0, 1.0));
	// the break: a soft, round thinning of the cloud with a ragged edge, low on the horizon - no column, no panel
	float rag = fbm(vec2(atan(d.x, -d.z) * 5.0 + t * 0.02, d.y * 7.0)) - 0.5;
	float gap = (1.0 - smoothstep(gap_size * 0.2, gap_size * 1.4, ang + rag * gap_size * 0.6)) * (1.0 - smoothstep(0.02, 0.16, y));
	float halo = exp(-ang * ang / (gap_size * gap_size * 2.0)) * (1.0 - smoothstep(0.0, 0.2, y));
	// churning storm cloud, two layers at two speeds
	vec2 p = d.xz / (max(y, 0.0) + 0.22) * cloud_scale;     // gentler projection: no stretched streaks at the horizon
	vec2 q1 = p + wind * t * 10.0;
	vec2 q2 = p * 2.4 + wind * t * 22.0 + 5.0;
	float n = fbm(q1 + vec2(fbm(q1 * 0.45 + t * 0.015), 0.0) * 0.9);
	float n2 = fbm(q2);
	float dens = clamp(n * 0.85 + n2 * 0.35 - gap * 0.7 - halo * 0.2, 0.0, 1.0);
	float c = smoothstep(0.22, 0.62, dens);
	float lit = clamp(0.25 + (n2 - n) * 1.3 + halo * 0.8 - smoothstep(0.05, 0.35, y) * 0.3, 0.0, 1.0);
	col = mix(col, mix(cloud_dark, cloud_lit, lit), c * smoothstep(-0.02, 0.06, y));
	float through = (1.0 - c) * gap * 0.5 + halo * 0.1 * (1.0 - c * 0.8);
	col += gap_color * through * gap_strength * (0.88 + 0.12 * sin(t * 0.6));
	// the horizon melts into blowing snow
	col = mix(col, horizon_color, (1.0 - smoothstep(-0.03, 0.05, y)) * 0.7);
	ALBEDO = col;
}
