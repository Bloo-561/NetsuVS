using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

/// <summary>
/// Netsu (Oct 25 2026): puts this fighter on a point around her opponent and turns her to face them. Offset.X is how
/// far from the opponent on the side she was on when the orbit began (Start = true on its first frame: remembered in
/// SakugaActor.NetsuOrbitSide, saved with the match), negative = past them on the far side; Offset.Y is above the
/// opponent's feet. Her speed is cleared: only this moves her. Run it on every frame of the orbit with the next point
/// of the path: Leticia's Crimson Waltz circles the flame prison smoothly on her board
/// (tools/sprite_port/moves_leticia.py works the path out).
/// </summary>
[GlobalClass]
public partial class NetsuOrbitAction : FrameDataAction
{
	/// <summary>Where she goes (engine units, 10000 = 1 m): X from the opponent towards her starting side, Y above
	/// their feet.</summary>
	[Export(PropertyHint.None, "")]
	public Vector2I Offset;

	/// <summary>The orbit's first frame: remember which side of the opponent she starts on.</summary>
	[Export(PropertyHint.None, "")]
	public bool Start;

	public override void Execute(ref SakugaActor Actor)
	{
		SakugaActor opponent = Actor.GetOpponent(0);
		if (Actor.Body == null || opponent == null || opponent.Body == null)
		{
			return;
		}
		Vector2I target = opponent.Body.FixedPosition;
		if (Start || Actor.NetsuOrbitSide == 0)
		{
			Actor.NetsuOrbitSide = Actor.Body.FixedPosition.X <= target.X ? -1 : 1;
		}
		int x = Mathf.Clamp(target.X + Offset.X * Actor.NetsuOrbitSide, -GlobalVariables.WallLimit, GlobalVariables.WallLimit);
		int y = Mathf.Clamp(target.Y + Offset.Y, 0, GlobalVariables.CeilingLimit);
		Actor.Body.FixedVelocity = Vector2I.Zero;
		Actor.Body.MoveTo(new Vector2I(x, y));
		if (x != target.X)   // right above / under them she keeps the way she faced
		{
			Actor.Body.UpdateSide(x < target.X);
			Actor.Body.FlipSide();
		}
	}
}
