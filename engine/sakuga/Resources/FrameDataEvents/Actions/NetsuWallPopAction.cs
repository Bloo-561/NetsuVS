using Godot;

namespace SakugaEngine.Resources;

/// <summary>
/// Netsu (Oct 24 2026): a wall bounce pops the opponent up so it can be followed up. Runs on entering the
/// wall-bounce hit state (34_*_Hit_Bounce_Wall, see tools/sprite_port/tune_movement.py). Unlike MoveYAction
/// it works while the opponent is being knocked back. Pop: the least upward speed after the bounce;
/// MaxBackSpeed: the fastest it may come back off the wall (0 = leave the bounce's own speed).
/// </summary>
[GlobalClass]
public partial class NetsuWallPopAction : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	public int Pop = 80000;

	[Export(PropertyHint.None, "")]
	public int MaxBackSpeed = 30000;

	public override void Execute(ref SakugaActor Actor)
	{
		if (Actor.Body == null)
		{
			return;
		}
		if (Actor.Body.FixedVelocity.Y < Pop)
		{
			Actor.Body.FixedVelocity.Y = Pop;
		}
		if (MaxBackSpeed > 0)
		{
			Actor.Body.FixedVelocity.X = Mathf.Clamp(Actor.Body.FixedVelocity.X, -MaxBackSpeed, MaxBackSpeed);
		}
		NetsuAimReturn(Actor);
	}

	/// <summary>Nov 3 (TamaDeez): after the bounce they fly back toward the attacker fast enough to come down
	/// GameManager.NetsuWallReturnGap in front of her (where she is now), so the bounce can always be followed up.
	/// Integer maths only (rollback).</summary>
	private static void NetsuAimReturn(SakugaActor actor)
	{
		SakugaEngine.Game.GameManager gm = SakugaEngine.Game.GameManager.Instance;
		SakugaActor attacker = actor.GetOpponent(0);
		if (gm == null || gm.NetsuWallReturnGap <= 0 || attacker == null || attacker.Body == null)
		{
			return;
		}
		long dx = attacker.Body.FixedPosition.X - actor.Body.FixedPosition.X;
		long dist = System.Math.Abs(dx) - gm.NetsuWallReturnGap;
		if (dist <= 0)
		{
			actor.Body.FixedVelocity.X = 0;
			return;
		}
		long g = System.Math.Max(1000, gm.NetsuJuggleGravity);   // units / s^2 (the hit states fall with the juggle gravity)
		long vy = actor.Body.FixedVelocity.Y;                     // units / s
		long h = System.Math.Max(0, actor.Body.FixedPosition.Y);  // units
		// time in the air (ms): (vy + sqrt(vy^2 + 2 g h)) / g
		long root = NetsuISqrt(vy * vy + 2 * g * h);
		long tMs = System.Math.Max(150, (vy + root) * 1000 / g);
		long vx = System.Math.Min(60000, dist * 1000 / tMs);
		actor.Body.FixedVelocity.X = (int)(dx > 0 ? vx : -vx);
	}

	private static long NetsuISqrt(long n)
	{
		if (n <= 0)
		{
			return 0;
		}
		long x = (long)System.Math.Sqrt(n);
		while (x * x > n) x--;
		while ((x + 1) * (x + 1) <= n) x++;
		return x;
	}
}
