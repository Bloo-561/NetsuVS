using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

/// <summary>
/// Netsu (Oct 26 2026, TamaDeez): turns the hit that just landed into a wall bounce or a ground bounce. Put it in a
/// state's OnHitConfirmEvents (with CheckHitCondition HIT_CANCEL, so not on block). It gives the opponent the bounce
/// (BounceTime / BounceX for the wall, BounceY for the floor), and optionally a different hit reaction (an index into the
/// stance's HitReactions, e.g. 7 = Hit_LaunchAway for a wall bounce, 9 = Hit_LaunchDown for a ground bounce), knockback,
/// hitstun and hitstun type, replacing the hitbox's. Only while the opponent is in a hit reaction and not lying on the
/// ground or knocked out. Flan's Overdrive: 236 always wall bounces, 214 always ground bounces.
/// </summary>
[GlobalClass]
public partial class NetsuBounceOpponentAction : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	public int BounceTime = 120;

	/// <summary>Wall bounce strength (0 = no wall bounce).</summary>
	[Export(PropertyHint.None, "")]
	public int BounceX;

	/// <summary>Ground bounce strength (0 = no ground bounce).</summary>
	[Export(PropertyHint.None, "")]
	public int BounceY;

	/// <summary>Netsu (Oct 26 c17): how far from the attacker the wall bounce happens (units, 0 = the usual 7 m).</summary>
	[Export(PropertyHint.None, "")]
	public int WallDistance;

	/// <summary>Index into the stance's HitReactions to play (-1 = keep the one the hit gave).</summary>
	[Export(PropertyHint.None, "")]
	public int HitReaction = -1;

	/// <summary>Knockback like a hitbox's (X negative = away from the attacker). Zero = keep the hit's.</summary>
	[Export(PropertyHint.None, "")]
	public Vector2I Knockback;

	[Export(PropertyHint.None, "")]
	public int KnockbackTime = 8;

	[Export(PropertyHint.None, "")]
	public int KnockbackGravity = 200000;

	/// <summary>Hitstun frames (0 = keep the hit's).</summary>
	[Export(PropertyHint.None, "")]
	public int Hitstun;

	/// <summary>Hitstun type (-1 = keep the hit's; 2 = KNOCKDOWN).</summary>
	[Export(PropertyHint.None, "")]
	public int HitstunType = -1;

	/// <summary>Netsu (Oct 28): a ground bounce on someone who is already ON the ground when hit (standing, crouching,
	/// landing). The floor bounce normally happens when they come down onto the floor, which a grounded opponent never
	/// does, so the downward knockback just flattened them. With this above 0 a grounded opponent bounces straight away
	/// instead: lifted a little off the floor, sent up at this speed (units/s, like MoveY) with the Knockback's X, into
	/// GroundedHitReaction (8 = Hit_LaunchUp). Airborne opponents still fall and bounce on the floor as before.
	/// Leticia's charged j.C.</summary>
	[Export(PropertyHint.None, "")]
	public int GroundedPopVelocity;

	[Export(PropertyHint.None, "")]
	public int GroundedHitReaction = 8;

	public override void Execute(ref SakugaActor Actor)
	{
		SakugaActor opponent = Actor.GetOpponent(0);
		if (opponent == null || opponent.Body == null || opponent.StateManager == null || opponent.IsKO() || opponent.NetsuLying())
		{
			return;
		}
		if (opponent.StateManager.CurrentStateType() != StateType.HIT_REACTION || opponent.HitstunType == SakugaEngine.Global.HitstunType.GRABBED)
		{
			return;
		}
		if (HitstunType >= 0)
		{
			opponent.HitstunType = (SakugaEngine.Global.HitstunType)HitstunType;
		}
		if (BounceY > 0 && opponent.NetsuGroundBounceRepeat(Actor))
		{
			// Oct 29 (TamaDeez): this move already ground-bounced them in this combo: hard knockdown, no bounce
			opponent.HitstunType = SakugaEngine.Global.HitstunType.HARD_KNOCKDOWN;
			if (opponent.CanBounce())
			{
				opponent.Bounce.Stop();
				opponent.BounceXIntensity = 0;
				opponent.BounceYIntensity = 0;
			}
			if (opponent.StanceManager != null)
			{
				int[] down = opponent.StanceManager.GetCurrentStance().HitReactions;
				if (down != null && down.Length > 9)
				{
					opponent.StateManager.PlayState(down[9], reset: true);   // Hit_LaunchDown: straight to the floor
				}
			}
			if (Actor.Body != null)
			{
				int kx = Knockback != Vector2I.Zero ? Knockback.X : -6000;
				opponent.PushActor(KnockbackTime, kx * -Actor.Body.PlayerSide, opponent.Body.IsOnGround ? 0 : -60000, KnockbackGravity);
			}
			return;
		}
		if (GroundedPopVelocity > 0 && BounceY > 0 && opponent.Body.IsOnGround)
		{
			// Oct 28: already on the floor: the bounce happens now
			if (Hitstun > 0 && opponent.CanHitstun())
			{
				opponent.Hitstun.Start((uint)Hitstun);
			}
			if (GroundedHitReaction >= 0 && opponent.StanceManager != null)
			{
				int[] up = opponent.StanceManager.GetCurrentStance().HitReactions;
				if (up != null && up.Length > 0)
				{
					opponent.StateManager.PlayState(up[Mathf.Clamp(GroundedHitReaction, 0, up.Length - 1)], reset: true);
				}
			}
			Vector2I at = opponent.Body.FixedPosition;
			opponent.Body.MoveTo(new Vector2I(at.X, at.Y + 1500));
			int side = Actor.Body != null ? Actor.Body.PlayerSide : 1;
			opponent.PushActor(KnockbackTime, Knockback.X * -side, GroundedPopVelocity, KnockbackGravity);
			if (opponent.CanBounce())
			{
				opponent.Bounce.Stop();
				opponent.BounceXIntensity = 0;
				opponent.BounceYIntensity = 0;
			}
			return;
		}
		if (Hitstun > 0 && opponent.CanHitstun())
		{
			opponent.Hitstun.Start((uint)Hitstun);
		}
		if (HitReaction >= 0 && opponent.StanceManager != null)
		{
			int[] reactions = opponent.StanceManager.GetCurrentStance().HitReactions;
			if (reactions != null && reactions.Length > 0)
			{
				opponent.StateManager.PlayState(reactions[Mathf.Clamp(HitReaction, 0, reactions.Length - 1)], reset: true);
			}
		}
		if (Knockback != Vector2I.Zero && Actor.Body != null)
		{
			opponent.PushActor(KnockbackTime, Knockback.X * -Actor.Body.PlayerSide, Knockback.Y, KnockbackGravity);
		}
		if (opponent.CanBounce())
		{
			opponent.Bounce.Start((uint)Mathf.Max(BounceTime, 1));
			opponent.BounceXIntensity = BounceX;
			opponent.BounceYIntensity = BounceY;
			opponent.NetsuWallBounceDistance = WallDistance;
		}
	}
}
