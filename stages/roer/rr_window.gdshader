// Roer - the windows (visual only). Card group "Win": UV.x across (shop windows use 2..3), UV.y = window id + height.
// At dusk about half the windows are lit: warm rooms with a ceiling light, some with curtains or a cool orbal-screen
// glow, now and then one switching on or off. The dark ones reflect the sunset sky. Shop windows are all lit.
// Fades into the smog with distance like the baked buildings.
shader_type spatial;
render_mode unshaded, cull_disabled, shadows_disabled, fog_disabled;

uniform float lit_fraction = 0.55;
uniform float energy = 1.25;
uniform float shop_energy = 1.55;
uniform vec3 warm : source_color = vec3(1.0, 0.76, 0.46);
uniform vec3 cool : source_color = vec3(0.62, 0.82, 1.0);
uniform vec3 frame_color : source_color = vec3(0.12, 0.12, 0.14);
uniform vec3 refl_low : source_color = vec3(0.92, 0.58, 0.44);
uniform vec3 refl_high : source_color = vec3(0.26, 0.24, 0.4);
uniform vec3 haze_color : source_color = vec3(0.7, 0.5, 0.48);
uniform vec2 haze_range = vec2(60.0, 260.0);
uniform float haze_max = 0.6;

varying vec3 wpos;
float h1(float n) { return fract(sin(n * 12.9898 + 4.1) * 43758.5453); }
void vertex() { wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz; }

void fragment() {
	float id = -floor(UV.y);
	float h = 1.0 - fract(UV.y);
	bool shop = UV.x > 1.5;
	float u = shop ? UV.x - 2.0 : UV.x;
	float r = h1(id);
	bool on = shop || r < lit_fraction;
	// a few windows switch on and off over time
	if (!shop && h1(id + 7.3) > 0.94) { on = fract(TIME / 47.0 + h1(id + 2.0)) < 0.55; }
	vec3 col;
	if (on) {
		vec3 tint = h1(id + 3.1) > 0.82 ? cool : warm * (0.85 + 0.3 * h1(id + 5.0));
		float lamp = 0.6 + 0.4 * smoothstep(0.0, 1.0, h);                        // brighter under the ceiling light
		col = tint * lamp * (shop ? shop_energy : energy);
		if (!shop && h1(id + 9.0) > 0.5) {                                        // curtains: dimmer, folds
			float fold = 0.75 + 0.25 * sin(u * 25.0 + id);
			col *= mix(1.0, 0.55 * fold, step(abs(u - 0.5), 0.5 - 0.18 * h1(id + 1.0)));
		}
		if (shop) {                                                               // shelves and goods
			col *= 0.8 + 0.2 * step(0.5, fract(h * 4.0));
			col *= 0.75 + 0.25 * step(0.3, h1(floor(u * 9.0) + id * 13.0));
		}
		// flicker of an orbal screen in the cool rooms
		if (h1(id + 3.1) > 0.82) { col *= 0.9 + 0.1 * sin(TIME * 7.0 + id); }
	} else {
		// dark glass reflecting the dusk sky (the view vector bounced off the facade)
		vec3 v = normalize(wpos - CAMERA_POSITION_WORLD);
		vec3 rf = reflect(v, normalize(mat3(INV_VIEW_MATRIX) * NORMAL));
		col = mix(refl_low, refl_high, smoothstep(-0.05, 0.4, rf.y)) * 0.42;
		col += vec3(1.0, 0.8, 0.6) * 0.12 * smoothstep(0.85, 1.0, fract(u * 0.7 + h * 0.6 + id * 0.13));
	}
	// frame and mullions
	float fr = step(0.07, u) * step(u, 0.93) * step(0.06, h) * step(h, 0.94);
	float mull = shop ? step(abs(fract(u * 3.0) - 0.5), 0.47) : step(0.035, abs(u - 0.5));
	float tr = shop ? 1.0 : step(0.03, abs(h - 0.68));
	col = mix(frame_color, col, fr * mull * tr);
	float dist = length(wpos - CAMERA_POSITION_WORLD);
	col = mix(col, haze_color, smoothstep(haze_range.x, haze_range.y, dist) * haze_max);
	ALBEDO = col;
}
