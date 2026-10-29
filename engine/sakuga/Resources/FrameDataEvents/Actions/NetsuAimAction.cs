using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

/// <summary>
/// Netsu: sets the sideways speed so the actor arrives at a point in Frames frames: a jump that
/// lands just behind the opponent, a dash that stops at them, wherever they stand.
/// The point: Target (OPPONENT, FIGHTER = the fighter who owns this assist/projectile, WORLD = x 0)
/// plus OffsetX along the actor's facing (positive = past the target, negative = short of it).
/// The speed is kept between MinSpeed and MaxSpeed (same units as MoveXAction; the actor moves
/// speed / 60 units a frame).
/// </summary>
[GlobalClass]
public partial class NetsuAimAction : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	private RelativeTo Target = RelativeTo.OPPONENT;

	[Export(PropertyHint.None, "")]
	private int OffsetX;

	[Export(PropertyHint.None, "")]
	private int Frames = 30;

	[Export(PropertyHint.None, "")]
	private int MinSpeed;

	[Export(PropertyHint.None, "")]
	private int MaxSpeed = 400000;

	public override void Execute(ref SakugaActor Actor)
	{
		if (Actor.Body == null || Frames <= 0)
		{
			return;
		}
		int side = Actor.Body.PlayerSide;
		int tx = NetsuTargets.X(Actor, Target) + OffsetX * side;
		int forward = (tx - Actor.Body.FixedPosition.X) * side;   // distance along the facing
		long speed = (long)forward * 60 / Frames;
		speed = System.Math.Max((long)MinSpeed, System.Math.Min((long)MaxSpeed, speed));
		Actor.Body.SetLateralVelocity((int)speed * side);
	}
}
