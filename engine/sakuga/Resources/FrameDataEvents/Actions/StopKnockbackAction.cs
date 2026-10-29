using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class StopKnockbackAction : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	private bool KeepXVelocity;

	public override void Execute(ref SakugaActor Actor)
	{
		if (Actor.Body != null)
		{
			Actor.StopKnockback(KeepXVelocity);
		}
	}
}
