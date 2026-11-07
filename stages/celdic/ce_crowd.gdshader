// Celdic - the crowd of shadow figures (visual only). Card group "Crowd": one quad per person, facing the camera.
// UV.x = seed + across (0..1), UV.y = pose + height (glTF flips v: pose = -floor(UV.y), h = 1 - fract(UV.y)).
// The card is 0.7 x 1.18 figure-heights; the figure is drawn as a soft-cornered silhouette from capsules, with
// a thin lit rim. Day poses cheer in waves; burning poses are restless, worried and hunched.
//   0 cheer (both arms up, bouncing)  1 clap  2 watch, hands on hips  3 wave one arm  4 child jumping
//   5 hands to the face  6 hugging themselves  7 restless, pacing and looking about  8 carrying a bucket  9 sitting slumped
shader_type spatial;
render_mode unshaded, cull_disabled, shadows_disabled, fog_disabled, depth_draw_opaque;

uniform vec3 body_color : source_color = vec3(0.14, 0.16, 0.26);
uniform vec3 rim_color : source_color = vec3(0.5, 0.58, 0.76);
uniform float rim_amount = 0.55;
uniform vec2 rim_dir = vec2(0.45, 0.9);         // where the rim light comes from (figure space)
uniform vec3 haze_color : source_color = vec3(0.62, 0.72, 0.86);
uniform vec2 haze_range = vec2(14.0, 70.0);
uniform float haze_max = 0.5;
uniform float energy = 1.0;                       // how lively the cheering is
uniform float flicker = 0.0;                      // burning: the rim flickers with the firelight

float hash(float n) { return fract(sin(n * 12.9898 + 4.1) * 43758.5453); }

varying float v_seed;
varying float v_pose;
varying float v_t;
varying vec3 v_wpos;

void vertex() {
	v_seed = floor(UV.x);
	v_pose = -floor(UV.y);
	float h = 1.0 - fract(UV.y);
	float ph = hash(v_seed) * 6.2831;
	float t = TIME;
	v_t = t + ph;
	// cheering in waves that roll across the crowd
	float wave = 0.5 + 0.5 * sin(t * 0.8 - VERTEX.x * 0.18 + VERTEX.z * 0.05);
	float bob = 0.0;
	if (v_pose < 0.5) { bob = abs(sin(v_t * 4.6)) * 0.07 * wave; }
	else if (v_pose > 3.5 && v_pose < 4.5) { bob = abs(sin(v_t * 5.5)) * 0.14 * (0.4 + 0.6 * wave); }
	else if (v_pose > 0.5 && v_pose < 1.5) { bob = abs(sin(v_t * 7.0)) * 0.015; }
	VERTEX.y += bob * energy;
	// restless figures pace a little; bucket carriers sway as they walk
	if (v_pose > 6.5 && v_pose < 8.5) { VERTEX.x += sin(t * 0.45 + ph) * (v_pose > 7.5 ? 0.5 : 0.3); }
	v_wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

float cap(vec2 p, vec2 a, vec2 b, float r) {
	vec2 pa = p - a, ba = b - a;
	float k = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
	return length(pa - ba * k) - r;
}
float rbox(vec2 p, vec2 c, vec2 b, float r) {
	vec2 q = abs(p - c) - b + r;
	return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r;
}
float smin(float a, float b, float k) {
	float h = clamp(0.5 + 0.5 * (b - a) / k, 0.0, 1.0);
	return mix(b, a, h) - k * h * (1.0 - h);
}

float figure(vec2 q, float pose, float s, float t) {
	float wide = 0.9 + 0.3 * hash(s + 1.0);
	float dress = step(0.55, hash(s + 2.0));
	float hat = step(0.68, hash(s + 3.0));
	float kid = step(3.5, pose) * step(pose, 4.5);
	q.x /= wide;
	float sway = 0.0;
	if (pose > 6.5 && pose < 7.5) { sway = sin(t * 1.3) * 0.03; }
	vec2 head = vec2(sway * 1.4, 0.905);
	float hunch = (pose > 4.5 && pose < 7.5) ? 0.025 : 0.0;
	head.y -= hunch; head.x += hunch * 0.6;
	float d;
	if (pose > 8.5) {        // sitting slumped, head bowed, arms on the knees
		head = vec2(0.06, 0.62);
		d = length(q - head) - 0.066;
		d = smin(d, rbox(q, vec2(0.02, 0.44), vec2(0.08, 0.13), 0.04), 0.04);
		d = min(d, cap(q, vec2(0.0, 0.32), vec2(0.17, 0.32), 0.05));
		d = min(d, cap(q, vec2(0.17, 0.32), vec2(0.18, 0.02), 0.04));
		d = min(d, cap(q, vec2(0.06, 0.53), vec2(0.15, 0.36), 0.028));
		return d;
	}
	d = length(q - head) - 0.068;
	if (hat > 0.5) {
		d = min(d, rbox(q, head + vec2(0.0, 0.05), vec2(0.105, 0.012), 0.006));
		d = min(d, rbox(q, head + vec2(0.0, 0.085), vec2(0.06, 0.035), 0.015));
	}
	vec2 neck = vec2(sway, 0.8 - hunch);
	float torso = rbox(q, vec2(sway * 0.5 + hunch * 0.3, 0.66 - hunch * 0.5), vec2(0.088, 0.145), 0.04);
	d = smin(d, torso, 0.03);
	d = smin(d, cap(q, vec2(-0.09, 0.775 - hunch), vec2(0.09, 0.775 - hunch), 0.03), 0.03);
	if (dress > 0.5 && kid < 0.5) {
		float sk = rbox(q, vec2(0.0, 0.36), vec2(0.13 - (q.y - 0.2) * 0.18, 0.17), 0.03);
		d = smin(d, sk, 0.03);
		d = min(d, cap(q, vec2(-0.045, 0.22), vec2(-0.05, 0.02), 0.026));
		d = min(d, cap(q, vec2(0.045, 0.22), vec2(0.05, 0.02), 0.026));
	} else {
		float step_ = (pose > 7.5 && pose < 8.5) ? sin(t * 2.2) * 0.04 : 0.0;
		d = smin(d, cap(q, vec2(-0.045, 0.53), vec2(-0.06 - step_, 0.03), 0.036), 0.02);
		d = smin(d, cap(q, vec2(0.045, 0.53), vec2(0.06 + step_, 0.03), 0.036), 0.02);
	}
	// arms: shoulder -> elbow -> hand, by pose
	vec2 sL = vec2(-0.1, 0.77 - hunch), sR = vec2(0.1, 0.77 - hunch);
	vec2 eL = vec2(-0.13, 0.6), hL = vec2(-0.12, 0.44), eR = vec2(0.13, 0.6), hR = vec2(0.12, 0.44);
	float w1 = sin(t * 6.0) * 0.05, w2 = sin(t * 6.0 + 1.7) * 0.05;
	if (pose < 0.5 || kid > 0.5) {
		eL = vec2(-0.18, 0.92); hL = vec2(-0.17 + w1, 1.1); eR = vec2(0.18, 0.92); hR = vec2(0.17 + w2, 1.1);
	} else if (pose < 1.5) {
		float c = 0.012 + 0.045 * abs(sin(t * 7.0));
		eL = vec2(-0.14, 0.64); hL = vec2(-c, 0.76); eR = vec2(0.14, 0.64); hR = vec2(c, 0.76);
	} else if (pose < 2.5) {
		eL = vec2(-0.19, 0.62); hL = vec2(-0.1, 0.53); eR = vec2(0.19, 0.62); hR = vec2(0.1, 0.53);
	} else if (pose < 3.5) {
		eR = vec2(0.19, 0.9); hR = vec2(0.22 + sin(t * 5.0) * 0.07, 1.07);
	} else if (pose > 4.5 && pose < 5.5) {
		eL = vec2(-0.14, 0.7); hL = vec2(-0.035, 0.87 - hunch); eR = vec2(0.14, 0.7); hR = vec2(0.035, 0.87 - hunch);
	} else if (pose > 5.5 && pose < 6.5) {
		float shiver = sin(t * 23.0) * 0.004;
		eL = vec2(-0.13, 0.62); hL = vec2(0.07 + shiver, 0.72); eR = vec2(0.13, 0.62); hR = vec2(-0.07 + shiver, 0.7);
	} else if (pose > 7.5 && pose < 8.5) {
		eR = vec2(0.13, 0.6); hR = vec2(0.15, 0.45);
		d = min(d, rbox(q, vec2(0.16, 0.34), vec2(0.06, 0.07), 0.015));             // the bucket
		d = min(d, cap(q, vec2(0.1, 0.42), vec2(0.22, 0.42), 0.006));
	}
	d = min(d, cap(q, sL, eL, 0.03)); d = min(d, cap(q, eL, hL, 0.026));
	d = min(d, cap(q, sR, eR, 0.03)); d = min(d, cap(q, eR, hR, 0.026));
	return d;
}

void fragment() {
	float u = fract(UV.x);
	float h = 1.0 - fract(UV.y);
	vec2 q = vec2((u - 0.5) * 0.7, h * 1.18);
	float d = figure(q, v_pose, v_seed, v_t);
	if (d > 0.0) { discard; }
	vec2 L = normalize(rim_dir);
	float rim = step(0.0, figure(q + L * 0.016, v_pose, v_seed, v_t));
	float fl = 1.0 + flicker * (sin(TIME * 9.0 + v_seed) * 0.5 + sin(TIME * 13.7 + v_seed * 2.0) * 0.3);
	vec3 col = body_color * (0.9 + 0.2 * hash(v_seed + 5.0));
	col = mix(col, rim_color * fl, rim * rim_amount);
	float dist = length(v_wpos - CAMERA_POSITION_WORLD);
	col = mix(col, haze_color, smoothstep(haze_range.x, haze_range.y, dist) * haze_max);
	ALBEDO = col;
}
