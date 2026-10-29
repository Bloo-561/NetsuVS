using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

/// <summary>
/// Netsu (Oct 25 2026, Noah): pulls the opponent toward this actor (a vacuum: Noah's black holes). Every frame it runs,
/// an opponent within Radius (horizontally, engine units) is moved Speed units closer (never past the centre), whatever
/// they are doing, unless they're knocked out or being thrown. With LiftRate above 0 their feet also go that share (per
/// mille) of the way to the centre's height above the floor (Lift). Never past the walls. Integer maths: the same on every
/// copy of the match.
/// </summary>
[GlobalClass]
public partial class NetsuPullOpponentAction : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	public int Radius = 30000;

	/// <summary>Units per frame toward the centre (10000 = 1 m).</summary>
	[Export(PropertyHint.None, "")]
	public int Speed = 500;

	/// <summary>Per mille of the way to Lift each frame (0 = no lift).</summary>
	[Export(PropertyHint.None, "")]
	public int LiftRate;

	/// <summary>Height above the floor the feet are lifted toward (units).</summary>
	[Export(PropertyHint.None, "")]
	public int Lift;

	public override void Execute(ref SakugaActor Actor)
	{
		SakugaActor opponent = Actor.GetOpponent(0);
		if (Actor.Body == null || opponent == null || opponent.Body == null || opponent.StateManager == null || opponent.IsKO())
		{
			return;
		}
		if (opponent.HitstunType == HitstunType.GRABBED)
		{
			return;
		}
		Vector2I at = opponent.Body.FixedPosition;
		Vector2I c = Actor.Body.FixedPosition;
		int dx = c.X - at.X;
		if (Mathf.Abs(dx) > Radius)
		{
			return;
		}
		int step = Mathf.Min(Mathf.Abs(dx), Mathf.Max(Speed, 0));
		int x = at.X + (dx > 0 ? step : -step);
		int y = at.Y;
		if (LiftRate > 0)
		{
			y = at.Y + (int)((long)(Lift - at.Y) * Mathf.Clamp(LiftRate, 1, 1000) / 1000L);
		}
		x = Mathf.Clamp(x, -GlobalVariables.WallLimit, GlobalVariables.WallLimit);
		y = Mathf.Clamp(y, 0, GlobalVariables.CeilingLimit);
		opponent.Body.MoveTo(new Vector2I(x, y));
	}
}
