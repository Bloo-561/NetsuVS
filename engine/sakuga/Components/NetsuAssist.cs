using Godot;
using MessagePack;
using SakugaEngine.Game;
using SakugaEngine.GameState;
using SakugaEngine.Global;
using SakugaEngine.Resources;

namespace SakugaEngine;

/// <summary>
/// NETSU ASSISTS (Oct 2026): support characters in the style of Dengeki Bunko Fighting Climax.
///
/// Each player picks an assist on the character select (the list: data/assist_list.tres).
/// In the fight:
///   S          calls the assist's neutral move (5S)
///   6 + S      calls its forward move (6S); any left / right counts (7 4 1 9 6 3)
///   8 / 2 + S  calls 5S, but only during Overdrive (Oct 26 c6)
/// The assist is its own character (a SakugaActor with states, hitboxes and sprites in
/// actors/assists/NAME/) that does its move and leaves. A call from neutral on the ground makes
/// your fighter pose for a moment; a call in the middle of your own attacks is an Assist Cancel
/// (no pose, 1 bar). Since Oct 28 the Assist Cancel is the only way to call. See the rules below.
///
/// Rules (numbers per move in data/assist_list.tres -> NetsuAssistMove):
///  - the assist gauge must be full; it empties when you call, and refills (Cooldown frames)
///    only after the assist has left the screen. Full at the start of every round.
///  - Oct 28 (second pass): two ways to call, both on the ground only:
///      neutral (standing, walking, crouching, dashing, landing): FREE, the fighter poses;
///      Assist Cancel: during your own normal or special once it has hit or been blocked, AssistCancelCost (1 bar).
///    Never in the air, while jumping, while blocking or in hitstun, nor out of an EX move, super or throw.
///  - HOW you call depends on what your fighter is doing (Oct 24, from the Cecilia Duel prototype):
///      standing, walking, crouching, dashing, landing -> your fighter POSES while calling
///        (its "Assist Call" state, 30 frames: can't act or block), so a neutral
///        call isn't free pressure;
///      in the air or starting a jump -> no pose, free;
///      during your own attack -> ASSIST CANCEL: no pose, the assist comes at once, costs
///        AssistCancelCost Craft Gauge (1 bar since Oct 26; was 2). Not enough gauge = no call.
///  - you can't call while you are being hit, blocking, grabbed, frozen by the opponent's
///    super, during your own super (or an EX move's follow-up, like the EX Dash Slash rush),
///    or before the round starts.
///  - everyone has an assist: a missing or -1 pick becomes the first one in the list.
///  - assists can't be hit. Their attacks combo with yours; they are blocked by holding away
///    from the assist (so one that comes from behind you crosses up).
///  - Mary's 5S buff: NetsuAssistBuffAction (the buff and its timer live here).
///
/// This node holds the gauge and is saved for rollback (NetsuAssistState). GameManager adds it
/// to its node list right after the assist character, so it ticks, renders and saves with
/// everything else. The battle HUD reads it through MatchSetup.netsu_assist_hud().
/// </summary>
public partial class NetsuAssist : SakugaNode
{
	public const string ListPath = "res://data/assist_list.tres";

	public const int PhaseReady = 0;
	public const int PhaseOnScreen = 1;
	public const int PhaseCooldown = 2;

	/// <summary>An S press is remembered this many frames (pressed a little early, during hitstop...).</summary>
	public const int BufferFrames = 6;

	/// <summary>Assists never appear outside the stage walls (units).</summary>
	public const int SpawnLimitX = 112000;

	/// <summary>Craft Gauge an Assist Cancel costs (calling during your own attack): 1 of the 4 bars ("100%",
	/// Melty-style). Oct 26 (TamaDeez): was 2 bars (4000).</summary>
	public const int AssistCancelCost = 10000;   // Oct 29: units x5 (1 bar of 40,000)

	/// <summary>The fighter's state shown while calling from neutral on the ground (made by
	/// tools/sprite_port/assist_pose.py; found by this name in the fighter's state list).</summary>
	public const string CallPoseStateName = "Assist Call";

	/// <summary>How a call happens right now (CallMode).</summary>
	public const int CallNone = 0;
	public const int CallPose = 1;
	public const int CallFree = 2;
	public const int CallCancel = 3;
	/// <summary>Oct 26 evening (TamaDeez): called while blocking (in blockstun): like an Assist Cancel (no pose, a small
	/// flash, AssistCancelCost gauge), but no hit needed.</summary>
	public const int CallGuard = 4;

	public SakugaActor Fighter;
	public SakugaActor Actor;
	public NetsuAssistElement Element;
	public int Index;

	// --- match state (saved for rollback) ------------------------------------------------
	public int Gauge;
	public int GaugeMax = 1;

	/// <summary>Oct 28: Overdrive Link. LinkReady = the fighter's Overdrive gave a Link that hasn't been used yet;
	/// LinkCall = the assist now on screen was called with it: when it leaves, its cooldown starts half full.
	/// Saved for rollback (NetsuAssistState keys 16, 17).</summary>
	public bool LinkReady;
	public bool LinkCall;
	public const int LinkRefundPercent = 50;
	public int Phase;
	public int Buffer;
	public int BufferedMove = -1;
	public int OnScreen;
	public int BuffFrames;
	public int BuffTotal;
	public int BuffDamagePercent = 100;
	public int BuffGainPercent = 100;
	public int AIWait;
	public int LastMove = -1;
	public int Calls;

	// Netsu (Oct 26 late, TamaDeez): assists were coming out too fast. A call now waits a few frames before the assist
	// appears (it's paid for and the fighter poses at once). If the fighter is hit or grabbed while it waits, the call
	// is lost (the gauge starts refilling). Saved for rollback (NetsuAssistState keys 13 / 14).
	/// <summary>Frames between the S press and the assist appearing (neutral calls, poses).</summary>
	public const int NetsuCallDelay = 12;
	/// <summary>The same for an Assist Cancel or a call from blockstun (shorter, so cancels still combo).</summary>
	public const int NetsuCancelDelay = 6;
	public int PendingMove = -1;
	public int PendingFrames;

	private NetsuAssistState _state;

	// the "Assist Call" state's index in the fighter's list (-2 = not looked up yet, -1 = none);
	// read from the fighter's data, the same on every machine, so it isn't saved
	private int _poseState = -2;

	// --- presentation only (never part of the match state) -----------------------------
	private Node3D _auraRoot;
	private Sprite3D _aura;
	private Node _hud;
	private bool _hudChecked;

	/// <summary>Makes the assist for a fighter (called by GameManager.CreateFighter).
	/// index: position in data/assist_list.tres. Everyone gets one: -1 or an index past the end
	/// (an old setting) becomes the first assist.</summary>
	public static NetsuAssist Create(SakugaActor fighter, int index)
	{
		if (fighter == null || !ResourceLoader.Exists(ListPath))
		{
			return null;
		}
		NetsuAssistList list = GD.Load<NetsuAssistList>(ListPath);
		if (list == null || list.Assists == null || list.Assists.Length == 0)
		{
			return null;
		}
		if (index < 0 || index >= list.Assists.Length)
		{
			index = 0;
		}
		NetsuAssistElement element = list.Assists[index];
		if (element == null || element.Instance == null || element.Moves == null || element.Moves.Length == 0)
		{
			GD.PushWarning("Netsu assist " + index + " is missing its scene or moves.");
			return null;
		}
		Node node = element.Instance.Instantiate(PackedScene.GenEditState.Disabled);
		if (node is not SakugaActor actor)
		{
			node?.QueueFree();
			GD.PushWarning("Netsu assist " + element.AssistName + ": its scene is not a SakugaActor.");
			return null;
		}
		// Netsu (Oct 25): the Assists frame data spreadsheet (data/frame_data), before anything reads the data
		NetsuFrameData.ApplyAssist(element, actor.Data);
		actor.Name = fighter.playerID + "_Assist_" + element.AssistName;
		actor.Inputs = fighter.Inputs;
		actor.playerID = fighter.playerID;
		GameManager.Instance.AddActor(actor);
		actor.Initialize();
		actor.SetMaster(fighter);
		actor.SetAllies(fighter.GetAllies());
		actor.SetOpponents(fighter.GetOpponents());
		NetsuAssist assist = new NetsuAssist
		{
			Fighter = fighter,
			Actor = actor,
			Element = element,
			Index = index
		};
		assist.Name = fighter.playerID + "_AssistGauge";
		GameManager.Instance.AddActor(assist, isPhysicsBody: false);
		assist.ResetRound();
		return assist;
	}

	/// <summary>New round (and the start of the match): the assist leaves, the gauge is full.</summary>
	public void ResetRound()
	{
		if (Actor != null)
		{
			Actor.Reset();
			Park();
		}
		// Oct 27: the assist is NOT ready at the start of a round: its gauge starts empty and fills (StartingCooldown
		// frames) once the round is running
		Phase = PhaseCooldown;
		GaugeMax = Mathf.Max(1, Element != null ? Element.StartingCooldown : 1);
		Gauge = 0;
		LinkReady = false;   // Oct 28: an unused Overdrive Link ends with the round
		LinkCall = false;
		Buffer = 0;
		BufferedMove = -1;
		PendingMove = -1;
		PendingFrames = 0;
		OnScreen = 0;
		BuffFrames = 0;
		BuffTotal = 0;
		BuffDamagePercent = 100;
		BuffGainPercent = 100;
		AIWait = 90;
		LastMove = -1;
	}

	/// <summary>The opponent started a super: the assist on screen stops for the flash too.</summary>
	public void Freeze(uint frames)
	{
		if (Actor != null && Actor.IsActive && Actor.Hitstop != null && Actor.Hitstop.TimeLeft < frames)
		{
			Actor.Hitstop.Start(frames);
		}
	}

	// --- buffs (Mary's 5S) ---------------------------------------------------------------

	/// <summary>Called by NetsuAssistBuffAction from the assist's state.</summary>
	public void StartBuff(int frames, int damagePercent, int gainPercent)
	{
		BuffTotal = Mathf.Max(1, frames);
		BuffFrames = BuffTotal;
		BuffDamagePercent = damagePercent;
		BuffGainPercent = gainPercent;
	}

	public bool BuffActive => BuffFrames > 0;

	/// <summary>Damage the fighter deals while buffed (SakugaParameters.OverdriveDamage).</summary>
	public int BuffDamage(int damage)
	{
		return BuffFrames > 0 ? damage * BuffDamagePercent / 100 : damage;
	}

	/// <summary>Craft Gauge the fighter gains while buffed.</summary>
	public int BuffGain(int gain)
	{
		return BuffFrames > 0 ? gain * BuffGainPercent / 100 : gain;
	}

	// --- every frame ---------------------------------------------------------------------

	public override void Tick()
	{
		if (Fighter == null || Actor == null || Element == null)
		{
			return;
		}
		GameManager gm = GameManager.Instance;
		bool frozen = Fighter.SuperFlashing;   // the opponent's super flash stops our timers too
		if (PendingMove >= 0)
		{
			StateType ft = Fighter.StateManager.CurrentStateType();
			if (ft == StateType.HIT_REACTION || Fighter.IsGrabbed() || Fighter.IsKO())
			{
				PendingMove = -1;   // hit before the assist came: the call is lost
				Leave();
			}
			else if (!frozen && !Fighter.OnHitstop() && --PendingFrames <= 0)
			{
				int m = PendingMove;
				PendingMove = -1;
				Spawn(m);
			}
		}
		else if (Phase == PhaseOnScreen)
		{
			OnScreen++;
			// Oct 27: the assist goes away when its partner is hit or grabbed (unless the move says it stays), or when
			// the assist itself is hit
			bool partnerHit = Fighter.StateManager.CurrentStateType() == StateType.HIT_REACTION || Fighter.IsGrabbed() || Fighter.IsKO();
			bool stays = LastMove >= 0 && LastMove < Element.Moves.Length && Element.Moves[LastMove] != null && Element.Moves[LastMove].StayWhenPartnerHit;
			bool assistHit = Actor.HitstunType != HitstunType.NONE && Actor.HitstunType != HitstunType.GRABBED;
			if (!Actor.IsActive || OnScreen > Mathf.Max(60, Element.MaxOnScreen) || (partnerHit && !stays) || assistHit)
			{
				Leave();
			}
		}
		else if (Phase == PhaseCooldown && !frozen && gm != null && gm.Monitor != null && gm.Monitor.MatchState == MatchState.ROUND_RUNNING)
		{
			Gauge++;
			bool instant = gm != null && (gm.Training != null ? gm.Training.AssistRefillsAtOnce
				: gm.Match != null && gm.Match.SelectedModeSettings.AutoFillResources);
			if (instant)
			{
				Gauge = GaugeMax;   // training: refills as soon as the assist has left (Training Menu: Assist Gauge)
			}
			if (Gauge >= GaugeMax)
			{
				Gauge = GaugeMax;
				Phase = PhaseReady;
				AIWait = 30 + RandomTo(120);
			}
		}
		if (BuffFrames > 0 && !frozen && gm != null && gm.Monitor.MatchState == MatchState.ROUND_RUNNING)
		{
			BuffFrames--;
		}
		if (Fighter.UseAI)
		{
			ThinkAI();
		}
		else
		{
			ReadInput();
		}
		if (Fighter != null && Fighter.Parameters != null && Fighter.Parameters.NetsuOverdriveLinkPending)
		{
			Fighter.Parameters.NetsuOverdriveLinkPending = false;   // Oct 28: Overdrive started: one Link
			LinkReady = true;
		}
		if (Buffer > 0)
		{
			if (CanCall())
			{
				Call(BufferedMove);
			}
			else
			{
				Buffer--;
			}
		}
	}

	/// <summary>True when the fighter is allowed to call right now.</summary>
	public bool CanCall()
	{
		if (Phase != PhaseReady || Element.Moves == null || Element.Moves.Length == 0)
		{
			return false;
		}
		GameManager gm = GameManager.Instance;
		if (gm == null || gm.Monitor == null || gm.Monitor.MatchState != MatchState.ROUND_RUNNING)
		{
			return false;
		}
		if (Fighter.IsKO() || Fighter.SuperFlashing || Fighter.CinematicState || Fighter.HitstunType == HitstunType.GRABBED)
		{
			return false;
		}
		SakugaActor opponent = Fighter.GetOpponent(0);
		if (opponent != null && opponent.SuperFlashing)
		{
			return false;   // not while your own EX / super flash has the opponent frozen
		}
		StateType type = Fighter.StateManager.CurrentStateType();
		if (type == StateType.HIT_REACTION || type == StateType.LOCKED)
		{
			return false;
		}
		// Oct 28: no calls while blocking any more (the guard call is gone); only Assist Cancels, see below
		if (type == StateType.BLOCKING || Fighter.OnHitstun() || InSuper())
		{
			return false;
		}
		if (Fighter.Body == null || !Fighter.Body.IsOnGround)
		{
			return false;   // Oct 28 (TamaDeez): never in the air (the Overdrive exception is gone with the old Overdrive)
		}
		int mode = CallMode();
		if (mode == CallPose)
		{
			return true;   // Oct 28 (TamaDeez): a neutral call on the ground is allowed again, and free (she poses)
		}
		if ((mode == CallCancel || mode == CallGuard) && (Fighter.Parameters == null || Fighter.Parameters.SuperGauge.CurrentValue < AssistCancelCost))
		{
			return false;   // an Assist Cancel (or a call from blockstun) needs the gauge
		}
		if (mode != CallCancel)
		{
			return false;   // Oct 28: otherwise only as an Assist Cancel (no call while blocking, jumping or in the air)
		}
		if ((Fighter.CancelConditions & (CancelCondition.HIT_CANCEL | CancelCondition.BLOCK_CANCEL)) == 0)
		{
			return false;   // Oct 28: once the attack has hit or been blocked (was: hit only)
		}
		return NetsuCancellableMove();
	}

	/// <summary>Oct 28: an Assist Cancel only comes out of a normal (Priority 6) or a special (Priority 7-8) that costs no
	/// gauge: not EX moves, supers, Pushblock, Burst / Overdrive or throws.</summary>
	private bool NetsuCancellableMove()
	{
		StanceManager stance = Fighter.StanceManager;
		MoveSettings move = stance != null && stance.CurrentMove >= 0 ? stance.GetCurrentMove() : null;
		if (move == null || move.SuperGaugeRequired > 0 || move.WillGaugeRequired > 0)
		{
			return false;
		}
		if (move.MoveName == "Throw" || move.MoveName == "Air Throw")
		{
			return false;
		}
		return move.Priority >= 6 && move.Priority <= 8;
	}

	/// <summary>True during the fighter's super (3 bars) and during an EX move's follow-up states
	/// (the EX Dash Slash rush...): no assists there.</summary>
	private bool InSuper()
	{
		StanceManager stance = Fighter.StanceManager;
		if (stance == null || stance.CurrentMove < 0)
		{
			return false;
		}
		MoveSettings move = stance.GetCurrentMove();
		if (move == null)
		{
			return false;
		}
		if (move.SuperGaugeRequired >= StanceManager.NetsuSuperCost)
		{
			return true;
		}
		return StanceManager.NetsuIsExMove(move) && Fighter.StateManager.CurrentState != move.MoveState;
	}

	/// <summary>How a call would happen right now: CallPose (standing, walking, crouching, dashing,
	/// landing), CallFree (in the air, starting a jump), CallCancel (during an attack).</summary>
	public int CallMode()
	{
		if (Fighter.StateManager.CurrentState == PoseState())
		{
			return CallNone;   // already posing
		}
		if (Fighter.StateManager.CurrentStateType() == StateType.COMBAT)
		{
			return CallCancel;
		}
		if (Fighter.StateManager.CurrentStateType() == StateType.BLOCKING)
		{
			return CallGuard;   // Oct 26 evening: from blockstun
		}
		if (Fighter.Body == null || !Fighter.Body.IsOnGround)
		{
			return CallFree;
		}
		string name = Fighter.StateManager.GetCurrentState()?.StateName ?? "";
		if (name.Contains("Jump"))
		{
			return CallFree;   // jump start: she's leaving the ground anyway
		}
		return CallPose;
	}

	/// <summary>Index of the fighter's "Assist Call" state, -1 if it has none (then neutral calls don't pose).</summary>
	public int PoseState()
	{
		if (_poseState == -2)
		{
			_poseState = -1;
			FighterState[] states = Fighter.Data?.States;
			for (int i = 0; states != null && i < states.Length; i++)
			{
				if (states[i] != null && states[i].StateName == CallPoseStateName)
				{
					_poseState = i;
					break;
				}
			}
		}
		return _poseState;
	}

	private void ReadInput()
	{
		InputManager input = Fighter.Inputs;
		if (input == null || input.InputHistory == null || !input.WasPressed(input.CurrentHistory, PlayerInputs.FACE_D))
		{
			return;
		}
		// Netsu (Oct 26 c6, TamaDeez): 6S = S with any left / right in it (7, 4, 1, 9, 6, 3), whichever way she faces.
		// 5S = S with no direction (5). Up or down alone (8, 2) also call 5S, but only during Overdrive (outside it,
		// 8 + S / 2 + S call nothing, so a jump or crouch with S pressed doesn't throw the assist out).
		int dir = 0;
		bool horizontal = input.IsBeingPressed(input.CurrentHistory, PlayerInputs.LEFT) || input.IsBeingPressed(input.CurrentHistory, PlayerInputs.RIGHT);
		bool vertical = input.IsBeingPressed(input.CurrentHistory, PlayerInputs.UP) || input.IsBeingPressed(input.CurrentHistory, PlayerInputs.DOWN);
		if (horizontal)
		{
			dir = 1;
		}
		else if (vertical)
		{
			return;   // Oct 28: 8 + S / 2 + S call nothing (the Overdrive exception is gone)
		}
		BufferedMove = PickMove(dir);
		Buffer = BufferFrames;
	}

	/// <summary>The move for a direction (0 neutral, 1 forward, 2 back); falls back to the neutral one.</summary>
	public int PickMove(int direction)
	{
		int neutral = -1;
		for (int i = 0; i < Element.Moves.Length; i++)
		{
			if (Element.Moves[i] == null)
			{
				continue;
			}
			if (Element.Moves[i].Direction == direction)
			{
				return i;
			}
			if (neutral < 0 && Element.Moves[i].Direction == 0)
			{
				neutral = i;
			}
		}
		return neutral >= 0 ? neutral : 0;
	}

	/// <summary>Sends the assist in.</summary>
	private void Call(int moveIndex)
	{
		Buffer = 0;
		if (moveIndex < 0 || moveIndex >= Element.Moves.Length || Element.Moves[moveIndex] == null)
		{
			return;
		}
		NetsuAssistMove move = Element.Moves[moveIndex];
		if (Actor.Data == null || Actor.Data.States == null || move.StateIndex < 0 || move.StateIndex >= Actor.Data.States.Length)
		{
			GD.PushWarning("Netsu assist " + Element.AssistName + ": move " + move.MoveName + " points at a state that doesn't exist.");
			return;
		}
		int mode = CallMode();
		if (mode == CallCancel || mode == CallGuard)
		{
			// Assist Cancel: the gauge pays, the fighter keeps attacking, a small flash shows it
			Fighter.Parameters.NetsuSpendMeter(AssistCancelCost);   // Oct 29: spending starts the meter cooldown
			NetsuFlash();
		}
		else if (mode == CallPose && PoseState() >= 0)
		{
			// a neutral call on the ground: the fighter stops and poses while the assist comes in
			Fighter.StanceManager?.NetsuDropMove();
			if (Fighter.Knockback != null)
			{
				Fighter.Knockback.Stop();
			}
			Fighter.Body.SetVelocity(Vector2I.Zero);
			Fighter.StateManager.PlayState(PoseState(), reset: true);
		}
		// paid for now; the assist itself comes after the delay (Tick -> Spawn)
		if (LinkReady)
		{
			LinkReady = false;   // Oct 28: this call uses the Overdrive Link
			LinkCall = true;
		}
		Phase = PhaseOnScreen;
		Gauge = 0;
		GaugeMax = Mathf.Max(1, move.Cooldown);
		OnScreen = 0;
		LastMove = moveIndex;
		Calls++;
		PendingMove = moveIndex;
		PendingFrames = (mode == CallCancel || mode == CallGuard) ? NetsuCancelDelay : NetsuCallDelay;
		PendingSide = Fighter.Body.PlayerSide;   // Oct 27 c29: the way the fighter faces when S is pressed
	}

	/// <summary>Oct 27 c29: the fighter's facing at the moment of the call (1 / -1). A NetsuFaceCaller move (Mary's 6S)
	/// faces and appears that way, even if the fighter turns during the call delay. Saved for rollback (key 15).</summary>
	public int PendingSide = 1;

	/// <summary>The assist appears (after the call delay).</summary>
	private void Spawn(int moveIndex)
	{
		NetsuAssistMove move = Element.Moves[moveIndex];
		int side = move.NetsuFaceCaller ? (PendingSide >= 0 ? 1 : -1) : Fighter.Body.PlayerSide;   // Oct 27 c29: facing at the call
		int x = Mathf.Clamp(Fighter.Body.FixedPosition.X + move.SpawnOffset.X * side, -SpawnLimitX, SpawnLimitX);
		int y = move.OnGround ? move.SpawnOffset.Y : Fighter.Body.FixedPosition.Y + move.SpawnOffset.Y;
		Actor.IsActive = true;
		Actor.HitstunType = HitstunType.NONE;
		Actor.BlockStun = false;
		Actor.FrameProperties = Actor.InitialProperties;
		Actor.HitCheck = Actor.AllowHit;
		Actor.LayerSorting = 1;
		if (Actor.Hitstop != null)
		{
			Actor.Hitstop.Stop();
		}
		if (Actor.Knockback != null)
		{
			Actor.Knockback.Stop();
		}
		Actor.Body.SetVelocity(Vector2I.Zero);
		Actor.Body.CurrentGravity = 260000;
		Actor.Body.IsMovable = true;
		// Oct 26 evening: a move marked NetsuFaceCaller (Mary's 6S) faces the way the fighter faces, not toward the
		// opponent (after a cross-up the two differ, and her note flew the wrong way)
		Actor.Body.UpdateSide(move.NetsuFaceCaller ? side > 0 : Fighter.Body.IsLeftSide);
		Actor.Body.FlipSide();
		Actor.Body.MoveTo(new Vector2I(x, Mathf.Max(0, y)));
		Actor.StateManager.PlayState(move.StateIndex, reset: true);
		Actor.StateManager.CurrentStateFrame = -1;
		OnScreen = 0;
	}

	/// <summary>Presentation only: the small flash on the fighter for an Assist Cancel
	/// (MatchSetup -> game/ui/battle_hud/netsu_super_flash.gd, which ignores repeats from rollback).</summary>
	private void NetsuFlash()
	{
		if (Engine.GetMainLoop() is not SceneTree tree)
		{
			return;
		}
		Node setup = tree.Root.GetNodeOrNull("MatchSetup");
		if (setup == null || !setup.HasMethod("netsu_super_flash"))
		{
			return;
		}
		Vector3 pos = GlobalFunctions.ToScaledVector3(Fighter.Body.FixedPosition + new Vector2I(0, SakugaActor.NetsuChestHeight));
		setup.Call("netsu_super_flash", (int)Fighter.playerID, pos, -1, 8);
	}

	/// <summary>The assist has finished (its last state switched it off) or stayed too long.</summary>
	private void Leave()
	{
		Park();
		Phase = PhaseCooldown;
		Gauge = 0;
		OnScreen = 0;
		if (LinkCall)
		{
			Gauge = GaugeMax * LinkRefundPercent / 100;   // Oct 28: Overdrive Link: half the cooldown back
			LinkCall = false;
		}
	}

	/// <summary>Hidden and harmless: state 0 (no boxes), not moving.</summary>
	private void Park()
	{
		Actor.IsActive = false;
		Actor.StateManager.CurrentState = 0;
		Actor.StateManager.CurrentStateFrame = 0;
		Actor.Body.SetVelocity(Vector2I.Zero);
		Actor.Body.ResetHits();
		Actor.Body.UpdateColliders();
		if (Actor.Hitstop != null)
		{
			Actor.Hitstop.Stop();
		}
	}

	// --- CPU -----------------------------------------------------------------------------

	private static int RandomTo(int max)
	{
		return max <= 0 || RNG.random == null ? 0 : RNG.Next(0, max);
	}

	/// <summary>The CPU calls its assist now and then when the opponent is in a move's AIRange,
	/// and much more often in the middle of a combo.</summary>
	private void ThinkAI()
	{
		if (Phase != PhaseReady || Buffer > 0)
		{
			return;
		}
		if (AIWait > 0)
		{
			AIWait--;
			return;
		}
		if (!CanCall())
		{
			return;
		}
		if (CallMode() == CallCancel && Fighter.Parameters.SuperGauge.CurrentValue < AssistCancelCost + 2 * StanceManager.NetsuBarSize)
		{
			AIWait = 30;   // the CPU only pays for an Assist Cancel when it still has 2 bars left after it
			return;
		}
		SakugaActor opponent = Fighter.GetOpponent(0);
		if (opponent == null)
		{
			return;
		}
		int distance = Mathf.Abs(opponent.Body.FixedPosition.X - Fighter.Body.FixedPosition.X);
		int pick = -1;
		int found = 0;
		for (int i = 0; i < Element.Moves.Length; i++)
		{
			NetsuAssistMove move = Element.Moves[i];
			if (move == null || distance < move.AIRange.X || distance > move.AIRange.Y)
			{
				continue;
			}
			found++;
			if (RandomTo(found) == 0)
			{
				pick = i;
			}
		}
		if (pick < 0)
		{
			AIWait = 20;
			return;
		}
		bool comboing = opponent.OnHitstun() && !opponent.BlockStun && opponent.StateManager.CurrentStateType() == StateType.HIT_REACTION;
		// Netsu (Oct 24 night): how keen the CPU is depends on its difficulty (AIBehavior.AssistRate, 5 = 10% / 50%)
		int rate = Fighter.Brain?.Behavior?.AssistRate ?? 5;
		if (RandomTo(100) < (comboing ? rate * 10 : rate * 2))
		{
			BufferedMove = pick;
			Buffer = 1;
		}
		else
		{
			AIWait = 15 + RandomTo(45);
		}
	}

	// --- rollback --------------------------------------------------------------------------

	public override byte[] GetStateData()
	{
		_state.GetStateData(this);
		return MessagePackSerializer.Serialize(_state);
	}

	public override void SetStateData(byte[] stateBuffer)
	{
		_state = MessagePackSerializer.Deserialize<NetsuAssistState>(stateBuffer);
		_state.SetStateData(this);
	}

	// --- presentation ----------------------------------------------------------------------

	public override void Render()
	{
		if (Fighter == null || Element == null)
		{
			return;
		}
		RenderBuff();
		PushHud();
	}

	private static readonly StringName NetsuHudMethod = new StringName("netsu_assist_hud");
	private float _hudRatio = -1f, _hudBuff = -1f;
	private int _hudPhase = int.MinValue;
	private int _hudQuiet;
	private string _hudName;
	private Texture2D _hudIcon;

	/// <summary>The gauge for the battle HUD (game/ui/battle_hud/netsu_hud.gd), through MatchSetup. Oct 25: only
	/// when something changed (a call every frame was garbage for the collector: its pauses were hitches).</summary>
	private void PushHud()
	{
		if (!_hudChecked)
		{
			_hudChecked = true;
			_hud = (Engine.GetMainLoop() as SceneTree)?.Root.GetNodeOrNull("MatchSetup");
			if (_hud != null && !_hud.HasMethod(NetsuHudMethod))
			{
				_hud = null;
			}
		}
		if (_hud == null)
		{
			return;
		}
		float ratio = Phase == PhaseReady ? 1f : (Phase == PhaseOnScreen ? 0f : (float)Gauge / Mathf.Max(1, GaugeMax));
		float buff = BuffFrames > 0 ? (float)BuffFrames / Mathf.Max(1, BuffTotal) : 0f;
		// (and every 15 renders anyway: the HUD hides the row when it hasn't heard from the assist for 0.6 s)
		_hudQuiet++;
		if (_hudQuiet < 15 && ratio == _hudRatio && buff == _hudBuff && Phase == _hudPhase && Element.AssistName == _hudName && Element.Icon == _hudIcon)
		{
			return;
		}
		_hudQuiet = 0;
		_hudRatio = ratio;
		_hudBuff = buff;
		_hudPhase = Phase;
		_hudName = Element.AssistName;
		_hudIcon = Element.Icon;
		_hud.Call(NetsuHudMethod, (int)Fighter.playerID, Element.AssistName, ratio, Phase, buff, Element.Icon);
	}

	/// <summary>A buffed fighter wears the assist's aura (Mary's music) until the buff runs out.</summary>
	private void RenderBuff()
	{
		if (Element.BuffAura == null || Element.BuffAura.Length == 0)
		{
			return;
		}
		if (_auraRoot == null)
		{
			_auraRoot = new Node3D { Name = "BuffAura" };
			_aura = new Sprite3D
			{
				Centered = false,
				PixelSize = Element.BuffAuraPixelSize,
				TextureFilter = BaseMaterial3D.TextureFilterEnum.LinearWithMipmaps,
				Layers = 2,
				Shaded = false,
				Visible = false
			};
			_auraRoot.AddChild(_aura);
			AddChild(_auraRoot);
		}
		bool on = BuffFrames > 0 && Fighter.IsActive;
		_aura.Visible = on;
		if (!on)
		{
			return;
		}
		int t = BuffTotal - BuffFrames;
		Texture2D tex = Element.BuffAura[(t / Mathf.Max(1, Element.BuffAuraFrameTime)) % Element.BuffAura.Length];
		if (t < 12 && Element.BuffPulse != null)
		{
			tex = Element.BuffPulse;
		}
		_aura.Texture = tex;
		_aura.Offset = Element.BuffAuraOffset;
		float fade = Mathf.Min(1f, BuffFrames / 30f) * Mathf.Min(1f, (t + 4) / 8f);
		_aura.Modulate = new Color(Element.BuffAuraTint.R, Element.BuffAuraTint.G, Element.BuffAuraTint.B, Element.BuffAuraTint.A * fade);
		_aura.SortingOffset = 3f;
		_auraRoot.GlobalPosition = GlobalFunctions.ToScaledVector3(Fighter.Body.FixedPosition);
		_auraRoot.Scale = new Vector3(Fighter.Body.PlayerSide, 1f, 1f);
	}
}
