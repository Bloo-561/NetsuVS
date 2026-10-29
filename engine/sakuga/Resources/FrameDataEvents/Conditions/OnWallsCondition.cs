using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class OnWallsCondition : FrameDataCondition
{
	[Export(PropertyHint.None, "")]
	private bool Not;

	/// <summary>Netsu: how far (units) a fighter knocked away by a wall-bounce hit has to be from the
	/// attacker before it counts as reaching the wall: the edge of the screen. The fighters can be at
	/// most 100000 apart (GameManager keeps them within 50000 of their midpoint); the prototype bounced
	/// at about 86% of the screen width.</summary>
	public const int NetsuScreenWallDistance = 20000;   // Oct 28: 38000 -> 20000, wall bounces now turn around close to the attacker
    //   // Oct 27 c26: 70000 -> 38000 (3.8 m, like Flan's 236C) so every wall bounce comes back early enough to combo; Oct 25 night: was 88000

	public override bool Check(ref SakugaActor Actor)
	{
		if (Actor.Body == null)
		{
			return false;
		}
		bool onWall = Actor.Body.IsOnWall || NetsuScreenWall(Actor);
		if (Not)
		{
			return !onWall;
		}
		return onWall;
	}

	/// <summary>Netsu: the stage walls are 24 m apart, so a wall bounce (a hit with BounceTime and
	/// BounceXIntensity) would almost never reach one. While such a bounce is active, being
	/// NetsuScreenWallDistance from the opposing fighter and still flying away counts as hitting a wall.
	/// Measured from the fighter, so it suits a fighter's own wall-bounce hits (Cecilia's 236B, the only
	/// one so far); a far-away projectile or assist hit with a wall bounce would bounce at once.</summary>
	private static bool NetsuScreenWall(SakugaActor actor)
	{
		if (!actor.IsBouncingX())
		{
			return false;
		}
		SakugaActor[] opponents = actor.GetOpponents();
		SakugaActor attacker = (opponents != null && opponents.Length > 0) ? opponents[0] : null;
		if (attacker == null || attacker.Body == null)
		{
			return false;
		}
		int dx = actor.Body.FixedPosition.X - attacker.Body.FixedPosition.X;
		int wallDistance = (actor.NetsuWallBounceDistance > 0 ? Mathf.Min(actor.NetsuWallBounceDistance, NetsuScreenWallDistance) : NetsuScreenWallDistance);   // Oct 28: capped so every wall bounce stays near the attacker
        //   // c17: per-hit distance
		if (Mathf.Abs(dx) < wallDistance)
		{
			return false;
		}
		int vx = actor.Body.FixedVelocity.X;
		return (dx > 0 && vx > 0) || (dx < 0 && vx < 0);
	}
}
