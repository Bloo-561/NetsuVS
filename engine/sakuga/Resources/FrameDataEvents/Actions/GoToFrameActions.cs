using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class GoToFrameActions : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	private int Frame;

	public override void Execute(ref SakugaActor Actor)
	{
		if (Actor.StateManager != null)
		{
			Actor.StateManager.CurrentStateFrame = Frame;
		}
	}
}
