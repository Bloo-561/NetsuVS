using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

/// <summary>
/// Netsu (Oct 28 2026): Pushblock's push. Shoves the OPPONENT straight away from this fighter by Distance this frame,
/// without hitting them: no damage, no hitstun, and they stay in whatever they were doing (their attack can just whiff).
/// Run it on each frame of the push with a falling Distance, so the shove starts fast and eases off.
/// If they're in the corner and can't go further, this fighter slides back the rest instead, the usual pushblock rule.
/// Only horizontal; their height and their own speed are left alone.
/// </summary>
[GlobalClass]
public partial class NetsuPushOpponentAction : FrameDataAction
{
	/// <summary>How far the opponent is pushed this frame (engine units, 10000 = 1 m).</summary>
	[Export(PropertyHint.None, "")]
	public int Distance = 2000;

	public override void Execute(ref SakugaActor Actor)
	{
		SakugaActor opponent = Actor.GetOpponent(0);
		if (Actor.Body == null || opponent == null || opponent.Body == null || Distance <= 0)
		{
			return;
		}
		Vector2I self = Actor.Body.FixedPosition;
		Vector2I them = opponent.Body.FixedPosition;
		int dir = them.X > self.X ? 1 : (them.X < self.X ? -1 : Actor.Body.PlayerSide);
		int wall = GlobalVariables.WallLimit;
		int x = Mathf.Clamp(them.X + Distance * dir, -wall, wall);
		int moved = Mathf.Abs(x - them.X);
		if (moved > 0)
		{
			opponent.Body.MoveTo(new Vector2I(x, them.Y));
		}
		int left = Distance - moved;
		if (left > 0)
		{
			int sx = Mathf.Clamp(self.X - left * dir, -wall, wall);
			Actor.Body.MoveTo(new Vector2I(sx, self.Y));
		}
	}
}
