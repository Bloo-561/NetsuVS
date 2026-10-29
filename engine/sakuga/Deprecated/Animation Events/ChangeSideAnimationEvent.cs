using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class ChangeSideAnimationEvent : AnimationEvent
{
	[Export(PropertyHint.None, "")]
	public int Index;
}
