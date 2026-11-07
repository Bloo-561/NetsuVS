using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class StateEndedCondition : FrameDataCondition
{
	[Export(PropertyHint.None, "")]
	private bool Not;

	public override bool Check(ref SakugaActor Actor)
	{
		if (Actor.StateManager == null)
		{
			return false;
		}
		// Nov 4: NetsuDuration = the animation's Duration, longer for a blocked DP's landing (FighterState.NetsuBlockedRecoveryHere)
		if (Not)
		{
			return Actor.StateManager.CurrentStateFrame < Actor.StateManager.NetsuDuration();
		}
		return Actor.StateManager.CurrentStateFrame >= Actor.StateManager.NetsuDuration();
	}
}
