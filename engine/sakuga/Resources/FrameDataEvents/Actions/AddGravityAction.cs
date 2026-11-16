using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class AddGravityAction : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	private bool SetValue;

	[Export(PropertyHint.None, "")]
	private bool UseDefault;

	[Export(PropertyHint.None, "")]
	private int Force;

	public override void Execute(ref SakugaActor Actor)
	{
		if (Actor.Body != null)
		{
			if (SetValue)
			{
				int def = 260000;
				// Nov 3 (TamaDeez): someone being hit uses the juggle gravity (GameManager.NetsuJuggleGravity) instead
				if (UseDefault && SakugaEngine.Game.GameManager.Instance != null && Actor.StateManager != null
					&& Actor.StateManager.CurrentStateType() == SakugaEngine.Global.StateType.HIT_REACTION)
				{
					def = SakugaEngine.Game.GameManager.Instance.NetsuJuggleGravity;
				}
				Actor.Body.CurrentGravity = (UseDefault ? def : Force);
			}
			// Nov 12 (Million Arthur feel): someone being hit hangs at the top of the arc and drops fast (NetsuJuggleGravityNow)
			if (Actor.StateManager != null && Actor.StateManager.CurrentStateType() == SakugaEngine.Global.StateType.HIT_REACTION)
			{
				// Nov 13 (Million Arthur): everyone being juggled falls with the one juggle gravity (GameManager.NetsuJuggleGravity),
				// whatever the hit or the hit state asked for, except hits that hold them up on purpose (under 50000) and a
				// Judith launch with its own gravity (SakugaActor.NetsuJGravity). In the air they drift less and less sideways
				// (GameManager.NetsuJuggleDrag), so launches go out and slow down instead of sailing across the stage.
				int g = NetsuJuggleBaseGravity(Actor);
				Actor.Body.FixedVelocity.Y -= NetsuJuggleGravityNow(g, Actor.Body.FixedVelocity.Y) / 60;
				SakugaEngine.Game.GameManager gmd = SakugaEngine.Game.GameManager.Instance;
				int drag = gmd != null ? gmd.NetsuJuggleDrag : 0;
				int vx = Actor.Body.FixedVelocity.X;
				if (drag > 0 && vx != 0 && !Actor.Body.IsOnGround)
				{
					Actor.Body.FixedVelocity.X = vx - Mathf.Min(Mathf.Abs(vx), drag) * Mathf.Sign(vx);
				}
				return;
			}
			Actor.Body.AddGravity();
		}
	}

	/// <summary>Nov 13: the gravity someone in a hit state falls with: their Judith launch gravity if they have one, the
	/// body's own if it is a hold (under 50000), otherwise the juggle gravity.</summary>
	public static int NetsuJuggleBaseGravity(SakugaActor a)
	{
		if (a.NetsuJGravity > 0)
		{
			return a.NetsuJGravity;
		}
		int g = a.Body.CurrentGravity;
		SakugaEngine.Game.GameManager gm = SakugaEngine.Game.GameManager.Instance;
		if (g < 50000 || gm == null)
		{
			return g;
		}
		return gm.NetsuJuggleGravity;
	}

	/// <summary>Nov 12: the gravity a juggled fighter falls with right now: the usual one going up, lighter at the top of
	/// the arc, heavier coming down (GameManager.NetsuJuggleHangBand / HangPercent / FallPercent). Integer only (rollback).</summary>
	public static int NetsuJuggleGravityNow(int gravity, int velocityY)
	{
		SakugaEngine.Game.GameManager gm = SakugaEngine.Game.GameManager.Instance;
		if (gm == null || gravity < 50000)
		{
			return gravity;
		}
		if (velocityY > gm.NetsuJuggleHangBand)
		{
			return gravity;
		}
		if (velocityY >= -gm.NetsuJuggleHangBand)
		{
			return gravity * gm.NetsuJuggleHangPercent / 100;
		}
		return gravity * gm.NetsuJuggleFallPercent / 100;
	}

	/// <summary>Nov 12: frames a juggled fighter launched at velocityY stays in the air (back to the height it left from),
	/// with the juggle gravity and the hang / fall split. Mirrors the physics: 2 steps of v / 120 per frame.</summary>
	public static int NetsuJuggleAirFrames(int velocityY, int gravity)
	{
		return NetsuJuggleAirFrames(velocityY, gravity, 0);
	}

	/// <summary>Nov 13: the same, starting startY units above the floor: frames until they land.</summary>
	public static int NetsuJuggleAirFrames(int velocityY, int gravity, int startY)
	{
		long y = startY > 0 ? startY : 0;
		int v = velocityY;
		for (int f = 1; f < 400; f++)
		{
			v -= NetsuJuggleGravityNow(gravity, v) / 60;
			y += 2 * (v / 120);
			if (y <= 0 && v < 0)
			{
				return f;
			}
		}
		return 400;
	}
}
