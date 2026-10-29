using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class PlayStateAction : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	private int StateIndex;

	[Export(PropertyHint.None, "")]
	private string StateName;

	[Export(PropertyHint.None, "")]
	private bool Reset = true;

	public override void Execute(ref SakugaActor Actor)
	{
		if (Actor.StateManager != null)
		{
			int nextState = StateIndex;
			if (StateIndex < 0 && StateName != "")
			{
				nextState = Actor.StateManager.GetStateIndex(StateName);
			}
			Actor.StateManager.PlayState(nextState, Reset);
		}
	}
}
