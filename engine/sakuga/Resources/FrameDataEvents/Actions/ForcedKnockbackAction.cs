using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class ForcedKnockbackAction : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	private int KnockbackTime;

	[Export(PropertyHint.None, "")]
	private Vector2I KnockbackDirection;

	[Export(PropertyHint.None, "")]
	private int KnockbackGravity;

	public override void Execute(ref SakugaActor Actor)
	{
		if (Actor.Body != null)
		{
			Actor.PushActor(KnockbackTime, KnockbackDirection.X * Actor.Body.PlayerSide, KnockbackDirection.Y, KnockbackGravity);
		}
	}
}
