using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class InterruptMoveAction : FrameDataAction
{
	public override void Execute(ref SakugaActor Actor)
	{
		if (Actor.StanceManager != null)
		{
			Actor.StanceManager.CurrentMove = -1;
		}
	}
}
