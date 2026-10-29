shader_type canvas_item;

uniform vec2 scroll_speed;

void fragment(){
	vec2 newuv = UV;
	newuv.x += scroll_speed.x * TIME;
	newuv.y -= scroll_speed.y * TIME;
	vec4 c = texture(TEXTURE, newuv);
	COLOR = c;
}