using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

/// <summary>
/// Netsu (Oct 24 2026, night): moves the OPPONENT to a point seen from this fighter: X along this fighter's
/// facing (negative = behind her). A back throw puts the grabbed opponent behind her this way, then throws them
/// "forward" (TurnAround turns her to face their new side first). Near a wall, when there is no room behind her,
/// she steps forward instead, so the opponent still ends up on the other side (into the corner).
/// Used by the throw states made by tools/sprite_port/throws.py.
/// </summary>
[GlobalClass]
public partial class NetsuMoveOpponentAction : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	public int X = -7000;

	[Export(PropertyHint.None, "")]
	public bool TurnAround = true;

	public override void Execute(ref SakugaActor Actor)
	{
		SakugaActor opponent = Actor.GetOpponent(0);
		if (Actor.Body == null || opponent == null || opponent.Body == null)
		{
			return;
		}
		int limit = GlobalVariables.WallLimit - 2500;
		int self = Actor.Body.FixedPosition.X;
		int target = self + X * Actor.Body.PlayerSide;
		if (target > limit)
		{
			self -= target - limit;
			target = limit;
		}
		else if (target < -limit)
		{
			self += -limit - target;
			target = -limit;
		}
		Actor.Body.MoveTo(new Vector2I(self, Actor.Body.FixedPosition.Y));
		opponent.Body.MoveTo(new Vector2I(target, opponent.Body.FixedPosition.Y));
		if (TurnAround && target != self)
		{
			Actor.Body.UpdateSide(self < target);
			Actor.Body.FlipSide();
			opponent.Body.UpdateSide(target < self);
			opponent.Body.FlipSide();
		}
	}
}
