using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

/// <summary>
/// Netsu (Oct 29 2026, TamaDeez): slides the fighter toward a point next to the opponent, at most Step units a frame,
/// without physics (run it on every frame of the slide). The point is the opponent's X + Offset along the fighter's
/// facing (positive = past them, on their far side). Only X moves. With no pushbox in that state she goes straight
/// through them: Flan's Star Cross (charged 236B) slides through to their back with afterimages before the punch.
/// </summary>
[GlobalClass]
public partial class NetsuSlideToAction : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	public int Offset = 9000;

	[Export(PropertyHint.None, "")]
	public int Step = 5000;

	public override void Execute(ref SakugaActor Actor)
	{
		SakugaActor opponent = Actor.GetOpponent(0);
		if (Actor.Body == null || opponent == null || opponent.Body == null)
		{
			return;
		}
		int target = opponent.Body.FixedPosition.X + Offset * Actor.Body.PlayerSide;
		target = Mathf.Clamp(target, -GlobalVariables.WallLimit, GlobalVariables.WallLimit);
		int x = Actor.Body.FixedPosition.X;
		int step = Mathf.Max(1, Step);
		x = x < target ? Mathf.Min(target, x + step) : Mathf.Max(target, x - step);
		Actor.Body.FixedVelocity = new Vector2I(0, Actor.Body.FixedVelocity.Y);
		Actor.Body.MoveTo(new Vector2I(x, Actor.Body.FixedPosition.Y));
	}
}
