using Godot;
using SakugaEngine.Game;
using SakugaEngine.Global;

namespace SakugaEngine;

// Nov 13 2026 (TamaDeez, Million Arthur style): launches are low and wide, for the whole cast. See GameManager
// NetsuLaunchHeightPercent / NetsuLaunchMinVy / NetsuLaunchMinX / NetsuJuggleDrag / NetsuJuggleGravity and
// AddGravityAction (one juggle gravity for every hit state, sideways drag in the air).
public partial class SakugaActor
{
	/// <summary>Nov 13 (Judith): the gravity a Judith launch gave them (0 = the usual juggle gravity). Cleared by the next
	/// hit and when they leave the hit state. Saved for rollback (SakugaActorState key 82).</summary>
	public int NetsuJGravity;

	/// <summary>HitDamage, right after the hit's knockback is applied (this = the one hit).</summary>
	private void NetsuLaunchShape(SakugaActor attacker)
	{
		NetsuJGravity = 0;   // a new hit: any Judith launch gravity is over (her own launch sets it again after this)
		GameManager gm = GameManager.Instance;
		if (gm == null || Body == null || IsKO() || Body.CurrentGravity < 50000)
		{
			return;   // (under 50000: a hit that holds them up on purpose)
		}
		int vy = Body.FixedVelocity.Y;
		if (vy <= 0)
		{
			return;
		}
		Body.FixedVelocity.Y = vy * gm.NetsuLaunchHeightPercent / 100;
		if (vy < gm.NetsuLaunchMinVy || gm.NetsuLaunchMinX <= 0)
		{
			return;   // a small pop (trip, air normal): only lower
		}
		SakugaActor root = attacker?.NetsuRoot();
		int away;
		if (root != null && root.Body != null && root.Body.FixedPosition.X != Body.FixedPosition.X)
		{
			away = Body.FixedPosition.X > root.Body.FixedPosition.X ? 1 : -1;
		}
		else
		{
			away = root != null && root.Body != null ? root.Body.PlayerSide : 1;
		}
		int vx = Body.FixedVelocity.X;
		if (vx * away < gm.NetsuLaunchMinX)
		{
			Body.FixedVelocity.X = gm.NetsuLaunchMinX * away;
		}
	}

	// ---------------------------------------------------------------------------------------------
	// Nov 13 (Judith): a sakura blooms where a Bloom hit lands. Presentation only (not saved; a rollback that undoes the
	// hit at worst shows it for a moment).
	public const int NetsuBloomFlowerFrames = 34;
	private int _bloomAt = -1000;
	private Vector2I _bloomPos;

	public void NetsuBloomFlowerStart()
	{
		_bloomAt = GameManager.Instance != null ? GameManager.Instance.Frame : 0;
		_bloomPos = Body != null ? Body.FixedPosition + new Vector2I(0, 5500) : Vector2I.Zero;
	}

	private void NetsuBloomFlowerLook()
	{
		if (Animator == null)
		{
			return;
		}
		int now = GameManager.Instance != null ? GameManager.Instance.Frame : 0;
		int f = now - _bloomAt;
		if (f < 0 || f >= NetsuBloomFlowerFrames)
		{
			Animator.SetBloomFlower(0f, 0f, 0f, Vector3.Zero);
			return;
		}
		float t = (float)f / NetsuBloomFlowerFrames;
		float open = 1f - (1f - Mathf.Min(1f, t * 3f)) * (1f - Mathf.Min(1f, t * 3f));   // opens fast in the first third
		float scale = Mathf.Lerp(0.25f, 1.0f, open) + 0.15f * t;   // Nov 13 (2): smaller
		float alpha = 0.75f * (t < 0.6f ? 1f : 1f - (t - 0.6f) / 0.4f);   // and see-through
		Animator.SetBloomFlower(scale, alpha, f * 0.05f, GlobalFunctions.ToScaledVector3(_bloomPos));
	}
}
