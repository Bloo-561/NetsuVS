// Crimson Abyss - 360 degree storm sky around the crater. Visual only.
// The painted sky (mirrored so it wraps) slowly turns around the crater, writhes with a
// domain warp, and dark cloud masses with crimson-lit edges drift over it at their own speeds.
// Pink sheet lightning flickers in the clouds every few seconds.
// UV.x runs 0..2 around the ring (the image ping-pongs so it is seamless); UV.y 0 = top.
shader_type spatial;
render_mode unshaded, cull_disabled, fog_disabled, shadows_disabled, depth_draw_opaque;

uniform sampler2D sky_tex : source_color, filter_linear_mipmap, repeat_disable;   // no wrap: the fold edges must not blend with the far side
uniform float rot_speed = 0.0055;        // ring units per second (2 units = full circle)
uniform float warp_amount = 0.008;
uniform float warp_speed = 0.05;
uniform float cloud_speed = 0.016;
uniform float cloud_dark = 0.6;
uniform vec3 cloud_rim : source_color = vec3(0.85, 0.16, 0.42);
uniform float rim_gain = 0.55;
uniform float shimmer = 0.18;
uniform vec3 flash_color : source_color = vec3(1.0, 0.62, 0.92);
uniform float flash_period = 8.5;
uniform float flash_strength = 0.55;
uniform float brightness = 1.0;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vnoise(vec2 p) {
	vec2 i = floor(p), f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}
float fbm(vec2 p) {
	float s = 0.0, a = 0.5;
	for (int i = 0; i < 5; i++) { s += vnoise(p) * a; p = p * 2.03 + vec2(1.7, 9.2); a *= 0.5; }
	return s / 0.97;
}

void fragment() {
	vec2 uv = UV;
	float t = TIME;
	// painted layer: rotates around the crater, ping-pong mirrored so the ring is seamless
	float s = uv.x + t * rot_speed;
	vec2 w = vec2(fbm(vec2(s * 6.0, uv.y * 3.0) + vec2(t * warp_speed, -t * warp_speed * 0.7)),
	              fbm(vec2(s * 6.0, uv.y * 3.0) + vec2(-t * warp_speed * 0.8, t * warp_speed) + 9.0)) - 0.5;
	vec2 pu = vec2(abs(fract(s * 0.5) * 2.0 - 1.0), uv.y) + w * warp_amount * (1.4 - uv.y);
	// explicit gradients from the continuous ring coordinate: the fold/wrap would otherwise
	// pick the smallest mip along one pixel column and draw a thin vertical seam
	vec2 g = vec2(s * 0.5 * 2.0, uv.y);
	vec3 c = textureGrad(sky_tex, pu, dFdx(g), dFdy(g)).rgb;
	float pink = clamp((c.r - c.g) * 2.2 - 0.25, 0.0, 1.0);
	c *= 1.0 + pink * shimmer * sin(t * 2.3 + pu.x * 40.0 + pu.y * 25.0);
	// drifting dark cloud masses (faster than the painting -> the sky churns and moves)
	float hfade = smoothstep(0.82, 0.45, uv.y);                        // fade out toward the horizon
	vec2 cp = vec2(uv.x * 9.0 + t * cloud_speed * 9.0, uv.y * 4.0 + 0.15 * sin(t * 0.07 + uv.x * 3.0));
	float n1 = fbm(cp + 2.0 * vec2(fbm(cp * 0.5 + t * 0.01), 0.0));
	float dark = smoothstep(0.48, 0.78, n1) * hfade;
	float rim = (smoothstep(0.40, 0.47, n1) - smoothstep(0.47, 0.56, n1)) * hfade;
	float n2 = fbm(vec2(uv.x * 22.0 - t * cloud_speed * 14.0, uv.y * 8.0));
	float wisp = smoothstep(0.55, 0.85, n2) * hfade;
	c *= 1.0 - dark * cloud_dark - wisp * 0.25;
	c += cloud_rim * rim * rim_gain * (0.6 + 0.4 * sin(t * 0.8 + uv.x * 12.0));
	// sheet lightning
	float cyc = floor(t / flash_period);
	float ph = fract(t / flash_period) * flash_period;
	float f = exp(-ph * 9.0) + 0.7 * exp(-max(ph - 0.16, 0.0) * 7.0) * step(0.16, ph);
	vec2 centre = vec2(0.55 + 0.9 * hash(vec2(cyc, 1.7)) - 0.45, 0.25 + 0.3 * hash(vec2(cyc, 4.2)));
	vec2 d = (uv - vec2(1.0 + centre.x - 0.55, centre.y)) * vec2(3.0, 5.0);
	float blob = exp(-dot(d, d));
	float cloud = clamp(dot(c, vec3(0.33)) * 2.0, 0.2, 1.0);
	c += flash_color * f * blob * cloud * flash_strength;
	ALBEDO = max(c, vec3(0.0)) * brightness;
}
