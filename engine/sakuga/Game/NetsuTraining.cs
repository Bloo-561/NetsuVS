using System.Collections.Generic;
using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Game;

/// <summary>
/// Netsu (Oct 24 2026): Training mode. What the dummy (player 2's fighter) does on its own, how the
/// health and gauges behave, and the in-fight tools (reset position, record and play back the dummy).
///
/// GameManager makes one for the "Training" mode and calls it every frame from GameLoop:
///   PreFrame  - runs the queued commands, then writes the dummy's input for this frame
///               (stance, recoveries, wake-up action, recording / playback, CPU on or off);
///   PostFrame - health and gauge settings (replaces the mode's AutoFillResources).
/// StanceManager.GetBlockState asks ForcedGuard (the Guard setting) and SakugaActor.IsCounter asks
/// ForceCounter (Counter Hit setting).
///
/// The settings come from the Training Menu (game/ui/training/netsu_training_menu.gd, stored in
/// GameSettings' "training" section) through GameManager.NetsuSetTraining(dictionary); the shortcuts
/// (reset, record, play) arrive through GameManager.NetsuTrainingCommand(name, value).
/// Inputs the dummy records and plays are stored facing right (forward / back), so a recording works
/// from either side of the screen.
/// </summary>
public class NetsuTraining
{
	/// <summary>Player index of the dummy.</summary>
	public const int Dummy = 1;

	// "dummy": what the dummy does when nobody controls it
	public const int ActStand = 0, ActCrouch = 1, ActJump = 2, ActCpu = 3, ActPlayback = 4;
	// "guard"
	public const int GuardNone = 0, GuardAll = 1, GuardAfterFirst = 2, GuardRandom = 3;
	// "air_recovery" (recovering while knocked into the air)
	public const int AirOff = 0, AirNeutral = 1, AirForward = 2, AirRandom = 3;
	// "wakeup" (recovering on the ground after a knockdown)
	public const int WakeStayDown = 0, WakeNeutral = 1, WakeForward = 2, WakeBack = 3, WakeRandom = 4;
	// "wakeup_action" (done on the first frame the dummy can act after getting up)
	public const int WakeActNone = 0, WakeActJump = 1, WakeActBackJump = 2, WakeActBackdash = 3, WakeActLight = 4,
		WakeActCrouchLight = 5, WakeActAssist = 6, WakeActBurst = 7, WakeActRecording = 8;

	/// <summary>Reset modes (NetsuTrainingCommand("reset", mode)).</summary>
	public const int ResetCenter = 0, ResetLeftCorner = 1, ResetRightCorner = 2, ResetSwap = 3,
		ResetPlayerLeftCorner = 4, ResetPlayerRightCorner = 5;

	/// <summary>Longest recording: 20 seconds.</summary>
	public const int MaxRecording = 60 * 20;

	// --- settings -----------------------------------------------------------------------
	public int Action;
	public int Guard;
	public bool CounterHit;
	public int AirRecovery;
	public int Wakeup;
	public int WakeupAction;
	public int CpuLevel = 2;
	/// <summary>Health each side goes back to once a combo is over, in % (0 = it doesn't refill).</summary>
	public readonly int[] Health = { 100, 100 };
	/// <summary>Craft Gauge: -1 always full, -2 works as in a match, 0-4 = back to that many bars after a combo (2000 each).</summary>
	public readonly int[] Craft = { -1, -1 };
	/// <summary>Burst gauge: -1 always full, -2 works as in a match.</summary>
	public readonly int[] Burst = { -1, -1 };
	/// <summary>The assist gauge refills the moment the assist has left.</summary>
	public bool AssistInstant = true;
	/// <summary>Playback started with the shortcut repeats until stopped.</summary>
	public bool PlaybackRepeat;

	// --- recording ----------------------------------------------------------------------
	private readonly List<ushort> _tape = new List<ushort>();
	public bool Recording { get; private set; }
	public bool Playing { get; private set; }
	private int _playIndex;
	private bool _playOnce;

	// --- dummy state --------------------------------------------------------------------
	private readonly Queue<KeyValuePair<string, int>> _commands = new Queue<KeyValuePair<string, int>>();
	private bool _dummyHuman;
	private bool _loopStopped;     // Dummy Action "Playback": the play shortcut stopped the loop
	private bool _guardArmed;      // "after first hit": hit once, so it guards from now on
	private int _randomGuard = -1; // "random": this attack string is guarded (1) or not (0)
	private int _calm;             // frames the dummy has been free (not hit, not guarding)
	private bool _down;            // knocked down: wake-up action pending
	private int _airChoice = -1;   // recovery picked for this juggle / knockdown ("random")
	private int _wakeChoice = -1;
	private int _wakeFrames;       // free frames left to input the wake-up action
	private bool _waitWake;        // wake-up action "recording": waiting for the first free frame
	private int _wakeStep;
	private int _wakeMoves;        // the dummy's move count when the wake-up action started
	private int _tick;
	private int _cpuLevel = -1;
	private readonly int[] _free = { 0, 0 };   // frames each side has been out of a combo (health / bars refill)

	private const PlayerInputs Forward = PlayerInputs.RIGHT;   // stored facing right
	private const PlayerInputs Back = PlayerInputs.LEFT;
	private const int RefillDelay = 40;   // frames out of a combo before health / set bars come back

	// --- from the menus ---------------------------------------------------------------

	/// <summary>The Training Menu's settings (GameSettings "training" keys). Missing keys keep their value.</summary>
	public void Apply(Godot.Collections.Dictionary o)
	{
		int oldAction = Action;
		Action = Get(o, "dummy", Action);
		if (Action != oldAction)
		{
			_loopStopped = false;
		}
		Guard = Get(o, "guard", Guard);
		CounterHit = Get(o, "counter_hit", CounterHit ? 1 : 0) != 0;
		AirRecovery = Get(o, "air_recovery", AirRecovery);
		Wakeup = Get(o, "wakeup", Wakeup);
		WakeupAction = Get(o, "wakeup_action", WakeupAction);
		CpuLevel = Mathf.Clamp(Get(o, "cpu_level", CpuLevel), 0, 5);
		Health[0] = Get(o, "p1_health", Health[0]);
		Health[1] = Get(o, "p2_health", Health[1]);
		Craft[0] = Get(o, "p1_craft", Craft[0]);
		Craft[1] = Get(o, "p2_craft", Craft[1]);
		Burst[0] = Get(o, "p1_burst", Burst[0]);
		Burst[1] = Get(o, "p2_burst", Burst[1]);
		AssistInstant = Get(o, "assist_instant", AssistInstant ? 1 : 0) != 0;
		PlaybackRepeat = Get(o, "playback_repeat", PlaybackRepeat ? 1 : 0) != 0;
		_guardArmed = false;
		_randomGuard = -1;
	}

	private static int Get(Godot.Collections.Dictionary o, string key, int fallback)
	{
		if (o == null || !o.ContainsKey(key))
		{
			return fallback;
		}
		Variant v = o[key];
		switch (v.VariantType)
		{
		case Variant.Type.Bool:
			return v.AsBool() ? 1 : 0;
		case Variant.Type.Int:
			return v.AsInt32();
		case Variant.Type.Float:
			return Mathf.RoundToInt(v.AsSingle());
		default:
			return fallback;
		}
	}

	/// <summary>"reset" (mode), "record" / "play" (the shortcuts: start or stop), "record_start" / "play_start"
	/// (the Training Menu: always start) wait for the next frame; "stop" and "clear" happen at once (the
	/// Training Menu shows the result while the fight is paused).</summary>
	public void Command(string name, int value)
	{
		if (name == "stop" || name == "clear")
		{
			Run(null, null, name, value);
			return;
		}
		_commands.Enqueue(new KeyValuePair<string, int>(name, value));
	}

	/// <summary>Dummy Action "Playback" with a recording: the dummy repeats it (the play shortcut stops it).</summary>
	private bool Looping => Action == ActPlayback && _tape.Count > 0 && !_loopStopped && !_dummyHuman;

	private Godot.Collections.Dictionary _status;
	// the keys as Variants made once (a string key becomes a new Variant, with its own clean-up object, on every set)
	private static readonly Variant KRecording = "recording", KPlaying = "playing", KFrames = "frames", KIndex = "index",
		KMax = "max", KCpu = "cpu", KHuman = "human";

	/// <summary>For the training HUD: recording / playback state and lengths in frames. Oct 25: one dictionary,
	/// updated in place (the HUD asks every frame; a new one each time was garbage for the collector).</summary>
	public Godot.Collections.Dictionary Status()
	{
		_status ??= new Godot.Collections.Dictionary();
		_status[KRecording] = Recording;
		_status[KPlaying] = Playing || (Looping && !Recording);
		_status[KFrames] = _tape.Count;
		_status[KIndex] = _playIndex;
		_status[KMax] = MaxRecording;
		_status[KCpu] = Action == ActCpu;
		_status[KHuman] = _dummyHuman;
		return _status;
	}

	// --- every frame --------------------------------------------------------------------

	/// <summary>Before inputs go into the input history. `input` holds both players' raw inputs and
	/// can be rewritten: the dummy's comes from here unless a person controls player 2 (dummyHuman).</summary>
	public void PreFrame(GameManager gm, SakugaActor[] f, PlayerInputs[] input, bool dummyHuman)
	{
		_tick++;
		_dummyHuman = dummyHuman;
		while (_commands.Count > 0)
		{
			KeyValuePair<string, int> c = _commands.Dequeue();
			Run(gm, f, c.Key, c.Value);
		}
		SakugaActor d = f[Dummy];
		bool cpu = Action == ActCpu && !Recording && !Playing && !dummyHuman;
		if (cpu != d.UseAI || (cpu && CpuLevel != _cpuLevel))
		{
			d.InitializeBrain(cpu, (BotDifficulty)CpuLevel);
			_cpuLevel = CpuLevel;
		}
		if (dummyHuman)
		{
			// a second player controls the dummy: no recording or playback
			Recording = false;
			Playing = false;
			_waitWake = false;
			return;
		}
		if (Recording)
		{
			// player 1 controls the dummy; player 1's own fighter stands still
			if (_tape.Count < MaxRecording)
			{
				_tape.Add(ToStored(input[0], d));
			}
			else
			{
				Recording = false;
			}
			input[Dummy] = input[0];
			input[0] = PlayerInputs.NEUTRAL;
			return;
		}
		if (cpu)
		{
			return;
		}
		if (Playing || Looping)
		{
			input[Dummy] = PlayStep(d);
			return;
		}
		input[Dummy] = DummyInput(d);
	}

	/// <summary>After the frame: health, gauges, and the guard settings' bookkeeping.</summary>
	public void PostFrame(SakugaActor[] f)
	{
		SakugaActor d = f[Dummy];
		StateType dt = d.StateManager.CurrentStateType();
		if (dt == StateType.HIT_REACTION)
		{
			_guardArmed = true;
			_calm = 0;
		}
		else if (dt == StateType.BLOCKING)
		{
			_calm = 0;
		}
		else if (++_calm > 30)
		{
			_guardArmed = false;   // left alone for half a second: the next string starts fresh
			_randomGuard = -1;
		}
		// frames each side has been out of hitstun / blockstun; health and set bars come back once
		// BOTH have been for RefillDelay frames (the attacker is never in hitstun during a combo)
		for (int i = 0; i < f.Length && i < 2; i++)
		{
			SakugaActor a = f[i];
			if (a == null || a.StateManager == null)
			{
				_free[i] = 0;
				continue;
			}
			StateType t = a.StateManager.CurrentStateType();
			bool inCombo = a.OnHitstun() || t == StateType.HIT_REACTION || t == StateType.BLOCKING;
			_free[i] = inCombo ? 0 : Mathf.Min(_free[i] + 1, 1000000);
		}
		bool calm = Mathf.Min(_free[0], _free[1]) >= RefillDelay;
		for (int i = 0; i < f.Length && i < 2; i++)
		{
			SakugaActor a = f[i];
			if (a == null || a.Parameters == null || a.StateManager == null)
			{
				continue;
			}
			bool idle = a.StateManager.CurrentStateType() <= StateType.MOVEMENT;
			// nobody is knocked out in Training
			if (a.Parameters.Health.CurrentValue < 0)
			{
				a.Parameters.Health.CurrentValue = 1;
			}
			if (Health[i] > 0 && calm)
			{
				a.Parameters.Health.CurrentValue = Mathf.Max(1, a.Data.MaxHealth * Mathf.Clamp(Health[i], 1, 100) / 100);
			}
			int maxCraft = a.Data.MaxSuperGauge;
			if (Craft[i] == -1 && idle)
			{
				a.Parameters.SuperGauge.CurrentValue = maxCraft;
			}
			else if (Craft[i] >= 0 && calm && idle)
			{
				a.Parameters.SuperGauge.CurrentValue = Mathf.Clamp(StanceManager.NetsuBarSize * Craft[i], 0, maxCraft);   // Oct 28: 2000 a bar (was a sixth of the gauge)
			}
			if (Burst[i] == -1 && idle && a.Parameters.Will.State == WillState.WORKING)
			{
				a.Parameters.Will.CurrentValue = a.Data.MaxWill;
			}
		}
	}

	/// <summary>StanceManager.GetBlockState: 1 = this fighter guards whatever it's pressing,
	/// -1 = it doesn't guard, 0 = its own inputs decide (players, CPU, playback).</summary>
	public int ForcedGuard(SakugaActor who)
	{
		if (who == null || who.playerID != Dummy || who.UseAI || Recording || Playing || _dummyHuman || Looping)
		{
			return 0;
		}
		switch (Guard)
		{
		case GuardAll:
			return 1;
		case GuardAfterFirst:
			return _guardArmed ? 1 : -1;
		case GuardRandom:
			if (_randomGuard < 0)
			{
				_randomGuard = RNG.Next(0, 2);
			}
			return _randomGuard == 1 ? 1 : -1;
		default:
			return 0;
		}
	}

	/// <summary>SakugaActor.IsCounter: "Counter Hit: Always" makes the hit that starts a combo on the
	/// dummy a counter hit.</summary>
	public bool ForceCounter(SakugaActor target)
	{
		if (!CounterHit || target == null || target.playerID != Dummy || _dummyHuman)
		{
			return false;
		}
		StateType t = target.StateManager.CurrentStateType();
		return t != StateType.HIT_REACTION && t != StateType.BLOCKING;
	}

	/// <summary>NetsuAssist: whether the assist gauge refills at once.</summary>
	public bool AssistRefillsAtOnce => AssistInstant;

	// --- the dummy's own input ------------------------------------------------------------

	private PlayerInputs DummyInput(SakugaActor d)
	{
		StateType type = d.StateManager.CurrentStateType();
		PlayerInputs stance = Action == ActCrouch ? PlayerInputs.DOWN : (Action == ActJump ? PlayerInputs.UP : PlayerInputs.NEUTRAL);
		if (type == StateType.HIT_REACTION)
		{
			_wakeFrames = 0;
			_waitWake = false;
			bool lying = d.Body.IsOnGround && (d.HitstunType == HitstunType.KNOCKDOWN || d.HitstunType == HitstunType.HARD_KNOCKDOWN
				|| d.StateManager.GetCurrentState().BaseStance == MasterStance.ON_THE_GROUND);
			if (lying)
			{
				_down = true;
			}
			PlayerInputs recover = RecoveryInput(d, lying);
			return recover != PlayerInputs.NEUTRAL ? recover : stance;
		}
		_airChoice = -1;
		_wakeChoice = -1;
		if (_down)
		{
			if (type == StateType.LOCKED)
			{
				return stance;   // rolling / quick rise: nothing can be input until it's over
			}
			// getting up: the wake-up action is input from now until it comes out (the engine buffers
			// it through the get-up and it comes out on the first frame the dummy can act)
			_down = false;
			if (WakeupAction == WakeActRecording && _tape.Count > 0)
			{
				_waitWake = true;
			}
			else if (WakeupAction != WakeActNone)
			{
				_wakeFrames = 8;   // free frames to keep trying once it can act
				_wakeStep = 0;
				_wakeMoves = d.StanceManager.ExecutedMoves;
			}
		}
		bool free = type == StateType.MOVEMENT || type == StateType.COMBAT || type == StateType.BLOCKING;
		if (_waitWake && free)
		{
			_waitWake = false;   // the recording starts on the first free frame
			StartPlayback(once: true);
			return PlayStep(d);
		}
		if (_wakeFrames > 0)
		{
			if (free)
			{
				_wakeFrames--;
			}
			// a backdash takes three frames of input (4, 5, 4): the walk the first 4 starts doesn't count
			int minSteps = WakeupAction == WakeActBackdash ? 3 : 1;
			if (_wakeStep >= minSteps && d.StanceManager.ExecutedMoves != _wakeMoves)
			{
				_wakeFrames = 0;   // it came out
			}
			else
			{
				return FromStored(WakeupStep(_wakeStep++), d);
			}
		}
		return stance;
	}

	/// <summary>Recovery while being hit: air recovery in the air, the wake-up choice when lying down.
	/// The button is pressed every other frame, so the engine sees a fresh press the moment the
	/// recovery is allowed (when hitstun runs out).</summary>
	private PlayerInputs RecoveryInput(SakugaActor d, bool lying)
	{
		ushort dir = 0;
		if (!d.Body.IsOnGround)
		{
			if (AirRecovery == AirOff)
			{
				return PlayerInputs.NEUTRAL;
			}
			if (_airChoice < 0)
			{
				_airChoice = AirRecovery == AirRandom ? 1 + RNG.Next(0, 2) : AirRecovery;
			}
			dir = (ushort)(_airChoice == AirForward ? Forward : 0);
		}
		else if (lying)
		{
			if (Wakeup == WakeStayDown)
			{
				return PlayerInputs.NEUTRAL;
			}
			if (_wakeChoice < 0)
			{
				_wakeChoice = Wakeup == WakeRandom ? 1 + RNG.Next(0, 3) : Wakeup;
			}
			dir = (ushort)(_wakeChoice == WakeForward ? Forward : (_wakeChoice == WakeBack ? Back : 0));
		}
		else
		{
			return PlayerInputs.NEUTRAL;   // standing / crouching hitstun: nothing to recover from
		}
		ushort press = (ushort)((_tick & 1) == 0 ? PlayerInputs.FACE_A : 0);
		return FromStored((ushort)(dir | press), d);
	}

	/// <summary>The wake-up action as stored (facing right) inputs, one per frame.</summary>
	private ushort WakeupStep(int step)
	{
		bool even = (step & 1) == 0;
		switch (WakeupAction)
		{
		case WakeActJump:
			return (ushort)PlayerInputs.UP;
		case WakeActBackJump:
			return (ushort)(PlayerInputs.UP | Back);
		case WakeActBackdash:
			return (ushort)(even ? Back : 0);
		case WakeActLight:
			return (ushort)(even ? PlayerInputs.FACE_A : 0);
		case WakeActCrouchLight:
			return (ushort)(PlayerInputs.DOWN | (even ? PlayerInputs.FACE_A : 0));
		case WakeActAssist:
			return (ushort)(even ? PlayerInputs.FACE_D : 0);
		case WakeActBurst:
			return (ushort)(even ? (PlayerInputs.FACE_A | PlayerInputs.FACE_C) : 0);
		default:
			return 0;
		}
	}

	// --- recording ------------------------------------------------------------------------

	private void StartPlayback(bool once)
	{
		if (_tape.Count == 0)
		{
			return;
		}
		Playing = true;
		_playOnce = once;
		_playIndex = 0;
	}

	private PlayerInputs PlayStep(SakugaActor d)
	{
		if (_tape.Count == 0)
		{
			Playing = false;
			return PlayerInputs.NEUTRAL;
		}
		if (_playIndex >= _tape.Count)
		{
			_playIndex = 0;
			// a playback started with the shortcut (or on wake-up) repeats only when set to; the
			// Dummy Action "Playback" loop always does
			bool again = Playing ? !_playOnce : Looping;
			if (!again)
			{
				Playing = false;
				return PlayerInputs.NEUTRAL;
			}
		}
		return FromStored(_tape[_playIndex++], d);
	}

	/// <summary>Absolute input -> stored facing right (forward = RIGHT, back = LEFT).</summary>
	private static ushort ToStored(PlayerInputs raw, SakugaActor facing)
	{
		return (ushort)(facing.Body.PlayerSide >= 0 ? raw : Mirror(raw));
	}

	/// <summary>Stored (facing right) -> absolute input for the way this fighter faces now.</summary>
	private static PlayerInputs FromStored(ushort stored, SakugaActor facing)
	{
		PlayerInputs p = (PlayerInputs)stored;
		return facing.Body.PlayerSide >= 0 ? p : Mirror(p);
	}

	private static PlayerInputs Mirror(PlayerInputs p)
	{
		bool left = (p & PlayerInputs.LEFT) != 0;
		bool right = (p & PlayerInputs.RIGHT) != 0;
		p &= ~(PlayerInputs.LEFT | PlayerInputs.RIGHT);
		if (left)
		{
			p |= PlayerInputs.RIGHT;
		}
		if (right)
		{
			p |= PlayerInputs.LEFT;
		}
		return p;
	}

	// --- commands ---------------------------------------------------------------------------

	private void Run(GameManager gm, SakugaActor[] f, string name, int value)
	{
		switch (name)
		{
		case "reset":
			ResetPositions(gm, f, value);
			break;
		case "record":         // the shortcut: start recording, or stop
		case "record_start":   // the Training Menu: always a new recording
			if (Recording && name == "record")
			{
				Recording = false;
				break;
			}
			if (_dummyHuman)
			{
				break;
			}
			Playing = false;
			_playIndex = 0;
			_loopStopped = false;   // Dummy Action "Playback" loops the new recording once it's done
			_tape.Clear();
			Recording = true;
			break;
		case "play":           // the shortcut: play, or stop
		case "play_start":     // the Training Menu: play from the top
		{
			bool restart = name == "play_start" || Recording;   // a press that ends a recording plays it
			Recording = false;
			if (_dummyHuman)
			{
				break;
			}
			if (Playing && !restart)
			{
				Playing = false;
				_playIndex = 0;
			}
			else if (Action == ActPlayback && _tape.Count > 0)
			{
				Playing = false;
				_loopStopped = !restart && !_loopStopped;   // the dummy's own loop: stop it, or start it from the top
				_playIndex = 0;
			}
			else
			{
				StartPlayback(once: !PlaybackRepeat);
			}
			break;
		}
		case "stop":
			Recording = false;
			Playing = false;
			_playIndex = 0;
			break;
		case "clear":
			Recording = false;
			Playing = false;
			_playIndex = 0;
			_tape.Clear();
			break;
		}
	}

	/// <summary>Both fighters back to a starting spot (like a new round, but the gauges set to "normal"
	/// keep what they had). Modes: centre, the dummy in the left / right corner, sides swapped,
	/// player 1 in the left / right corner.</summary>
	private void ResetPositions(GameManager gm, SakugaActor[] f, int mode)
	{
		if (f == null || f.Length < 2)
		{
			return;
		}
		int[] craft = new int[2];
		int[] will = new int[2];
		for (int i = 0; i < 2; i++)
		{
			craft[i] = f[i].Parameters.SuperGauge.CurrentValue;
			will[i] = f[i].Parameters.Will.CurrentValue;
		}
		for (int i = 0; i < 2; i++)
		{
			f[i].Reset();
			if (f[i].Brain != null)
			{
				f[i].Brain.Reset();
			}
		}
		const int wall = GlobalVariables.WallLimit - 2000;
		const int gap = 25000;
		int p1 = -12500;
		int p2 = 12500;
		switch (mode)
		{
		case ResetLeftCorner:
			p2 = -wall;
			p1 = -wall + gap;
			break;
		case ResetRightCorner:
			p2 = wall;
			p1 = wall - gap;
			break;
		case ResetSwap:
			p1 = 12500;
			p2 = -12500;
			break;
		case ResetPlayerLeftCorner:
			p1 = -wall;
			p2 = -wall + gap;
			break;
		case ResetPlayerRightCorner:
			p1 = wall;
			p2 = wall - gap;
			break;
		}
		Place(f[0], p1, p1 < p2);
		Place(f[1], p2, p2 < p1);
		for (int i = 0; i < 2; i++)
		{
			if (Craft[i] == -2)
			{
				f[i].Parameters.SuperGauge.CurrentValue = craft[i];
			}
			else if (Craft[i] >= 0)
			{
				f[i].Parameters.SuperGauge.CurrentValue = Mathf.Clamp(StanceManager.NetsuBarSize * Craft[i], 0, f[i].Data.MaxSuperGauge);
			}
			if (Burst[i] == -2)
			{
				f[i].Parameters.Will.CurrentValue = will[i];
			}
			if (Health[i] > 0)
			{
				f[i].Parameters.Health.CurrentValue = Mathf.Max(1, f[i].Data.MaxHealth * Mathf.Clamp(Health[i], 1, 100) / 100);
			}
			_free[i] = RefillDelay + 1;
		}
		Playing = Playing && !_playOnce;
		_playIndex = 0;
		_guardArmed = false;
		_randomGuard = -1;
		_down = false;
		_wakeFrames = 0;
		_waitWake = false;
		_airChoice = -1;
		_wakeChoice = -1;
		gm?.Camera?.NetsuSnap();
	}

	private static void Place(SakugaActor a, int x, bool leftSide)
	{
		// SakugaActor.Reset leaves the hit timers running: a reset during hitstop would freeze the fighter at
		// the new spot, and knockback / bounce would push it from there
		a.Hitstop?.Stop();
		a.Hitstun?.Stop();
		a.Knockback?.Stop();
		a.Bounce?.Stop();
		a.HitstunType = HitstunType.NONE;
		a.BlockStun = false;
		a.SuperFlashing = false;
		a.Body.SetVelocity(Vector2I.Zero);
		a.Body.FixedPosition.X = x;
		a.Body.FixedPosition.Y = 0;
		a.Body.UpdateSide(leftSide);
		a.Body.FlipSide();
		a.Body.UpdateColliders();
	}
}
