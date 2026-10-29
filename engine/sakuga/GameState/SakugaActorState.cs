using MessagePack;
using SakugaEngine.Global;

namespace SakugaEngine.GameState;

[MessagePackObject(false)]
public struct SakugaActorState
{
	[Key(0)]
	public bool IsActive;

	[Key(1)]
	public PhysicsBodyState Body;

	[Key(2)]
	public ParametersState Parameters;

	[Key(3)]
	public StateManagerState StateManager;

	[Key(4)]
	public StanceManagerState StanceManager;

	[Key(5)]
	public int LayerSorting;

	[Key(6)]
	public int BounceXIntensity;

	[Key(7)]
	public int BounceYIntensity;

	[Key(8)]
	public bool SuperFlashing;

	[Key(9)]
	public bool CinematicState;

	[Key(10)]
	public bool BlockStun;

	[Key(11)]
	public HitstunType HitstunType;

	[Key(12)]
	public FrameProperties FrameProperties;

	[Key(13)]
	public HitChecker HitCheck;

	[Key(14)]
	public CancelCondition CancelConditions;

	[Key(15)]
	public int NetsuThrowProtect;   // Netsu (Oct 24 night): frames left that the fighter can't be thrown

	[Key(16)]
	public int NetsuOrbitSide;      // Netsu (Oct 25): the side of the opponent an orbit started on (NetsuOrbitAction)

	[Key(17)]
	public int NetsuDownFrames;     // Netsu (Oct 26): frames lying on the ground (OTG window, wake-up invincibility)

	[Key(43)]
	public int NetsuRecoveryScale;  // Netsu (Oct 28): the combo's recovery scale (permille; 0 = untouched = 1000)

	[Key(18)]
	public bool NetsuNoBurst;       // Netsu (Oct 26 evening): hit by an Overdrive: no Burst until the combo ends

	[Key(19)]
	public bool NetsuAirMoveUsed;   // Netsu (Oct 26 late): a once-per-jump move (Flan's air 623) was used this jump

	[Key(20)]
	public ulong NetsuChainUsed;    // Netsu (Oct 26 late): normals already used in this chain (one bit per move)

	[Key(21)]
	public bool NetsuSuperActive;   // Netsu (Oct 26 late): a 3-bar super is running (its hits do more damage)

	[Key(25)]
	public bool NetsuSuperConnected;   // Netsu (Oct 26 c14): the running super has already hit

	[Key(26)]
	public int NetsuComboFrames;       // Netsu (Oct 26 c15): juggle system: combo time on this fighter

	[Key(27)]
	public int NetsuUntechMax;         // Netsu (Oct 26 c15): hitstun the last hit gave (juggle meter)

	[Key(28)]
	public bool NetsuAirCounterLock;   // Netsu (Oct 26 c15): air counter hit: no tech until landing

	[Key(29)]
	public int NetsuCounterFlashAt;    // Netsu (Oct 26 c15): frame of the last counter hit (red flash)

	[Key(30)]
	public int NetsuWallBounceDistance;   // Netsu (Oct 26 c17)

	[Key(22)]
	public int NetsuLandLag;        // Netsu (Oct 26 late): landing recovery frames left

	[Key(23)]
	public int NetsuAirAttackLag;   // Netsu (Oct 26 late): landing recovery this jump will have (air normals used)

	[Key(24)]
	public bool NetsuWasAir;

	[Key(31)]
	public ulong NetsuComboUsedLo;   // Netsu (Oct 27 c27): repeat proration: moves used in this combo (low bit of each 2-bit count)

	[Key(32)]
	public ulong NetsuComboUsedHi;   // (high bit)

	[Key(33)]
	public int NetsuComboUseA;       // the last three move uses counted

	[Key(34)]
	public int NetsuComboUseB;

	[Key(35)]
	public int NetsuComboUseC;

	[Key(36)]
	public int NetsuSpawnMove;       // Netsu (Oct 27 c27): on a projectile: the owner's move that spawned it

	[Key(37)]
	public int NetsuSpawnUse;

	[Key(38)]
	public int NetsuOtgWindowAtLand; // Netsu (Oct 27 c27): OTG window set on landing (-1 = not lying)

	[Key(39)]
	public int NetsuOtgSpent;        // Oct 27 c34: OTG window used up by OTG hits

	[Key(40)]
	public int NetsuKdImpact;        // per-hit knockdown timing overrides (0 = global)

	[Key(41)]
	public int NetsuKdLying;

	[Key(42)]
	public int NetsuKdGetUp;

	[Key(44)]
	public bool NetsuAirTechInvul;   // Oct 28: air tech: invincible until landing or until she acts

	[Key(45)]
	public int NetsuAirTechWait;     // Oct 28: air tech: frames left before she can act

	[Key(46)]
	public int NetsuAirTechFresh;    // Oct 28: air tech: frames since she can act (only presses after that count)

	[Key(47)]
	public int NetsuFloatFrame;      // Oct 28: float (j.236 hit): frames since the hit, 0 = not floating

	[Key(48)]
	public int NetsuFloatTotal;      // frames the float lasts

	[Key(49)]
	public int NetsuFloatRise;       // rise (units) and its frames, packed: rise * 64 + frames

	[Key(50)]
	public ulong NetsuBounceUsedLo;  // Oct 29: moves that ground-bounced them in this combo

	[Key(51)]
	public ulong NetsuBounceUsedHi;

	[Key(52)]
	public int NetsuBounceUse;

	[Key(53)]
	public int NetsuExHoldKey;       // Oct 29: the EX use keeping them airborne (0 = none)

	[Key(54)]
	public int NetsuStarStacks;      // Oct 29: Flan's star stacks

	[Key(55)]
	public bool NetsuMeterSpendTag;  // Oct 29: belongs to a meter-spending move (no meter for its hits)

	public void GetStateData(ref SakugaActor reference)
	{
		IsActive = reference.IsActive;
		Body.GetStateData(ref reference.Body);
		Parameters.GetStateData(ref reference.Parameters);
		StateManager.GetStateData(ref reference.StateManager);
		StanceManager.GetStateData(ref reference.StanceManager);
		LayerSorting = reference.LayerSorting;
		BounceXIntensity = reference.BounceXIntensity;   // Netsu fix: these saved LayerSorting by mistake
		BounceYIntensity = reference.BounceYIntensity;
		SuperFlashing = reference.SuperFlashing;
		CinematicState = reference.CinematicState;
		BlockStun = reference.BlockStun;
		HitstunType = reference.HitstunType;
		FrameProperties = reference.FrameProperties;
		HitCheck = reference.HitCheck;
		CancelConditions = reference.CancelConditions;
		NetsuThrowProtect = reference.NetsuThrowProtect;
		NetsuOrbitSide = reference.NetsuOrbitSide;
		NetsuDownFrames = reference.NetsuDownFrames;
		NetsuNoBurst = reference.NetsuNoBurst;
		NetsuRecoveryScale = reference.NetsuRecoveryScale;
		NetsuAirMoveUsed = reference.NetsuAirMoveUsed;
		NetsuChainUsed = reference.NetsuChainUsed;
		NetsuSuperActive = reference.NetsuSuperActive;
		NetsuSuperConnected = reference.NetsuSuperConnected;
		NetsuComboFrames = reference.NetsuComboFrames;
		NetsuUntechMax = reference.NetsuUntechMax;
		NetsuAirCounterLock = reference.NetsuAirCounterLock;
		NetsuCounterFlashAt = reference.NetsuCounterFlashAt;
		NetsuLandLag = reference.NetsuLandLag;
		NetsuAirAttackLag = reference.NetsuAirAttackLag;
		NetsuWasAir = reference.NetsuWasAir;
		NetsuWallBounceDistance = reference.NetsuWallBounceDistance;
		NetsuComboUsedLo = reference.NetsuComboUsedLo;
		NetsuComboUsedHi = reference.NetsuComboUsedHi;
		NetsuComboUseA = reference.NetsuComboUseA;
		NetsuComboUseB = reference.NetsuComboUseB;
		NetsuComboUseC = reference.NetsuComboUseC;
		NetsuSpawnMove = reference.NetsuSpawnMove;
		NetsuSpawnUse = reference.NetsuSpawnUse;
		NetsuOtgWindowAtLand = reference.NetsuOtgWindowAtLand;
		NetsuOtgSpent = reference.NetsuOtgSpent;
		NetsuKdImpact = reference.NetsuKdImpact;
		NetsuKdLying = reference.NetsuKdLying;
		NetsuKdGetUp = reference.NetsuKdGetUp;
		NetsuAirTechInvul = reference.NetsuAirTechInvul;
		NetsuAirTechWait = reference.NetsuAirTechWait;
		NetsuAirTechFresh = reference.NetsuAirTechFresh;
		NetsuFloatFrame = reference.NetsuFloatFrame;
		NetsuFloatTotal = reference.NetsuFloatTotal;
		NetsuFloatRise = reference.NetsuFloatRise;
		NetsuBounceUsedLo = reference.NetsuBounceUsedLo;
		NetsuBounceUsedHi = reference.NetsuBounceUsedHi;
		NetsuBounceUse = reference.NetsuBounceUse;
		NetsuExHoldKey = reference.NetsuExHoldKey;
		NetsuStarStacks = reference.NetsuStarStacks;
		NetsuMeterSpendTag = reference.NetsuMeterSpendTag;
	}

	public void SetStateData(ref SakugaActor reference)
	{
		reference.IsActive = IsActive;
		Body.SetStateData(ref reference.Body);
		Parameters.SetStateData(ref reference.Parameters);
		StateManager.SetStateData(ref reference.StateManager);
		StanceManager.SetStateData(ref reference.StanceManager);
		reference.LayerSorting = LayerSorting;
		reference.BounceXIntensity = BounceXIntensity;
		reference.BounceYIntensity = BounceYIntensity;
		reference.NetsuWallBounceDistance = NetsuWallBounceDistance;
		reference.SuperFlashing = SuperFlashing;
		reference.CinematicState = CinematicState;
		reference.BlockStun = BlockStun;
		reference.HitstunType = HitstunType;
		reference.FrameProperties = FrameProperties;
		reference.HitCheck = HitCheck;
		reference.CancelConditions = CancelConditions;
		reference.NetsuThrowProtect = NetsuThrowProtect;
		reference.NetsuOrbitSide = NetsuOrbitSide;
		reference.NetsuDownFrames = NetsuDownFrames;
		reference.NetsuNoBurst = NetsuNoBurst;
		reference.NetsuRecoveryScale = NetsuRecoveryScale;
		reference.NetsuAirMoveUsed = NetsuAirMoveUsed;
		reference.NetsuChainUsed = NetsuChainUsed;
		reference.NetsuSuperActive = NetsuSuperActive;
		reference.NetsuSuperConnected = NetsuSuperConnected;
		reference.NetsuComboFrames = NetsuComboFrames;
		reference.NetsuUntechMax = NetsuUntechMax;
		reference.NetsuAirCounterLock = NetsuAirCounterLock;
		reference.NetsuCounterFlashAt = NetsuCounterFlashAt;
		reference.NetsuLandLag = NetsuLandLag;
		reference.NetsuAirAttackLag = NetsuAirAttackLag;
		reference.NetsuWasAir = NetsuWasAir;
		reference.NetsuComboUsedLo = NetsuComboUsedLo;
		reference.NetsuComboUsedHi = NetsuComboUsedHi;
		reference.NetsuComboUseA = NetsuComboUseA;
		reference.NetsuComboUseB = NetsuComboUseB;
		reference.NetsuComboUseC = NetsuComboUseC;
		reference.NetsuSpawnMove = NetsuSpawnMove;
		reference.NetsuSpawnUse = NetsuSpawnUse;
		reference.NetsuOtgWindowAtLand = NetsuOtgWindowAtLand;
		reference.NetsuOtgSpent = NetsuOtgSpent;
		reference.NetsuKdImpact = NetsuKdImpact;
		reference.NetsuKdLying = NetsuKdLying;
		reference.NetsuKdGetUp = NetsuKdGetUp;
		reference.NetsuAirTechInvul = NetsuAirTechInvul;
		reference.NetsuAirTechWait = NetsuAirTechWait;
		reference.NetsuAirTechFresh = NetsuAirTechFresh;
		reference.NetsuFloatFrame = NetsuFloatFrame;
		reference.NetsuFloatTotal = NetsuFloatTotal;
		reference.NetsuFloatRise = NetsuFloatRise;
		reference.NetsuBounceUsedLo = NetsuBounceUsedLo;
		reference.NetsuBounceUsedHi = NetsuBounceUsedHi;
		reference.NetsuBounceUse = NetsuBounceUse;
		reference.NetsuExHoldKey = NetsuExHoldKey;
		reference.NetsuStarStacks = NetsuStarStacks;
		reference.NetsuMeterSpendTag = NetsuMeterSpendTag;
	}
}
