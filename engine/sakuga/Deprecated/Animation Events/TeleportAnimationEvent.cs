using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class TeleportAnimationEvent : AnimationEvent
{
	[Export(PropertyHint.None, "")]
	public int Index;

	[Export(PropertyHint.None, "")]
	public Vector2I TargetPosition = Vector2I.Zero;

	[Export(PropertyHint.None, "")]
	public RelativeTo xRelativeTo;

	[Export(PropertyHint.None, "")]
	public RelativeTo yRelativeTo;
}
