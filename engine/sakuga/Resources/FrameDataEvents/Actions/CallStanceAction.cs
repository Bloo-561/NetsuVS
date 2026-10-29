using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class CallStanceAction : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	private int NextStance;

	public override void Execute(ref SakugaActor Actor)
	{
		if (Actor.StanceManager != null)
		{
			Actor.StanceManager.CallStance(NextStance);
		}
	}
}
