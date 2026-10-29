// North Ambria - the blizzard sky (visual only), from the VIEW DIRECTION (a sky at infinity).
// Dark, heavy storm clouds racing with the wind; a bright gap in the clouds above the gravestones whose
// light shafts and glow breathe as clouds pass in front; streaks of driven snow across the whole sky.
shader_type spatial;
render_mode unshaded, cull_disabled, shadows_disabled, fog_disabled, depth_draw_opaque;

uniform vec3 zenith_color : source_color = vec3(0.12, 0.14, 0.2);
uniform vec3 sky_color : source_color = vec3(0.36, 0.4, 0.5);
uniform vec3 horizon_color : source_color = vec3(0.66, 0.71, 0.79);
uniform vec3 cloud_lit : source_color = vec3(0.66, 0.7, 0.8);
uniform vec3 cloud_dark : source_color = vec3(0.13, 0.15, 0.2);
uniform vec2 wind = vec2(0.03, 0.006);           // fast storm
uniform float cloud_scale = 0.9;

group_uniforms gap;
uniform vec3 gap_dir = vec3(0.0, 0.15, -1.0);    // the bright break in the clouds (behind the mound)
uniform vec3 gap_color : source_color = vec3(0.95, 0.97, 1.0);
uniform float gap_size = 0.11;                   // radius of the break, radians
uniform float gap_strength = 1.0;

group_uniforms snow;
uniform float streaks = 0.35;                    // driven snow streaks across the sky
uniform float streak_speed = 0.6;

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
void vertex() { wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz; }

void fragment() {
	vec3 d = normalize(wpos - CAMERA_POSITION_WORLD);
	float y = d.y;
	float t = TIME;
	// the fight cams only see a thin band of sky (y ~ 0 .. 0.3), so the gradient is packed into it
	vec3 col = mix(horizon_color, sky_color, smoothstep(0.0, 0.07, y));
	col = mix(col, zenith_color, smoothstep(0.05, 0.32, y));
	// the bright gap
	float g = max(dot(d, normalize(gap_dir)), 0.0);
	float ang = acos(clamp(g, -1.0, 1.0));
	// ragged edge: the break is torn open by the clouds, not a disc
	float rag = fbm(vec2(atan(d.x, -d.z) * 9.0 + t * 0.05, d.y * 12.0 - t * 0.03)) - 0.5;
	float gap = 1.0 - smoothstep(gap_size * 0.05, gap_size * 1.4, ang + rag * gap_size * 0.9);
	float halo = exp(-ang * ang / (gap_size * gap_size * 5.0));
	// storm clouds on a curved layer, two speeds, billowing
	vec2 p = d.xz / (max(y, 0.0) + 0.12) * cloud_scale;
	vec2 q1 = p + wind * t * 10.0;
	vec2 q2 = p * 2.3 + wind * t * 18.0 + 5.0;
	float n = fbm(q1 + vec2(fbm(q1 * 0.5 + t * 0.02), 0.0) * 0.8);
	float n2 = fbm(q2);
	float dens = clamp(n * 0.8 + n2 * 0.35 - gap * 0.6 - halo * 0.15, 0.0, 1.0);
	float c = smoothstep(0.25, 0.6, dens);
	float lit = clamp(0.2 + (n2 - n) * 1.4 + halo * 0.9 - smoothstep(0.05, 0.3, y) * 0.25, 0.0, 1.0);
	vec3 cc = mix(cloud_dark, cloud_lit, lit);
	col = mix(col, cc, c * smoothstep(-0.02, 0.08, y));
	// light from the gap glowing through thin cloud, pulsing as clouds race past
	float through = (1.0 - c) * gap * 0.75 + halo * 0.28 * (1.0 - c * 0.7);
	// light shafts fanning down from the break
	float ray = vnoise(vec2(atan(d.x, -d.z - 0.0) * 60.0, t * 0.05)) * smoothstep(0.2, 0.0, d.y) * halo;
	through += ray * 0.25 * (1.0 - c * 0.5);
	col += gap_color * through * gap_strength * (0.85 + 0.15 * sin(t * 0.7));
	// driven snow streaks
	float s = vnoise(vec2(d.x * 30.0 - t * streak_speed * 20.0, y * 160.0 + d.x * 40.0));
	col = mix(col, vec3(0.9, 0.93, 1.0), smoothstep(0.82, 0.95, s) * streaks);
	// the horizon disappears into white-out
	col = mix(col, horizon_color, (1.0 - smoothstep(-0.02, 0.05, y)) * 0.6);
	ALBEDO = col;
}
