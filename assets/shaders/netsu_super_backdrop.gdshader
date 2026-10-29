shader_type canvas_item;
// Netsu (Oct 24): the backdrop of a super (S-Craft), Under Night In-Birth style: the stage goes almost black
// and slow smoke in the fighter's colour drifts over it, thickest on her side. game/ui/battle_hud/netsu_cut_in.gd
// draws it on a full-screen rect under the fighters and sets these values every frame.

uniform vec4 smoke_color : source_color = vec4(0.75, 0.08, 0.16, 1.0);
uniform vec4 base_color : source_color = vec4(0.012, 0.008, 0.03, 1.0);
uniform float amount : hint_range(0.0, 1.0) = 1.0;   // overall strength (fades it in and out)
uniform float seconds = 0.0;                         // time since the super started
uniform float from_left = 1.0;                       // 1 = her side is the left, -1 = the right
uniform float aspect = 1.7778;

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float noise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}

float fbm(vec2 p) {
	float v = 0.0;
	float a = 0.5;
	for (int i = 0; i < 5; i++) {
		v += a * noise(p);
		p = p * 2.03 + vec2(1.7, 9.2);
		a *= 0.5;
	}
	return v;
}

void fragment() {
	vec2 uv = UV;
	vec2 p = vec2(uv.x * aspect, uv.y) * 2.6;
	float t = seconds;
	// smoke rolls away from her side and slowly upwards
	vec2 drift = vec2(-0.32 * from_left, 0.1) * t;
	float warp = fbm(p * 0.8 + drift * 0.6);
	float n = fbm(p + drift + vec2(warp * 1.6, warp * 0.8));
	float smoke = smoothstep(0.42, 0.9, n);
	// thicker on her side and low down, a dark band across the top
	float side_x = from_left > 0.0 ? 1.0 - uv.x : uv.x;
	float weight = 0.35 + 0.65 * smoothstep(0.0, 0.85, side_x);
	weight *= 0.55 + 0.45 * smoothstep(0.0, 0.7, uv.y);
	// a glow behind her
	vec2 c = vec2(from_left > 0.0 ? 0.3 : 0.7, 0.58);
	float glow = smoothstep(0.75, 0.0, distance(vec2(uv.x * aspect, uv.y), vec2(c.x * aspect, c.y)));
	vec3 col = base_color.rgb;
	col += smoke_color.rgb * smoke * weight * 0.9;
	col += smoke_color.rgb * glow * 0.32;
	col += vec3(1.0) * pow(smoke * weight, 3.0) * 0.12;
	float vignette = smoothstep(1.25, 0.35, length((uv - vec2(0.5)) * vec2(1.5, 1.15)));
	col *= mix(0.45, 1.0, vignette);
	COLOR = vec4(col, amount);
}
