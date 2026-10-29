using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

[GlobalClass]
[Icon("res://assets/sakuga_ui/Icons/Icon_Motion.png")]
public partial class MoveSettings : Resource
{
	[ExportCategory("Move Parameters")]
	[Export(PropertyHint.None, "")]
	public string MoveName;

	[Export(PropertyHint.None, "")]
	public int MoveState;

	[Export(PropertyHint.None, "")]
	public InputSideCheck SideCheck = InputSideCheck.CHARACTER_RELATIVE;

	[Export(PropertyHint.None, "")]
	public MotionInputs Inputs;

	[Export(PropertyHint.None, "")]
	public int FrameLimit = -1;

	[Export(PropertyHint.None, "")]
	public int SuperFlash;

	/// <summary>Netsu: no super flash or cut-in when the move starts; a NetsuSuperFlashAction in one of its
	/// states starts them later (counter supers flash only when the counter catches something).</summary>
	[Export(PropertyHint.None, "")]
	public bool NetsuFlashOnHit;

	/// <summary>Netsu: where this move comes in the neutral move check (which runs from the END of the move list
	/// down: the first move whose input matches wins). -1 = its place in the list. The throw (B+C) is appended at
	/// the end but checked as if at 37.5: after the supers, specials, Overdrive, Burst and Pushblock (so 236 + B+C
	/// is still a super), before the normals (so B+C isn't a 5C).</summary>
	[Export(PropertyHint.None, "")]
	public float NetsuCheckOrder = -1f;

	/// <summary>Netsu (Oct 25): frames the whole fight stops for when this EX move / super starts (the pause:
	/// GameManager.NetsuPause; the camera moves in, the stage goes dark). -1 = the usual length: EX moves
	/// GameManager.NetsuPauseExFrames (30 = half a second), supers NetsuPauseSuperFrames (60 = a second).</summary>
	[Export(PropertyHint.None, "")]
	public int NetsuPauseFrames = -1;

	/// <summary>Netsu (Oct 25): a state of this fighter whose animation plays while that pause holds the fight (only
	/// the picture moves, nothing else: Flan's 214 super twirls, charging the punch). -1 = she holds still.</summary>
	[Export(PropertyHint.None, "")]
	public int NetsuPauseState = -1;

	[Export(PropertyHint.None, "")]
	public int Priority;

	[Export(PropertyHint.None, "")]
	public MoveEndCondition MoveEnd;

	[Export(PropertyHint.None, "")]
	public int MoveEndState = -1;

	[ExportCategory("Move Conditions")]
	[Export(PropertyHint.None, "")]
	public int SuperGaugeRequired;

	[Export(PropertyHint.None, "")]
	public int WillGaugeRequired;

	[Export(PropertyHint.None, "")]
	public Vector2I HealthRequired = new Vector2I(0, 99999);

	[Export(PropertyHint.None, "")]
	public Vector2I DistanceArea = new Vector2I(0, 999999);

	[Export(PropertyHint.None, "")]
	public int MinimumHeight;

	[Export(PropertyHint.None, "")]
	public int[] IsSequenceFromStates;

	[Export(PropertyHint.None, "")]
	public int[] IgnoreStates;

	[Export(PropertyHint.None, "")]
	public MoveCancelSettings[] CanCancelTo;

	[Export(PropertyHint.None, "")]
	public CustomVariableCondition[] VariablesRequirement;

	[Export(PropertyHint.None, "")]
	public CustomVariableChange[] VariablesChange;

	[ExportCategory("Move Flags")]
	[Export(PropertyHint.None, "")]
	public bool SkipCheck;

	[Export(PropertyHint.None, "")]
	public bool Unlockable;

	[Export(PropertyHint.None, "")]
	public bool CanBeOverrided;

	[Export(PropertyHint.None, "")]
	public bool IgnoreSelf = true;

	[Export(PropertyHint.None, "")]
	public bool PriorityBuffer;

	[Export(PropertyHint.None, "")]
	public bool IgnoreSamePriority = true;

	[Export(PropertyHint.None, "")]
	public bool AcceptNullStates;

	[Export(PropertyHint.None, "")]
	public bool AcceptMovementStates = true;

	[Export(PropertyHint.None, "")]
	public bool AcceptCombatStates;

	[Export(PropertyHint.None, "")]
	public bool AcceptBlockingStates;

	[Export(PropertyHint.None, "")]
	public bool AcceptHitReactionStates;

	[Export(PropertyHint.None, "")]
	public bool IgnoreHitstop;

	[Export(PropertyHint.None, "")]
	public bool IgnoreHitstun;

	[Export(PropertyHint.None, "")]
	public bool IgnoreKnockdownHits;

	[Export(PropertyHint.None, "")]
	public bool UseOnGround;

	[Export(PropertyHint.None, "")]
	public bool UseOnAir;

	/// <summary>Netsu (Oct 26 2026, TamaDeez): in the air this move can be done once until she lands (Flan's air
	/// Rising Star / Spiral Star: no rising again and again). Doing it on the ground also uses it up until she
	/// lands again. SakugaActor.NetsuAirMoveUsed.</summary>
	[Export(PropertyHint.None, "")]
	public bool NetsuOncePerJump;

	/// <summary>Netsu (Oct 28): landing recovery (frames) this jump will have after this move (Leticia's air dashes: 12).
	/// An air normal done afterwards cuts it down to the normal's own landing lag (StanceManager.NetsuAirDashLandLag).</summary>
	[Export(PropertyHint.None, "")]
	public int NetsuAirLandLag;

	/// <summary>Netsu (Oct 28): this move can't be started while anything spawned by a move with this same flag is still
	/// active (Leticia's 214: no new fragments until the current ones have exploded).</summary>
	[Export(PropertyHint.None, "")]
	public bool NetsuNoRepeatWhileSpawned;
}
