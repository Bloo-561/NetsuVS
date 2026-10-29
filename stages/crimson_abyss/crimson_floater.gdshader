// Crimson Abyss - floating crystal shards: slow bob + spin around their own centre. Visual only.
shader_type spatial;
render_mode unshaded, cull_back, shadows_disabled;

uniform sampler2D albedo_tex : source_color, filter_linear_mipmap;
uniform float bob = 0.6;
uniform float spin = 0.12;

void vertex() {
	vec3 o = NODE_POSITION_WORLD;
	float ph = o.x * 0.37 + o.z * 0.21;
	float a = sin(TIME * 0.35 + ph) * spin + TIME * spin * 0.3;
	float c = cos(a), s = sin(a);
	VERTEX.xz = mat2(vec2(c, -s), vec2(s, c)) * VERTEX.xz;
	VERTEX.y += sin(TIME * 0.6 + ph) * bob;
}

void fragment() {
	ALBEDO = texture(albedo_tex, UV).rgb;
}
