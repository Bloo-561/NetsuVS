// Roer - the great rotors on top of the orbal turbines (visual only). Card group "Rotor": one square card per
// turbine (UV 0..1, id in UV.y). Three blades turning, a glowing green rim and hub.
shader_type spatial;
render_mode unshaded, cull_disabled, shadows_disabled, fog_disabled;

uniform vec3 blade_color : source_color = vec3(0.26, 0.27, 0.32);
uniform vec3 rim_color : source_color = vec3(0.4, 1.0, 0.68);
uniform vec3 haze_color : source_color = vec3(0.7, 0.5, 0.48);
uniform float haze = 0.5;

void fragment() {
	float id = -floor(UV.y);
	vec2 q = vec2(UV.x, 1.0 - fract(UV.y)) * 2.0 - 1.0;
	float r = length(q);
	if (r > 1.0) { discard; }
	float sp = 0.45 + 0.12 * id;
	float a = atan(q.y, q.x) + TIME * sp * (mod(id, 2.0) < 0.5 ? 1.0 : -1.0);
	float sector = fract(a / 6.2831853 * 3.0);
	float bw = mix(0.1, 0.03, r);                                                 // blades taper outward
	float blade = 1.0 - smoothstep(bw, bw + 0.02, abs(sector - 0.5) * 2.0 * 0.5);
	float rim = step(0.9, r) * step(r, 0.97);
	float hub = step(r, 0.16);
	float strut = step(0.86, r) * step(r, 0.9);
	float m = max(max(blade * step(0.12, r) * step(r, 0.9), rim), max(hub, strut));
	if (m < 0.5) { discard; }
	vec3 col = blade_color * (0.9 + 0.2 * q.y);
	col = mix(col, rim_color * 1.8, rim * (0.85 + 0.15 * sin(TIME * 2.0 + id)));
	col = mix(col, rim_color * 1.3, step(r, 0.08));
	ALBEDO = mix(col, haze_color, haze);
}
