using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

/// <summary>
/// Netsu (Oct 29 2026, TamaDeez): deals Damage to the opponent directly, without a hitbox, so it also lands on an
/// opponent lying on the floor (outside the OTG window). For moves that already have them: Noah's j.214A (Fallen Grasp)
/// drains them at frame 30 of its landing state. Only while they're in a hit reaction (someone who teched, Burst or got
/// up isn't hit). Combo scaling, the combo counter, Craft Gauge and Burst all count it as a normal hit. HitEffect
/// spawns that hit spark on them (-1 = none); Hitstop freezes both fighters for the impact (0 = none).
/// </summary>
[GlobalClass]
public partial class NetsuDamageOpponentAction : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	public int Damage = 400;

	[Export(PropertyHint.None, "")]
	public int ScalingLoss = 10;

	[Export(PropertyHint.None, "")]
	public int HitEffect = -1;

	[Export(PropertyHint.None, "")]
	public int Hitstop = 16;

	public override void Execute(ref SakugaActor Actor)
	{
		SakugaActor opponent = Actor.GetOpponent(0);
		if (opponent == null || opponent.Parameters == null || opponent.Parameters.Prorations == null || opponent.StateManager == null
			|| opponent.IsKO() || opponent.StateManager.CurrentStateType() != StateType.HIT_REACTION)
		{
			return;
		}
		int attack = Actor.Parameters != null && Actor.Parameters.Prorations != null ? Actor.Parameters.Prorations.CurrentAttack : Actor.Data.BaseAttack;
		int damage = opponent.Parameters.CalculateProrations(Damage, attack, opponent.Parameters.Prorations.CurrentDefense, (ushort)Mathf.Max(0, ScalingLoss));
		damage = Actor.Parameters != null ? Actor.Parameters.OverdriveDamage(damage) : damage;
		damage = opponent.Parameters.NetsuOverdriveTaken(damage);
		opponent.Parameters.TakeDamage(damage, 0, true);
		opponent.NetsuMeterOnHit(Actor, damage);
		if (opponent.Parameters.Tracker != null)
		{
			opponent.Parameters.Tracker.UpdateTrackers(damage, 0, 1, 1);
		}
		if (HitEffect >= 0 && opponent.Body != null)
		{
			Actor.NetsuSpawnVFX(HitEffect, opponent.Body.FixedPosition + new Vector2I(0, 3000));
		}
		if (Hitstop > 0)
		{
			if (opponent.CanHitstop())
			{
				opponent.Hitstop.Start((uint)Hitstop);
			}
			if (Actor.CanHitstop())
			{
				Actor.Hitstop.Start((uint)Hitstop);
			}
		}
		opponent.NetsuKoWhileLying();
	}
}
