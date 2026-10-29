using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class CheckSideChangeCondition : FrameDataCondition
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
			if (!Actor.Body.IsLeftSide || Actor.InputSide() <= 0)
			{
				if (!Actor.Body.IsLeftSide)
				{
					return Actor.InputSide() < 0;
				}
				return false;
			}
			return true;
		}
		if (!Actor.Body.IsLeftSide || Actor.InputSide() >= 0)
		{
			if (!Actor.Body.IsLeftSide)
			{
				return Actor.InputSide() > 0;
			}
			return false;
		}
		return true;
	}
}
