using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class CanBounceGroundCondition : FrameDataCondition
{
	[Export(PropertyHint.None, "")]
	private bool Not;

	public override bool Check(ref SakugaActor Actor)
	{
		if (!Actor.CanBounce())
		{
			return false;
		}
		if (Not)
		{
			return !Actor.IsBouncingY();
		}
		return Actor.IsBouncingY();
	}
}
