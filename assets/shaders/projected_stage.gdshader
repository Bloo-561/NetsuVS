// PROJECTED STAGE  (2.5D stages from a single painting)
//
// The stage is a simple 3D box room: floor, back wall, two side walls and a
// ceiling. Instead of normal UVs, every pixel of that room asks "where would
// I be in the painting if I were seen from the REFERENCE camera?" and takes
// that colour. From the reference camera the room looks exactly like the
// painting; when the fight camera pans or zooms you get real 3D parallax.
//
// Parts of the room the painting never shows (the side walls close to the
// camera, the ceiling overhead, far left/right floor) repeat the nearest
// painted part in 3D space, so the hall simply continues.
//
// Each surface of the room uses its own material with this shader and sets
// `surface`: 0 = floor, 1 = ceiling, 2 = side wall, 3 = back wall.
// Everything else is shared; see stages/thors_hall/README.md for how to make
// a new stage from a different painting.
shader_type spatial;
render_mode unshaded, cull_disabled;

uniform sampler2D painting : source_color, filter_linear_mipmap, repeat_disable;
uniform vec2 painting_size = vec2(1672.0, 941.0);
// Reference camera: where the "painter" stood (metres) and how they looked.
uniform vec3 ref_position = vec3(0.0, 1.5, 9.0);
uniform float focal_px = 1756.0;                 // 30 degree fov on a 941 px tall image
uniform vec2 horizon_px = vec2(836.0, 515.0);    // vanishing point in the painting
// Room size (must match the meshes in the stage scene).
uniform float half_width = 15.5;
uniform float ceiling_height = 8.4;
uniform float back_wall_z = -27.1;
uniform int surface = 0;
uniform float brightness = 1.0;

varying vec3 world_pos;

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

// Bounce t back and forth inside [lo, hi].
float ping_pong(float t, float lo, float hi) {
	float w = max(hi - lo, 0.001);
	float m = mod(t - lo, 2.0 * w);
	return lo + (m > w ? 2.0 * w - m : m);
}

void fragment() {
	vec3 p = world_pos;
	if (surface == 0 || surface == 1) {
		// Floor / ceiling: keep depth inside the painted part, then width.
		float rise = surface == 1 ? ceiling_height - ref_position.y : ref_position.y;
		float rows = surface == 1 ? horizon_px.y : painting_size.y - horizon_px.y;
		float z_near = ref_position.z - rise * focal_px / (rows - 2.0);
		p.z = ping_pong(p.z, back_wall_z, z_near);
		float half_painted = min((ref_position.z - p.z) * (horizon_px.x - 2.0) / focal_px, half_width);
		p.x = ping_pong(p.x, -half_painted, half_painted);
	} else if (surface == 2) {
		// Side walls: repeat the painted window bays along the hall.
		float z_near = ref_position.z - half_width * focal_px / (horizon_px.x - 2.0);
		p.z = ping_pong(p.z, back_wall_z, z_near);
	}
	vec3 rel = p - ref_position;
	float depth = max(-rel.z, 0.05);
	vec2 px = vec2(horizon_px.x + focal_px * rel.x / depth,
	               horizon_px.y - focal_px * rel.y / depth);
	vec2 uv = clamp(px / painting_size, vec2(0.0), vec2(1.0));
	ALBEDO = texture(painting, uv).rgb * brightness;
}
