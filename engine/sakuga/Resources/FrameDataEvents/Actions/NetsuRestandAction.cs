using Godot;

namespace SakugaEngine.Resources;

/// <summary>
/// Netsu (Oct 26 2026, TamaDeez): "restand" the opponent (put in an attacker state's OnHitConfirmEvents). A grounded
/// victim keeps the standing hit reaction the hitbox gave; an airborne one is brought down to the floor at once (no
/// knockback, no fall), so the hitbox's standing reaction plays on the ground. Used by Cecilia's held-B lightning
/// slash-through (214B) and her counter super.
/// </summary>
[GlobalClass]
public partial class NetsuRestandAction : FrameDataAction
{
	public override void Execute(ref SakugaActor Actor)
	{
		SakugaActor opponent = Actor.GetOpponent(0);
		if (opponent == null || opponent.Body == null || opponent.Body.IsOnGround)
		{
			return;
		}
		opponent.Knockback?.Stop();
		opponent.Body.SetVelocity(Vector2I.Zero);
		opponent.Body.MoveTo(new Vector2I(opponent.Body.FixedPosition.X, 0));
	}
}
