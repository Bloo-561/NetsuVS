// Celdic - the cobbled town square. Visual only.
// Cobbles (cobble_tex, 4 m repeat) everywhere; inside the round paved area around the well they run
// in rings (polar mapping) with stone curb seams, like the painting. Multiplied by the baked light map
// and graded like the baked atlases. Burning variant: the fire light in the light map flickers.
shader_type spatial;
render_mode unshaded, cull_back, shadows_disabled;

uniform sampler2D cobble_tex : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D light_tex : hint_default_white, filter_linear, repeat_disable;
uniform float tile_m = 4.0;
uniform float light_max = 4.0;
uniform float floor_gain = 0.6;                // the open square catches a lot of sky; keep the stones mid-tone
uniform vec3 floor_ambient : source_color = vec3(0.0); // burning: a little firelit fill so the foreground isn't pitch black
uniform vec2 floor_x = vec2(-40.0, 40.0);
uniform vec2 floor_z = vec2(-62.0, 22.0);
uniform vec2 ring_centre = vec2(0.0, -18.0);
uniform float ring_radius = 9.5;
uniform float ring_stone = 1.1;           // cobble size inside the ring (relative to the square)

group_uniforms damage;
uniform float scorch = 0.5;               // burnt / sooty patches on the paving
uniform vec3 soot_color : source_color = vec3(0.06, 0.05, 0.05);
uniform float ember_glow = 0.0;           // Burning: embers glowing in the scorched cracks
uniform vec3 ember_color : source_color = vec3(1.0, 0.35, 0.08);
uniform float crater_strength = 1.0;
const vec4 CRATERS[4] = vec4[4](vec4(-8.0, -12.5, 2.6, 1.0), vec4(9.5, -21.0, 3.2, 1.0), vec4(-17.0, -4.0, 2.4, 1.0), vec4(17.5, -9.5, 2.2, 1.0));  // x, z, radius, weight

group_uniforms fire;
uniform float flicker = 0.0;              // 0 = off (day); ~0.18 for the burning town
uniform float flicker_speed = 9.0;

group_uniforms look;      // keep in sync with LOOKS in src/bake_celdic.py
uniform float exposure = 0.35;
uniform float shoulder = 0.8;
uniform float saturation = 1.12;
uniform vec3 shadow_tint = vec3(0.9, 0.92, 1.1);
uniform vec3 highlight_tint = vec3(1.06, 1.0, 0.92);
uniform float tint_amount = 0.5;

varying vec3 wpos;
void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

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

void fragment() {
	vec2 p = wpos.xz;
	vec2 luv = vec2((p.x - floor_x.x) / (floor_x.y - floor_x.x), 1.0 - (p.y - floor_z.x) / (floor_z.y - floor_z.x));
	vec3 light = pow(texture(light_tex, luv).rgb, vec3(2.2)) * light_max * floor_gain + floor_ambient;
	// cobbles: straight grid outside, concentric rings inside the round plaza
	vec2 d = p - ring_centre;
	float r = length(d);
	float ang = atan(d.x, d.y);
	vec2 puv = vec2(ang * r / tile_m / ring_stone, r / tile_m / ring_stone);
	vec2 duv = p / tile_m;
	vec3 alb_grid = textureGrad(cobble_tex, duv, dFdx(duv), dFdy(duv)).rgb;
	vec3 alb_ring = textureGrad(cobble_tex, puv, dFdx(duv) / ring_stone, dFdy(duv) / ring_stone).rgb;
	float inside = 1.0 - smoothstep(ring_radius - 0.05, ring_radius + 0.05, r);
	vec3 alb = mix(alb_grid, alb_ring * vec3(1.02, 0.98, 0.95), inside);
	// curb seams: a line of dark mortar at the ring edge and a second ring halfway in
	float aa = fwidth(r) * 1.5;
	float seam = (1.0 - smoothstep(0.06, 0.06 + aa, abs(r - ring_radius - 0.25)))
		+ 0.7 * (1.0 - smoothstep(0.05, 0.05 + aa, abs(r - ring_radius * 0.62)));
	alb *= 1.0 - 0.55 * clamp(seam, 0.0, 1.0);
	// fire flicker: only where the baked light is warm (near the flames)
	float warm = clamp((light.r - light.b) * 1.2, 0.0, 1.0);
	float t = TIME * flicker_speed;
	float fl = (vnoise(vec2(t, p.x * 0.05)) * 0.6 + vnoise(vec2(t * 2.3, p.y * 0.05 + 7.0)) * 0.4 - 0.5) * 2.0;
	light *= 1.0 + flicker * warm * fl;
	// scorch marks: blotchy patches (bigger near nothing in particular - the square has been fought over)
	float sn = vnoise(p * 0.22) * 0.55 + vnoise(p * 0.6 + 7.0) * 0.3 + vnoise(p * 2.1 + 3.0) * 0.15;
	float burn = smoothstep(0.66 - scorch * 0.3, 0.72 - scorch * 0.2, sn);
	float lane = 1.0 - 0.5 * (1.0 - smoothstep(1.5, 4.0, abs(p.y)));            // lighter right under the fighters
	burn *= lane;
	// blast marks: dark radial scorch with a lighter cracked rim (outside the fight lane)
	for (int i = 0; i < 4; i++) {
		vec2 c = CRATERS[i].xy; float rad = CRATERS[i].z;
		float dd = length(p - c) / rad;
		float ray = 0.75 + 0.25 * sin(atan(p.y - c.y, p.x - c.x) * 9.0 + float(i) * 2.0);
		burn = max(burn, (1.0 - smoothstep(0.4 * ray, 1.0 * ray, dd)) * CRATERS[i].w * crater_strength);
	}
	vec3 col = grade(alb * light);
	col = mix(col, soot_color * (0.7 + 0.6 * vnoise(p * 3.0)), burn * 0.85);
	// embers in the cracks of the burnt patches: dark mortar lines = low albedo
	float crack = smoothstep(0.32, 0.18, dot(alb, vec3(0.333)));
	float em = crack * burn * ember_glow * (0.55 + 0.45 * vnoise(vec2(TIME * 2.5, p.x * 2.0 + p.y)));
	col += ember_color * em;
	ALBEDO = col;
}
