using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

[GlobalClass]
[Tool]
public partial class AttackProfile : Resource
{
	[ExportGroup("Damage Settings", "")]
	[Export(PropertyHint.None, "")]
	public HitType HitType = HitType.MEDIUM;

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
	public AttackLevel AttackLevel;

	[ExportGroup("Ground Hit Settings", "")]
	[Export(PropertyHint.None, "")]
	public HitstunType GroundHitstunType = HitstunType.BASIC;

	[Export(PropertyHint.None, "")]
	public Vector2I GroundHitKnockback = new Vector2I(-30000, 0);

	[Export(PropertyHint.None, "")]
	public Vector2I GroundBlockKnockback = new Vector2I(-30000, 0);

	[ExportGroup("Air Hit Settings", "")]
	[Export(PropertyHint.None, "")]
	public HitstunType AirHitstunType = HitstunType.BASIC;

	[Export(PropertyHint.None, "")]
	public Vector2I AirHitKnockback = new Vector2I(-30000, 20000);

	[Export(PropertyHint.None, "")]
	public Vector2I AirBlockKnockback = new Vector2I(-30000, 15000);

	[ExportGroup("Throw Hit Settings", "")]
	[Export(PropertyHint.None, "")]
	public bool GroundThrow = true;

	[Export(PropertyHint.None, "")]
	public bool AirThrow;

	[Export(PropertyHint.None, "")]
	public bool Immediate;

	[Export(PropertyHint.None, "")]
	public int ThrowHitReaction = -1;

	[ExportGroup("Bounce Settings", "")]
	[Export(PropertyHint.None, "")]
	public int BounceTime;

	[Export(PropertyHint.None, "")]
	public int BounceXIntensity = 100;

	[Export(PropertyHint.None, "")]
	public int BounceYIntensity = 100;

	[ExportGroup("Override Values", "")]
	[Export(PropertyHint.None, "")]
	public int OverridePriority = -1;

	[Export(PropertyHint.None, "")]
	public int OverrideSelfHitStop = -1;

	[Export(PropertyHint.None, "")]
	public int OverrideOpponentHitStop = -1;

	[Export(PropertyHint.None, "")]
	public int OverrideBlockStop = -1;

	[Export(PropertyHint.None, "")]
	public int OverrideArmorDamage = -1;

	[Export(PropertyHint.None, "")]
	public int OverrideGroundHitstun = -1;

	[Export(PropertyHint.None, "")]
	public int OverrideAirHitstun = -1;

	[Export(PropertyHint.None, "")]
	public int OverrideGroundBlockstun = -1;

	[Export(PropertyHint.None, "")]
	public int OverrideAirBlockstun = -1;

	[Export(PropertyHint.None, "")]
	public int OverrideDamageScalingSubtract = -1;

	[Export(PropertyHint.None, "")]
	public int OverrideGroundHitReaction = -1;

	[Export(PropertyHint.None, "")]
	public int OverrideCrouchHitReaction = -1;

	[Export(PropertyHint.None, "")]
	public int OverrideAirHitReaction = -1;

	[Export(PropertyHint.None, "")]
	public int OverrideHitEffect = -1;

	[Export(PropertyHint.None, "")]
	public int OverrideHitKnockbackDuration = -1;

	[Export(PropertyHint.None, "")]
	public int OverrideBlockKnockbackDuration = -1;

	[Export(PropertyHint.None, "")]
	public int OverrideGroundKnockbackGravity = -1;

	[Export(PropertyHint.None, "")]
	public int OverrideAirKnockbackGravity = -1;

	[Export(PropertyHint.None, "")]
	public int OverrideCornerPushback = -1;
}
