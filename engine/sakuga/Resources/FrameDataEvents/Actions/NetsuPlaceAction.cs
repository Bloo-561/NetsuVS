using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

/// <summary>
/// Netsu: moves the actor to a point: Target (OPPONENT, FIGHTER = the fighter who owns this
/// assist/projectile, SELF, WORLD) + Offset, where Offset.X runs along the ACTOR's facing
/// (positive = in front of it). Unlike TeleportAction, the opponent's facing doesn't matter:
/// e.g. Target OPPONENT, Offset (70000, 0) = 7 m beyond the opponent, seen from the actor.
/// KeepHeight leaves the actor's height alone; FaceBack turns it around afterwards.
/// </summary>
[GlobalClass]
public partial class NetsuPlaceAction : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	private RelativeTo Target = RelativeTo.OPPONENT;

	[Export(PropertyHint.None, "")]
	private Vector2I Offset;

	[Export(PropertyHint.None, "")]
	private bool KeepHeight = true;

	[Export(PropertyHint.None, "")]
	private bool FaceBack;

	public override void Execute(ref SakugaActor Actor)
	{
		if (Actor.Body == null)
		{
			return;
		}
		int side = Actor.Body.PlayerSide;
		int x = NetsuTargets.X(Actor, Target) + Offset.X * side;
		int y = KeepHeight ? Actor.Body.FixedPosition.Y : NetsuTargets.Y(Actor, Target) + Offset.Y;
		Actor.Body.MoveTo(new Vector2I(x, System.Math.Max(0, y)));
		if (FaceBack)
		{
			// Oct 26 c8: turn around from the way she faces NOW. (Before: from IsLeftSide, which the game updates every
			// frame from the positions: once she was already past the opponent, "turn around" made her face away.)
			Actor.Body.UpdateSide(side < 0);
			Actor.Body.FlipSide();
		}
	}
}
