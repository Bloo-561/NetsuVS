// Roer - trains crossing the viaduct behind its truss (visual only). Card group "Train": a 180 m strip along the
// deck, UV.x = metres / 20, UV.y = id + height (2.5 m). An orbal train (locomotive + carriages, lit windows)
// runs across every `period` seconds, alternating direction.
shader_type spatial;
render_mode unshaded, cull_disabled, shadows_disabled, fog_disabled;

uniform float span = 180.0;
uniform float speed = 24.0;           // m/s
uniform float period = 38.0;          // seconds between trains
uniform float phase = 0.16;           // so a train is on the viaduct at the start
uniform int cars = 6;
uniform vec3 body_color : source_color = vec3(0.24, 0.3, 0.42);
uniform vec3 stripe_color : source_color = vec3(0.86, 0.8, 0.66);
uniform vec3 window_color : source_color = vec3(1.0, 0.82, 0.52);
uniform vec3 haze_color : source_color = vec3(0.7, 0.5, 0.48);
uniform float haze = 0.22;

void fragment() {
	float x = UV.x * 20.0;
	float h = 1.0 - fract(UV.y);
	float hm = h * 2.5;
	float L = float(cars) * 18.6;
	float cyc = TIME / period + phase;
	float k = floor(cyc);
	float travel = fract(cyc) * period * speed;                    // metres travelled since this train entered
	bool rtl = mod(k, 2.0) > 0.5;
	float head = rtl ? span - travel : travel - 0.0;
	float s = rtl ? x - head : head - x;                           // metres behind the locomotive's nose
	if (s < 0.0 || s > L) { discard; }
	float car = floor(s / 18.6), lc = mod(s, 18.6);
	if (lc > 18.0) { if (hm < 1.0 || hm > 1.4) { discard; } }      // the coupling between cars
	if (hm < 0.15) { discard; }
	// the locomotive's rounded nose
	if (car < 0.5 && lc < 2.6) { float e = (2.6 - lc) / 2.6; if (hm > 2.25 - e * e * 1.4 || hm < 0.15 + e * 0.6) { discard; } }
	if (hm > 2.3) { discard; }
	vec3 col = body_color;
	col = mix(col, body_color * 0.55, step(2.05, hm));                         // roof
	col = mix(col, stripe_color, step(0.62, hm) * step(hm, 0.74));               // cream stripe
	col = mix(col, vec3(0.06), step(hm, 0.42));                                  // bogies / underframe
	float win = step(1.05, hm) * step(hm, 1.75) * step(0.35, fract(lc / 1.55)) * step(1.0, lc) * step(lc, 17.0);
	if (car < 0.5) { win = step(1.15, hm) * step(hm, 1.8) * step(lc, 2.4) * step(0.8, lc); }  // the cab window
	col = mix(col, window_color * 1.2, win);
	if (car < 0.5 && lc < 1.0 && hm > 0.8 && hm < 1.05) { col = vec3(2.2, 2.0, 1.6); }        // headlight
	ALBEDO = mix(col, haze_color, haze);
}
