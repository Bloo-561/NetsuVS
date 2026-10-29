using Godot;

namespace SakugaEngine.Resources;

/// <summary>
/// Netsu (Oct 24 2026): a wall bounce pops the opponent up so it can be followed up. Runs on entering the
/// wall-bounce hit state (34_*_Hit_Bounce_Wall, see tools/sprite_port/tune_movement.py). Unlike MoveYAction
/// it works while the opponent is being knocked back. Pop: the least upward speed after the bounce;
/// MaxBackSpeed: the fastest it may come back off the wall (0 = leave the bounce's own speed).
/// </summary>
[GlobalClass]
public partial class NetsuWallPopAction : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	public int Pop = 80000;

	[Export(PropertyHint.None, "")]
	public int MaxBackSpeed = 30000;

	public override void Execute(ref SakugaActor Actor)
	{
		if (Actor.Body == null)
		{
			return;
		}
		if (Actor.Body.FixedVelocity.Y < Pop)
		{
			Actor.Body.FixedVelocity.Y = Pop;
		}
		if (MaxBackSpeed > 0)
		{
			Actor.Body.FixedVelocity.X = Mathf.Clamp(Actor.Body.FixedVelocity.X, -MaxBackSpeed, MaxBackSpeed);
		}
	}
}
