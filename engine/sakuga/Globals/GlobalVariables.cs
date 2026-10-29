namespace SakugaEngine.Global;

public static class GlobalVariables
{
	public const int TicksPerSecond = 60;

	public const int SubSteps = 2;

	public const int Delta = 120;

	public const int SimulationScale = 10000;

	/// <summary>Netsu (Oct 27 c26): half the stage width (the walls are at -WallLimit and +WallLimit). Every wall,
	/// the camera's limit and the moves that carry the opponent read this one number. To undo c26: 120000 (24 m).</summary>
	public const int WallLimit = 90000;   // c26: 120000 -> 90000 (stage 24 m -> 18 m wide)

	public const int CeilingLimit = 250000;

	/// <summary>Netsu (Oct 28): how big the fighters look on the screen (Under Night In-Birth's framing). Only the view
	/// changes (the camera sits closer, the stage is drawn a little smaller): nothing in the fight (sizes, hitboxes,
	/// distances) moves. 1 = the old view. F8 in a match switches between the two. Each match starts from this
	/// default: set NetsuViewZoom = 1f and NetsuStageScale = 1f to go back for good.</summary>
	/// <summary>Netsu (Oct 28): the most the two fighters can be apart (10000 = 1 m; 0 = no limit, the old 18 m of stage).
	/// Like Under Night In-Birth the one walking away is stopped at the edge of the screen and the stage scrolls behind
	/// them, so the camera can stay close. This IS gameplay (zoning range, corner carry): to undo set 0.</summary>
	public const int NetsuMaxSeparation = 75000;

	public const float NetsuViewZoom = 1.08f;

	/// <summary>...and how much smaller the stage is drawn then (1 = the old size).</summary>
	public const float NetsuStageScale = 0.9f;

	/// <summary>Runtime switch for the two numbers above (F8). Presentation only: never saved or rolled back.</summary>
	public static bool NetsuBigView = true;

	public static float NetsuZoomNow => NetsuBigView ? NetsuViewZoom : 1f;

	public static float NetsuStageScaleNow => NetsuBigView ? NetsuStageScale : 1f;

	/// <summary>Netsu (Oct 29): the health every Craft Gauge / Burst gain is measured against (normalizedDamage =
	/// damage x 10,000 / this). One number for every character, so a hit worth 10% of it gives the same meter whoever
	/// takes it. 12,500 = the usual MaxHealth.</summary>
	public const int NetsuReferenceHP = 12500;

	public const int StartingPosition = 12500;

	public const int MaxPlayersDistance = 100000;

	public const int InputHistorySize = 16;

	public const int KaraCancelWindow = 3;

	public const int InstantBlockWindow = 3;

	public const int DefaultGravity = 260000;

	public const int DefaultAcceleration = 360000;

	public const int DefaultDeceleration = 250000;

	public const int DefaultFriction = 400000;

	public const int GravityDecay = 2500;

	public const int HitstunDecayMinCombo = 8;

	public const int MinHitstun = 8;

	public const int GuardCrushHitstun = 40;

	public const int DefaultBaseHitstop = 10;

	public const int DefaultCounterHitstop = 20;

	public const int DefaultClashHitstop = 20;

	public const int DefaultArmorHitstop = 20;

	public const int DefaultBlockHitstop = 6;

	public const int DefaultThrowHitstop = 16;

	public const int DefaultLongThrowHitstop = 30;

	public const int DefaultKnockbackDuration = 8;

	public const int ThrowEscapePushForce = 45000;

	public const ushort BaseMinDamageScaling = 15;

	public const ushort BaseMaxDamageScaling = 100;

	public const ushort CornerMinDamageScaling = 20;

	public const ushort CornerMaxDamageScaling = 120;

	public const ushort DamageScalingSubtract = 10;

	public const int MoveBufferLength = 10;

	public const int NotificationDuration = 60;

	public const int BlockEffectIndex = 1;

	public const int ClashEffectIndex = 2;

	public const int ArmorEffectIndex = 3;

	public const int GuardCrushEffectIndex = 0;
}
