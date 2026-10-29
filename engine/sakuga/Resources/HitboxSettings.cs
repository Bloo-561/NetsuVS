using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
[Tool]
[Icon("res://assets/sakuga_ui/Icons/Icon_Hitbox.png")]
public partial class HitboxSettings : Resource
{
	[Export(PropertyHint.None, "")]
	public BoxShape Pushbox;

	[Export(PropertyHint.None, "")]
	public HitboxElement[] Hitboxes;
}
