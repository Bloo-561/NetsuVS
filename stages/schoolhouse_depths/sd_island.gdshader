// Depths of the Old Schoolhouse - floating ruins: slow bob and a gentle sway around their own centre.
// Each Island_* node has its origin at the island's centre, so the phase differs per island. Visual only.
shader_type spatial;
render_mode unshaded, cull_back, shadows_disabled;

uniform sampler2D albedo_tex : source_color, filter_linear_mipmap;
uniform float bob = 1.2;            // metres
uniform float bob_speed = 0.25;
uniform float sway = 0.035;         // radians
uniform float haze = 0.18;          // fade toward the sky colour (distance)
uniform vec3 haze_color : source_color = vec3(0.35, 0.7, 0.9);

varying float dist;
void vertex() {
	vec3 o = NODE_POSITION_WORLD;
	float ph = o.x * 0.37 + o.z * 0.21;
	float a = sin(TIME * bob_speed * 0.7 + ph) * sway;
	float c = cos(a), s = sin(a);
	VERTEX.xy = mat2(vec2(c, -s), vec2(s, c)) * VERTEX.xy;
	VERTEX.y += sin(TIME * bob_speed + ph) * bob;
	dist = length(o - CAMERA_POSITION_WORLD);
}

void fragment() {
	vec3 col = texture(albedo_tex, UV).rgb;
	ALBEDO = mix(col, haze_color, clamp(haze * (dist - 60.0) / 100.0, 0.0, 0.5));
}
