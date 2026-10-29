using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class SuperArmorAnimationEvent : AnimationEvent
{
	[Export(PropertyHint.None, "")]
	public int ArmorValue;
}
