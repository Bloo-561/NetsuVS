using Godot;
using SakugaEngine.Global;
using SakugaEngine.Resources;

namespace SakugaEngine;

// ---------------------------------------------------------------------------------------------
// Nov 12 2026 (TamaDeez): Cecilia's Judith variation (patience), prototype. Design: the move sheet's "Redesign" section.
// - Hold to charge: a move flagged MoveSettings.NetsuChargeable waits on its first frame while its button is held.
//   Released at once = Tap (85% damage), held NetsuJBudFrames = Bud (100%), NetsuJBloomFrames = Bloom (112%, the hit
//   pops them up, and the move can cancel into another special). At NetsuJMaxHold it comes out on its own.
// - D during the hold drops it (back to neutral). A move charged with D itself (214D) can't be dropped.
// - No invincibility while holding (a charged DP is invincible on its startup only, after the release).
// - MoveSettings.NetsuJudithHub (236A / 236B): cancels into any special on hit or block. NetsuJudithLaunch (236B): the
//   hit launches them high at normal gravity: the time to charge the next special. No floating hits.
// - Each special once per combo for these cancels (NetsuJUsed).
// Everything that changes the match is saved for rollback (SakugaActorState keys 73-81).
public partial class SakugaActor
{
	public const int NetsuVariationNone = 0;
	public const int NetsuVariationJudith = 1;

	/// <summary>Prototype switch: Cecilia always plays the Judith variation until variations can be picked.</summary>
	public static bool NetsuJudithPrototype = true;

	public const int NetsuJHoldFrame = 1;       // the frame of the move's first state she waits on
	public const int NetsuJBudFrames = 15;
	public const int NetsuJBloomFrames = 35;
	public const int NetsuJMaxHold = 60;
	public static readonly int[] NetsuJDamagePercent = { 85, 100, 112 };   // Tap, Bud, Bloom

	// Nov 12 (4): launches, not floats. A Bloom hit's launch (X away, Y up); 236B's is MoveSettings.NetsuJudithLaunch.
	// Juggled fighters fall at GameManager.NetsuJuggleGravity (200000), lighter at the top and heavier coming down
	// (AddGravityAction.NetsuJuggleGravityNow). 80000: peak ~16000 units (a bit above a jump), ~48 frames in the air.
	public static readonly Vector2I NetsuJBloomLaunch = new Vector2I(15000, 46000);   // (Y no longer used: see NetsuJBloomHeight)
	public const int NetsuJBloomHeight = 9000;    // Nov 13 (2): a Bloom pops them to about one body height above the floor
	public const int NetsuJBloomMinBump = 1500;   // ...or by at least this much if they're already that high   // Nov 13: ~1 body height up at the juggle gravity, ~46F in the air

	/// <summary>The variation this fighter plays (set when the fighter is created; not part of the match state).</summary>
	public int NetsuVariation;

	public int NetsuJChargeMove = -1;   // the move being charged / last charged (-1 = none)
	public int NetsuJChargeFrames;      // frames held
	public int NetsuJLevel = -1;        // -1 = not a charge move, 0 Tap, 1 Bud, 2 Bloom
	public bool NetsuJudithHolding;     // waiting on the hold frame right now
	public int NetsuJButton;            // PlayerInputs bit of the button that charges it
	public Vector2I NetsuJSavedVel;     // her velocity when the hold started (given back on release)
	public FrameProperties NetsuJSavedProps;
	public ulong NetsuJUsed;            // specials used in this combo (bit = move index)

	public static void NetsuJudithAssign(SakugaActor f)
	{
		if (f == null)
		{
			return;
		}
		string name = f.Data?.Profile?.ShortName ?? "";
		f.NetsuVariation = (NetsuJudithPrototype && name == "Cecilia") ? NetsuVariationJudith : NetsuVariationNone;
	}

	public bool NetsuIsJudith()
	{
		return NetsuVariation == NetsuVariationJudith;
	}

	public void NetsuJudithClear()
	{
		NetsuJChargeMove = -1;
		NetsuJChargeFrames = 0;
		NetsuJLevel = -1;
		NetsuJudithHolding = false;
		NetsuJButton = 0;
		NetsuJUsed = 0;
	}

	/// <summary>The button of a one-button move's input, as a PlayerInputs bit (0 = none / several).</summary>
	public static int NetsuJMoveButton(MotionInputs inputs)
	{
		if (inputs == null || inputs.ValidInputs == null)
		{
			return 0;
		}
		foreach (InputOption opt in inputs.ValidInputs)
		{
			if (opt == null || opt.Inputs == null || opt.Inputs.Length == 0)
			{
				continue;
			}
			InputSequence last = opt.Inputs[opt.Inputs.Length - 1];
			if (last == null || InputManager.NetsuButtonCount(last.Buttons) != 1)
			{
				continue;
			}
			return ((int)last.Buttons & 0xFF) << 4;   // ButtonInputs FACE_A = 1 -> PlayerInputs FACE_A = 0x10
		}
		return 0;
	}

	/// <summary>StanceManager.ExecuteMove, just before the move's state starts.</summary>
	public void NetsuJudithMoveStart(int moveIndex, MoveSettings m)
	{
		if (!NetsuIsJudith())
		{
			return;
		}
		NetsuJudithHolding = false;
		NetsuJChargeMove = -1;
		NetsuJChargeFrames = 0;
		NetsuJLevel = -1;
		if (m == null)
		{
			return;
		}
		if ((m.NetsuChargeable || m.NetsuJudithHub) && moveIndex >= 0 && moveIndex < 64)
		{
			NetsuJUsed |= 1UL << moveIndex;   // used in this combo
		}
		if (!m.NetsuChargeable)
		{
			return;
		}
		int btn = NetsuJMoveButton(m.Inputs);
		if (btn == 0)
		{
			return;
		}
		NetsuJChargeMove = moveIndex;
		NetsuJButton = btn;
		NetsuJLevel = 0;
		NetsuJudithHolding = true;
	}

	private static int NetsuJLevelFor(int frames)
	{
		return frames >= NetsuJBloomFrames ? 2 : (frames >= NetsuJBudFrames ? 1 : 0);
	}

	/// <summary>PreTick, before the state frame moves on. True = she waits (the state frame doesn't advance).</summary>
	private bool NetsuJudithChargeTick()
	{
		if (!NetsuIsJudith() || StanceManager == null || StateManager == null || Inputs == null)
		{
			NetsuJudithHolding = false;
			return false;
		}
		SakugaActor foe = GetOpponent(0);
		if (StateManager.CurrentStateType() != StateType.COMBAT
			&& (foe == null || foe.StateManager == null || foe.StateManager.CurrentStateType() != StateType.HIT_REACTION))
		{
			NetsuJUsed = 0;   // not attacking and they aren't in hitstun: the combo is over
		}
		if (!NetsuJudithHolding)
		{
			return false;
		}
		int mi = NetsuJChargeMove;
		MoveSettings m = (mi >= 0) ? StanceManager.GetMove(mi) : null;
		if (m == null || StanceManager.CurrentMove != mi || StateManager.CurrentState != m.MoveState)
		{
			NetsuJudithRelease(false);   // hit out of it, or the move went on to another state
			return false;
		}
		if (StateManager.CurrentStateFrame < NetsuJHoldFrame)
		{
			return false;
		}
		PlayerInputs raw = Inputs.CurrentInput().rawInput;
		if (NetsuJButton != (int)PlayerInputs.FACE_D && Inputs.WasPressed(Inputs.CurrentHistory, PlayerInputs.FACE_D))
		{
			// D: drop the charge, back to neutral
			if (NetsuJChargeFrames > 0)
			{
				FrameProperties = NetsuJSavedProps;
			}
			NetsuJudithHolding = false;
			NetsuJLevel = -1;
			NetsuJChargeMove = -1;
			StanceManager.NetsuDropMove();
			bool ground = Body == null || Body.IsOnGround;
			if (Body != null)
			{
				Body.FixedVelocity = ground ? Vector2I.Zero : new Vector2I(0, NetsuJSavedVel.Y < 0 ? NetsuJSavedVel.Y : 0);
			}
			StateManager.PlayState(ground ? 0 : 10, reset: true);   // Cecilia: 0 idle, 10 falling
			return false;
		}
		bool held = ((int)raw & NetsuJButton) != 0;
		if (held && NetsuJChargeFrames < NetsuJMaxHold)
		{
			if (NetsuJChargeFrames == 0)
			{
				NetsuJSavedVel = Body != null ? Body.FixedVelocity : Vector2I.Zero;
				NetsuJSavedProps = FrameProperties;
			}
			NetsuJChargeFrames++;
			int lvl = NetsuJLevelFor(NetsuJChargeFrames);
			if (lvl > NetsuJLevel)
			{
				NetsuJLevel = lvl;
				NetsuJudithCue(lvl);
			}
			if (Body != null)
			{
				Body.FixedVelocity = Vector2I.Zero;   // she waits where she is (in the air too)
			}
			// no invincibility while she waits
			FrameProperties &= ~(FrameProperties.DAMAGE_IMUNITY | FrameProperties.THROW_IMUNITY | FrameProperties.PROJECTILE_IMUNITY);
			return true;
		}
		NetsuJudithRelease(NetsuJChargeFrames > 0);
		return false;
	}

	private void NetsuJudithRelease(bool restore)
	{
		NetsuJudithHolding = false;
		if (restore)
		{
			if (Body != null)
			{
				Body.FixedVelocity = NetsuJSavedVel;
			}
			FrameProperties = NetsuJSavedProps;
		}
	}

	public const int NetsuJCueSource = 3;
	public const int NetsuJCueSound = 35;   // the same spark as the old 214 [C] charge

	private void NetsuJudithCue(int level)
	{
		if (level <= 0 || Parameters == null || Parameters.SoundSources == null || Parameters.SoundSources.Length <= NetsuJCueSource
			|| SFXList == null || SFXList.Sounds == null || SFXList.Sounds.Length <= NetsuJCueSound)
		{
			return;
		}
		Parameters.SoundSources[NetsuJCueSource].QueueSound(SFXList.Sounds[NetsuJCueSound]);
	}

	/// <summary>HitDamage: the attacker's charge level changes the damage (Tap 85%, Bud 100%, Bloom 112%).</summary>
	private static int NetsuJudithDamage(SakugaActor attacker, int damage)
	{
		SakugaActor root = attacker?.NetsuRoot();
		if (root == null || !root.NetsuIsJudith() || root.NetsuJLevel < 0)
		{
			return damage;
		}
		return damage * NetsuJDamagePercent[Mathf.Clamp(root.NetsuJLevel, 0, 2)] / 100;
	}

	/// <summary>HitDamage, on the one being hit (after the hit's own knockback). Nov 12 (2): no floating. Every Judith
	/// hit drops any float (2C's, which Low Slash borrows, included). 236B (MoveSettings.NetsuJudithLaunch) and a Bloom hit
	/// launch them instead: a normal launch at the hit's own gravity, just higher, with hitstun lasting the whole trip up
	/// and down, so the combo can go on (Iai Arthur's slash in the reference clip).</summary>
	private void NetsuJudithOnHit(SakugaActor attacker)
	{
		SakugaActor root = attacker?.NetsuRoot();
		if (root == null || !root.NetsuIsJudith() || root.StanceManager == null || IsKO() || Body == null)
		{
			return;
		}
		NetsuFloatFrame = 0;   // no floaty hits for Judith
		if (root.StanceManager.CurrentMove < 0)
		{
			return;
		}
		MoveSettings m = root.StanceManager.GetCurrentMove();
		bool bloom = root.NetsuJLevel == 2 && m != null && m.NetsuChargeable;
		if (bloom)
		{
			NetsuBloomFlowerStart();   // Nov 13: the sakura where the Bloom hit lands
		}
		Vector2I launch = Vector2I.Zero;
		int ownGravity = 0;
		if (m != null && m.NetsuJudithLaunch.Y > 0)
		{
			launch = m.NetsuJudithLaunch;
			ownGravity = m.NetsuJudithLaunchGravity;
		}
		else if (bloom)
		{
			// Nov 13 (2): a Bloom pops them to about NetsuJBloomHeight above the FLOOR, wherever they were hit (a Bloom on
			// someone already up there is only a small bump), so ground and air follow-ups both reach them
			int jgb = SakugaEngine.Game.GameManager.Instance != null ? SakugaEngine.Game.GameManager.Instance.NetsuJuggleGravity : 120000;
			int dh = Mathf.Max(NetsuJBloomHeight - Mathf.Max(0, Body.FixedPosition.Y), NetsuJBloomMinBump);
			launch = new Vector2I(NetsuJBloomLaunch.X, (int)Mathf.Sqrt(2.0 * jgb * dh));
		}
		if (launch.Y <= 0 || Body.CurrentGravity < 50000 || root.Body == null)
		{
			return;   // (gravity 1 = a hit that holds them up on purpose: left alone)
		}
		int away = Body.FixedPosition.X != root.Body.FixedPosition.X ? (Body.FixedPosition.X > root.Body.FixedPosition.X ? 1 : -1) : root.Body.PlayerSide;
		// set, not "at least": the hit's own launch is replaced
		Body.FixedVelocity = new Vector2I(launch.X * away, launch.Y);
		NetsuJGravity = ownGravity;   // 236B: its own slow arc (AddGravityAction); 0 = the usual juggle gravity
		int jg = ownGravity > 0 ? ownGravity
			: (SakugaEngine.Game.GameManager.Instance != null ? SakugaEngine.Game.GameManager.Instance.NetsuJuggleGravity : 120000);
		int air = AddGravityAction.NetsuJuggleAirFrames(launch.Y, jg, Body.FixedPosition.Y) + 2;   // Nov 13 (2): until they land, from where they are
		if (HitstunType < HitstunType.KNOCKDOWN)
		{
			HitstunType = HitstunType.KNOCKDOWN;   // juggled: no restand
		}
		if (CanHitstun() && Hitstun.TimeLeft < air)
		{
			Hitstun.Start((uint)air);
			NetsuUntechMax = Mathf.Max(NetsuUntechMax, air);
		}
	}

	/// <summary>Render: while she holds a move with MoveSettings.NetsuJudithHoldState, that state's animation (looping) is
	/// shown instead of the move's frozen frame. Presentation only.</summary>
	private AnimationSettings NetsuJudithHoldAnimation()
	{
		if (!NetsuJudithHolding || NetsuJChargeFrames <= 0 || StanceManager == null || StateManager == null || Data == null || Data.States == null)
		{
			return null;
		}
		MoveSettings m = NetsuJChargeMove >= 0 ? StanceManager.GetMove(NetsuJChargeMove) : null;
		if (m == null || m.NetsuJudithHoldState < 0 || m.NetsuJudithHoldState >= Data.States.Length)
		{
			return null;
		}
		AnimationData ad = Data.States[m.NetsuJudithHoldState].AnimationData;
		if (ad == null || ad.Animations == null || ad.Animations.Length == 0)
		{
			return null;
		}
		int dur = Mathf.Max(1, ad.Duration);
		int f = NetsuJChargeFrames % dur;
		AnimationSettings pick = ad.Animations[0];
		for (int i = 0; i < ad.Animations.Length; i++)
		{
			if (ad.Animations[i] != null && ad.Animations[i].AtFrame <= f)
			{
				pick = ad.Animations[i];
			}
		}
		return pick;
	}

	/// <summary>Render: the charge spark while she holds (bigger at Bud, biggest at Bloom). Presentation only.</summary>
	private bool NetsuJudithFlare()
	{
		if (!NetsuJudithHolding || Body == null || Animator == null || StateManager == null || StateManager.CurrentStateFrame < NetsuJHoldFrame)
		{
			return false;
		}
		float[] sizes = { 0.5f, 1.4f, 2.4f };
		float scale = sizes[Mathf.Clamp(NetsuJLevel, 0, 2)];
		float pulse = 0.85f + 0.15f * Mathf.Sin(NetsuJChargeFrames * 0.6f);
		Vector2I at = Body.FixedPosition + new Vector2I(1500 * Body.PlayerSide, 6000);
		Animator.SetChargeFlare(scale * pulse, NetsuJLevel >= 2 ? 1f : 0.75f, NetsuJChargeFrames, GlobalFunctions.ToScaledVector3(at));
		return true;
	}
}

public partial class StanceManager
{
	/// <summary>Judith: 236A / 236B (on hit or block) and a Bloom special (on hit) cancel into any special not used yet in
	/// this combo. Returns true when it buffered one (or one is already waiting).</summary>
	private bool NetsuJudithCancel()
	{
		if (_owner == null || !_owner.NetsuIsJudith() || CurrentMove < 0 || _owner.NetsuJudithHolding || _owner.StateManager == null)
		{
			return false;
		}
		MoveSettings cur = GetCurrentMove();
		if (cur == null)
		{
			return false;
		}
		bool hub = cur.NetsuJudithHub && (_owner.CancelConditions & (CancelCondition.HIT_CANCEL | CancelCondition.BLOCK_CANCEL)) != 0;
		bool bloom = cur.NetsuChargeable && _owner.NetsuJLevel == 2 && (_owner.CancelConditions & CancelCondition.HIT_CANCEL) != 0;
		if (!hub && !bloom)
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
			if (move == null || move.SkipCheck || i == CurrentMove || !(move.NetsuChargeable || move.NetsuJudithHub) || NetsuIsExOrSuper(move))
			{
				continue;
			}
			if (i < 64 && (_owner.NetsuJUsed & (1UL << i)) != 0)
			{
				continue;   // once per combo
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
}
