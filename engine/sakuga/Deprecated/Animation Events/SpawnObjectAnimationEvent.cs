using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class SpawnObjectAnimationEvent : AnimationEvent
{
	[Export(PropertyHint.None, "")]
	public ObjectType Object;

	[Export(PropertyHint.None, "")]
	public Vector2I TargetPosition = Vector2I.Zero;

	[Export(PropertyHint.None, "")]
	public RelativeTo xRelativeTo;

	[Export(PropertyHint.None, "")]
	public RelativeTo yRelativeTo;

	[Export(PropertyHint.None, "")]
	public int Index;

	[Export(PropertyHint.None, "")]
	public bool IsRandom;

	[Export(PropertyHint.None, "")]
	public int Range;

	[Export(PropertyHint.None, "")]
	public int FromExtraVariable = -1;

	[Export(PropertyHint.None, "")]
	public bool FollowParent;
}
