using System;
using Godot;
using SakugaEngine.Collision;
using SakugaEngine.Game;
using SakugaEngine.Global;
using SakugaEngine.Resources;

namespace SakugaEngine;

/// <summary>
/// The CPU. Each frame (GameManager.GameLoop: SelectCommand, then UpdateCommand feeds this frame's input):
///   1. hit / grabbed: tech, throw break (TechingRate), recoveries;
///   2. reactions (Netsu, Oct 24 night): "counter" conditions of its behaviour (CounterFlags, PredictionQuality)
///      are checked every frame, once per opponent move, after ReactionTime frames: anti-airs, punishes
///      (AIFlags.NETSU_RECOVERY), meaties... and a wake-up reversal (WakeupReversal) as it gets up;
///   3. defence (Netsu): it looks NetsuLookAhead frames ahead at every attack box of the opponent's side
///      (fighter, assist, projectiles, beams) and guards the right height, away from where the attack comes
///      from: on sight after ReactionTime frames (BlockingRate, BlockAccuracy), and keeps guarding through a
///      string (GuardHold). It used to guard only when an attack's proximity box touched it early, which
///      jump-ins, most specials, supers, long beams and assists never do;
///   4. its plan: every DecisionRate frames it picks an action list by distance (Near / Mid / Far / Distant).
///      A list is a combo: attacks wait to connect, then ComboSkill / BlockConfirm decide whether to go on.
/// Tuning: tools/ai/build_*_ai.py (writes actors/*/AI/*.tres).
/// </summary>
[GlobalClass]
public partial class AIBrain : Node
{
	private SakugaActor _owner;

	private BotMode mode;

	private AIBehavior currentBehavior;

	private int tick;

	private int tickLimit = 1;

	private int inputTick;

	private int inputTickLimit = 1;

	private int[] currentCommandList = Array.Empty<int>();

	private int currentCommand;

	private int currentInputIndex;

	private int currentDecisionRate;

	public bool canAdvance;

	public bool inputFinished = true;

	public bool blocking;

	public bool teching;

	public HitType proximityHit;

	// Combo tracking (Netsu): see UpdateCommand.
	private bool actionStarted;

	private int movesAtActionStart;

	private int delayTick;

	private bool waitingLink;

	// --- Netsu brain v2 (Oct 24 2026, night) -------------------------------------------------------------
	/// <summary>How many frames ahead it checks for an attack about to reach it.</summary>
	public const int NetsuLookAhead = 14;

	/// <summary>Room around an incoming attack box (its future position is an estimate): 0.15 m.</summary>
	public const int NetsuMargin = 1500;

	/// <summary>GuardHabit applies with the opponent this close (1.8 m).</summary>
	public const int NetsuGuardHabitRange = 18000;

	/// <summary>A wake-up reversal only when the opponent is this close (2.6 m).</summary>
	public const int NetsuWakeupRange = 26000;

	private struct NetsuThreat
	{
		public bool Found;

		public int Frames;

		public HitType Type;

		public int SourceX;

		public bool FromFighter;

		public bool FromAir;

		public ulong Key;

		public int Visible;
	}

	private struct NetsuTrack
	{
		public bool Used;

		public uint Id;

		public int State;

		public int Frame;

		public int Instance;
	}

	private readonly NetsuTrack[] _netsuTracks = new NetsuTrack[12];

	private bool _netsuGuarding;

	private bool _netsuGuardLow;

	private int _netsuGuardAway;

	private int _netsuGuardHold;

	private ulong _netsuThreatKey = ulong.MaxValue;

	private bool _netsuThreatBlock;

	private int _netsuOppInstance;

	private int _netsuOppState = -1;

	private int _netsuOppFrame;

	private int _netsuReacted = -1;

	private int _netsuOppAirFrames;

	private int _netsuJumpInstance;

	private int _netsuJumpReacted = -1;

	private bool _netsuWasDown;

	private int _netsuExtraDelay;

	private int _netsuRetries;

	/// <summary>The action list running is one of its plans (picked at a decision), not a reaction.</summary>
	private bool _netsuPlanFromDecision;

	/// <summary>The anti-air picked for the jump _netsuAAPickJump.</summary>
	private AICondition _netsuAAPick;

	private int _netsuAAPickJump = -1;

	/// <summary>Game frame until which a reaction it started is left alone (no other reaction or guard
	/// replaces it while it inputs the motion).</summary>
	private int _netsuCommitUntil = -1;

	/// <summary>How many times it inputs a cancel / follow-up again when it didn't come out.</summary>
	public const int NetsuRetries = 3;

	private AIData data => _owner.Data._aiData;

	/// <summary>Test switch: prints the CPU's reactions and guard decisions (off in the game).</summary>
	public static bool NetsuDebug;

	private void Dbg(string what)
	{
		if (NetsuDebug)
		{
			GD.Print($"[brain] {GameManager.Instance?.Frame} P{_owner.playerID + 1} {what}");
		}
	}

	private int Reaction => Math.Max(0, currentBehavior.ReactionTime);

	/// <summary>Netsu: the CPU's own dice. The game's RNG is re-seeded every frame from the game state, and the
	/// first numbers after a re-seed barely change from one frame to the next, so the CPU's rolls (keep the combo
	/// going? guard?) came out the same way far too often. The CPU never plays online, so it needs no rollback.</summary>
	private Random _rng = new Random(1);

	public void Initialize(SakugaActor owner, BotDifficulty difficulty)
	{
		_owner = owner;
		switch (difficulty)
		{
		case BotDifficulty.BEGINNER:
			currentBehavior = data.BehaviorBeginner;
			break;
		case BotDifficulty.EASY:
			currentBehavior = data.BehaviorEasy;
			break;
		case BotDifficulty.MEDIUM:
			currentBehavior = data.BehaviorMedium;
			break;
		case BotDifficulty.HARD:
			currentBehavior = data.BehaviorHard;
			break;
		case BotDifficulty.VERY_HARD:
			currentBehavior = data.BehaviorVeryHard;
			break;
		case BotDifficulty.PRO:
			currentBehavior = data.BehaviorPro;
			break;
		}
		// A fighter without a behaviour for this difficulty falls back to the
		// nearest one that exists instead of crashing.
		if (currentBehavior == null)
		{
			AIBehavior[] order = { data.BehaviorMedium, data.BehaviorHard, data.BehaviorEasy, data.BehaviorVeryHard, data.BehaviorBeginner, data.BehaviorPro };
			foreach (AIBehavior b in order)
			{
				if (b != null)
				{
					currentBehavior = b;
					break;
				}
			}
		}
		currentDecisionRate = 60;
		_rng = new Random(unchecked((int)owner.playerID * 7919 + (int)difficulty * 104729 + (int)(Time.GetTicksMsec() & 0x7FFFFFFF)));
		currentCommandList = Array.Empty<int>();
		_netsuGuarding = false;
		_netsuGuardHold = 0;
		_netsuThreatKey = ulong.MaxValue;
		_netsuReacted = -1;
		_netsuJumpReacted = -1;
		_netsuAAPick = null;
		_netsuAAPickJump = -1;
		_netsuOppAirFrames = 0;
		_netsuOppState = -1;
		_netsuWasDown = false;
		Array.Clear(_netsuTracks);
	}

	/// <summary>The behaviour in use (the assist's CPU reads AssistRate from it).</summary>
	public AIBehavior Behavior => currentBehavior;

	private int UpdateDecisionRateFree()
	{
		return _rng.Next(currentBehavior.DecisionRateFree.X, currentBehavior.DecisionRateFree.Y + 1);
	}

	private int UpdateDecisionRateBusy()
	{
		return _rng.Next(currentBehavior.DecisionRateBusy.X, currentBehavior.DecisionRateBusy.Y + 1);
	}

	private int SetInputRandomWaitTime()
	{
		return _rng.Next(currentBehavior.InputRandomness.X, currentBehavior.InputRandomness.Y + 1);
	}

	public void Reset()
	{
		currentCommandList = Array.Empty<int>();
		blocking = false;
		currentCommand = 0;
		currentInputIndex = 0;
		teching = false;
		canAdvance = false;
		inputFinished = true;
		actionStarted = false;
		waitingLink = false;
		delayTick = 0;
	}

	/// <summary>Test hook: runs this action list now.</summary>
	public void DebugRun(int[] list)
	{
		NetsuStart(list);
	}

	/// <summary>Test hook: makes no decisions of its own (only runs what DebugRun gives it).</summary>
	public bool DebugPassive;

	/// <summary>Starts an action list now (a reaction), dropping whatever it was doing.</summary>
	private void NetsuStart(int[] list, int extraDelay = 0)
	{
		_netsuCommitUntil = (GameManager.Instance?.Frame ?? 0) + 14 + extraDelay;
		Reset();
		currentCommandList = list ?? Array.Empty<int>();
		inputTick = 0;
		inputTickLimit = SetInputRandomWaitTime();
		tick = 0;
		_netsuExtraDelay = extraDelay;
		_netsuGuarding = false;
		_netsuGuardHold = 0;
		_netsuPlanFromDecision = false;
	}

	public void SelectCommand()
	{
		if (DebugPassive)
		{
			return;
		}
		SakugaActor opponent = _owner.GetOpponent(0);
		if (_owner.IsKO() || opponent == null || opponent.IsKO())
		{
			_netsuGuarding = false;
			return;
		}
		NetsuTrackOpponent(opponent);
		StateType type = _owner.StateManager.CurrentStateType();
		if (type == StateType.HIT_REACTION)
		{
			_netsuGuarding = false;
			_netsuGuardHold = 0;
			if ((_owner.StateManager.GetCurrentState().AIFlags & AIFlags.KNOCKED_DOWN) != 0)
			{
				_netsuWasDown = true;
			}
			if (!teching)
			{
				NetsuHitReaction();
			}
			return;
		}
		if (type == StateType.COMBAT || type == StateType.LOCKED)
		{
			_netsuGuarding = false;
			_netsuGuardHold = 0;
			if (type == StateType.LOCKED)
			{
				Reset();
			}
			tick = 0;
			return;
		}
		bool inBlockstun = type == StateType.BLOCKING;
		if (!inBlockstun && (GameManager.Instance?.Frame ?? 0) < _netsuCommitUntil && currentCommand < currentCommandList.Length)
		{
			return;   // inputting a reaction (an anti-air's motion...): let it come out
		}
		_netsuThreatNow = NetsuScan();
		if (!inBlockstun)
		{
			if (_netsuWasDown)
			{
				_netsuWasDown = false;
				if (NetsuWakeup(opponent))
				{
					return;
				}
			}
			if (NetsuReact(opponent))
			{
				return;
			}
		}
		if (NetsuDefend(inBlockstun))
		{
			tick = 0;
			return;
		}
		if (inBlockstun)
		{
			tick = 0;
			return;
		}
		if (_netsuPlanFromDecision && currentCommand < currentCommandList.Length && !waitingLink && _owner.Body.IsOnGround
			&& NetsuJumpingIn(opponent) && _netsuOppAirFrames >= Reaction)
		{
			// a plan under way (a dash in, a walk up to throw) when they jump in at it: once it has seen the jump it
			// drops the plan (guards or anti-airs) instead of running under them or throwing at the air
			Dbg("they jumped in: plan dropped");
			Reset();
			_netsuPlanFromDecision = false;
		}
		if ((currentCommand >= currentCommandList.Length || (inputFinished && !canAdvance && currentCommandList.Length > 0 && currentCommand >= 0 && !data.Actions[currentCommandList[currentCommand]].AutoAdvance)) && _owner.StanceManager.CurrentMove < 0)
		{
			Reset();
		}
		if ((currentCommand != 0 && currentCommand < currentCommandList.Length) || currentInputIndex != 0)
		{
			tick = 0;
			return;
		}
		if (NetsuJumpingIn(opponent))
		{
			return;   // they're jumping in: no new plan (an anti-air or a guard comes from the reactions)
		}
		tick++;
		if (tick <= tickLimit)
		{
			return;
		}
		if (_owner.StanceManager.CurrentMove < 0)
		{
			tickLimit = UpdateDecisionRateFree();
		}
		else
		{
			tickLimit = UpdateDecisionRateBusy();
		}
		tick = 0;
		int[] previousCommandList = currentCommandList;
		int previousCommand = currentCommand;
		int previousInputIndex = currentInputIndex;
		Reset();
		Vector2I distance = GlobalFunctions.Distance(_owner.Body.FixedPosition, opponent.Body.FixedPosition);
		AIActionPack selectedList = PackFor(distance.X);
		mode = ((_owner.Parameters.Health.CurrentValue < currentBehavior.LowHealth) ? BotMode.DEFENSIVE : BotMode.AGGRESSIVE);
		if (distance.X <= NetsuGuardHabitRange && _owner.Body.IsOnGround && NetsuCanAttackSoon(opponent)
			&& _rng.Next(0, 10) < currentBehavior.GuardHabit + (mode == BotMode.DEFENSIVE ? 1 : 0))
		{
			currentCommandList = new int[1] { data.LowBlockAction };   // hold crouch guard until the next decision
			_netsuPlanFromDecision = true;
			inputTick = 0;
			inputTickLimit = SetInputRandomWaitTime();
			return;
		}
		if (selectedList.Conditions.Length == 1)
		{
			currentCommandList = selectedList.Conditions[0].ActionsList;
		}
		else
		{
			int prevDistX = 0;
			int prevDistY = 0;
			for (int i = 0; i < selectedList.Conditions.Length; i++)
			{
				AICondition cond = selectedList.Conditions[i];
				if (!GroundAirOk(cond) || cond.SuperGaugeRequired > _owner.Parameters.SuperGauge.CurrentValue)
				{
					continue;
				}
				// reads (CounterFlags) are reactions now: NetsuReact checks them every frame
				if (cond.CounterFlags != 0 && cond.Probability == 0)
				{
					continue;
				}
				bool sameBand = cond.Distance.X == prevDistX;
				bool ignoreY = cond.Distance.Y == 0;
				bool beyondPrev = (sameBand || distance.X > prevDistX) && (ignoreY || distance.Y >= prevDistY);
				bool checkClose = distance.X <= cond.Distance.X && (ignoreY || distance.Y <= cond.Distance.Y);
				if (!beyondPrev || !checkClose)
				{
					continue;
				}
				if (i > 0)
				{
					if (cond.Probability == 0)
					{
						continue;
					}
					int probability = VariableProbability(cond);
					if (_rng.Next(0, 10) > probability - 1)
					{
						continue;
					}
				}
				currentCommandList = cond.ActionsList;
				prevDistX = cond.Distance.X;
				prevDistY = cond.Distance.Y;
			}
		}
		if (CompareCommands(currentCommandList, previousCommandList))
		{
			currentCommand = previousCommand;
			currentInputIndex = previousInputIndex;
		}
		_netsuPlanFromDecision = true;
		if (NetsuDebug && !CompareCommands(currentCommandList, previousCommandList))
		{
			Dbg($"plan {string.Join(",", currentCommandList)} (distance {distance.X})");
		}
		inputTick = 0;
		inputTickLimit = SetInputRandomWaitTime();
	}

	private AIActionPack PackFor(int distanceX)
	{
		AIActionPack selectedList = currentBehavior.NearActions;
		if (distanceX > currentBehavior.NearActions.HorizontalDistance && distanceX <= currentBehavior.MidActions.HorizontalDistance)
		{
			selectedList = currentBehavior.MidActions;
		}
		else if (distanceX > currentBehavior.MidActions.HorizontalDistance && distanceX <= currentBehavior.FarActions.HorizontalDistance)
		{
			selectedList = currentBehavior.FarActions;
		}
		else if (distanceX > currentBehavior.FarActions.HorizontalDistance)
		{
			selectedList = currentBehavior.DistantActions;
		}
		return selectedList;
	}

	private bool GroundAirOk(AICondition cond)
	{
		bool onGround = _owner.Body.IsOnGround;
		if (cond.UseOnGround && cond.UseOnAir)
		{
			return true;
		}
		if (cond.UseOnGround)
		{
			return onGround;
		}
		if (cond.UseOnAir)
		{
			return !onGround;
		}
		return false;
	}

	// --- being hit -----------------------------------------------------------------------------------------

	private void NetsuHitReaction()
	{
		if (_owner.IsGrabbed() && _owner.Hitstop.IsRunning())
		{
			// a throw: break it (B+C) with TechingRate, after noticing it (half its reaction time, the window is 12 f)
			if (_rng.Next(0, 10) < currentBehavior.TechingRate)
			{
				NetsuStart(new int[1] { data.ThrowEscapeAction }, Math.Min(Reaction / 2, 8));
			}
			teching = true;
			return;
		}
		if (!_owner.Hitstun.IsRunning())
		{
			return;
		}
		int rnd = _rng.Next(0, 10);
		if (rnd < currentBehavior.TechingRate)
		{
			rnd = _rng.Next(0, 10);
			currentCommandList = new int[1];
			switch (mode)
			{
			case BotMode.AGGRESSIVE:
				currentCommandList[0] = rnd < currentBehavior.TechingRate ? data.ForwardRecoveryAction : data.BackRecoveryAction;
				break;
			default:
				currentCommandList[0] = rnd < currentBehavior.TechingRate ? data.BackRecoveryAction : data.ForwardRecoveryAction;
				break;
			}
			currentCommand = 0;
			currentInputIndex = 0;
			actionStarted = false;
		}
		teching = true;
	}

	/// <summary>The first free frame after a knockdown: maybe an invincible move if they're right there.</summary>
	private bool NetsuWakeup(SakugaActor opponent)
	{
		int[] list = currentBehavior.WakeupReversal;
		if (list == null || list.Length == 0 || currentBehavior.WakeupRate <= 0)
		{
			return false;
		}
		if (currentBehavior.WakeupGauge > _owner.Parameters.SuperGauge.CurrentValue)
		{
			return false;
		}
		if (Math.Abs(opponent.Body.FixedPosition.X - _owner.Body.FixedPosition.X) > NetsuWakeupRange)
		{
			return false;
		}
		if (_rng.Next(0, 10) >= currentBehavior.WakeupRate)
		{
			return false;
		}
		NetsuStart(list);
		return true;
	}

	// --- reactions -----------------------------------------------------------------------------------------

	/// <summary>Counts the opponent's moves (a new state, or the same one started again).</summary>
	private void NetsuTrackOpponent(SakugaActor opponent)
	{
		int state = opponent.StateManager.CurrentState;
		int frame = opponent.StateManager.CurrentStateFrame;
		if (state != _netsuOppState || frame < _netsuOppFrame)
		{
			_netsuOppInstance++;
			_netsuOppState = state;
		}
		_netsuOppFrame = frame;
		// a jump (not being juggled): counted from the frame they leave the ground
		if (NetsuJumping(opponent))
		{
			if (_netsuOppAirFrames == 0)
			{
				_netsuJumpInstance++;
			}
			_netsuOppAirFrames++;
		}
		else
		{
			_netsuOppAirFrames = 0;
		}
	}

	/// <summary>The opponent could start an attack any moment (standing, walking, crouching, dashing...).</summary>
	private static bool NetsuCanAttackSoon(SakugaActor o)
	{
		StateType t = o.StateManager.CurrentStateType();
		return o.Body.IsOnGround && (t == StateType.NULL || t == StateType.MOVEMENT);
	}

	/// <summary>The opponent in a jump coming its way, close enough to land on it.</summary>
	private bool NetsuJumpingIn(SakugaActor o)
	{
		if (!NetsuJumping(o))
		{
			return false;
		}
		int dx = o.Body.FixedPosition.X - _owner.Body.FixedPosition.X;
		return Math.Abs(dx) <= 32000 && (Math.Abs(dx) < 14000 || (long)dx * o.Body.FixedVelocity.X <= 0);
	}

	private static bool NetsuJumping(SakugaActor a)
	{
		StateType t = a.StateManager.CurrentStateType();
		if (t == StateType.HIT_REACTION)
		{
			return false;
		}
		if (!a.Body.IsOnGround)
		{
			return true;
		}
		// the jump squat (a jump state's frames before take-off): a player sees the jump coming from there
		FighterState s = a.StateManager.GetCurrentState();
		return t == StateType.MOVEMENT && s != null && (s.AIFlags & AIFlags.AIR_ACTION) != 0;
	}

	/// <summary>A "counter" condition (CounterFlags) that fits what the opponent is doing, with a
	/// PredictionQuality-in-10 chance, after ReactionTime frames: an anti-air (AIR_ACTION) once per jump, seen
	/// from the jump itself (an air attack is too quick to react to); any other read once per opponent move.</summary>
	private bool NetsuReact(SakugaActor opponent)
	{
		if (currentBehavior.PredictionQuality <= 0)
		{
			return false;
		}
		Vector2I distance = GlobalFunctions.Distance(_owner.Body.FixedPosition, opponent.Body.FixedPosition);
		bool tooLate = _netsuThreatNow.Found && _netsuThreatNow.Frames <= 3;   // their attack is already coming out: guard
		if (NetsuJumping(opponent) && !tooLate && _netsuJumpReacted != _netsuJumpInstance && _netsuOppAirFrames >= Reaction)
		{
			if (_netsuAAPickJump != _netsuJumpInstance || _netsuAAPick == null)
			{
				// one anti-air per jump, picked first: each has its own timing (NetsuStartup)
				_netsuAAPickJump = _netsuJumpInstance;
				_netsuAAPick = NetsuPickCounter(AIFlags.AIR_ACTION, distance);
			}
			AICondition aa = _netsuAAPick;
			if (aa != null && NetsuAntiAirTime(opponent, NetsuAntiAirLead(aa)))
			{
				_netsuJumpReacted = _netsuJumpInstance;
				if (_rng.Next(0, 100) < currentBehavior.PredictionQuality * aa.ReactChance)
				{
					Dbg($"anti-air {string.Join(",", aa.ActionsList)} (air {_netsuOppAirFrames} f)");
					NetsuStart(aa.ActionsList);
					return true;
				}
				Dbg("anti-air roll failed");
			}
		}
		if (_netsuReacted == _netsuOppInstance || opponent.StateManager.CurrentStateFrame < Reaction)
		{
			return false;
		}
		AIFlags flags = (opponent.StateManager.GetCurrentState().AIFlags | NetsuExtraFlags(opponent)) & ~AIFlags.AIR_ACTION;
		AICondition pick = NetsuPickCounter(flags, distance);
		if (pick == null)
		{
			return false;
		}
		_netsuReacted = _netsuOppInstance;
		if (_rng.Next(0, 100) >= currentBehavior.PredictionQuality * pick.ReactChance)
		{
			Dbg($"read roll failed ({flags})");
			return false;
		}
		Dbg($"read {flags}: {string.Join(",", pick.ActionsList)}");
		NetsuStart(pick.ActionsList);
		return true;
	}

	/// <summary>The counter condition for these opponent flags that fits the distance best (the tightest range;
	/// one of them at random on a tie), over all four distance lists.</summary>
	private AICondition NetsuPickCounter(AIFlags flags, Vector2I distance)
	{
		AICondition pick = null;
		int bestDist = int.MaxValue;
		int ties = 0;
		AIActionPack[] packs = { currentBehavior.NearActions, currentBehavior.MidActions, currentBehavior.FarActions, currentBehavior.DistantActions };
		foreach (AIActionPack pack in packs)
		{
			if (pack?.Conditions == null)
			{
				continue;
			}
			foreach (AICondition cond in pack.Conditions)
			{
				if (cond == null || cond.Probability != 0 || (cond.CounterFlags & flags) == 0)
				{
					continue;
				}
				if (!GroundAirOk(cond) || cond.SuperGaugeRequired > _owner.Parameters.SuperGauge.CurrentValue)
				{
					continue;
				}
				if (distance.X > cond.Distance.X || (cond.Distance.Y != 0 && distance.Y > cond.Distance.Y))
				{
					continue;
				}
				if (cond.Distance.X < bestDist)
				{
					bestDist = cond.Distance.X;
					pick = cond;
					ties = 1;
				}
				else if (cond.Distance.X == bestDist && _rng.Next(0, ++ties) == 0)
				{
					pick = cond;   // several for the same range: one of them at random
				}
			}
		}
		return pick;
	}

	/// <summary>A jumping opponent worth anti-airing: coming down (or low) and coming at it.</summary>
	private bool NetsuAntiAirWindow(SakugaActor opponent)
	{
		PhysicsBody o = opponent.Body;
		if (o.IsOnGround)
		{
			return false;
		}
		if (o.FixedVelocity.Y > 0 && o.FixedPosition.Y > 22000)
		{
			return false;
		}
		int dx = o.FixedPosition.X - _owner.Body.FixedPosition.X;
		return Math.Abs(dx) < 14000 || (long)dx * o.FixedVelocity.X <= 0;
	}

	/// <summary>Frames from starting an anti-air to its hit: its start-up (NetsuStartup, as the opponent sees it)
	/// plus the time to input it (each step of the motion up to the button takes InputRandomness frames).</summary>
	private int NetsuAntiAirLead(AICondition aa)
	{
		int startup = aa.NetsuStartup >= 0 ? aa.NetsuStartup : 7;
		int presses = 3;
		if (aa.ActionsList != null && aa.ActionsList.Length > 0 && aa.ActionsList[0] >= 0 && aa.ActionsList[0] < data.Actions.Length)
		{
			AIInput[] inputs = data.Actions[aa.ActionsList[0]].Inputs;
			if (inputs != null && inputs.Length > 0)
			{
				presses = inputs.Length;
				for (int i = 0; i < inputs.Length; i++)
				{
					if (inputs[i] != null && inputs[i].Buttons != 0)
					{
						presses = i + 1;   // up to the button
						break;
					}
				}
			}
		}
		return startup + presses * (currentBehavior.InputRandomness.X + currentBehavior.InputRandomness.Y) / 2;
	}

	/// <summary>Time to anti-air: the jumper will be in reach (about 1.1 m away, 1.7 m up) in no more frames than
	/// it takes to input and start this anti-air (`lead`), and it isn't already there. A jumper still rising past
	/// that height is waited for until it comes back down.</summary>
	private bool NetsuAntiAirTime(SakugaActor opponent, int lead)
	{
		PhysicsBody o = opponent.Body;
		if (o.IsOnGround)
		{
			return false;
		}
		int dx = Math.Abs(o.FixedPosition.X - _owner.Body.FixedPosition.X);
		int closing = (long)(o.FixedPosition.X - _owner.Body.FixedPosition.X) * o.FixedVelocity.X < 0 ? Math.Abs(o.FixedVelocity.X) / 60 : 0;
		float tx = dx <= 11000 ? 0f : (closing > 0 ? (dx - 11000) / (float)closing : 999f);
		float ty = 0f;
		int y = o.FixedPosition.Y;
		float vy = o.FixedVelocity.Y / 60f;               // units per frame, falling < 0
		float g = Math.Max(1f, o.CurrentGravity / 3600f);  // units per frame per frame
		// y + vy t - g t^2 / 2 = 17000  ->  a t^2 + b t + c = 0
		float a = g / 2f, b = -vy, c = 17000 - y;
		float disc = b * b - 4 * a * c;
		if (y > 17000)
		{
			ty = disc < 0 ? 999f : (-b + (float)Math.Sqrt(disc)) / (2 * a);   // coming down into reach
		}
		else if (vy > 0 && disc >= 0)
		{
			float up = (-b - (float)Math.Sqrt(disc)) / (2 * a);   // it rises out of reach then...
			if (up < lead)
			{
				ty = (-b + (float)Math.Sqrt(disc)) / (2 * a);      // ...and comes back down: wait for that
			}
		}
		float t = Math.Max(tx, ty);
		return t <= lead && (t > 1f || dx <= 11000);
	}

	/// <summary>NETSU_RECOVERY: the opponent's attack has nothing more to come out (punishable).</summary>
	private AIFlags NetsuExtraFlags(SakugaActor opponent)
	{
		if (opponent.StateManager.CurrentStateType() != StateType.COMBAT || !opponent.Body.IsOnGround)
		{
			return 0;
		}
		AnimationData ad = opponent.StateManager.GetCurrentState().AnimationData;
		if (ad == null || ad.Duration <= 0)
		{
			return 0;
		}
		int cur = opponent.StateManager.CurrentStateFrame;
		if (ad.Duration - cur < 6)
		{
			return 0;
		}
		for (int f = cur; f < ad.Duration; f++)
		{
			HitboxElement[] els = NetsuHitboxAt(ad, f)?.HitboxData?.Hitboxes;
			if (els == null)
			{
				continue;
			}
			foreach (HitboxElement e in els)
			{
				if (e != null && (e.HitboxType == HitboxType.HITBOX || e.HitboxType == HitboxType.PROJECTILE || e.HitboxType == HitboxType.THROW || e.HitboxType == HitboxType.COUNTER))
				{
					return 0;
				}
			}
		}
		return AIFlags.NETSU_RECOVERY;
	}

	// --- defence -------------------------------------------------------------------------------------------

	private bool NetsuDefend(bool inBlockstun)
	{
		NetsuThreat t = _netsuThreatNow;
		if (!t.Found)
		{
			t = NetsuAnticipate();
		}
		bool guardingAlready = _netsuGuarding || inBlockstun;
		if (t.Found && t.Key != _netsuThreatKey)
		{
			if (t.Visible >= Reaction)
			{
				_netsuThreatKey = t.Key;
				int rate = currentBehavior.BlockingRate + (guardingAlready ? 3 : 0);
				_netsuThreatBlock = t.Type != HitType.UNBLOCKABLE && _rng.Next(0, 10) < rate;
				_netsuGuardLow = NetsuPickLow(t);
				Dbg($"threat {t.Type} in {t.Frames} f (seen {t.Visible} f){(t.Key >= 0xFFFE000000000000UL ? " anticipated" : "")}: {(_netsuThreatBlock ? (_netsuGuardLow ? "guard low" : "guard high") : "no guard")}");
			}
			else if (guardingAlready)
			{
				// too quick to see yet: it keeps the guard it has (a fast low / overhead can open it up)
				_netsuGuardHold = Math.Max(_netsuGuardHold, currentBehavior.GuardHold);
				_netsuGuarding = true;
				return true;
			}
		}
		if (t.Found && t.Key == _netsuThreatKey && _netsuThreatBlock)
		{
			_netsuGuardAway = t.FromFighter ? 0 : (t.SourceX > _owner.Body.FixedPosition.X ? -1 : 1);
			_netsuGuarding = true;
			_netsuGuardHold = Math.Max(_netsuGuardHold, currentBehavior.GuardHold);
			return true;
		}
		if (_netsuGuarding)
		{
			if (inBlockstun)
			{
				_netsuGuardHold = Math.Max(_netsuGuardHold, currentBehavior.GuardHold);
			}
			if (_netsuGuardHold > 0)
			{
				_netsuGuardHold--;
				return true;
			}
			_netsuGuarding = false;
		}
		return false;
	}

	/// <summary>Attacks a player sees coming before any attack box is out: the opponent jumping in at it
	/// (guard high, judged from the jump), or rushing at it in an attack (a dash attack, a rushing super).</summary>
	private NetsuThreat NetsuAnticipate()
	{
		NetsuThreat t = new NetsuThreat { Frames = int.MaxValue };
		SakugaActor o = _owner.GetOpponent(0);
		if (o == null || !o.IsActive)
		{
			return t;
		}
		int dx = o.Body.FixedPosition.X - _owner.Body.FixedPosition.X;
		if (NetsuJumping(o) && Math.Abs(dx) <= 28000 && NetsuAntiAirWindow(o))
		{
			t.Found = true;
			t.Type = HitType.HIGH;
			t.FromFighter = true;
			t.FromAir = true;
			t.SourceX = o.Body.FixedPosition.X;
			t.Key = 0xFFFF000000000000UL | (uint)_netsuJumpInstance;
			t.Visible = _netsuOppAirFrames;
			t.Frames = 6;
			return t;
		}
		if (o.StateManager.CurrentStateType() == StateType.COMBAT && Math.Abs(dx) <= 38000 && (long)dx * o.Body.FixedVelocity.X < 0 && Math.Abs(o.Body.FixedVelocity.X) >= 60000)
		{
			t.Found = true;
			t.Type = HitType.MEDIUM;
			t.FromFighter = true;
			t.FromAir = !o.Body.IsOnGround;
			t.SourceX = o.Body.FixedPosition.X;
			t.Key = 0xFFFE000000000000UL | (uint)_netsuOppInstance;
			t.Visible = o.StateManager.CurrentStateFrame;
			t.Frames = 6;
		}
		return t;
	}

	private bool NetsuPickLow(NetsuThreat t)
	{
		if (t.FromAir && t.Type != HitType.LOW)
		{
			return false;   // a jump-in: everybody knows to guard high
		}
		bool low;
		switch (t.Type)
		{
		case HitType.LOW:
			low = true;
			break;
		case HitType.HIGH:
			low = false;
			break;
		default:
			low = !t.FromAir && (_netsuGuarding ? _netsuGuardLow : true);   // a mid: crouch guard also stops a low after it
			break;
		}
		if (_rng.Next(0, 10) >= currentBehavior.BlockAccuracy)
		{
			low = !low;   // guessed wrong
		}
		return low;
	}

	/// <summary>The guard: away from the attack (a fighter's: "back"; an assist's or a projectile's: away
	/// from where it is), crouching for a low.</summary>
	private PlayerInputs NetsuGuardInput()
	{
		int away = _netsuGuardAway;
		if (away == 0)
		{
			away = _owner.Body.IsLeftSide ? -1 : 1;
		}
		PlayerInputs input = away < 0 ? PlayerInputs.LEFT : PlayerInputs.RIGHT;
		if (_netsuGuardLow && _owner.Body.IsOnGround)
		{
			input |= PlayerInputs.DOWN;
		}
		return input;
	}

	/// <summary>The soonest attack box of the opponent's side (fighter, assist, projectiles) that will touch
	/// its hurtboxes in the next NetsuLookAhead frames (where it will be, from its animation and speed).</summary>
	private NetsuThreat _netsuThreatNow;

	private NetsuThreat NetsuScan()
	{
		NetsuThreat best = new NetsuThreat { Frames = int.MaxValue };
		PhysicsWorld world = GameManager.Instance?.NetsuWorld;
		PhysicsBody mine = _owner.Body;
		HitboxElement[] myEls = mine?.CurrentHitbox?.HitboxData?.Hitboxes;
		if (world == null || myEls == null)
		{
			return best;
		}
		for (int b = 0; b < world.BodyCount; b++)
		{
			if (!world.GetBody(b, out PhysicsBody body) || body == null || body == mine)
			{
				continue;
			}
			SakugaActor a = body.Parent as SakugaActor;
			if (a == null || !a.IsActive || a.StateManager == null || a.NetsuRoot() == _owner || !body.CanHitBody(mine))
			{
				continue;
			}
			FighterState st = a.StateManager.GetCurrentState();
			AnimationData ad = st?.AnimationData;
			int instance = NetsuInstance(body, a);
			if (ad?.Hitboxes == null || ad.Hitboxes.Length == 0)
			{
				continue;
			}
			int cur = a.StateManager.CurrentStateFrame;
			Vector2I side = new Vector2I(body.PlayerSide, 1);
			for (int f = 0; f <= NetsuLookAhead && f < best.Frames; f++)
			{
				int frame = cur + f;
				if (ad.Duration > 0 && frame >= ad.Duration)
				{
					break;   // the state is over by then
				}
				HitboxElement[] els = NetsuHitboxAt(ad, frame)?.HitboxData?.Hitboxes;
				if (els == null)
				{
					continue;
				}
				Vector2I pos = body.FixedPosition + body.FixedVelocity * f / 60;
				bool found = false;
				HitType type = HitType.MEDIUM;
				for (int i = 0; i < els.Length && !found; i++)
				{
					HitboxElement e = els[i];
					if (e == null || (e.HitboxType != HitboxType.HITBOX && e.HitboxType != HitboxType.PROJECTILE))
					{
						continue;
					}
					Collider atk = new Collider
					{
						Center = pos + e.Center * side,
						Size = e.Size + new Vector2I(NetsuMargin * 2, NetsuMargin)
					};
					for (int j = 0; j < mine.Hitboxes.Length && j < myEls.Length; j++)
					{
						if (myEls[j] != null && myEls[j].HitboxType == HitboxType.HURTBOX && atk.IsOverlapping(mine.Hitboxes[j]))
						{
							found = true;
							type = e.HitType;
							break;
						}
					}
				}
				if (found)
				{
					best.Found = true;
					best.Frames = f;
					best.Type = type;
					best.SourceX = body.FixedPosition.X;
					best.FromFighter = a.GetMaster() == null;
					best.FromAir = !body.IsOnGround;
					best.Key = ((ulong)body.ID << 32) | (uint)instance;
					best.Visible = cur;
					break;
				}
			}
		}
		return best;
	}

	/// <summary>Counts each actor's moves, so one attack is decided on once.</summary>
	private int NetsuInstance(PhysicsBody body, SakugaActor a)
	{
		int state = a.StateManager.CurrentState;
		int frame = a.StateManager.CurrentStateFrame;
		int free = -1;
		for (int i = 0; i < _netsuTracks.Length; i++)
		{
			if (_netsuTracks[i].Used && _netsuTracks[i].Id == body.ID)
			{
				if (_netsuTracks[i].State != state || frame < _netsuTracks[i].Frame)
				{
					_netsuTracks[i].Instance++;
					_netsuTracks[i].State = state;
				}
				_netsuTracks[i].Frame = frame;
				return _netsuTracks[i].Instance;
			}
			if (!_netsuTracks[i].Used && free < 0)
			{
				free = i;
			}
		}
		if (free < 0)
		{
			free = (int)(body.ID % (uint)_netsuTracks.Length);
		}
		_netsuTracks[free] = new NetsuTrack { Used = true, Id = body.ID, State = state, Frame = frame, Instance = 1 };
		return 1;
	}

	/// <summary>The hitbox set an animation uses on a frame (as PhysicsBody.GetCurrentHitboxSettings).</summary>
	private static HitboxState NetsuHitboxAt(AnimationData ad, int frame)
	{
		HitboxState[] list = ad.Hitboxes;
		if (list == null || list.Length == 0)
		{
			return null;
		}
		if (list.Length == 1)
		{
			return list[0];
		}
		int anim = 0;
		for (int i = 0; i < list.Length; i++)
		{
			int next = (i == list.Length - 1) ? int.MaxValue : (list[i + 1].AtFrame - 1);
			if (frame >= list[i].AtFrame && frame <= next)
			{
				anim = i;
			}
		}
		return list[anim];
	}

	// --- inputs ----------------------------------------------------------------------------------------------

	/// <summary>Feeds this frame's input for the current action. Netsu change:
	/// after an attack's inputs, the CPU waits for that attack to CONNECT (hit or
	/// block) before inputting the next part of the combo - the engine only allows
	/// cancels on contact - then rolls ComboSkill / BlockConfirm to decide whether
	/// to keep going. Movement actions with AutoAdvance go straight on.</summary>
	public void UpdateCommand()
	{
		if (_netsuGuarding)
		{
			_owner.Inputs.InsertToHistory(NetsuGuardInput());
			return;
		}
		if (currentCommandList == null || currentCommandList.Length == 0 || currentCommand >= currentCommandList.Length)
		{
			_owner.Inputs.InsertToHistory(PlayerInputs.NEUTRAL);
			return;
		}
		int curr = currentCommandList[currentCommand];
		if (curr < 0 || curr >= data.Actions.Length)
		{
			_owner.Inputs.InsertToHistory(PlayerInputs.NEUTRAL);
			return;
		}
		AIAction action = data.Actions[curr];
		if (!actionStarted)
		{
			actionStarted = true;
			_netsuRetries = 0;
			waitingLink = false;
			movesAtActionStart = _owner.StanceManager.ExecutedMoves;
			delayTick = action.StartDelay + _netsuExtraDelay;
			_netsuExtraDelay = 0;
		}
		if (delayTick > 0)
		{
			delayTick--;
			_owner.Inputs.InsertToHistory(PlayerInputs.NEUTRAL);
			return;
		}
		if (waitingLink)
		{
			_owner.Inputs.InsertToHistory(PlayerInputs.NEUTRAL);
			CancelCondition contact = _owner.CancelConditions & (CancelCondition.HIT_CANCEL | CancelCondition.BLOCK_CANCEL);
			if (contact != 0)
			{
				bool hit = (contact & CancelCondition.HIT_CANCEL) != 0;
				bool keepGoing = _rng.Next(0, 10) < currentBehavior.ComboSkill;
				if (!hit && _rng.Next(0, 10) < currentBehavior.BlockConfirm)
				{
					keepGoing = false; // blocked: don't throw out the risky part
				}
				Dbg($"link {(hit ? "hit" : "blocked")}: {(keepGoing ? "go on" : "stop")} (action {currentCommand + 1}/{currentCommandList.Length})");
				if (keepGoing)
				{
					NextAction();
				}
				else
				{
					currentCommand = currentCommandList.Length;
				}
			}
			return;
		}
		if (currentInputIndex == 0 && inputTick == 0 && NetsuIsThrow(action) && NetsuOpponentInTheAir())
		{
			// they jumped (it has seen it): a throw can't grab them, so no throw and the rest of the plan goes too
			Dbg("they're in the air: no throw");
			currentCommand = currentCommandList.Length;
			_owner.Inputs.InsertToHistory(PlayerInputs.NEUTRAL);
			return;
		}
		inputTick++;
		inputFinished = currentInputIndex >= action.Inputs.Length - 1;
		_owner.Inputs.InsertToHistory(GenerateInput(action.Inputs[currentInputIndex]));
		if (inputTick <= inputTickLimit)
		{
			return;
		}
		inputTickLimit = SetInputRandomWaitTime();
		inputTick = 0;
		if (!inputFinished)
		{
			currentInputIndex++;
			return;
		}
		bool cameOut = _owner.StanceManager.ExecutedMoves != movesAtActionStart;
		if (!cameOut && _netsuRetries < NetsuRetries && NetsuExpectsMove(action) && _owner.StateManager.CurrentStateType() == StateType.COMBAT)
		{
			// Netsu: a cancel / follow-up whose window isn't open yet (the press came too early): input it again,
			// like a player pressing it on time (a rekka follow-up, a dash cancel...)
			_netsuRetries++;
			currentInputIndex = 0;
			return;
		}
		if (currentCommand + 1 >= currentCommandList.Length)
		{
			return; // last action: hold the final input until the next decision
		}
		if (action.AutoAdvance || canAdvance)
		{
			NextAction();
		}
		else if (cameOut)
		{
			waitingLink = true; // the attack came out - wait for it to connect
			Dbg($"action {curr} out, waiting for contact");
		}
	}

	/// <summary>A throw: B+C on its first input (supers press B+C at the end of a motion).</summary>
	private static bool NetsuIsThrow(AIAction action)
	{
		if (action.Inputs == null || action.Inputs.Length == 0 || action.Inputs[0] == null)
		{
			return false;
		}
		ButtonInputs bc = ButtonInputs.FACE_B | ButtonInputs.FACE_C;
		return (action.Inputs[0].Buttons & bc) == bc;
	}

	/// <summary>The opponent has been off the ground (jumping, not juggled) long enough for it to notice.</summary>
	private bool NetsuOpponentInTheAir()
	{
		SakugaActor o = _owner.GetOpponent(0);
		return o != null && NetsuJumping(o) && _netsuOppAirFrames >= Reaction;
	}

	/// <summary>An action that should start a move (it presses something), unlike a wait.</summary>
	private static bool NetsuExpectsMove(AIAction action)
	{
		foreach (AIInput input in action.Inputs)
		{
			if (input != null && (input.Buttons != 0 || input.Direction != 0))
			{
				return true;
			}
		}
		return false;
	}

	private void NextAction()
	{
		_netsuRetries = 0;
		currentCommand++;
		currentInputIndex = 0;
		inputTick = 0;
		canAdvance = false;
		inputFinished = false;
		actionStarted = false;
		waitingLink = false;
	}

	private int VariableProbability(AICondition condition)
	{
		int prob = 0;
		switch (mode)
		{
		case BotMode.AGGRESSIVE:
			switch (condition.ActionMode)
			{
			case BotMode.AGGRESSIVE:
				prob++;
				break;
			case BotMode.DEFENSIVE:
				prob -= 2;
				break;
			}
			break;
		case BotMode.DEFENSIVE:
			switch (condition.ActionMode)
			{
			case BotMode.AGGRESSIVE:
				prob -= 2;
				break;
			case BotMode.DEFENSIVE:
				prob++;
				break;
			}
			break;
		}
		int result = condition.Probability + prob;
		if (result > 10)
		{
			result = 10;
		}
		else if (result < 0)
		{
			result = 0;
		}
		return result;
	}

	private bool CompareCommands(int[] c1, int[] c2)
	{
		if (c1 == null || c2 == null)
		{
			return false;
		}
		if (c1.Length == 0 || c2.Length == 0)
		{
			return false;
		}
		if (c1.Length != c2.Length)
		{
			return false;
		}
		for (int i = 0; i < c1.Length; i++)
		{
			if (c1[i] != c2[i])
			{
				return false;
			}
		}
		return true;
	}

	private PlayerInputs GenerateInput(AIInput input)
	{
		PlayerInputs result = PlayerInputs.NEUTRAL;
		bool isLeftSide = _owner.Body.IsLeftSide;
		PlayerInputs left = (isLeftSide ? PlayerInputs.LEFT : PlayerInputs.RIGHT);
		PlayerInputs right = (isLeftSide ? PlayerInputs.RIGHT : PlayerInputs.LEFT);
		if ((int)(input.Direction & DirectionalInputs.UP) > 0)
		{
			result |= PlayerInputs.UP;
		}
		if ((int)(input.Direction & DirectionalInputs.DOWN) > 0)
		{
			result |= PlayerInputs.DOWN;
		}
		if ((int)(input.Direction & DirectionalInputs.LEFT) > 0)
		{
			result |= left;
		}
		if ((int)(input.Direction & DirectionalInputs.RIGHT) > 0)
		{
			result |= right;
		}
		if ((int)(input.Buttons & ButtonInputs.FACE_A) > 0)
		{
			result |= PlayerInputs.FACE_A;
		}
		if ((int)(input.Buttons & ButtonInputs.FACE_B) > 0)
		{
			result |= PlayerInputs.FACE_B;
		}
		if ((int)(input.Buttons & ButtonInputs.FACE_C) > 0)
		{
			result |= PlayerInputs.FACE_C;
		}
		if ((int)(input.Buttons & ButtonInputs.FACE_D) > 0)
		{
			result |= PlayerInputs.FACE_D;
		}
		return result;
	}
}
