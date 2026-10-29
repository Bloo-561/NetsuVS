using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class HitNotificationList : Resource
{
	[Export(PropertyHint.None, "")]
	public HitNotificationElement[] Elements;
}
