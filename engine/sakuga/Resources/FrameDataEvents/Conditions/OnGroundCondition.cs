using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class OnGroundCondition : FrameDataCondition
{
	[Export(PropertyHint.None, "")]
	private bool Not;

	public override bool Check(ref SakugaActor Actor)
	{
		if (Actor.Body == null)
		{
			return false;
		}
		if (Not)
		{
			return !Actor.Body.IsOnGround;
		}
		return Actor.Body.IsOnGround;
	}
}
