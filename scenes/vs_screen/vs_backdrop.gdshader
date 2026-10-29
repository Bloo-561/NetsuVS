shader_type canvas_item;
// VS screen backdrop: the stage picture, softly blurred, darkened and tinted night-blue
// (scenes/vs_screen/vs_screen.gd). Cheap: 13 taps of the 1280x720 stage thumbnail.

uniform float blur : hint_range(0.0, 10.0) = 3.0;          // blur radius in pixels of the picture
uniform float darken : hint_range(0.0, 1.0) = 0.5;         // 0 = the picture as it is, 1 = all veil
uniform float desaturate : hint_range(0.0, 1.0) = 0.35;
uniform vec4 veil : source_color = vec4(0.03, 0.05, 0.17, 1.0);

void fragment() {
	vec2 px = TEXTURE_PIXEL_SIZE * blur;
	vec3 c = texture(TEXTURE, UV).rgb * 0.16;
	c += texture(TEXTURE, UV + vec2(px.x, 0.0)).rgb * 0.08;
	c += texture(TEXTURE, UV - vec2(px.x, 0.0)).rgb * 0.08;
	c += texture(TEXTURE, UV + vec2(0.0, px.y)).rgb * 0.08;
	c += texture(TEXTURE, UV - vec2(0.0, px.y)).rgb * 0.08;
	c += texture(TEXTURE, UV + px * 0.7).rgb * 0.07;
	c += texture(TEXTURE, UV - px * 0.7).rgb * 0.07;
	c += texture(TEXTURE, UV + vec2(px.x, -px.y) * 0.7).rgb * 0.07;
	c += texture(TEXTURE, UV + vec2(-px.x, px.y) * 0.7).rgb * 0.07;
	c += texture(TEXTURE, UV + vec2(px.x * 2.0, 0.0)).rgb * 0.0625;
	c += texture(TEXTURE, UV - vec2(px.x * 2.0, 0.0)).rgb * 0.0625;
	c += texture(TEXTURE, UV + vec2(0.0, px.y * 2.0)).rgb * 0.0625;
	c += texture(TEXTURE, UV - vec2(0.0, px.y * 2.0)).rgb * 0.0625;
	float grey = dot(c, vec3(0.299, 0.587, 0.114));
	c = mix(c, vec3(grey), desaturate);
	// the veil keeps a little of the picture's light, so lamps and windows still glow through
	c = mix(c, veil.rgb + c * 0.18, darken);
	COLOR = vec4(c, 1.0);
}
