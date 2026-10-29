using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class ResetProrationsAction : FrameDataAction
{
	public override void Execute(ref SakugaActor Actor)
	{
		if (Actor.Parameters != null && Actor.Parameters.Prorations != null)
		{
			Actor.Parameters.Prorations.ResetProrations();
		}
	}
}
