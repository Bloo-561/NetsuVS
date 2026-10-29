using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class AtFrameRangeCondition : FrameDataCondition
{
	[Export(PropertyHint.None, "")]
	private int MinFrame;

	[Export(PropertyHint.None, "")]
	private int MaxFrame;

	[Export(PropertyHint.None, "")]
	private bool Not;

	public override bool Check(ref SakugaActor Actor)
	{
		if (Actor.StateManager == null)
		{
			return false;
		}
		if (Not)
		{
			if (Actor.StateManager.CurrentStateFrame >= MinFrame)
			{
				return Actor.StateManager.CurrentStateFrame > MaxFrame;
			}
			return true;
		}
		if (Actor.StateManager.CurrentStateFrame >= MinFrame)
		{
			return Actor.StateManager.CurrentStateFrame <= MaxFrame;
		}
		return false;
	}
}
