// Septian Chapel - tufts of grass swaying in the breeze (visual only). Card group "Grass": two crossed cards per tuft,
// UV.x across, UV.y = kind + height.  kind 0 grass, 1 grass with wildflowers, 2 tall grass with seed heads.
// Blades are drawn in the shader (alpha cut); the tops sway with gusts that roll across the meadow.
shader_type spatial;
render_mode unshaded, cull_disabled, shadows_disabled, fog_disabled;

uniform vec3 base_color : source_color = vec3(0.17, 0.28, 0.1);
uniform vec3 tip_color : source_color = vec3(0.56, 0.72, 0.3);
uniform vec3 seed_color : source_color = vec3(0.86, 0.76, 0.48);
uniform float light = 1.0;
uniform float sway = 0.09;
uniform vec2 wind_dir = vec2(1.0, 0.35);

float hash(float n) { return fract(sin(n * 12.9898 + 1.7) * 43758.5453); }
varying float hv;
void vertex() {
	hv = 1.0 - fract(UV.y);
	float gust = 0.6 + 0.4 * sin(dot(VERTEX.xz, normalize(wind_dir)) * 0.22 - TIME * 1.4);
	float s = sin(TIME * 2.3 + VERTEX.x * 0.7 + VERTEX.z * 0.5) * 0.5 + 0.5;
	vec2 off = normalize(wind_dir) * sway * hv * (0.4 + 0.9 * gust) * (0.5 + 0.5 * s);
	VERTEX.xz += off;
}

void fragment() {
	float kind = -floor(UV.y);
	float h = 1.0 - fract(UV.y);
	float u = fract(UV.x);
	float seed = floor(UV.x);
	float a = 0.0; vec3 col = vec3(0.0); float best = -1.0;
	int n = kind > 1.5 ? 9 : 11;
	for (int i = 0; i < 11; i++) {
		if (i >= n) { break; }
		float fi = float(i);
		float c = 0.12 + 0.76 * hash(seed + fi * 3.1);
		float H = (kind > 1.5 ? 0.6 : 0.45) + 0.55 * hash(seed + fi * 5.7);
		float lean = (hash(seed + fi * 2.3) - 0.5) * 0.5;
		float w = 0.045 * (1.0 - h / H);
		float x = c + lean * h * h;
		if (h < H && abs(u - x) < w) { a = 1.0; float tt = h / H; vec3 bc = mix(base_color, tip_color, tt) * (0.85 + 0.3 * hash(seed + fi)); if (tt > best) { best = tt; col = bc; } }
		// flowers and seed heads at some blade tips
		if (kind > 0.5) {
			float fl = hash(seed + fi * 9.1);
			vec2 tip = vec2(c + lean * H * H, H);
			float r = length((vec2(u, h) - tip) * vec2(1.0, 0.7));
			if (kind < 1.5 && fl > 0.55 && r < 0.055) {
				a = 1.0;
				vec3 fc = fl > 0.85 ? vec3(0.62, 0.42, 0.86) : (fl > 0.7 ? vec3(0.98, 0.84, 0.24) : vec3(0.97, 0.96, 0.92));
				col = r < 0.018 ? vec3(0.95, 0.75, 0.2) : fc; best = 2.0;
			}
			if (kind > 1.5 && fl > 0.4 && abs(u - tip.x) < 0.025 && h > H && h < H + 0.12) { a = 1.0; col = seed_color; best = 2.0; }
		}
	}
	if (a < 0.5) { discard; }
	ALBEDO = col * light;
}
