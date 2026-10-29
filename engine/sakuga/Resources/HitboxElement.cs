using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

[GlobalClass]
[Tool]
public partial class HitboxElement : Resource
{
	[ExportGroup("Box Settings", "")]
	[Export(PropertyHint.None, "")]
	public Vector2I Center = Vector2I.Zero;

	[Export(PropertyHint.None, "")]
	public Vector2I Size = Vector2I.Zero;

	[Export(PropertyHint.None, "")]
	public HitboxType HitboxType;

	[Export(PropertyHint.None, "")]
	public int Profile = -1;

	[ExportGroup("Damage Settings", "")]
	[Export(PropertyHint.None, "")]
	public HitType HitType;

	[Export(PropertyHint.None, "")]
	public int BaseDamage = 150;

	[Export(PropertyHint.None, "")]
	public int ChipDamage;

	[Export(PropertyHint.None, "")]
	public bool ChipDeath;

	[Export(PropertyHint.None, "")]
	public bool KillingBlow = true;

	[Export(PropertyHint.None, "")]
	public bool GuardCrush;

	[Export(PropertyHint.None, "")]
	public int GuardCrushDamage = 100;

	[Export(PropertyHint.None, "")]
	public int SelfSuperGaugeGain = 250;

	[Export(PropertyHint.None, "")]
	public int OpponentSuperGaugeGain = 100;

	[Export(PropertyHint.None, "")]
	public int ArmorDamage = 1;

	[Export(PropertyHint.None, "")]
	public int Priority;

	[Export(PropertyHint.None, "")]
	public int SelfHitStopDuration = 12;

	[Export(PropertyHint.None, "")]
	public int OpponentHitStopDuration = 12;

	[Export(PropertyHint.None, "")]
	public int BlockStopDuration = 12;

	[Export(PropertyHint.None, "")]
	public int CounterHitStopDuration = 20;

	[Export(PropertyHint.None, "")]
	public int ClashHitStopDuration = 20;

	[Export(PropertyHint.None, "")]
	public int DamageScalingSubtract = 15;

	[ExportGroup("VFX Settings", "")]
	[Export(PropertyHint.None, "")]
	public int HitEffectIndex;

	[Export(PropertyHint.None, "")]
	public int BlockEffectIndex = 1;

	[Export(PropertyHint.None, "")]
	public int ClashEffectIndex = 2;

	[Export(PropertyHint.None, "")]
	public int ArmorEffectIndex = 3;

	[Export(PropertyHint.None, "")]
	public int GuardCrushEffectIndex;

	[ExportGroup("Ground Hit Settings", "")]
	[Export(PropertyHint.None, "")]
	public HitstunType GroundHitstunType;

	[Export(PropertyHint.None, "")]
	public int GroundHitReaction;

	[Export(PropertyHint.None, "")]
	public int CrouchHitReaction;

	[Export(PropertyHint.None, "")]
	public Vector2I GroundHitKnockback;

	[Export(PropertyHint.None, "")]
	public int GroundHitKnockbackGravity;

	[Export(PropertyHint.None, "")]
	public int GroundHitKnockbackTime = 8;

	[Export(PropertyHint.None, "")]
	public int GroundHitstun = 8;

	[Export(PropertyHint.None, "")]
	public Vector2I GroundBlockKnockback;

	[Export(PropertyHint.None, "")]
	public int GroundBlockKnockbackGravity;

	[Export(PropertyHint.None, "")]
	public int GroundBlockKnockbackTime = 8;

	[Export(PropertyHint.None, "")]
	public int GroundBlockstun = 8;

	[ExportGroup("Air Hit Settings", "")]
	[Export(PropertyHint.None, "")]
	public HitstunType AirHitstunType;

	[Export(PropertyHint.None, "")]
	public int AirHitReaction;

	[Export(PropertyHint.None, "")]
	public Vector2I AirHitKnockback;

	[Export(PropertyHint.None, "")]
	public int AirHitKnockbackGravity = 200000;

	[Export(PropertyHint.None, "")]
	public int AirHitKnockbackTime = 8;

	[Export(PropertyHint.None, "")]
	public int AirHitstun = 8;

	// Netsu (Oct 28): UNI-style recovery scaling (GameManager.NetsuRecoveryScaling). 0 = use the default for the move's
	// strength (light 24 / medium 32 / heavy 40 / special 40 / EX and super 48 frames; x0.94 / 0.92 / 0.90 / 0.90 / 0.90).
	/// <summary>Frames before the victim can recover from this hit in the air (before the combo's recovery scale).</summary>
	[Export(PropertyHint.Range, "0,120,1")]
	public int NetsuAirUntech;

	/// <summary>How much this hit scales every LATER hit's untech time, in thousandths (940 = x0.94; 0 = the default).</summary>
	[Export(PropertyHint.Range, "0,1000,1")]
	public int NetsuRecoveryScalePermille;

	/// <summary>This hit always gives its full untech time and doesn't reduce the combo's recovery scale (cinematic attacks).</summary>
	[Export(PropertyHint.None, "")]
	public bool NetsuIgnoreRecoveryScaling;

	/// <summary>Netsu (Oct 28): this hit never knocks down hard: the victim gets plain (BASIC) hitstun even in a juggle,
	/// so they can tech in the air or on landing (soft knockdown). Leticia's grenades and their explosions.</summary>
	[Export(PropertyHint.None, "")]
	public bool NetsuSoftKnockdown;

	[Export(PropertyHint.None, "")]
	public Vector2I AirBlockKnockback;

	[Export(PropertyHint.None, "")]
	public int AirBlockKnockbackGravity = 200000;

	[Export(PropertyHint.None, "")]
	public int AirBlockKnockbackTime = 8;

	[Export(PropertyHint.None, "")]
	public int AirBlockstun = 8;

	[ExportGroup("Throw Hit Settings", "")]
	[Export(PropertyHint.None, "")]
	public bool GroundThrow;

	[Export(PropertyHint.None, "")]
	public bool AirThrow;

	[Export(PropertyHint.None, "")]
	public int ThrowHitstop = 16;

	[Export(PropertyHint.None, "")]
	public int ThrowHitstopAfterHit = 30;

	[Export(PropertyHint.None, "")]
	public int ThrowHitReaction = -1;

	[ExportGroup("Corner Pushback Settings", "")]
	[Export(PropertyHint.None, "")]
	public bool AllowSelfPushback = true;

	[Export(PropertyHint.None, "")]
	public int SelfPushbackForce = -30000;

	[Export(PropertyHint.None, "")]
	public int SelfPushbackDuration = 8;

	[ExportGroup("Bounce Settings", "")]
	[Export(PropertyHint.None, "")]
	public int BounceTime;

	[Export(PropertyHint.None, "")]
	public int BounceXIntensity = 100;

	[Export(PropertyHint.None, "")]
	public int BounceYIntensity = 100;

	/// <summary>Netsu (Oct 26 c17): with BounceTime + BounceXIntensity, how far (units) from the attacker the opponent
	/// bounces off the "screen wall". 0 = the usual OnWallsCondition.NetsuScreenWallDistance (7 m). Smaller = earlier bounce.</summary>
	[Export(PropertyHint.None, "")]
	public int NetsuWallBounceDistance;

	/// <summary>Netsu (Oct 26 2026, TamaDeez): keep this attack box exactly where it is. By default a fighter's attack
	/// boxes reach down to her feet (PhysicsBody.NetsuBox); tick this for the rare move that must stay up high.</summary>
	[ExportGroup("Netsu", "")]
	[Export(PropertyHint.None, "")]
	public bool NetsuKeepHeight;

	// Oct 27 c33 (TamaDeez): on a special's counter hit the vertical knockback uses this percent instead of the global
	// GameManager.NetsuSpecialCounterKnockbackPercent (0 = use the global). Cecilia's slash-through lifts much higher on CH.
	[Export(PropertyHint.None, "")]
	public int NetsuCounterLiftPercent;

	// Oct 27 c35 (TamaDeez): an opponent who is being juggled (launched, still in the air) can't be put back on their
	// feet by a hit: a hit on them uses its air properties and, if those are plain hitstun, they stay launched.
	// Turn this on for a move that is designed to stand them up again.
	[Export(PropertyHint.None, "")]
	public bool NetsuAllowRestand;

	/// <summary>Netsu (Oct 28): this attack box only comes out if the opponent is in hitstun (a hit reaction). On block,
	/// or if they are in any other state, it does nothing and the attacker passes right through (Leticia's j.236).</summary>
	[Export(PropertyHint.None, "")]
	public bool NetsuRequireTargetHitstun;

	// Oct 27 c34: this hit's hard knockdown timing in simulation ticks (0 = the GameManager globals: 28 / 22 / 22)
	[Export(PropertyHint.None, "")]
	public int NetsuKnockdownImpact;

	[Export(PropertyHint.None, "")]
	public int NetsuKnockdownLying;

	[Export(PropertyHint.None, "")]
	public int NetsuKnockdownGetUp;

	/// <summary>Netsu (Oct 28, TamaDeez): float. An opponent hit in the air by this box rises NetsuFloatRise units over
	/// the first NetsuFloatRiseFrames frames, then hangs in place; NetsuFloatFrames frames after the hit they start to
	/// fall normally. They can't tech while floating (0 = off). Leticia's j.236.</summary>
	[Export(PropertyHint.None, "")]
	public int NetsuFloatFrames;

	/// <summary>Netsu (Oct 29, TamaDeez): carry. An opponent hit by this box moves with the attacker (same speed, so no
	/// pull toward her) while she is still rising; at her peak they stop rising and fall as usual, with at least
	/// SakugaActor.NetsuCarryReleaseHitstun frames of hitstun left. Flan's upward Star Rush (7/8/9).</summary>
	[Export(PropertyHint.None, "")]
	public bool NetsuCarryUp;

	/// <summary>Netsu (Oct 29, TamaDeez): the hit reaction this box puts them in plays at this speed (percent; 0 or 100
	/// = normal, 200 = twice as fast). Cecilia's 214EX ending: a quicker crumple so she can't combo after it.</summary>
	[Export(PropertyHint.None, "")]
	public int NetsuReactionSpeedPercent;

	[Export(PropertyHint.None, "")]
	public int NetsuFloatRise = 4000;

	[Export(PropertyHint.None, "")]
	public int NetsuFloatRiseFrames = 10;

	/// <summary>Netsu (Oct 29): the float also starts on a grounded opponent (a launcher that floats them: Leticia's 2C).</summary>
	[Export(PropertyHint.None, "")]
	public bool NetsuFloatFromGround;

	/// <summary>Netsu (Oct 29, TamaDeez): a hard knockdown hit stays a hard knockdown only while the combo's damage
	/// scaling is at least this % (before this hit); lower than that it's a normal knockdown (0 = always hard).
	/// Cecilia's 623A: hard knockdown early in a combo, not at the end of a long one.</summary>
	[Export(PropertyHint.Range, "0,100,1")]
	public int NetsuHardKnockdownMinScaling;
}
