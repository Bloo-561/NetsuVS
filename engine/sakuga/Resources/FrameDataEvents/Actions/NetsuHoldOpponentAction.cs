using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

/// <summary>
/// Netsu (Oct 25 2026): holds the OPPONENT while they're being hit. Two ways:
///  - at a point seen from this fighter (LiftRate 0): Offset.X along her facing (positive = in front of her), Offset.Y
///    above her feet. The point is where she will be at the end of this frame (her speed is counted in). Flan's Big Bang
///    Crash takes them up into the sky on her fist this way, then drags them back down to the ground under it.
///  - lifted in place (LiftRate above 0): they stay where they are across, and their feet go LiftRate per mille of the
///    way to Offset.Y above the floor every frame (a smooth rise that slows as it gets there, then holds them there).
///    Leticia's Crimson Waltz floats them up inside the flame prison.
/// Run it on every frame of the hold. Their own speed is cleared, so only this moves them. Only while the opponent is in
/// a hit reaction: someone who escaped (Burst...) or recovered isn't pulled back. Never past the walls nor under the floor.
/// Used by tools/sprite_port/moves_flan.py and moves_leticia.py.
/// </summary>
[GlobalClass]
public partial class NetsuHoldOpponentAction : FrameDataAction
{
	/// <summary>Where the opponent's feet go (engine units, 10000 = 1 m): X along her facing, Y above her feet; lifted
	/// in place: Y = the height above the floor (X unused).</summary>
	[Export(PropertyHint.None, "")]
	public Vector2I Offset = new Vector2I(6000, 10000);

	/// <summary>0 = at the point seen from her; above 0 = lifted in place, this share (per mille) of the way each frame.</summary>
	[Export(PropertyHint.None, "")]
	public int LiftRate;

	public override void Execute(ref SakugaActor Actor)
	{
		SakugaActor opponent = Actor.GetOpponent(0);
		if (Actor.Body == null || opponent == null || opponent.Body == null || opponent.StateManager == null)
		{
			return;
		}
		if (opponent.StateManager.CurrentStateType() != StateType.HIT_REACTION)
		{
			return;
		}
		int x;
		int y;
		if (LiftRate > 0)
		{
			Vector2I at = opponent.Body.FixedPosition;
			int rate = Mathf.Clamp(LiftRate, 1, 1000);
			x = at.X;
			y = at.Y + (int)((long)(Offset.Y - at.Y) * rate / 1000L);
		}
		else
		{
			// where she'll be after this frame's two physics steps (PhysicsBody.Move: position += speed / 120, twice)
			Vector2I self = Actor.Body.FixedPosition;
			if (Actor.Body.IsMovable)
			{
				self += Actor.Body.FixedVelocity / 120 * 2;
			}
			x = self.X + Offset.X * Actor.Body.PlayerSide;
			y = self.Y + Offset.Y;
		}
		x = Mathf.Clamp(x, -GlobalVariables.WallLimit, GlobalVariables.WallLimit);
		y = Mathf.Clamp(y, 0, GlobalVariables.CeilingLimit);
		opponent.Body.FixedVelocity = Vector2I.Zero;
		opponent.Body.MoveTo(new Vector2I(x, y));
	}
}
