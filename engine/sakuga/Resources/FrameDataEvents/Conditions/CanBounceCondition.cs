using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class CanBounceCondition : FrameDataCondition
{
	[Export(PropertyHint.None, "")]
	private bool GroundBounce;

	[Export(PropertyHint.None, "")]
	private bool WallBounce;

	[Export(PropertyHint.None, "")]
	private bool Not;

	public override bool Check(ref SakugaActor Actor)
	{
		bool num = GroundBounce && (Not ? Actor.IsBouncingY() : (!Actor.IsBouncingY()));
		bool canWallBounce = WallBounce && (Not ? Actor.IsBouncingX() : (!Actor.IsBouncingX()));
		return num | canWallBounce;
	}
}
