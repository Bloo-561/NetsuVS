using Godot;
using SakugaEngine.Game;
using SakugaEngine.Global;
using SakugaEngine.Resources;

namespace SakugaEngine;

[GlobalClass]
public partial class StanceManager : Node
{
	private SakugaActor _owner;

	[Export(PropertyHint.None, "")]
	public FrameTimer MoveBuffer;

	public bool CanRun;

	public int CurrentStance;

	public int BufferedMove = -1;

	public int CurrentMove = -1;

	public bool CancelBuffer;

	/// <summary>Counts every move that starts. The CPU (AIBrain) uses it to see
	/// that the move it just input actually came out.</summary>
	public int ExecutedMoves;

	public void Initialize(SakugaActor owner)
	{
		_owner = owner;
		CurrentStance = 0;
	}

	public bool CheckMoveConditions(int index)
	{
		return CheckMoveConditions(index, ignoreStateType: false);
	}

	/// <param name="ignoreStateType">Netsu: skip the "can it start in this kind of state" check (the move is only
	/// being buffered, or replaces a normal that just started from the first button of a two-button press).</param>
	public bool CheckMoveConditions(int index, bool ignoreStateType)
	{
		if (!NetsuBurstOrOverdriveState(index))
		{
			return false;   // Netsu (Oct 26 late): Burst only in hitstun, Overdrive anywhere else
		}
		if (!ignoreStateType && !NetsuAllowedStateType(index))
		{
			return false;
		}
		if (CurrentMove >= 0)
		{
			if (CurrentMove == index && GetMove(index).IgnoreSelf)
			{
				return false;
			}
			if (GetMove(index).PriorityBuffer && GetMove(index).Priority < GetCurrentMove().Priority)
			{
				return false;
			}
		}
		if (GetMove(index).AcceptHitReactionStates && GetMove(index).IgnoreKnockdownHits && _owner.HitstunType >= HitstunType.KNOCKDOWN)
		{
			return false;
		}
		if (_owner.NetsuAirCounterLock && GetMove(index).AcceptHitReactionStates && !NetsuIsBurst(index) && !NetsuIsOverdrive(index))
		{
			return false;   // Oct 27: air counter hit: no tech (any recovery move) until they land or are hit again
		}
		if (_owner.Parameters.SuperGauge.CurrentValue < GetMove(index).SuperGaugeRequired)
		{
			return false;
		}
		if (_owner.Parameters.Will.CurrentValue < GetMove(index).WillGaugeRequired)
		{
			return false;
		}
		if (GetMove(index).WillGaugeRequired > 0 && _owner.Parameters.Will.State != SakugaEngine.Global.WillState.WORKING)
		{
			return false;   // Netsu: no Burst or second Overdrive while Overdrive is running
		}
		if (GetMove(index).WillGaugeRequired > 0 && _owner.NetsuNoBurst && GetMove(index).MoveName != NetsuOverdriveName)
		{
			return false;   // Netsu (Oct 26 evening): hit by an Overdrive, no Burst until this combo ends
		}
		if (_owner.Parameters.Health.CurrentValue < GetMove(index).HealthRequired.X || _owner.Parameters.Health.CurrentValue > GetMove(index).HealthRequired.Y)
		{
			return false;
		}
		int distance = GlobalFunctions.Distance(_owner.GetOpponent(0).Body.FixedPosition, _owner.Body.FixedPosition).X;
		if (distance < GetMove(index).DistanceArea.X || distance > GetMove(index).DistanceArea.Y)
		{
			return false;
		}
		if (!IsCorrectSurface(index))
		{
			return false;
		}
		if (GetMove(index).NetsuNeedSpawnPool >= 0 && !NetsuSpawnInState(GetMove(index)))
		{
			return false;   // Nov 3: Noah's 22A / 22B snaps need their own hole out and waiting
		}
		if (GetMove(index).NetsuNoRepeatWhileSpawned && _owner.Pool != null)
		{
			FighterStance netsuSt = GetCurrentStance();
			for (int nm = 0; netsuSt != null && netsuSt.Moves != null && nm < netsuSt.Moves.Length; nm++)
			{
				MoveSettings other = GetMove(nm);
				if (other != null && other.NetsuNoRepeatWhileSpawned && _owner.Pool.NetsuHasActiveSpawnFrom(nm))
				{
					return false;   // Oct 28: the last fragments haven't exploded yet
				}
			}
		}
		if (GetMove(index).NetsuOncePerJump && _owner.NetsuAirMoveUsed && _owner.Body != null && !_owner.Body.IsOnGround)
		{
			return false;   // Netsu (Oct 26 late): once per jump (Flan's air 623)
		}
		if (!CheckStatesToIgnore(index))
		{
			return false;
		}
		if (!CheckOwnerState(index))
		{
			return false;
		}
		if (!_owner.Parameters.CompareVariables(GetMove(index).VariablesRequirement))
		{
			return false;
		}
		bool AllowedFrameWindow = _owner.StateManager.CurrentStateFrame < GetMove(index).FrameLimit;
		if (GetMove(index).FrameLimit > 0 && !AllowedFrameWindow)
		{
			return false;
		}
		return true;
	}

	public void CheckMoves()
	{
		if (MoveBuffer == null || !CanRun)
		{
			return;
		}
		if (_owner != null && _owner.NetsuDownFrames > 0 && !_owner.IsKO())
		{
			return;   // Oct 27 c34: hard knockdown: no moves, jumps, throws or bursts (holding a guard direction is fine) until the 72 ticks are over
		}
		if (_owner != null && (_owner.NetsuBursting() || _owner.NetsuBurstPunishable))
		{
			CheckMoveEndCondition();
			return;   // Nov 3: nothing else during a Burst or while coming down from it (until she's back to neutral)
		}
		if (NetsuAutoAirTech())
		{
			CheckMoveEndCondition();
			CheckMoveCancel();
			ProcessMoveBuffer();
			return;   // Oct 29: holding A / B / C in the air while hit: tech as soon as the untech time is over
		}
		bool netsuTechWait = _owner != null && _owner.NetsuAirTechLocked();   // Oct 28: just air teched: can't act yet
		int netsuTechFresh = _owner != null ? _owner.NetsuAirTechFresh : 0;
		int netsuPressAge = netsuTechFresh > 0 ? _owner.Inputs.NetsuLastButtonPressAge() : 0;
		int[] order = NetsuMoveOrder();
		bool kara = NetsuKaraWindow();
		bool stunBuffer = NetsuStunBuffer();
		_netsuMultiPressed = false;
		bool netsuAb = !netsuTechWait && NetsuAbDash();
		for (int o = 0; o < order.Length && !netsuAb && !netsuTechWait; o++)
		{
			int i = order[o];
			MoveSettings move = GetMove(i);
			if (move.SkipCheck)
			{
				continue;
			}
			if (NetsuIsAirTechMove(i))
			{
				continue;   // Oct 29: air tech only happens by holding a button (NetsuAutoAirTech), not by a press
			}
			if (netsuTechFresh > 0 && netsuPressAge > netsuTechFresh && NetsuUsesButton(move.Inputs))
			{
				continue;   // Oct 28: a button pressed during the air tech wait doesn't count (no instant mash normal)
			}
			// Netsu: B, then C a frame later: the 5B (or 236B) that came out on the B becomes the B+C move (throw,
			// 236 + B+C super) at once, instead of waiting for the first move to end
			bool asCancel = kara && move.Priority > GetCurrentMove().Priority && NetsuMultiButton(move.Inputs) && CheckMoveConditions(i, ignoreStateType: true);
			bool allowed = asCancel || CheckMoveConditions(i);
			if (!allowed && stunBuffer && move.Priority >= NetsuStunBufferPriority && (move.AcceptNullStates || move.AcceptMovementStates) && CheckMoveConditions(i, ignoreStateType: true))
			{
				// Netsu: pressed in the last frames of block / hit stun (or while knocked down): kept in the buffer and
				// done on the first frame it's allowed (ProcessMoveBuffer checks the state type again)
				allowed = true;
			}
			if (allowed && NetsuInputDone(i))
			{
				BufferMove(i, asCancel);
				// (Oct 25: only when two buttons really are down: a super whose inputs also list a B+C version, matched
				// with one button (214214 + A), wrongly stopped the 214 + A rekka follow-up below)
				_netsuMultiPressed = NetsuMultiButton(move.Inputs) && _owner.Inputs.NetsuHeldButtonCount() >= 2;
				break;
			}
		}
		CheckMoveEndCondition();
		CheckMoveCancel();
		if (netsuTechWait)
		{
			BufferedMove = -1;   // Oct 28: nothing pressed before the tech (or during its wait) comes out after it
			return;
		}
		ProcessMoveBuffer();
	}

	// ---------------------------------------------------------------------------------------------
	// Netsu (Oct 29 2026, TamaDeez): air tech by holding. A fighter knocked into the air techs (Recovery_Air) the moment
	// they are allowed to, but only while holding A, B or C; holding forward picks the forward tech, anything else the
	// back one. Without a button held they don't tech at all (they fall and land). Tapping a button no longer techs.

	/// <summary>The move starts an air tech (its state is a "Recovery_Air" one).</summary>
	public bool NetsuIsAirTechMove(int index)
	{
		MoveSettings m = GetMove(index);
		FighterState[] states = _owner?.Data?.States;
		if (m == null || states == null || m.MoveState < 0 || m.MoveState >= states.Length || states[m.MoveState] == null)
		{
			return false;
		}
		string n = states[m.MoveState].StateName;
		return n != null && n.StartsWith("Recovery_Air");
	}

	/// <summary>Netsu (Oct 29): the untech time ran out in the air: tech now, whatever is pressed. Forward held = forward
	/// tech, back held = back tech, nothing = straight down (the forward tech with no sideways motion).</summary>
	public bool NetsuForceAirTech()
	{
		if (_owner == null || _owner.Inputs == null || _owner.Data == null || _owner.Data.States == null)
		{
			return false;
		}
		int h = _owner.Inputs.CurrentHistory;
		bool forward = _owner.Inputs.CheckDirectionalInputs(h, _owner.InputSide(), DirectionalInputs.RIGHT, ButtonMode.HOLD, false)
			|| _owner.Inputs.CheckDirectionalInputs(h, _owner.InputSide(), DirectionalInputs.UP_RIGHT, ButtonMode.HOLD, false)
			|| _owner.Inputs.CheckDirectionalInputs(h, _owner.InputSide(), DirectionalInputs.DOWN_RIGHT, ButtonMode.HOLD, false);
		bool back = !forward && (_owner.Inputs.CheckDirectionalInputs(h, _owner.InputSide(), DirectionalInputs.LEFT, ButtonMode.HOLD, false)
			|| _owner.Inputs.CheckDirectionalInputs(h, _owner.InputSide(), DirectionalInputs.UP_LEFT, ButtonMode.HOLD, false)
			|| _owner.Inputs.CheckDirectionalInputs(h, _owner.InputSide(), DirectionalInputs.DOWN_LEFT, ButtonMode.HOLD, false));
		FighterStance stance = GetCurrentStance();
		int fwd = -1;
		int bwd = -1;
		for (int i = 0; stance != null && stance.Moves != null && i < stance.Moves.Length; i++)
		{
			if (!NetsuIsAirTechMove(i))
			{
				continue;
			}
			if (_owner.Data.States[GetMove(i).MoveState].StateName.Contains("Forward"))
			{
				fwd = i;
			}
			else
			{
				bwd = i;
			}
		}
		int pick = back ? (bwd >= 0 ? bwd : fwd) : (fwd >= 0 ? fwd : bwd);
		if (pick < 0)
		{
			return false;
		}
		_owner.NetsuNeutralTech = !forward && !back;
		ExecuteMove(pick);
		return true;
	}

	private bool NetsuAutoAirTech()
	{
		if (_owner == null || _owner.Body == null || _owner.Body.IsOnGround || _owner.StateManager == null || _owner.Inputs == null
			|| _owner.StateManager.CurrentStateType() != StateType.HIT_REACTION || _owner.IsKO())
		{
			return false;
		}
		if ((_owner.CanHitstun() && _owner.Hitstun.IsRunning()) || _owner.OnHitstop())
		{
			return false;   // not yet (Burst and the rest are checked as usual meanwhile)
		}
		PlayerInputs raw = _owner.Inputs.InputHistory[_owner.Inputs.CurrentHistory].rawInput;
		if ((raw & (PlayerInputs.FACE_A | PlayerInputs.FACE_B | PlayerInputs.FACE_C)) == 0)
		{
			return false;
		}
		bool forward = _owner.Inputs.CheckDirectionalInputs(_owner.Inputs.CurrentHistory, _owner.InputSide(), DirectionalInputs.RIGHT, ButtonMode.HOLD, false);
		bool back = !forward && _owner.Inputs.CheckDirectionalInputs(_owner.Inputs.CurrentHistory, _owner.InputSide(), DirectionalInputs.LEFT, ButtonMode.HOLD, false);
		forward = !back;   // Oct 29: no direction = neutral tech (the forward one, no sideways motion: SakugaActor.NetsuNeutralTick)
		FighterStance stance = GetCurrentStance();
		int pick = -1;
		int other = -1;
		for (int i = 0; stance != null && stance.Moves != null && i < stance.Moves.Length; i++)
		{
			if (!NetsuIsAirTechMove(i) || !CheckMoveConditions(i))
			{
				continue;
			}
			bool isForward = _owner.Data.States[GetMove(i).MoveState].StateName.Contains("Forward");
			if (isForward == forward)
			{
				pick = i;
			}
			else
			{
				other = i;
			}
		}
		if (pick < 0)
		{
			pick = other;
		}
		if (pick < 0)
		{
			return false;
		}
		_owner.NetsuNeutralTech = !back && !_owner.Inputs.CheckDirectionalInputs(_owner.Inputs.CurrentHistory, _owner.InputSide(), DirectionalInputs.RIGHT, ButtonMode.HOLD, false);
		BufferMove(pick, false);
		return true;
	}

	/// <summary>Netsu (Oct 28): the move's input has a button in it (normals, specials, supers, throws, Burst).</summary>
	private static bool NetsuUsesButton(MotionInputs inputs)
	{
		if (inputs == null || inputs.ValidInputs == null)
		{
			return false;
		}
		for (int a = 0; a < inputs.ValidInputs.Length; a++)
		{
			var steps = inputs.ValidInputs[a].Inputs;
			for (int s = 0; steps != null && s < steps.Length; s++)
			{
				if ((int)steps[s].Buttons != 0)
				{
					return true;
				}
			}
		}
		return false;
	}

	// ---------------------------------------------------------------------------------------------
	// Netsu (Oct 24 2026, night): input leniency (see also InputManager).
	public const int NetsuKaraFrames = 2;           // a two-button press may replace a normal this many frames into it
	public const int NetsuStunBufferFrames = 4;     // moves pressed in the last 4 frames of block / hit stun are kept
	public const int NetsuStunBufferPriority = 6;   // normals and up (not walks, dashes, jumps)

	private bool _netsuMultiPressed;   // this frame's neutral check found a two-button move (not saved: set every frame)

	private static readonly System.Collections.Generic.Dictionary<FighterStance, int[]> _netsuOrders = new System.Collections.Generic.Dictionary<FighterStance, int[]>();

	/// <summary>Netsu: the order of the neutral move check: from the end of the list down, except moves with a
	/// NetsuCheckOrder (checked as if they were at that place). Worked out once per stance (data only).</summary>
	private int[] NetsuMoveOrder()
	{
		FighterStance stance = GetCurrentStance();
		lock (_netsuOrders)
		{
			if (_netsuOrders.TryGetValue(stance, out int[] cached) && cached.Length == stance.Moves.Length)
			{
				return cached;
			}
			int n = stance.Moves.Length;
			int[] order = new int[n];
			float[] key = new float[n];
			for (int i = 0; i < n; i++)
			{
				order[i] = i;
				float k = stance.Moves[i] != null ? stance.Moves[i].NetsuCheckOrder : -1f;
				key[i] = k >= 0f ? k : i;
			}
			System.Array.Sort(order, (a, b) => key[a] != key[b] ? key[b].CompareTo(key[a]) : b.CompareTo(a));
			_netsuOrders[stance] = order;
			return order;
		}
	}

	/// <summary>Netsu: the first frames of a move that just came out (and isn't frozen by hitstop).</summary>
	private bool NetsuKaraWindow()
	{
		// (Oct 26, TamaDeez: not out of an EX move or a super: their first frames come right after the flash freeze,
		// and a B+C press there turned the EX into a super before it had even come out)
		return CurrentMove >= 0 && _owner.StateManager.CurrentStateType() == StateType.COMBAT
			&& GetCurrentMove().SuperGaugeRequired == 0
			&& _owner.StateManager.CurrentStateFrame <= NetsuKaraFrames && !_owner.OnHitstop()
			&& _owner.StateManager.CurrentState == GetCurrentMove().MoveState;
	}

	/// <summary>Netsu: the end of block / hit stun, or lying knocked down, when a press is buffered for the first
	/// frame the fighter can act (a reversal on wake-up, a normal right out of blockstun).</summary>
	private bool NetsuStunBuffer()
	{
		StateType type = _owner.StateManager.CurrentStateType();
		if ((type != StateType.BLOCKING && type != StateType.HIT_REACTION) || _owner.IsGrabbed() || _owner.IsKO())
		{
			return false;
		}
		if (_owner.Hitstun != null && _owner.Hitstun.IsRunning())
		{
			return _owner.Hitstun.TimeLeft <= NetsuStunBufferFrames;
		}
		return type == StateType.HIT_REACTION && _owner.HitstunType >= HitstunType.KNOCKDOWN && _owner.Body != null && _owner.Body.IsOnGround;
	}

	/// <summary>Netsu: is this an input with two or more buttons pressed together (B+C, 236 + B+C, A+B+C...)?</summary>
	public static bool NetsuMultiButton(MotionInputs inputs)
	{
		if (inputs == null || inputs.ValidInputs == null)
		{
			return false;
		}
		foreach (InputOption opt in inputs.ValidInputs)
		{
			if (opt == null || opt.Inputs == null || opt.Inputs.Length == 0)
			{
				continue;
			}
			InputSequence last = opt.Inputs[opt.Inputs.Length - 1];
			if (last != null && last.ButtonMode == ButtonMode.PRESS && InputManager.NetsuButtonCount(last.Buttons) >= 2)
			{
				return true;
			}
		}
		return false;
	}

	private void BufferMove(int moveIndex, bool moveCancel)
	{
		BufferedMove = moveIndex;
		CancelBuffer = moveCancel;
		uint netsuWait = 0u;
		if (NetsuIsBurst(moveIndex) && _owner.Hitstop != null && _owner.Hitstop.IsRunning())
		{
			netsuWait = _owner.Hitstop.TimeLeft;   // Nov 3: a Burst pressed in hitstop waits for it to end (stays buffered)
		}
		MoveBuffer.Start(10u + netsuWait);
	}

	public const int NetsuAirDashLandLag = 12;   // Oct 28: Leticia's air dashes (MoveSettings.NetsuAirLandLag)

	public void ExecuteMove(int moveIndex)
	{
		if (NetsuAutoFace(GetMove(moveIndex)) && _owner.Body != null)
		{
			_owner.Body.FlipSide();   // Nov 3: auto-correct: specials / EX / supers start facing the opponent
		}
		// Netsu (Oct 28): an air tech starts its lockout / invincibility; anything else she does ends the invincibility
		int netsuMs = GetMove(moveIndex).MoveState;
		FighterState[] netsuStates = _owner.Data?.States;
		FighterState netsuNext = (netsuStates != null && netsuMs >= 0 && netsuMs < netsuStates.Length) ? netsuStates[netsuMs] : null;
		if (netsuNext != null && netsuNext.StateName != null && netsuNext.StateName.StartsWith("Recovery_Air"))
		{
			_owner.NetsuAirTechBegin();
		}
		else if (_owner.NetsuAirTechInvul)
		{
			_owner.NetsuAirTechInvul = false;
		}
		if (NetsuIsBurst(moveIndex))
		{
			_owner.NetsuBurstBegin();   // Nov 3: fully invincible, a moment's pause, the explosion
		}
		else
		{
			_owner.NetsuBurstInvul = false;   // anything else she does ends it
		}
		int netsuCost = GetMove(moveIndex).SuperGaugeRequired;
		if (netsuCost > 0)
		{
			_owner.Parameters.NetsuSpendMeter(netsuCost, GetMove(moveIndex).NetsuMeterCooldown);   // Oct 29: starts the meter cooldown
		}
		_owner.NetsuMeterSpendTag = netsuCost > 0;   // Oct 29: its hits (and what it spawns) give her no meter
		_owner.Parameters.Will.CurrentValue -= GetMove(moveIndex).WillGaugeRequired;
		bool netsuOverdrive = GetMove(moveIndex).MoveName == NetsuOverdriveName;
		_owner.NetsuSuperActive = GetMove(moveIndex).SuperGaugeRequired >= NetsuSuperCost;   // Netsu: super damage bonus
		_owner.NetsuSuperConnected = false;   // Netsu (Oct 26 c14): a new move hasn't hit yet
		if (_owner.StateManager.CurrentStateType() != StateType.HIT_REACTION && !NetsuIsNormal(moveIndex) && _owner.OnKnockback())
		{
			// Netsu (Oct 27 c33): the corner pushback (HitPushback) is a knockback timer on the attacker, and MoveX / MoveY
			// actions do nothing while it runs: a special cancelled out of a hit or block in the corner never rose / jumped
			// (Noah's 214B, Flan's 214 series). A special / super starts from a clean slate, like supers already do for the
			// velocity.
			_owner.StopKnockback(false);
		}
		if (NetsuIsNormal(moveIndex) && GetMove(moveIndex).UseOnAir && !GetMove(moveIndex).UseOnGround)
		{
			int netsuS = NetsuStrength(moveIndex);
			int lag = 2 + (netsuS < 0 ? 2 : netsuS);   // Netsu: landing recovery A 2, B 3, C (or a held button) 4
			// Oct 28: an air dash's 12 frames of landing lag are cut down by whiffing an air normal
			_owner.NetsuAirAttackLag = (_owner.NetsuAirAttackLag == NetsuAirDashLandLag) ? lag : Mathf.Max(_owner.NetsuAirAttackLag, lag);
		}
		if (GetMove(moveIndex).NetsuAirLandLag > 0 && _owner.Body != null && !_owner.Body.IsOnGround)
		{
			_owner.NetsuAirAttackLag = Mathf.Max(_owner.NetsuAirAttackLag, GetMove(moveIndex).NetsuAirLandLag);
		}
		if (NetsuIsNormal(moveIndex) && moveIndex < 64)
		{
			_owner.NetsuChainUsed |= 1UL << moveIndex;   // Netsu (Oct 26 late): used in this chain
		}
		if (GetMove(moveIndex).NetsuOncePerJump)
		{
			_owner.NetsuAirMoveUsed = true;   // Netsu (Oct 26 late): used up until she lands
		}
		if (netsuOverdrive)
		{
			_owner.Parameters.StartOverdrive();   // Netsu: A+B+C offensive burst
		}
		if (GetMove(moveIndex).SuperFlash > 0 && !_owner.SuperFlashing)
		{
			_owner.NetsuFlashCost = GetMove(moveIndex).SuperGaugeRequired;   // Netsu: which look the flash gets
			_owner.GetOpponent(0).StartSuperFlash((uint)GetMove(moveIndex).SuperFlash);
			if (_owner.GetOpponent(0).NetsuAssist != null)
			{
				_owner.GetOpponent(0).NetsuAssist.Freeze((uint)GetMove(moveIndex).SuperFlash);   // Netsu: their assist stops too
			}
			if (NetsuIsExOrSuper(GetMove(moveIndex)) && !GetMove(moveIndex).NetsuFlashOnHit && GameManager.Instance != null)
			{
				// Netsu: EX moves and supers stop the whole fight for a moment first (GameManager.NetsuPause)
				GameManager.Instance.NetsuStartPause((int)_owner.playerID, GetMove(moveIndex).SuperGaugeRequired, GetMove(moveIndex).NetsuPauseFrames);
			}
		}
		if (NetsuIsExOrSuper(GetMove(moveIndex)) && !GetMove(moveIndex).NetsuFlashOnHit)
		{
			NetsuCutIn(GetMove(moveIndex));   // Netsu: EX moves and supers flash the fighter's picture
		}
		if (netsuOverdrive && GameManager.Instance != null)
		{
			// Netsu (Oct 26 evening): Overdrive activation stops the fight while she strikes her win pose and glows
			// (SakugaActor.NetsuPauseAnimation / NetsuSuperFlashLook); nobody can input during it
			GameManager.Instance.NetsuStartPause((int)_owner.playerID, 0, GameManager.Instance.NetsuOverdrivePauseFrames);
		}
		if (GetMove(moveIndex).SuperGaugeRequired >= NetsuSuperCost && _owner.Body != null)
		{
			// Netsu: a super stops the fighter where it starts (no dash, jump arc or knockback carried into it);
			// the super's own states then move her
			if (_owner.Knockback != null)
			{
				_owner.Knockback.Stop();
			}
			_owner.Body.SetVelocity(Vector2I.Zero);
		}
		if (GetMove(moveIndex).MoveState >= 0)
		{
			_owner.StateManager.PlayState(GetMove(moveIndex).MoveState, reset: true);
		}
		_owner.Parameters.ChangeVariablesBehavior(CustomVariableBehaviorTarget.ON_MOVE_ENTER);
		_owner.Parameters.SetVariables(GetMove(moveIndex).VariablesChange);
		CurrentMove = moveIndex;
		ExecutedMoves++;
		BufferedMove = -1;
		CancelBuffer = false;
		MoveBuffer.Stop();
		NetsuLog.Debug("You executed " + GetCurrentMove().MoveName + "!");
	}

	/// <summary>Netsu: the super flash started from a state (NetsuSuperFlashAction): the opponent (and its
	/// assist) freeze for `frames`, and the cut-in of the move being done shows. Used by counter supers, whose
	/// move has NetsuFlashOnHit so nothing shows while the stance waits.</summary>
	public void NetsuDelayedFlash(int frames, bool cutIn)
	{
		SakugaActor opponent = _owner.GetOpponent(0);
		if (frames > 0 && opponent != null && !_owner.SuperFlashing)
		{
			// the move may already be over (a counter super's hit state ends its move): count it as a super then
			_owner.NetsuFlashCost = CurrentMove >= 0 ? GetCurrentMove().SuperGaugeRequired : NetsuSuperCost;
			opponent.StartSuperFlash((uint)frames);
			if (opponent.NetsuAssist != null)
			{
				opponent.NetsuAssist.Freeze((uint)frames);
			}
			if (cutIn && _owner.NetsuFlashCost >= NetsuExCost && GameManager.Instance != null)
			{
				GameManager.Instance.NetsuStartPause((int)_owner.playerID, _owner.NetsuFlashCost, CurrentMove >= 0 ? GetCurrentMove().NetsuPauseFrames : -1);   // the pause too
			}
		}
		if (cutIn && CurrentMove >= 0)
		{
			NetsuCutIn(GetCurrentMove());
		}
	}

	/// <summary>Netsu: asks the battle HUD for an EX (1 bar) or super (3 bars) cut-in.
	/// MatchSetup (GDScript autoload) forwards it to game/ui/battle_hud/netsu_cut_in.gd.
	/// Presentation only: nothing in the match state depends on it.</summary>
	private void NetsuCutIn(MoveSettings move)
	{
		if (Engine.GetMainLoop() is not SceneTree tree)
		{
			return;
		}
		Node setup = tree.Root.GetNodeOrNull("MatchSetup");
		if (setup == null || !setup.HasMethod("netsu_cut_in"))
		{
			return;
		}
		string fighter = _owner.Data?.Profile?.ShortName ?? "";
		bool fromLeft = _owner.Body != null ? _owner.Body.IsLeftSide : _owner.playerID == 0;
		setup.Call("netsu_cut_in", (int)_owner.playerID, fighter, move.MoveName, move.SuperGaugeRequired >= NetsuSuperCost, fromLeft);
	}

	private void CheckMoveCancel()
	{
		if (!CanRun)
		{
			return;
		}
		if (NetsuThrowCancel())
		{
			return;
		}
		if (CurrentMove < 0)
		{
			return;
		}
		MoveCancelSettings[] canCancelTo = GetCurrentMove().CanCancelTo;
		bool found = false;
		for (int c = 0; canCancelTo != null && c < canCancelTo.Length; c++)
		{
			MoveCancelSettings cancel = canCancelTo[c];
			// Netsu: this frame's press was two buttons together for a two-button move (B+C throw, 236 + B+C):
			// it doesn't also chain into a one-button move (5A > B+C stays a throw, buffered for after 5A)
			if (_netsuMultiPressed && !NetsuMultiButton(GetMove(cancel.MoveIndex).Inputs))
			{
				continue;
			}
			if (NetsuChainBlocked(cancel.MoveIndex))
			{
				continue;   // Netsu (Oct 26 late): that normal was already used in this chain
			}
			if (CheckCancelConditions(cancel) && CheckMoveConditions(cancel.MoveIndex) && NetsuInputDone(cancel.MoveIndex))
			{
				BufferMove(cancel.MoveIndex, moveCancel: true);
				found = true;
				break;
			}
		}
		if (!found && !NetsuReverseBeat() && !NetsuJumpCancel() && !NetsuOverdriveCancel() && !NetsuStarCancel() && !NetsuExToSuper())
		{
			NetsuSpecialToEx();
		}
	}

	/// <summary>Netsu (Oct 27): REVERSE BEAT. A normal that hit or was blocked can chain into any other normal, not only a
	/// stronger one (5C > 5B > 5A, 2C > 2A...), as long as that normal hasn't been used yet in this chain
	/// (NetsuChainUsed: no normal twice, same rule as before). The timing window is the move's own: it opens when one of
	/// the normals in the move's CanCancelTo list could be cancelled into right now. The move's own list is checked first
	/// (CheckMoveCancel), so its normal chains, specials and supers keep winning over this.
	/// Returns true when it buffered one.</summary>
	private bool NetsuReverseBeat()
	{
		if (CurrentMove < 0 || !NetsuIsNormal(CurrentMove))
		{
			return false;
		}
		if ((_owner.CancelConditions & (CancelCondition.HIT_CANCEL | CancelCondition.BLOCK_CANCEL)) == 0)
		{
			return false;
		}
		MoveCancelSettings[] own = GetCurrentMove().CanCancelTo;
		bool windowOpen = false;
		for (int c = 0; own != null && c < own.Length; c++)
		{
			if (NetsuIsNormal(own[c].MoveIndex) && (own[c].Conditions & (CancelCondition.HIT_CANCEL | CancelCondition.BLOCK_CANCEL)) != 0 && CheckCancelConditions(own[c]))
			{
				windowOpen = true;
				break;
			}
		}
		if (!windowOpen)
		{
			return false;
		}
		if (BufferedMove >= 0 && CancelBuffer)
		{
			return true;   // already waiting
		}
		int[] order = NetsuMoveOrder();
		for (int o = 0; o < order.Length; o++)
		{
			int i = order[o];
			MoveSettings move = GetMove(i);
			if (move == null || move.SkipCheck || i == CurrentMove || !NetsuIsNormal(i))
			{
				continue;
			}
			if (_netsuMultiPressed && !NetsuMultiButton(move.Inputs))
			{
				continue;
			}
			if (NetsuChainBlocked(i))
			{
				continue;   // already used in this chain (also: only 5A / 5B jump-cancel)
			}
			if (CheckMoveConditions(i) && NetsuInputDone(i))
			{
				BufferMove(i, moveCancel: true);
				return true;
			}
		}
		return false;
	}

	// ---------------------------------------------------------------------------------------------
	// Netsu (Oct 26 late, TamaDeez): one button, two jobs. The Burst input (A+C) is a Burst only while being hit
	// (hitstun, launched, knocked down). Everywhere else (neutral, blocking, during her own attacks on hit or block)
	// the same press, or the Overdrive's own A+B+C, starts Overdrive. Before this Burst also worked in neutral, and
	// since it is checked before Overdrive and A+C is part of A+B+C, Overdrive never came out.

	/// <summary>A Burst: costs the Burst gauge (Will) and isn't the Overdrive.</summary>
	public bool NetsuIsBurst(int index)
	{
		MoveSettings m = GetMove(index);
		return m != null && m.WillGaugeRequired > 0 && m.MoveName != NetsuOverdriveName;
	}

	public bool NetsuIsOverdrive(int index)
	{
		MoveSettings m = GetMove(index);
		return m != null && m.MoveName == NetsuOverdriveName;
	}

	/// <summary>Burst: only in a hit reaction. Overdrive: never in a hit reaction or while grabbed.</summary>
	private bool NetsuBurstOrOverdriveState(int index)
	{
		StateType t = _owner.StateManager.CurrentStateType();
		if (NetsuIsBurst(index))
		{
			return t == StateType.HIT_REACTION || t == StateType.BLOCKING;   // Nov 3 (BlazBlue): also out of blockstun
		}
		if (NetsuIsOverdrive(index))
		{
			return false;   // Oct 28 (TamaDeez): the Overdrive move (A+B+C) is removed; Overdrive is now low health
			// Oct 26 c16 (TamaDeez): from neutral, normals, specials / EX moves and block only: never out of a super
			// (nor its follow-up states: NetsuSuperActive stays on until she is out of her attack)
			bool fromSuper = _owner.NetsuSuperActive || (CurrentMove >= 0 && GetCurrentMove().SuperGaugeRequired >= NetsuSuperCost);
			return t != StateType.HIT_REACTION && t != StateType.LOCKED && !_owner.IsGrabbed() && !_owner.IsKO() && !fromSuper;
		}
		return true;
	}

	/// <summary>CheckAllowedStateType, except Overdrive starts from neutral (null / movement states) and from
	/// blocking whatever its data says (from her own attacks it comes through NetsuOverdriveCancel).</summary>
	private bool NetsuAllowedStateType(int index)
	{
		if (NetsuIsBurst(index) && _owner.StateManager.CurrentStateType() == StateType.BLOCKING)
		{
			return true;   // Nov 3: a Burst also works while blocking (its move data only accepts hit reactions)
		}
		if (NetsuIsOverdrive(index))
		{
			StateType t = _owner.StateManager.CurrentStateType();
			return t == StateType.NULL || t == StateType.MOVEMENT || t == StateType.BLOCKING;
		}
		return CheckAllowedStateType(index);
	}

	/// <summary>The move's input is done. Overdrive also takes the Burst's input (the same press does both jobs).</summary>
	// ---------------------------------------------------------------------------------------------
	// Netsu (Nov 3 2026, TamaDeez): AUTO-CORRECT, the way Street Fighter / Guilty Gear / BlazBlue do it. Specials, EX
	// moves, supers, Burst and Pushblock read their motion from the side the opponent is really on (not the way the
	// fighter happens to be facing) and turn her to face the opponent as they start, so a special that crossed through
	// the opponent cancels into an EX / super aimed at where they are now. Throws keep her facing (4 + B + C is a back
	// throw). When any attack ends (StateManager.PlayState), she turns to face the opponent too (NetsuFaceOpponent).

	/// <summary>A move that reads its input from the opponent's side and turns her round as it starts.</summary>
	public bool NetsuAutoFace(MoveSettings m)
	{
		if (m == null || _owner == null || _owner.GetMaster() != null)
		{
			return false;   // fighters only (not assists, not projectiles)
		}
		if (m.MoveName != null && m.MoveName.Contains("Throw"))
		{
			return false;
		}
		return m.Priority >= 7 || m.SuperGaugeRequired > 0 || m.WillGaugeRequired > 0;
	}

	/// <summary>The side (1 / -1) to read a move's motion from.</summary>
	public int NetsuMoveInputSide(MoveSettings m)
	{
		if (m != null && m.SideCheck == InputSideCheck.CHARACTER_RELATIVE && NetsuAutoFace(m) && _owner.Body != null)
		{
			return _owner.Body.IsLeftSide ? 1 : -1;
		}
		return _owner.InputSide(m != null ? m.SideCheck : InputSideCheck.CHARACTER_RELATIVE);
	}

	public bool NetsuInputDone(int index)
	{
		MoveSettings m = GetMove(index);
		if (m == null)
		{
			return false;
		}
		if (_owner.Inputs.CheckMotionInputs(m.Inputs, NetsuMoveInputSide(m)))
		{
			return true;
		}
		if (!NetsuIsOverdrive(index))
		{
			return false;
		}
		FighterStance stance = GetCurrentStance();
		for (int i = 0; stance != null && stance.Moves != null && i < stance.Moves.Length; i++)
		{
			if (NetsuIsBurst(i) && _owner.Inputs.CheckMotionInputs(GetMove(i).Inputs, _owner.InputSide(GetMove(i).SideCheck)))
			{
				return true;
			}
		}
		return false;
	}

	/// <summary>Overdrive out of any of her moves that has hit or been blocked (not out of Overdrive or a Burst).</summary>
	private bool NetsuOverdriveCancel()
	{
		return false;   // Oct 28: the Overdrive move is removed
#pragma warning disable CS0162
		if (CurrentMove < 0 || NetsuIsOverdrive(CurrentMove) || NetsuIsBurst(CurrentMove))
		{
			return false;
		}
		if ((_owner.CancelConditions & (CancelCondition.HIT_CANCEL | CancelCondition.BLOCK_CANCEL)) == 0)
		{
			return false;
		}
		if (BufferedMove >= 0 && CancelBuffer)
		{
			return true;
		}
		FighterStance stance = GetCurrentStance();
		for (int i = 0; stance != null && stance.Moves != null && i < stance.Moves.Length; i++)
		{
			if (NetsuIsOverdrive(i) && CheckMoveConditions(i, ignoreStateType: true) && NetsuInputDone(i))
			{
				BufferMove(i, moveCancel: true);
				return true;
			}
		}
		return false;
#pragma warning restore CS0162
	}

	// ---------------------------------------------------------------------------------------------
	// Netsu (Oct 29 2026, TamaDeez): star cancel (Flan). With a star stack, a special can be cancelled into a DIFFERENT
	// special (or EX) at any point of it, hit, block or whiff; that spends one stack. Supers, Burst, throws and the
	// stack moves themselves aren't part of it. Only fighters with DataContainer.NetsuStarStackMax > 0 have stacks.

	public const string NetsuStarChargeName = "Star Charge";

	private bool NetsuIsStarSpecial(MoveSettings m)
	{
		return m != null && m.Priority >= 7 && m.SuperGaugeRequired < NetsuSuperCost && m.WillGaugeRequired == 0
			&& m.MoveName != null && m.MoveName != NetsuPushblockName && !m.MoveName.Contains("Breakthrough")
			&& !m.MoveName.Contains("Throw") && !m.MoveName.StartsWith(NetsuStarChargeName);
	}

	private bool NetsuStarCancel()
	{
		if (_owner == null || _owner.NetsuStarStacks <= 0 || CurrentMove < 0 || _owner.StateManager == null)
		{
			return false;
		}
		MoveSettings current = GetCurrentMove();
		if (!NetsuIsStarSpecial(current) || _owner.StateManager.CurrentStateType() != StateType.COMBAT || _owner.StateManager.CurrentStateFrame < 2)
		{
			return false;
		}
		if (BufferedMove >= 0 && CancelBuffer)
		{
			return true;
		}
		int[] order = NetsuMoveOrder();
		for (int o = 0; o < order.Length; o++)
		{
			int i = order[o];
			MoveSettings move = GetMove(i);
			if (move == null || move.SkipCheck || i == CurrentMove || move.MoveState == current.MoveState || !NetsuIsStarSpecial(move))
			{
				continue;
			}
			if (_netsuMultiPressed && !NetsuMultiButton(move.Inputs))
			{
				continue;
			}
			if (CheckMoveConditions(i, ignoreStateType: true) && NetsuInputDone(i))
			{
				BufferMove(i, moveCancel: true);
				_owner.NetsuStarStacks--;
				return true;
			}
		}
		return false;
	}

	/// <summary>Netsu (Nov 2 2026, TamaDeez): EX Craft → S-Craft cancel, for every fighter. An EX move that has hit or been
	/// blocked can be cancelled into any S-Craft (a super, 300%) whose input is done, until the EX move ends. The EX's
	/// 100% is already spent, so it needs 300% left: with the normal 300% cap that means Overdrive (400%). The move's own
	/// CanCancelTo list is checked first. Returns true when it buffered one (or one is already waiting).</summary>
	private bool NetsuExToSuper()
	{
		MoveSettings current = GetCurrentMove();
		if (!NetsuIsExMove(current) || current.WillGaugeRequired > 0)
		{
			return false;
		}
		if ((_owner.CancelConditions & (CancelCondition.HIT_CANCEL | CancelCondition.BLOCK_CANCEL)) == 0)
		{
			return false;
		}
		if (BufferedMove >= 0 && CancelBuffer)
		{
			return true;
		}
		int[] order = NetsuMoveOrder();
		for (int o = 0; o < order.Length; o++)
		{
			int i = order[o];
			MoveSettings move = GetMove(i);
			if (move == null || move.SkipCheck || i == CurrentMove || move.SuperGaugeRequired < NetsuSuperCost || move.WillGaugeRequired > 0)
			{
				continue;
			}
			if (_netsuMultiPressed && !NetsuMultiButton(move.Inputs))
			{
				continue;
			}
			if (CheckMoveConditions(i, ignoreStateType: true) && NetsuInputDone(i))
			{
				BufferMove(i, moveCancel: true);
				return true;
			}
		}
		return false;
	}

	/// <summary>Netsu (Oct 26, TamaDeez): Special → EX cancel, for every fighter. A special move (no meter,
	/// Priority 7 or 8) that has hit or been blocked can be cancelled into any EX move (costs 1 bar since Oct 28, under a
	/// super's 3) whose input is done, from the hit until the special ends. Works on top of the moves' own CanCancelTo lists
	/// (those are checked first, so a special's own follow-ups and super cancels win). Needs the gauge, like any EX.</summary>
	private void NetsuSpecialToEx()
	{
		MoveSettings current = GetCurrentMove();
		if (current == null || current.SuperGaugeRequired > 0 || current.Priority < 7 || current.Priority > 8)
		{
			return;
		}
		if ((_owner.CancelConditions & (CancelCondition.HIT_CANCEL | CancelCondition.BLOCK_CANCEL)) == 0)
		{
			return;
		}
		if (BufferedMove >= 0 && CancelBuffer)
		{
			return;   // a cancel is already waiting (from the move's own list)
		}
		int[] order = NetsuMoveOrder();
		for (int o = 0; o < order.Length; o++)
		{
			int i = order[o];
			MoveSettings move = GetMove(i);
			if (move == null || move.SkipCheck || i == CurrentMove || !NetsuIsExMove(move) || move.WillGaugeRequired > 0)
			{
				continue;
			}
			if (_netsuMultiPressed && !NetsuMultiButton(move.Inputs))
			{
				continue;
			}
			if (CheckMoveConditions(i) && _owner.Inputs.CheckMotionInputs(move.Inputs, NetsuMoveInputSide(move)))
			{
				BufferMove(i, moveCancel: true);
				return;
			}
		}
	}


	// ---------------------------------------------------------------------------------------------
	// Netsu (Oct 27 c35): the AB macro. A+B pressed on the same frame (the AB button) does the dash: on the ground
	// a dash forward, or a back dash with back held; in the air an air dash forward / back. Not with C (that is
	// A+B+C, Overdrive). Two buttons a frame apart still chain normally (5A > 5B).

	/// <summary>Buffers the dash for this frame's A+B press. Returns true when it did (the normal check is skipped).</summary>
	private bool NetsuAbDash()
	{
		InputManager inp = _owner.Inputs;
		int h = inp.CurrentHistory;
		if (!inp.WasPressed(h, PlayerInputs.FACE_A) || !inp.WasPressed(h, PlayerInputs.FACE_B)
			|| inp.IsBeingPressed(h, PlayerInputs.FACE_C) || inp.IsBeingPressed(h, PlayerInputs.FACE_D))
		{
			return false;
		}
		bool ground = _owner.Body != null && _owner.Body.IsOnGround;
		PlayerInputs backKey = _owner.InputSide() > 0 ? PlayerInputs.LEFT : PlayerInputs.RIGHT;
		bool back = inp.IsBeingPressed(h, backKey);
		string[] names = ground
			? (back ? new[] { "Dash Backwards" } : new[] { "Dash Forward" })
			: (back ? new[] { "Backwards Air Dash" } : new[] { "Forward Air Dash" });
		FighterStance stance = GetCurrentStance();
		for (int i = 0; stance != null && stance.Moves != null && i < stance.Moves.Length; i++)
		{
			MoveSettings m = GetMove(i);
			if (m == null || System.Array.IndexOf(names, m.MoveName) < 0)
			{
				continue;
			}
			if (CheckMoveConditions(i))
			{
				BufferMove(i, false);
				_netsuMultiPressed = true;
				return true;
			}
		}
		return false;
	}

	// Netsu (Oct 28): the Roman Cancel (B+C during an attack, Oct 27 c35) was removed. B+C is the throw again, nothing
	// else.

	/// <summary>The Overdrive move is recognised by this name (its MoveName).</summary>
	public const string NetsuOverdriveName = "Overdrive";

	/// <summary>Netsu (Oct 26 evening, TamaDeez): once a throw has done its damage (its "Throw Forward" / "Throw Back" state has
	/// hit; not the grab itself, not the throw break), it can be cancelled into an EX move, a super or Overdrive whose input is done.
	/// Returns true when it buffered one.</summary>
	private bool NetsuThrowCancel()
	{
		string name = _owner.StateManager.GetCurrentState()?.StateName;
		if (name == null || !name.StartsWith("Throw ") || name.Contains("Break")
			|| (_owner.CancelConditions & CancelCondition.HIT_CANCEL) == 0)
		{
			return false;
		}
		if (BufferedMove >= 0 && CancelBuffer)
		{
			return true;   // already waiting
		}
		int[] order = NetsuMoveOrder();
		for (int o = 0; o < order.Length; o++)
		{
			int i = order[o];
			MoveSettings move = GetMove(i);
			if (move == null)
			{
				continue;
			}
			bool overdrive = move.MoveName == NetsuOverdriveName;
			if (!overdrive && (move.SkipCheck || !NetsuIsExOrSuper(move)))
			{
				continue;
			}
			if (_netsuMultiPressed && !NetsuMultiButton(move.Inputs))
			{
				continue;
			}
			if (CheckMoveConditions(i, ignoreStateType: true) && NetsuInputDone(i))
			{
				BufferMove(i, moveCancel: true);
				return true;
			}
		}
		return false;
	}

	/// <summary>Netsu (Oct 26 late, TamaDeez): how strong a move's button is: 0 = A (light), 1 = B (medium), 2 = C (hard),
	/// -1 = a two-button / hold / no-button move. A move that takes "B or C" counts as B.</summary>
	public int NetsuStrength(int index)
	{
		MoveSettings m = GetMove(index);
		if (m == null || m.Inputs == null || m.Inputs.ValidInputs == null)
		{
			return -1;
		}
		int best = -1;
		foreach (InputOption opt in m.Inputs.ValidInputs)
		{
			if (opt == null || opt.Inputs == null || opt.Inputs.Length == 0)
			{
				continue;
			}
			InputSequence last = opt.Inputs[opt.Inputs.Length - 1];
			if (last == null || last.ButtonMode != ButtonMode.PRESS || InputManager.NetsuButtonCount(last.Buttons) != 1)
			{
				continue;
			}
			int b = (int)last.Buttons;
			int s = b == 1 ? 0 : (b == 2 ? 1 : (b == 4 ? 2 : -1));
			if (s >= 0 && (best < 0 || s < best))
			{
				best = s;
			}
		}
		return best;
	}

	/// <summary>Netsu (Oct 26 late, TamaDeez): the frame advantage the current move should have on block (negative = the
	/// attacker is behind): ground normals A -4, B -5, C -8; specials A -4, B / C -6. Dragon punches (623 inputs), EX
	/// moves, supers, air moves and projectiles keep their own numbers.</summary>
	public bool NetsuBlockAdvantage(out int advantage)
	{
		advantage = 0;
		if (CurrentMove < 0 || _owner.GetMaster() != null)
		{
			return false;
		}
		MoveSettings m = GetCurrentMove();
		if (m == null || m.SuperGaugeRequired > 0 || m.WillGaugeRequired > 0 || (m.UseOnAir && !m.UseOnGround))
		{
			return false;
		}
		int s = NetsuStrength(CurrentMove);
		if (s < 0)
		{
			return false;
		}
		if (m.Priority == 6)
		{
			advantage = s == 0 ? -4 : (s == 1 ? -5 : -8);
			return true;
		}
		if (m.Priority == 7 || m.Priority == 8)
		{
			if (m.Inputs.ResourcePath != null && m.Inputs.ResourcePath.Contains("623"))
			{
				return false;
			}
			advantage = s == 0 ? -4 : -6;
			return true;
		}
		return false;
	}

	/// <summary>Netsu (Oct 26 c6, TamaDeez): a normal's cancel list may name the jumps (Cecilia's 5C did). The rule is the
	/// same for everyone: only 5A / 5B (hit or block) and 2B (hit) jump-cancel; every other normal's jump cancel is
	/// ignored, whatever its cancel list says.</summary>
	private bool NetsuJumpCancelBlocked(int index)
	{
		if (CurrentMove < 0 || index < 0 || !NetsuIsNormal(CurrentMove))
		{
			return false;
		}
		MoveSettings j = GetMove(index);
		if (j == null || !j.UseOnGround || j.UseOnAir || j.MoveName == null || !j.MoveName.Contains("Jump"))
		{
			return false;
		}
		string name = GetCurrentMove().MoveName;
		if (name == "5A" || name == "5B")
		{
			return (_owner.CancelConditions & (CancelCondition.HIT_CANCEL | CancelCondition.BLOCK_CANCEL)) == 0;
		}
		if (name == "2B" || name == "6C" || name == "5C" || GetCurrentMove().NetsuJumpCancelOnHit)   // Oct 29 (TamaDeez): 6C jump-cancels on hit only, not on block; Nov 3: 5C too
		{
			return (_owner.CancelConditions & CancelCondition.HIT_CANCEL) == 0;
		}
		return true;
	}

	/// <summary>Netsu (Oct 26 late, TamaDeez): 5A and 5B can be jump-cancelled on hit or block, 2B, 6C (Oct 29) and 5C (Nov 3) on hit only.</summary>
	private bool NetsuJumpCancel()
	{
		if (CurrentMove < 0)
		{
			return false;
		}
		// Nov 3 (TamaDeez): a move flagged NetsuJumpCancelOnHit that is in the air on hit (Noah's 214B~X Abyss Riser)
		// cancels into an air jump instead (the air jumps' own limit still applies)
		bool netsuAir = !_owner.Body.IsOnGround;
		if (netsuAir && !GetCurrentMove().NetsuJumpCancelOnHit)
		{
			return false;
		}
		string name = GetCurrentMove().MoveName;
		CancelCondition need = name == "5A" || name == "5B" ? (CancelCondition.HIT_CANCEL | CancelCondition.BLOCK_CANCEL)
			: (name == "2B" || name == "6C" || name == "5C" || GetCurrentMove().NetsuJumpCancelOnHit ? CancelCondition.HIT_CANCEL : 0);   // Oct 29: 6C on hit only; Nov 3: every 5C on hit
		if (need == 0 || (_owner.CancelConditions & need) == 0)
		{
			return false;
		}
		FighterStance stance = GetCurrentStance();
		// (Oct 26 c16: from the end of the list, like the neutral move check, so a 2~8 super jump wins over the jump)
		for (int i = (stance != null && stance.Moves != null ? stance.Moves.Length : 0) - 1; i >= 0; i--)
		{
			MoveSettings j = stance.Moves[i];
			if (j == null || j.MoveName == null || j.MoveName.Contains("Dash")
				|| (!netsuAir && (!j.UseOnGround || j.UseOnAir || !j.MoveName.Contains("Jump")))
				|| (netsuAir && (!j.UseOnAir || j.UseOnGround || !j.MoveName.Contains("Air Jump"))))
			{
				continue;
			}
			if (CheckMoveConditions(i, true) && NetsuInputDone(i))
			{
				BufferMove(i, moveCancel: true);
				return true;
			}
		}
		return false;
	}

	/// <summary>Netsu (Nov 3): one of the owner's spawned objects from pool m.NetsuNeedSpawnPool is active and in one of
	/// m.NetsuNeedSpawnStates.</summary>
	private bool NetsuSpawnInState(MoveSettings m)
	{
		if (_owner.Pool == null || m.NetsuNeedSpawnPool >= _owner.Pool.SpawnCount || m.NetsuNeedSpawnStates == null)
		{
			return false;
		}
		PoolReference reference = _owner.Pool.GetSpawnReference(m.NetsuNeedSpawnPool);
		if (reference.Objects == null)
		{
			return false;
		}
		foreach (SakugaActor spawn in reference.Objects)
		{
			if (spawn == null || !spawn.IsActive || spawn.StateManager == null)
			{
				continue;
			}
			foreach (int st in m.NetsuNeedSpawnStates)
			{
				if (spawn.StateManager.CurrentState == st)
				{
					return true;
				}
			}
		}
		return false;
	}

	/// <summary>Netsu: a normal attack (Priority 6, no meter).</summary>
	public bool NetsuIsNormal(int index)
	{
		MoveSettings m = GetMove(index);
		return m != null && m.Priority == 6 && m.SuperGaugeRequired == 0 && m.WillGaugeRequired == 0;
	}

	/// <summary>Netsu (Oct 26 late, TamaDeez): no normal twice in one chain (5C > 2C > 5C). Cancelling a light into
	/// itself (2A > 2A) is still fine; only going back to one used earlier is stopped.</summary>
	private bool NetsuChainBlocked(int index)
	{
		if (NetsuJumpCancelBlocked(index))
		{
			return true;   // Netsu (Oct 26 c6): only 5A / 5B (and 2B on hit) jump-cancel
		}
		if (index < 0 || index >= 64 || index == CurrentMove || !NetsuIsNormal(index))
		{
			return false;
		}
		return (_owner.NetsuChainUsed & (1UL << index)) != 0;
	}

	public const int NetsuExCost = 10000;      // an EX move costs this (1 bar; Oct 28: was 2 bars, 4000)
	public const int NetsuSuperCost = 30000;   // a super costs this (3 bars)
	public const int NetsuBarSize = 10000;     // one bar of Craft Gauge ("100%"); the gauge holds 4 bars (MaxSuperGauge 40000; Oct 29: units x5, 100 = 1%)

	/// <summary>Pushblock is recognised by this name (its MoveName). It costs 1 bar like an EX move but isn't one.</summary>
	public const string NetsuPushblockName = "Pushblock";

	/// <summary>Netsu (Oct 28): an EX move: costs at least NetsuExCost, less than a super, and isn't Pushblock (which
	/// also costs 1 bar since EX moves went down to 1 bar).</summary>
	public static bool NetsuIsExMove(MoveSettings m)
	{
		return m != null && m.SuperGaugeRequired >= NetsuExCost && m.SuperGaugeRequired < NetsuSuperCost && m.MoveName != NetsuPushblockName;
	}

	/// <summary>Netsu (Oct 28): an EX move or a super (Pushblock isn't either).</summary>
	public static bool NetsuIsExOrSuper(MoveSettings m)
	{
		return m != null && m.SuperGaugeRequired >= NetsuExCost && m.MoveName != NetsuPushblockName;
	}

	public void ProcessMoveBuffer()
	{
		if (BufferedMove < 0)
		{
			return;
		}
		if (_owner.NetsuLandLag > 0)
		{
			return;   // Netsu (Oct 26 late): landing recovery: the press stays buffered until it's over
		}
		if (!MoveBuffer.IsRunning() || !IsCorrectSurface(BufferedMove))
		{
			BufferedMove = -1;
			NetsuLog.Debug("Buffer Cleaned!");
		}
		else if ((CancelBuffer || _owner.StateManager.CurrentStateType() != StateType.COMBAT) && (CancelBuffer || NetsuAllowedStateType(BufferedMove)) && NetsuBurstOrOverdriveState(BufferedMove) && (GetBufferedMove().Unlockable || !_owner.ContainsFrameProperty(FrameProperties.LOCK_MOVE)) && ((GetBufferedMove().IgnoreHitstop && !NetsuIsBurst(BufferedMove)) || !_owner.Hitstop.IsRunning()) && (GetBufferedMove().IgnoreHitstun || NetsuIsOverdrive(BufferedMove) || !_owner.Hitstun.IsRunning()))
		{
			if (CurrentMove < 0 || CancelBuffer || (GetCurrentMove().CanBeOverrided && (GetCurrentMove().IgnoreSamePriority ? (GetBufferedMove().Priority > GetCurrentMove().Priority) : (GetBufferedMove().Priority >= GetCurrentMove().Priority))))
			{
				ExecuteMove(BufferedMove);
			}
			else
			{
				NetsuLog.Debug("Move " + GetBufferedMove().MoveName + " Buffered!");
			}
		}
	}

	public bool IsCorrectSurface(int index)
	{
		if ((!GetMove(index).UseOnGround || !_owner.Body.IsOnGround) && (!GetMove(index).UseOnAir || _owner.Body.IsOnGround || _owner.Body.FixedPosition.Y < GetMove(index).MinimumHeight))
		{
			if (GetMove(index).UseOnGround)
			{
				return GetMove(index).UseOnAir;
			}
			return false;
		}
		return true;
	}

	public bool CheckAllowedStateType(int moveIndex)
	{
		bool num = _owner.StateManager.GetCurrentState().Type != StateType.LOCKED;
		bool checkNullState = GetMove(moveIndex).AcceptNullStates && _owner.StateManager.GetCurrentState().Type == StateType.NULL;
		bool checkMovementState = GetMove(moveIndex).AcceptMovementStates && _owner.StateManager.GetCurrentState().Type == StateType.MOVEMENT;
		bool checkCombatState = GetMove(moveIndex).AcceptCombatStates && _owner.StateManager.GetCurrentState().Type == StateType.COMBAT;
		bool checkBlockingState = GetMove(moveIndex).AcceptBlockingStates && _owner.StateManager.GetCurrentState().Type == StateType.BLOCKING;
		bool checkHitReactionState = GetMove(moveIndex).AcceptHitReactionStates && _owner.StateManager.GetCurrentState().Type == StateType.HIT_REACTION && _owner.HitstunType < HitstunType.HARD_KNOCKDOWN;
		if (num)
		{
			return checkNullState | checkMovementState | checkCombatState | checkBlockingState | checkHitReactionState;
		}
		return false;
	}

	private void CheckMoveEndCondition()
	{
		if (CurrentMove < 0)
		{
			return;
		}
		switch (GetCurrentMove().MoveEnd)
		{
		case MoveEndCondition.STATE_END:
			if (_owner.StateManager.CurrentState != GetCurrentMove().MoveState)
			{
				EndMove();
			}
			break;
		case MoveEndCondition.RELEASE_BUTTON:
			if (_owner.Inputs.CheckInputEnd(GetCurrentMove().Inputs, _owner.InputSide(GetCurrentMove().SideCheck)))
			{
				EndMove();
			}
			break;
		case MoveEndCondition.STATE_TYPE_CHANGE:
			if (_owner.StateManager.CurrentStateType() != _owner.Data.States[GetCurrentMove().MoveState].Type)
			{
				EndMove();
			}
			break;
		case MoveEndCondition.ON_FALL:
			if (_owner.Body.IsFalling)
			{
				EndMove();
			}
			break;
		}
	}

	/// <summary>Netsu: forgets the current move WITHOUT playing its end state (a dash's stop, a walk's idle):
	/// the assist call pose (NetsuAssist) takes over from whatever the fighter was doing.</summary>
	public void NetsuDropMove()
	{
		if (CurrentMove >= 0)
		{
			_owner.Parameters.ChangeVariablesBehavior(CustomVariableBehaviorTarget.ON_MOVE_EXIT);
		}
		CurrentMove = -1;
		BufferedMove = -1;
		CancelBuffer = false;
		MoveBuffer.Stop();
	}

	public void EndMove()
	{
		if (GetCurrentMove().MoveEndState >= 0)
		{
			_owner.StateManager.PlayState(GetCurrentMove().MoveEndState);
		}
		CurrentMove = -1;
		_owner.Parameters.ChangeVariablesBehavior(CustomVariableBehaviorTarget.ON_MOVE_EXIT);
	}

	public void CallStance(int NextStance)
	{
		CurrentStance = NextStance;
		CurrentMove = -1;
		BufferedMove = -1;
		CancelBuffer = false;
		MoveBuffer.Stop();
	}

	public void Clear()
	{
		CurrentMove = -1;
		BufferedMove = -1;
		CancelBuffer = false;
		if (!GetCurrentStance().IsDamagePersistent)
		{
			CurrentStance = 0;
		}
		MoveBuffer.Stop();
	}

	public bool CheckOwnerState(int index)
	{
		if (GetMove(index).IsSequenceFromStates == null)
		{
			return true;
		}
		if (GetMove(index).IsSequenceFromStates.Length == 0)
		{
			return true;
		}
		int[] isSequenceFromStates = GetMove(index).IsSequenceFromStates;
		foreach (int possibleStates in isSequenceFromStates)
		{
			if (_owner.StateManager.CurrentState == possibleStates)
			{
				return true;
			}
		}
		return false;
	}

	public bool CheckStatesToIgnore(int index)
	{
		if (GetMove(index).IgnoreStates == null)
		{
			return true;
		}
		if (GetMove(index).IgnoreStates.Length == 0)
		{
			return true;
		}
		int[] ignoreStates = GetMove(index).IgnoreStates;
		foreach (int possibleStates in ignoreStates)
		{
			if (_owner.StateManager.CurrentState == possibleStates)
			{
				return false;
			}
		}
		return true;
	}

	private bool CheckCancelConditions(MoveCancelSettings cancelSettings)
	{
		if (cancelSettings.NetsuOverdriveOnly && (!SakugaParameters.OverdriveCharacterExtras || _owner.Parameters == null || !_owner.Parameters.InOverdrive()))
		{
			return false;   // Netsu (Oct 26 late): an Overdrive-only cancel (Flan's 623 jump cancel)
		}
		if (cancelSettings.NetsuOnlyInState >= 0 && _owner.StateManager.CurrentState != cancelSettings.NetsuOnlyInState)
		{
			return false;   // Netsu (Oct 29): a cancel for one state only (Flan's 236 pass-through)
		}
		bool isKaraCancel = (int)(_owner.CancelConditions & cancelSettings.Conditions & CancelCondition.KARA_CANCEL) > 0;
		if ((int)(_owner.CancelConditions & cancelSettings.Conditions) > 0 && ((isKaraCancel && _owner.StateManager.CurrentStateFrame < 3) || (!isKaraCancel && _owner.StateManager.CurrentStateFrame >= cancelSettings.FrameThreshold.X && _owner.StateManager.CurrentStateFrame <= cancelSettings.FrameThreshold.Y)))
		{
			return true;
		}
		return false;
	}

	/// <param name="sideOverride">Netsu: 0 = the usual block direction (away from the other fighter);
	/// +1 / -1 = the attack comes from the right / left (assists and projectiles that cross up).</param>
	/// <summary>Netsu (Oct 27): frames at the start of a jump (counted from the first jump frame) in which the fighter cannot block.</summary>
	public const int NetsuJumpNoBlockFrames = 10;

	private bool NetsuInJumpNoBlock()
	{
		if (_owner.StateManager.CurrentStateFrame >= NetsuJumpNoBlockFrames)
		{
			return false;
		}
		string n = _owner.StateManager.GetCurrentState()?.StateName;
		return n != null && (n.StartsWith("Jump_") || n.StartsWith("Super_Jump") || n.StartsWith("Dash_Jump"));
	}

	// ---------------------------------------------------------------------------------------------
	// Netsu (Nov 3 2026, TamaDeez): BAITING A BURST, a rule for the whole game.
	//  - A Burst only comes out once the Burster's hitstop is over (ProcessMoveBuffer), so the attacker gets the same
	//    frames to react as the Burst's startup (6).
	//  - Against a Burst hit (NetsuVsBurst, set by the Burster's hit code), the attacker guards if she is free:
	//      * in the recovery of a LIGHT (A) normal that connected and she pressed nothing after it (lights recover fast
	//        enough: bursting a light is a risk);
	//      * in a jump, from its first frame (a jump cancel out of a B / C normal is fast enough; the usual "no block in
	//        the first 10F of a jump" doesn't apply to a Burst);
	//      * in neutral / walking / dashing.
	//    She guards unless she's holding toward the Burster; she doesn't need to hold back (she saw it coming or not).
	//  - Still in a B / C normal (no jump cancel), a special, a super, or already in her next attack: she gets hit.

	/// <summary>Set by the attacker's hit code while it asks whether a Burst hit is guarded.</summary>
	public bool NetsuVsBurst;

	/// <summary>A light (A) normal that has hit or been blocked: its recovery can guard a Burst.</summary>
	private bool NetsuLightRecovery()
	{
		return CurrentMove >= 0 && NetsuIsNormal(CurrentMove) && NetsuStrength(CurrentMove) == 0
			&& (_owner.CancelConditions & (CancelCondition.HIT_CANCEL | CancelCondition.BLOCK_CANCEL)) != 0;
	}

	private int NetsuBurstGuard(HitType type, byte state)
	{
		StateType t = _owner.StateManager.CurrentStateType();
		if (t == StateType.HIT_REACTION || t == StateType.LOCKED || _owner.NetsuLandLag > 0)
		{
			return -1;
		}
		if (t == StateType.COMBAT && _owner.StateManager.CurrentStateFrame >= 3 && !NetsuLightRecovery())
		{
			return -1;   // still in her attack (a B / C normal, a special, a super) or already in the next one
		}
		if (GetCurrentStance().BlockReactions == null || GetCurrentStance().BlockReactions.Length == 0)
		{
			return -1;
		}
		int forcedGuard = GameManager.Instance?.Training?.ForcedGuard(_owner) ?? 0;
		if (forcedGuard < 0)
		{
			return -1;   // Training: a dummy set to not guard
		}
		InputManager inp = _owner.Inputs;
		PlayerInputs toward = (_owner.Body != null && _owner.Body.IsLeftSide) ? PlayerInputs.RIGHT : PlayerInputs.LEFT;
		if (forcedGuard == 0 && inp != null && inp.IsBeingPressed(inp.CurrentHistory, toward))
		{
			return -1;   // walking into it
		}
		int pick = NetsuForcedBlock(type);
		if (pick < 0)
		{
			return -1;
		}
		BlockSettings b = GetCurrentStance().BlockReactions[pick];
		switch (state)
		{
		case 0:
			return b.EnterState;
		case 1:
			return b.StunState;
		case 2:
			return b.GuardCrushState;
		}
		return -1;
	}

	public int GetBlockState(HitType Type, byte state, int sideOverride = 0)
	{
		if (_owner.NetsuBurstPunishable)
		{
			return -1;   // Nov 3: coming down from her Burst: she can't block (the punish window)
		}
		if (NetsuVsBurst)
		{
			return NetsuBurstGuard(Type, state);
		}
		if (_owner.NetsuLandLag > 0)
		{
			return -1;   // Netsu (Oct 26 late): can't block during landing recovery
		}
		if (NetsuInJumpNoBlock())
		{
			return -1;   // Netsu (Oct 27): no blocking for the first 10F of a jump (4F startup + 6F in the air)
		}
		if (_owner.StateManager.CurrentStateType() == StateType.HIT_REACTION)
		{
			return -1;
		}
		if (_owner.StateManager.CurrentStateType() == StateType.LOCKED)
		{
			return -1;
		}
		if (_owner.StateManager.CurrentStateType() == StateType.COMBAT && _owner.StateManager.CurrentStateFrame >= 3)
		{
			return -1;
		}
		if (GetCurrentStance().BlockReactions == null || GetCurrentStance().BlockReactions.Length == 0)
		{
			return -1;
		}
		// Netsu: Training mode's Guard setting for the dummy (1 = guards whatever it's pressing,
		// -1 = doesn't guard, 0 = its inputs decide as usual)
		int netsuForced = GameManager.Instance?.Training?.ForcedGuard(_owner) ?? 0;
		if (netsuForced < 0)
		{
			return -1;
		}
		if (netsuForced > 0)
		{
			int pick = NetsuForcedBlock(Type);
			if (pick < 0)
			{
				return -1;
			}
			BlockSettings forced = GetCurrentStance().BlockReactions[pick];
			switch (state)
			{
			case 0:
				return forced.EnterState;
			case 1:
				return forced.StunState;
			case 2:
				return forced.GuardCrushState;
			}
			return -1;
		}
		for (int i = 0; i < GetCurrentStance().BlockReactions.Length; i++)
		{
			BlockSettings block = GetCurrentStance().BlockReactions[i];
			if ((!_owner.Body.IsOnGround || block.ReferenceStance != StanceSelect.AIR) && (_owner.Body.IsOnGround || block.ReferenceStance == StanceSelect.AIR) && ValidHitType(Type, block.BlockType) && block.InputToCheck != null && _owner.Inputs.CheckMotionInputs(block.InputToCheck, sideOverride != 0 ? sideOverride : _owner.InputSide(InputSideCheck.SIDE_RELATIVE)))
			{
				switch (state)
				{
				case 0:
					return block.EnterState;
				case 1:
					return block.StunState;
				case 2:
					return block.GuardCrushState;
				}
			}
		}
		return -1;
	}

	/// <summary>Netsu (Training): the block reaction a guarding dummy uses against this hit type: the
	/// one for the stance it's in (crouching keeps crouching when that stops the hit), else any that
	/// stops it (an overhead makes a crouching dummy stand up to guard).</summary>
	private int NetsuForcedBlock(HitType type)
	{
		BlockSettings[] list = GetCurrentStance().BlockReactions;
		bool inAir = !_owner.Body.IsOnGround;
		StanceSelect want = inAir ? StanceSelect.AIR : (_owner.IsCrouchState() ? StanceSelect.CROUCH : StanceSelect.GROUND);
		int any = -1;
		for (int i = 0; i < list.Length; i++)
		{
			BlockSettings b = list[i];
			if (b == null || (b.ReferenceStance == StanceSelect.AIR) != inAir || !ValidHitType(type, b.BlockType))
			{
				continue;
			}
			if (b.ReferenceStance == want)
			{
				return i;
			}
			if (any < 0)
			{
				any = i;
			}
		}
		return any;
	}

	public int ExitBlockState(StanceSelect stance)
	{
		if (GetCurrentStance().BlockReactions == null || GetCurrentStance().BlockReactions.Length == 0)
		{
			return -1;
		}
		for (int i = 0; i < GetCurrentStance().BlockReactions.Length; i++)
		{
			BlockSettings block = GetCurrentStance().BlockReactions[i];
			if (IsValidStance(block.ReferenceStance, stance))
			{
				return block.ExitState;
			}
		}
		return -1;
	}

	private bool IsValidStance(StanceSelect stance, StanceSelect compare)
	{
		return stance == compare;
	}

	private bool ValidHitType(HitType hitType, BlockType blockType)
	{
		switch (hitType)
		{
		case HitType.UNBLOCKABLE:
			return false;
		case HitType.HIGH:
			if ((int)(blockType & BlockType.HIGH) > 0)
			{
				return true;
			}
			break;
		}
		if (hitType == HitType.MEDIUM && (int)(blockType & BlockType.MEDIUM) > 0)
		{
			return true;
		}
		if (hitType == HitType.LOW && (int)(blockType & BlockType.LOW) > 0)
		{
			return true;
		}
		return false;
	}

	public FighterStance GetStance(int index)
	{
		return _owner.Data.Stances[index];
	}

	public FighterStance GetCurrentStance()
	{
		return GetStance(CurrentStance);
	}

	public MoveSettings GetMove(int index)
	{
		return GetCurrentStance().Moves[index];
	}

	public MoveSettings GetCurrentMove()
	{
		return GetMove(CurrentMove);
	}

	public MoveSettings GetBufferedMove()
	{
		return GetMove(BufferedMove);
	}

	public int GetMoveListLength()
	{
		return GetCurrentStance().Moves.Length;
	}
}
