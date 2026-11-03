using System.Linq;
using Godot;
using MessagePack;
using SakugaEngine.Collision;
using SakugaEngine.Game;
using SakugaEngine.GameState;
using SakugaEngine.Global;
using SakugaEngine.Resources;

namespace SakugaEngine;

[GlobalClass]
public partial class SakugaActor : SakugaNode, IDamage
{
	public InputManager Inputs;

	[ExportCategory("Components")]
	[Export(PropertyHint.None, "")]
	public PhysicsBody Body;

	[Export(PropertyHint.None, "")]
	public SakugaParameters Parameters;

	[Export(PropertyHint.None, "")]
	public StateManager StateManager;

	[Export(PropertyHint.None, "")]
	public StanceManager StanceManager;

	[Export(PropertyHint.None, "")]
	public ObjectPool Pool;

	[Export(PropertyHint.None, "")]
	public AIBrain Brain;

	/// <summary>Netsu: this fighter's assist (Mary, Adin, Eren...), or null when none was picked.
	/// Made by GameManager.CreateFighter; see NetsuAssist.cs.</summary>
	public NetsuAssist NetsuAssist;

	[ExportCategory("Variables")]
	[Export(PropertyHint.None, "")]
	public FrameProperties InitialProperties;

	[Export(PropertyHint.None, "")]
	public HitChecker AllowHit;

	[ExportCategory("Visuals")]
	[Export(PropertyHint.None, "")]
	private AnimationViewer Animator;

	[Export(PropertyHint.None, "")]
	protected Node3D[] Graphics;

	[ExportCategory("Resources")]
	[Export(PropertyHint.None, "")]
	public DataContainer Data;

	[Export(PropertyHint.None, "")]
	public SpawnsList SpawnablesList;

	[Export(PropertyHint.None, "")]
	public SpawnsList VFXList;

	[Export(PropertyHint.None, "")]
	public SoundsList SFXList;

	[Export(PropertyHint.None, "")]
	public SoundsList VoiceLines;

	[ExportCategory("Default Timers")]
	[Export(PropertyHint.None, "")]
	public FrameTimer Hitstop;

	[Export(PropertyHint.None, "")]
	public FrameTimer Hitstun;

	[Export(PropertyHint.None, "")]
	public FrameTimer Knockback;

	[Export(PropertyHint.None, "")]
	public FrameTimer Bounce;

	public bool UseAI;

	public uint playerID;

	public int LayerSorting = -1;

	public int BounceXIntensity;

	public int BounceYIntensity;

	public int NetsuWallBounceDistance;   // Netsu (Oct 26 c17): wall-bounce distance of the last bounce hit (0 = default)

	public bool SuperFlashing;

	public bool CinematicState;

	public bool BlockStun;

	public HitstunType HitstunType;

	public FrameProperties FrameProperties;

	public HitChecker HitCheck;

	public CancelCondition CancelConditions;

	private SakugaActor actor;

	private SakugaActor _master;

	private SakugaActor[] _allies;

	private SakugaActor[] _opponents;

	private SakugaActorState State;

	public SakugaActor GetMaster()
	{
		return _master;
	}

	public void SetMaster(SakugaActor master)
	{
		if (master != _master)
		{
			_master = master;
		}
	}

	public SakugaActor[] GetAllies()
	{
		if (GetMaster() == null)
		{
			return _allies;
		}
		return GetMaster().GetAllies();
	}

	public SakugaActor GetAlly(int index)
	{
		if (GetMaster() == null)
		{
			return _allies[index];
		}
		return GetMaster().GetAlly(index);
	}

	public void SetAllies(SakugaActor[] allies)
	{
		if (allies != _allies)
		{
			_allies = allies;
		}
	}

	public SakugaActor[] GetOpponents()
	{
		if (GetMaster() == null)
		{
			return _opponents;
		}
		return GetMaster().GetOpponents();
	}

	public SakugaActor GetOpponent(int index)
	{
		if (GetMaster() == null)
		{
			return _opponents[index];
		}
		return GetMaster().GetOpponent(index);
	}

	public void SetOpponents(SakugaActor[] opponents)
	{
		if (opponents != _opponents)
		{
			_opponents = opponents;
		}
	}

	public bool IsCounter(SakugaActor target)
	{
		// Netsu: Training mode's "Counter Hit: Always" (the hit that starts a combo on the dummy)
		if (GameManager.Instance != null && GameManager.Instance.Training != null && GameManager.Instance.Training.ForceCounter(target))
		{
			return true;
		}
		if (StateManager.CurrentStateType() == StateType.COMBAT && target.StateManager.CurrentStateType() == StateType.COMBAT && Body.CurrentHitbox.animationStage < AnimationStage.RECOVERY)
		{
			return target.Body.CurrentHitbox.animationStage < AnimationStage.RECOVERY;
		}
		return false;
	}

	public bool IsPunishCounter(SakugaActor target)
	{
		if (StateManager.CurrentStateType() == StateType.COMBAT && target.StateManager.CurrentStateType() == StateType.COMBAT && Body.CurrentHitbox.animationStage < AnimationStage.RECOVERY)
		{
			return target.Body.CurrentHitbox.animationStage == AnimationStage.RECOVERY;
		}
		return false;
	}

	public bool IsInstantBlock()
	{
		return StateManager.CurrentStateType() != StateType.BLOCKING;
	}

	public bool CanHitTarget(SakugaActor target)
	{
		if (!IsActive || !target.IsActive)
		{
			return false;
		}
		if (HitCheck == HitChecker.NONE)
		{
			return false;
		}
		if (GetMaster() != null && target.GetMaster() != null && target.GetMaster() == GetMaster())
		{
			return false;
		}
		if ((int)(HitCheck & HitChecker.MASTER) > 0 && GetMaster() != null && GetMaster() != target)
		{
			return false;
		}
		// Netsu: NetsuRoot() so a projectile spawned by an assist (projectile -> assist -> fighter) counts as the fighter's
		if ((int)(HitCheck & HitChecker.OPPONENTS) > 0 && !GetOpponents().Contains(target) && !GetOpponents().Contains(target.GetMaster()) && !GetOpponents().Contains(target.NetsuRoot()))
		{
			return false;
		}
		if ((int)(HitCheck & HitChecker.ALLIES) > 0 && !GetAllies().Contains(target) && !GetAllies().Contains(target.GetMaster()) && !GetAllies().Contains(target.NetsuRoot()))
		{
			return false;
		}
		NetsuLog.Debug("Hit is valid");
		return true;
	}

	public SakugaActor GetClosestAlly()
	{
		if (_allies.Length == 1)
		{
			return _allies[0];
		}
		int dist = int.MaxValue;
		int index = 0;
		for (int i = 0; i < _allies.Length; i++)
		{
			int newDist = GlobalFunctions.HorizontalDistance(Body.FixedPosition, _allies[i].Body.FixedPosition);
			if (newDist < dist)
			{
				dist = newDist;
				index = i;
			}
		}
		return _allies[index];
	}

	public SakugaActor GetClosestOpponent()
	{
		if (_opponents.Length == 1)
		{
			return _opponents[0];
		}
		int dist = int.MaxValue;
		int index = 0;
		for (int i = 0; i < _opponents.Length; i++)
		{
			int newDist = GlobalFunctions.HorizontalDistance(Body.FixedPosition, _opponents[i].Body.FixedPosition);
			if (newDist < dist)
			{
				dist = newDist;
				index = i;
			}
		}
		return _opponents[index];
	}

	public bool IsGroundState()
	{
		if (Body != null && Body.IsOnGround)
		{
			return StateManager.GetCurrentState().BaseStance == MasterStance.NEUTRAL;
		}
		return false;
	}

	public bool IsCrouchState()
	{
		if (Body != null && Body.IsOnGround)
		{
			return StateManager.GetCurrentState().BaseStance == MasterStance.CROUCH;
		}
		return false;
	}

	public bool IsAirState()
	{
		if (Body != null)
		{
			if (Body.IsOnGround)
			{
				if (Body.IsOnGround)
				{
					return StateManager.GetCurrentState().BaseStance == MasterStance.ON_THE_GROUND;
				}
				return false;
			}
			return true;
		}
		return false;
	}

	public bool IsKO()
	{
		if (Parameters != null && Parameters.Health != null)
		{
			return Parameters.Health.CurrentValue < 0;   // Netsu (Oct 27): 0 HP stays alive
		}
		return false;
	}

	public bool IsStunLocked()
	{
		if (OnHitstun() && StateManager.GetCurrentState().AnimationData != null && StateManager.GetCurrentState().AnimationData.HitstunHold >= 0 && Hitstun.TimeLeft >= StateManager.GetCurrentState().AnimationData.Duration - StateManager.GetCurrentState().AnimationData.HitstunHold + 1)
		{
			return StateManager.CurrentStateFrame >= StateManager.GetCurrentState().AnimationData.HitstunHold;
		}
		return false;
	}

	public bool CanBlock()
	{
		if (StanceManager != null && StanceManager.GetCurrentStance().BlockReactions != null)
		{
			return StanceManager.GetCurrentStance().BlockReactions.Length != 0;
		}
		return false;
	}

	public bool IsGrabbed()
	{
		return HitstunType == HitstunType.GRABBED;
	}

	public bool CanHitstop()
	{
		return Hitstop != null;
	}

	public bool OnHitstop()
	{
		if (CanHitstop())
		{
			return Hitstop.IsRunning();
		}
		return false;
	}

	public bool CanHitstun()
	{
		return Hitstun != null;
	}

	public bool OnHitstun()
	{
		if (CanHitstun())
		{
			return Hitstun.IsRunning();
		}
		return false;
	}

	public bool CanKnockback()
	{
		if (Body != null)
		{
			return Knockback != null;
		}
		return false;
	}

	public bool OnKnockback()
	{
		if (CanKnockback())
		{
			return Knockback.IsRunning();
		}
		return false;
	}

	public bool CanBounce()
	{
		return Bounce != null;
	}

	public bool IsBouncingX()
	{
		if (CanBounce() && Bounce.IsRunning())
		{
			return BounceXIntensity > 0;
		}
		return false;
	}

	public bool IsBouncingY()
	{
		if (CanBounce() && Bounce.IsRunning())
		{
			return BounceYIntensity > 0;
		}
		return false;
	}

	public bool ContainsFrameProperty(FrameProperties CompareTo)
	{
		if ((CompareTo & NetsuWakeImmunity) != 0 && NetsuWakeInvincible())
		{
			return true;   // Netsu (Oct 26): lying after the OTG window, or getting up: can't be hit or thrown
		}
		if ((CompareTo & NetsuWakeImmunity) != 0 && NetsuAirTechInvul)
		{
			return true;   // Netsu (Oct 28): air tech: can't be hit or thrown until she lands or acts
		}
		return (FrameProperties & CompareTo) != 0;
	}

	// ---------------------------------------------------------------------------------------------
	// Netsu (Oct 26 2026, TamaDeez): OTG and invincible wake-up.
	//  - Lying on the ground (a knockdown's "on the ground" states) a fighter can still be hit for a short while
	//    (GameManager.NetsuOtgWindowFrames from landing, shorter the more the combo is scaled; nothing at the
	//    minimum scaling). An OTG hit only does damage, hitstop and meter: they stay down, aren't picked up and their
	//    down time doesn't start again.
	//  - After that window, and while getting up (or tech-rolling on the ground), they can't be hit or thrown.
	//  NetsuDownFrames is saved for rollback (SakugaActorState key 17).

	private const FrameProperties NetsuWakeImmunity = FrameProperties.DAMAGE_IMUNITY | FrameProperties.THROW_IMUNITY | FrameProperties.PROJECTILE_IMUNITY;

	/// <summary>Frames this fighter has been lying on the ground (not counting hitstop). 0 = not lying.</summary>
	public int NetsuDownFrames;

	// Oct 27 c34 (TamaDeez): universal hard knockdown, counted in simulation ticks from the FIRST ground impact:
	// impact / bounce (GameManager.NetsuKnockdownImpactFrames, 28) + lying (22) + getting up (22) = 72. NetsuDownFrames
	// is that counter now (bounces don't restart it). Invulnerable the whole time except the OTG window (set by the
	// combo's proration, never longer than impact + lying). A hit can override the three lengths (HitboxElement
	// NetsuKnockdown*, 0 = global); they are remembered here. Saved for rollback (SakugaActorState keys 39-42).
	public int NetsuOtgSpent;

	/// <summary>Nov 3: set by BaseDamage for a splash hit (HitboxElement.NetsuOtgRelaunch) on a downed opponent, read and
	/// cleared by HitDamage in the same call (never kept across frames, so rollback needn't save it).</summary>
	public bool NetsuRelaunchNow;
	public int NetsuKdImpact;
	public int NetsuKdLying;
	public int NetsuKdGetUp;

	public int NetsuKdImpactFrames()
	{
		return NetsuKdImpact > 0 ? NetsuKdImpact : (GameManager.Instance != null ? GameManager.Instance.NetsuKnockdownImpactFrames : 28);
	}

	public int NetsuKdLyingFrames()
	{
		return NetsuKdLying > 0 ? NetsuKdLying : (GameManager.Instance != null ? GameManager.Instance.NetsuKnockdownLyingFrames : 22);
	}

	public int NetsuKdGetUpFrames()
	{
		return NetsuKdGetUp > 0 ? NetsuKdGetUp : (GameManager.Instance != null ? GameManager.Instance.NetsuKnockdownGetUpFrames : 22);
	}

	/// <summary>Standing in the get-up state (Hit_GetUp).</summary>
	private bool NetsuInGetUp()
	{
		int[] reactions = StanceManager?.GetCurrentStance()?.HitReactions;
		return StateManager != null && reactions != null && reactions.Length > NetsuGetUpReaction && StateManager.CurrentState == reactions[NetsuGetUpReaction];
	}

	/// <summary>The knockdown counter for this tick: starts on the first tick lying on the ground, keeps counting through
	/// the bounce (airborne in an on-the-ground reaction) and the get-up, and stops when control comes back.</summary>
	private int NetsuKnockdownTick()
	{
		if (IsKO() || Body == null || StateManager == null || StanceManager == null || GetMaster() != null)
		{
			return 0;
		}
		if (NetsuLying())
		{
			return NetsuDownFrames + 1;
		}
		if (NetsuDownFrames > 0)
		{
			FighterState st = StateManager.GetCurrentState();
			bool bouncing = st != null && st.Type == StateType.HIT_REACTION && st.BaseStance == MasterStance.ON_THE_GROUND;
			if (bouncing || NetsuInGetUp())
			{
				return NetsuDownFrames + 1;
			}
		}
		return 0;
	}

	/// <summary>Lying on the ground in a hit reaction (Hit_Knockdown, its slide / spin, Hit_Down).</summary>
	public bool NetsuLying()
	{
		if (Body == null || StateManager == null || StanceManager == null || GetMaster() != null || !Body.IsOnGround)
		{
			return false;
		}
		FighterState state = StateManager.GetCurrentState();
		return state != null && state.Type == StateType.HIT_REACTION && state.BaseStance == MasterStance.ON_THE_GROUND;
	}

	/// <summary>How long the OTG window lasts right now: the full GameManager.NetsuOtgWindowFrames down to 50% damage
	/// scaling, then shorter and shorter, none at the lowest scaling (15%). (Oct 26 evening: it shrank from 100%
	/// before, so in a real combo it was nearly gone.)</summary>
	public int NetsuOtgWindow()
	{
		// Oct 27 c27: fixed when they land (from the combo's scaling then); OTG hits take frames off by button strength
		// (NetsuOtgHitCost) instead of shrinking it through their own damage scaling
		if (NetsuOtgWindowAtLand >= 0)
		{
			return NetsuOtgWindowAtLand;
		}
		return NetsuOtgWindowFromScaling();
	}

	/// <summary>Oct 27 c27: the OTG window set when they land (-1 = not lying). Saved for rollback (key 38).</summary>
	public int NetsuOtgWindowAtLand = -1;

	private int NetsuOtgWindowFromScaling()
	{
		GameManager gm = GameManager.Instance;
		if (gm == null || Parameters == null || Parameters.Prorations == null)
		{
			return 0;
		}
		// c20: the whole scaling range decides it now: full window at 100%, none at the lowest scaling (15%)
		int scaling = Mathf.Clamp((int)Parameters.Prorations.CurrentBaseDamageScaling, 15, 100);
		return Mathf.Min(gm.NetsuOtgWindowFrames * (scaling - 15) / 85, NetsuDownLimit());   // Oct 27 c34: by proration, never past the lying phase
	}

	/// <summary>Oct 26 c20 / c23: how long they lie before getting up: the OTG window, then 45 frames down, at least
	/// GameManager.NetsuDownTotalFrames.</summary>
	public int NetsuDownLimit()
	{
		return NetsuKdImpactFrames() + NetsuKdLyingFrames();   // Oct 27 c34: get-up starts here (frame 50 by default)
	}

	public const int NetsuOtgGetUpMargin = 0;   // Oct 27 c33 (TamaDeez): OTG and hard knockdown are one and the same: when the OTG window ends they get up at once (invincible, no input until the get-up is over). Was 45 (c23), 6 before

	/// <summary>Oct 26 c20: lying, and the knockdown isn't over yet (OTG window / NetsuDownLimit, or a super's ending).</summary>
	private bool NetsuKeepLying()
	{
		return NetsuLying() && !IsKO() && (NetsuDownFrames < NetsuDownLimit() || NetsuHeldDownBySuper());
	}

	/// <summary>Lying and still inside the OTG window: a hit that reaches them is an OTG hit.</summary>
	public bool NetsuOtgOpen()
	{
		return (NetsuDownFrames > 0 || NetsuLying()) && !IsKO() && NetsuDownFrames + NetsuOtgSpent <= NetsuOtgWindow();   // Oct 27 c34: window from proration; OTG hits eat into it (NetsuOtgSpent)
	}

	/// <summary>Lying past the OTG window, or getting up / tech-rolling on the ground: can't be hit or thrown.</summary>
	public bool NetsuWakeInvincible()
	{
		if (IsKO() || StateManager == null || StanceManager == null || GetMaster() != null)
		{
			return false;
		}
		if (NetsuDownFrames > 0 || NetsuLying())
		{
			return !NetsuOtgOpen();   // Oct 27 c34: invulnerable through impact / lying / get-up, except inside the OTG window
		}
		FighterState state = StateManager.GetCurrentState();
		int[] reactions = StanceManager.GetCurrentStance()?.HitReactions;
		if (reactions != null && reactions.Length > NetsuGetUpReaction && StateManager.CurrentState == reactions[NetsuGetUpReaction])
		{
			return true;   // Hit_GetUp
		}
		string name = state?.StateName;
		return name != null && Body != null && Body.IsOnGround && (name.StartsWith("Recovery_Ground") || name == "Recovery_OTG");
	}

	/// <summary>Oct 26 evening (TamaDeez): supers can't OTG. True when this hit comes from a super (3 bars) and the
	/// target is lying on the ground: the hit doesn't connect.</summary>
	private bool NetsuSuperOtg(SakugaActor target)
	{
		if (target == null || !target.NetsuLying())
		{
			return false;
		}
		SakugaActor root = NetsuRoot();
		if (root != null && root.NetsuSuperConnected)
		{
			return false;   // Oct 26 c14: the super's own combo (it put them down) may keep hitting
		}
		return root != null && root.StanceManager != null && root.StanceManager.CurrentMove >= 0
			&& root.StanceManager.GetCurrentMove().SuperGaugeRequired >= SakugaEngine.StanceManager.NetsuSuperCost;
	}

	/// <summary>Oct 26 evening (TamaDeez): a knockdown keeps them on the floor at most GameManager.NetsuDownTotalFrames
	/// (frames lying, from landing); then they get up (Hit_GetUp, invincible). Before, every knockdown lay 76 frames.</summary>
	private void NetsuGetUpWhenDue()
	{
		if (NetsuDownFrames > 0 && NetsuInGetUp() && NetsuDownFrames >= NetsuDownLimit() + NetsuKdGetUpFrames())
		{
			StateManager.PlayState(0, reset: true);   // Oct 27 c34: the get-up lasts exactly NetsuKdGetUpFrames ticks, whatever the animation
			return;
		}
		GameManager gm = GameManager.Instance;
		if (gm == null || NetsuDownFrames < NetsuDownLimit() || IsKO() || !NetsuLying())
		{
			return;
		}
		if (NetsuHeldDownBySuper())
		{
			return;   // c18: wait until the super's ending pose is over
		}
		int[] reactions = StanceManager.GetCurrentStance()?.HitReactions;
		if (reactions != null && reactions.Length > NetsuGetUpReaction && reactions[NetsuGetUpReaction] >= 0)
		{
			StateManager.PlayState(reactions[NetsuGetUpReaction], reset: true);
		}
	}

	/// <summary>Oct 26 c18 (TamaDeez): a fighter put on the floor by a 3-bar super stays down (no get-up) until the
	/// attacker's super, ending pose included, is over. Flan's Big Bang Crash ends with a long sweat wipe and the
	/// opponent used to get up first and counter hit her.</summary>
	public bool NetsuHeldDownBySuper()
	{
		if (IsKO() || !NetsuLying())
		{
			return false;
		}
		SakugaActor[] opponents = GetOpponents();
		SakugaActor attacker = (opponents != null && opponents.Length > 0) ? opponents[0] : null;
		if (attacker == null || attacker.StateManager == null || attacker.StateManager.CurrentStateType() != StateType.COMBAT)
		{
			return false;
		}
		// Oct 29: a state marked NetsuHoldDown (Noah's j.214A landing) keeps them down until it's over
		FighterState holdState = attacker.StateManager.GetCurrentState();
		if (holdState != null && holdState.NetsuHoldDown && (holdState.AnimationData == null || attacker.StateManager.CurrentStateFrame < holdState.AnimationData.Duration - 1))
		{
			GameManager gmHold = GameManager.Instance;
			return NetsuDownFrames < (gmHold != null ? gmHold.NetsuDownTotalFrames : 50) + NetsuSuperHoldMax;
		}
		if (!attacker.NetsuSuperActive || !attacker.NetsuSuperConnected)
		{
			return false;
		}
		// c20: never wait for a super that is itself waiting for us to recover (Cecilia's counter super holds its sheathe
		// pose until the opponent is out of hit reaction: both waited for good), nor one past its animation's end; and
		// never more than NetsuSuperHoldMax frames past the usual get-up time.
		FighterState st = attacker.StateManager.GetCurrentState();
		if (st == null || NetsuWaitsForOpponent(st) || (st.AnimationData != null && attacker.StateManager.CurrentStateFrame >= st.AnimationData.Duration - 1))
		{
			return false;
		}
		GameManager gm = GameManager.Instance;
		int usual = gm != null ? gm.NetsuDownTotalFrames : 50;
		return NetsuDownFrames < usual + NetsuSuperHoldMax;
	}

	public const int NetsuSuperHoldMax = 150;

	/// <summary>Oct 29: knocked out by a hit while lying (NetsuDamageOpponentAction): Hit_Down plays its KO from its start.</summary>
	public void NetsuKoWhileLying()
	{
		if (!IsKO() || StateManager == null || StanceManager == null || !NetsuLying())
		{
			return;
		}
		int[] reactions = StanceManager.GetCurrentStance()?.HitReactions;
		if (reactions != null && reactions.Length > NetsuDownReaction && (StateManager.CurrentState != reactions[NetsuDownReaction] || StateManager.CurrentStateFrame > 4))
		{
			StateManager.PlayState(reactions[NetsuDownReaction], reset: true);
		}
	}

	private static bool NetsuWaitsForOpponent(FighterState st)
	{
		return NetsuHasOpponentCheck(st.TransitionEvents) || NetsuHasOpponentCheck(st.OnTickEvents);
	}

	private static bool NetsuHasOpponentCheck(FrameDataEvent[] events)
	{
		for (int i = 0; events != null && i < events.Length; i++)
		{
			FrameDataCondition[] conds = events[i]?.Conditions;
			for (int j = 0; conds != null && j < conds.Length; j++)
			{
				if (conds[j] is NetsuOpponentHitReactionCondition)
				{
					return true;
				}
			}
		}
		return false;
	}

	/// <summary>Where the stance's HitReactions list keeps Hit_Down and Hit_GetUp (the same for every fighter).</summary>
	public const int NetsuDownReaction = 17;
	public const int NetsuGetUpReaction = 18;

	/// <summary>An OTG hit (HitDamage on a fighter lying inside the OTG window): damage, hitstop, meter and the combo
	/// counter, but no new hit reaction, knockback, hitstun or bounce: they stay down.</summary>
	private void NetsuOtgHit(SakugaActor attacker, HitboxElement box, bool isTrade)
	{
		attacker.NetsuOtgJustHit = true;   // Oct 27: HitConfirm then skips the attacker's on-hit events (hit-grabs, follow-up animations)
		NetsuCounterHitstunBonus = 0;
		if (CanHitstop())
		{
			if (!isTrade)
			{
				Hitstop.Start((uint)box.OpponentHitStopDuration);
			}
			else
			{
				Hitstop.Stop();
			}
		}
		if (Parameters == null)
		{
			return;
		}
		int finalAttack = (attacker.Parameters.Prorations != null) ? attacker.Parameters.Prorations.CurrentAttack : attacker.Data.BaseAttack;
		int finalDamage = Parameters.CalculateProrations(box.BaseDamage, finalAttack, Parameters.Prorations.CurrentDefense, (ushort)box.DamageScalingSubtract, NetsuScalingKind(attacker));
		finalDamage = attacker.Parameters.OverdriveDamage(finalDamage);
		NetsuRepeatDecay(attacker);   // Oct 27 c27: an OTG hit is a use of the move too (repeat proration)
		finalDamage = finalDamage * NetsuRepeatDamagePercent[Mathf.Clamp(NetsuLastRepeatUses, 0, 3)] / 100;   // Oct 28: same move again
		finalDamage = Parameters.NetsuOverdriveTaken(finalDamage);   // Oct 28: Overdrive takes 10% less
		Parameters.TakeDamage(finalDamage, box.OpponentSuperGaugeGain, box.KillingBlow);
		NetsuMeterOnHit(attacker, finalDamage);   // Oct 29: Craft Gauge / Burst for both sides
		Parameters.Tracker.UpdateTrackers(finalDamage, 0, 0, (int)box.HitType, false);
		NetsuOtgSpent += NetsuOtgHitCost(attacker);   // Oct 27 c27: OTG hits shorten the window a little, more for stronger buttons
		if (IsKO() && StateManager != null && StanceManager != null)
		{
			// knocked out while lying: Hit_Down plays its KO from its start (it checks the health on its 4th frame)
			int[] reactions = StanceManager.GetCurrentStance()?.HitReactions;
			if (reactions != null && reactions.Length > NetsuDownReaction && (StateManager.CurrentState != reactions[NetsuDownReaction] || StateManager.CurrentStateFrame > 4))
			{
				StateManager.PlayState(reactions[NetsuDownReaction], reset: true);
			}
		}
	}

	public int InputSide(InputSideCheck sideCheck = InputSideCheck.CHARACTER_RELATIVE)
	{
		switch (sideCheck)
		{
		case InputSideCheck.ABSOLUTE:
			return 1;
		case InputSideCheck.SIDE_RELATIVE:
			if (!Body.IsLeftSide)
			{
				return -1;
			}
			return 1;
		case InputSideCheck.CHARACTER_RELATIVE:
			return Body.PlayerSide;
		default:
			return 1;
		}
	}

	public StanceSelect SelectBlockStance()
	{
		if (IsGroundState())
		{
			return StanceSelect.GROUND;
		}
		if (IsCrouchState())
		{
			return StanceSelect.CROUCH;
		}
		return StanceSelect.AIR;
	}

	public override void Initialize()
	{
		base.Initialize();
		actor = this;
		if (Body != null)
		{
			Body.Initialize(this, this);
			Body.FixedPosition.X = 12500 * (-1 + (int)(playerID * 2));
			Body.UpdateSide(Mathf.Sign(Body.FixedPosition.X) < 0);
			Body.FlipSide();
		}
		if (StanceManager != null)
		{
			StanceManager.Initialize(this);
		}
		if (StateManager != null)
		{
			StateManager.Initialize(this);
		}
		if (Parameters != null)
		{
			Parameters.Initialize(this);
		}
		if (Pool != null)
		{
			Pool.Initialize(this);
		}
		FrameProperties = InitialProperties;
		HitCheck = AllowHit;
	}

	public void InitializeBrain(bool active, BotDifficulty diff)
	{
		if (Brain != null)
		{
			UseAI = active;
			Brain.Initialize(this, diff);
		}
	}

	public void Reset()
	{
		IsActive = StartActive;
		if (Body != null)
		{
			Body.FixedPosition.X = 12500 * (-1 + (int)(playerID * 2));
			Body.FixedPosition.Y = 0;
			Body.SetVelocity(Vector2I.Zero);
			Body.UpdateSide(Mathf.Sign(Body.FixedPosition.X) < 0);
			Body.FlipSide();
		}
		if (StanceManager != null)
		{
			StanceManager.CallStance(0);
		}
		if (StateManager != null)
		{
			StateManager.Reset();
		}
		if (Parameters != null)
		{
			Parameters.Reset();
		}
		if (Pool != null)
		{
			Pool.Reset();
		}
		FrameProperties = InitialProperties;
		HitCheck = AllowHit;
		NetsuAirTechClear();
		NetsuStarStacks = 0;   // Oct 29: Flan's stars start empty every round
		if (NetsuAssist != null)
		{
			NetsuAssist.ResetRound();   // Netsu: the assist leaves and its gauge refills for the new round
		}
	}

	public override void PreTick()
	{
		if (!IsActive)
		{
			return;
		}
		if (Parameters != null && GetMaster() == null)
		{
			Parameters.NetsuResourceTick();   // Oct 29: meter cooldown, low-health meter, Burst recharge (runs in hitstop too)
		}
		if (CanHitstop())
		{
			Hitstop.Run();
		}
		if (Body != null)
		{
			Body.IsMovable = !OnHitstop();
		}
		if (SuperFlashing && !OnHitstop())
		{
			SuperFlashing = false;
		}
		if (OnHitstop())
		{
			return;
		}
		NetsuDownFrames = NetsuKnockdownTick();   // Netsu (Oct 26): OTG window / wake-up; Oct 27 c34: the whole hard knockdown
		if (NetsuDownFrames == 0)
		{
			NetsuOtgWindowAtLand = -1;
			NetsuOtgSpent = 0;
		}
		else if (NetsuOtgWindowAtLand < 0)
		{
			NetsuOtgWindowAtLand = NetsuOtgWindowFromScaling();   // Oct 27 c27: the OTG window is set on landing
		}
		if (NetsuLandLag > 0)
		{
			NetsuLandLag--;
		}
		bool netsuAir = Body != null && !Body.IsOnGround;
		if (!netsuAir)
		{
			if (NetsuWasAir && NetsuAirAttackLag > 0 && StateManager.CurrentStateType() != StateType.HIT_REACTION)
			{
				NetsuLandLag = NetsuAirAttackLag;   // Netsu (Oct 26 late): landing recovery after an air normal
			}
			NetsuAirAttackLag = 0;
		}
		NetsuWasAir = netsuAir;
		NetsuAirTechTick();   // Netsu (Oct 28): air tech lockout / invincibility
		if (StateManager.CurrentStateType() != StateType.COMBAT)
		{
			NetsuChainUsed = 0;   // Netsu (Oct 26 late): out of her moves: a new chain
			if (StanceManager == null || StanceManager.CurrentMove < 0)
			{
				NetsuSuperActive = false;   // the super (and its follow-ups) is over
				NetsuSuperConnected = false;
				NetsuMeterSpendTag = false;   // Oct 29: the meter-spending move (and its follow-ups) is over
			}
		}
		if (NetsuAirMoveUsed && Body != null && Body.IsOnGround && StateManager.CurrentStateType() != StateType.COMBAT)
		{
			NetsuAirMoveUsed = false;   // Netsu (Oct 26 late): landed: the once-per-jump moves are back
		}
		NetsuGetUpWhenDue();
		if (CanHitstun() && HitstunType < HitstunType.HARD_KNOCKDOWN)
		{
			Hitstun.Run();
		}
		if (NetsuAirCounterLock)
		{
			// Netsu (Oct 26 c15): air counter hit: the hitstun can't run out (so no tech) until she touches the floor
			if (Body == null || Body.IsOnGround || IsKO() || StateManager.CurrentStateType() != StateType.HIT_REACTION)
			{
				NetsuAirCounterLock = false;
			}
			else if (CanHitstun() && Hitstun.TimeLeft <= 1)
			{
				Hitstun.Start(2u);
			}
		}
		NetsuComboFrames = (StateManager.CurrentStateType() == StateType.HIT_REACTION && Parameters != null && Parameters.Tracker != null
			&& Parameters.Tracker.HitCombo > 0) ? NetsuComboFrames + 1 : 0;
		if (NetsuComboFrames == 0)
		{
			NetsuRecoveryScale = 0;   // Oct 28: the combo is over: recovery scale back to 1.0
			NetsuComboUsedLo = 0;   // Oct 27 c27: combo over: the moves used in it are forgotten (repeat proration)
			NetsuComboUsedHi = 0;
			NetsuComboUseA = 0;
			NetsuComboUseB = 0;
			NetsuComboUseC = 0;
			NetsuBounceUsedLo = 0;   // Oct 29: ground bounces used in the combo are forgotten too
			NetsuBounceUsedHi = 0;
			NetsuBounceUse = 0;
		}
		// Netsu (Oct 25): blockstun lasts as long as the attack's blockstun says (GroundBlockstun / AirBlockstun). Before
		// this the check below stopped the stun timer every frame for blocking states too, so a blocked attack held the
		// defender only for the hitstop: every move was about -10 to -15 on block, whatever its blockstun was.
		bool netsuBlockstun = BlockStun && StateManager.CurrentStateType() == StateType.BLOCKING && CanHitstun() && Hitstun.IsRunning();
		if (StateManager.CurrentStateType() != StateType.HIT_REACTION && !netsuBlockstun)
		{
			if (CanHitstun())
			{
				Hitstun.Stop();
			}
			HitstunType = HitstunType.NONE;
			BlockStun = false;
			NetsuNoBurst = false;   // Netsu (Oct 26): the combo is over: Burst is allowed again
			if (Parameters != null)
			{
				Parameters.Clear();
			}
		}
		// Netsu (Oct 24 night): can't be thrown in block / hit stun, nor for a few frames after it (a throw right as
		// blockstun ends, or on wake-up, would be unbreakable pressure). Saved for rollback (SakugaActorState).
		StateType netsuType = StateManager.CurrentStateType();
		if (netsuType == StateType.BLOCKING || netsuType == StateType.HIT_REACTION)
		{
			NetsuThrowProtect = NetsuThrowProtectFrames;
		}
		else if (NetsuThrowProtect > 0)
		{
			NetsuThrowProtect--;
		}
		if (Parameters != null)
		{
			Parameters.Tick();
		}
		NetsuFastReactionTick();
		int netsuPrevState = StateManager.CurrentState;   // Oct 29 (later): see NetsuNoFreeFall
		bool netsuWasHit = StateManager.CurrentStateType() == StateType.HIT_REACTION;
		bool netsuHoldDown = StateManager != null && NetsuKeepLying()
			&& StateManager.CurrentStateFrame >= StateManager.GetCurrentState().AnimationData.Duration - 2;   // c18/c20: stay down
		if (StateManager != null && !IsStunLocked() && !netsuHoldDown)
		{
			StateManager.RunState();
		}
		FrameDataEvent[] transitionEvents = StateManager.GetCurrentState().TransitionEvents;
		for (int i = 0; transitionEvents != null && i < transitionEvents.Length; i++)   // Netsu: a state may have none
		{
			transitionEvents[i].RunEvent(ref actor);
		}
		NetsuNoFreeFall(netsuPrevState, netsuWasHit);
	}

	/// <summary>Netsu (Oct 29 2026, TamaDeez): no free fall out of a dropped air combo. Some air hit reactions (Hit_Air_Weak)
	/// end into the plain Falling state, from which they could attack straight away (j.A) without ever teching. Now an
	/// airborne fighter whose hit reaction ends stays in it (holding its last frame, still falling) until they air tech
	/// (they may tech late, or not at all) or land; landing then plays out as usual.</summary>
	private void NetsuNoFreeFall(int prevState, bool wasHit)
	{
		if (!wasHit || Body == null || Body.IsOnGround || IsKO() || GetMaster() != null || StateManager == null || Data == null
			|| Data.States == null || prevState < 0 || prevState >= Data.States.Length || HitstunType == HitstunType.GRABBED)
		{
			return;
		}
		StateType t = StateManager.CurrentStateType();
		if (t == StateType.HIT_REACTION || t == StateType.BLOCKING || StateManager.CurrentState == prevState)
		{
			return;
		}
		string n = StateManager.GetCurrentState()?.StateName;
		if (n != null && n.StartsWith("Recovery_"))
		{
			return;
		}
		FighterState old = Data.States[prevState];
		StateManager.CurrentState = prevState;
		StateManager.CurrentStateFrame = Mathf.Max(0, (old.AnimationData != null ? old.AnimationData.Duration : 1) - 1);
	}

	public override void Tick()
	{
		if (!IsActive)
		{
			return;
		}
		// Netsu (Oct 24 night): throw breaks. A grabbed fighter is frozen for the throw's hitstop (the break window);
		// pressing the stance's ThrowEscapeInput (B+C) then breaks it (Mahou had the code but nothing called it)
		if (IsGrabbed() && OnHitstop() && StanceManager != null && GetOpponent(0) != null)
		{
			ThrowEscape(GetOpponent(0));
		}
		if (StanceManager != null)
		{
			StanceManager.CheckMoves();
		}
		if (!OnHitstop())
		{
			FrameDataEvent[] onTickEvents = StateManager.GetCurrentState().OnTickEvents;
			for (int i = 0; onTickEvents != null && i < onTickEvents.Length; i++)
			{
				onTickEvents[i].RunEvent(ref actor);
			}
			NetsuFloatTick();   // after the hit state's own gravity, before the physics step
			NetsuCarryTick();
			NetsuNeutralTechTick();
			NetsuExHoldTick();
		}
	}

	// ---------------------------------------------------------------------------------------------
	// Netsu (Oct 29 2026, TamaDeez): EX moves keep the opponent airborne until they're finished. After an EX move's hit
	// they can't fall (only rise) and can't tech while the attacker is still in that EX move and its current state still
	// has attack frames to come; then everything is normal again. Saved for rollback (SakugaActorState key 53).
	public int NetsuExHoldKey;   // the EX use holding them (0 = none)
	// Oct 29 (late): the attacker's state and state frame at the EX's last hit. The hold only lasts until the EX's NEXT
	// attack has had its chance: if that one misses (they fell out), they fall and can tech as usual. Keys 56-57.
	public int NetsuExHoldState = -1;
	public int NetsuExHoldFrame;
	// Oct 29 (evening): frames since the EX last hit them (hitstop not counted). Past GameManager.NetsuExHoldGraceFrames
	// the hold lets go even if the EX still has attack frames (Cecilia's 623C dive on an airborne opponent). Key 58.
	public int NetsuExHoldAge;

	private void NetsuExHoldStart(SakugaActor attacker, int knockbackY = 0)
	{
		NetsuExHoldKey = 0;
		// Nov 3 (TamaDeez): a slam (a hit that sends them DOWN: Flan's 214C punch, Leticia's 623C finisher) never holds
		// them up. The hold zeroed the slam's fall, and LaunchDown has no gravity of its own, so they hung in the air,
		// drifting across the screen, and with a hard knockdown they could never tech. It also ends any earlier hold.
		if (knockbackY < 0)
		{
			return;
		}
		if (!NetsuHitMove(attacker, out SakugaActor root, out int move, out int use) || root.StanceManager == null)
		{
			return;
		}
		MoveSettings m = root.StanceManager.GetMove(move);
		if (m == null || m.SuperGaugeRequired <= 0 || m.SuperGaugeRequired >= SakugaEngine.StanceManager.NetsuSuperCost || m.MoveName == null || m.MoveName.Contains("Pushblock") || m.MoveName.Contains("Breakthrough"))
		{
			return;   // EX moves only (supers and pushblock aren't)
		}
		NetsuExHoldKey = (1 << 30) | (move << 22) | (use & 0x3FFFFF);
		NetsuExHoldState = root.StateManager != null ? root.StateManager.CurrentState : -1;
		NetsuExHoldFrame = root.StateManager != null ? root.StateManager.CurrentStateFrame : 0;
		NetsuExHoldAge = 0;
	}

	/// <summary>The attacker is still in the EX use NetsuExHoldKey and its state has attack frames left.</summary>
	private bool NetsuExStillGoing(SakugaActor a)
	{
		if (a == null || a.StanceManager == null || a.StateManager == null || a.StanceManager.CurrentMove < 0)
		{
			return false;
		}
		int key = (1 << 30) | (a.StanceManager.CurrentMove << 22) | (a.StanceManager.ExecutedMoves & 0x3FFFFF);
		if (key != NetsuExHoldKey || a.StateManager.CurrentStateType() != StateType.COMBAT)
		{
			return false;
		}
		AnimationData anim = a.StateManager.GetCurrentState().AnimationData;
		if (anim == null || anim.Hitboxes == null)
		{
			return false;
		}
		// Oct 29 (late): hold until the end of the first attack window that starts after the last hit (in the state that
		// hit; in a follow-up state, its first attack window). No such window: until the end of the one that hit.
		bool sameState = a.StateManager.CurrentState == NetsuExHoldState;
		int hitFrame = sameState ? NetsuExHoldFrame : -1;
		int nextEnd = -1;
		int nextStart = int.MaxValue;
		int curEnd = -1;
		int lastEnd = -1;
		for (int w = 0; w < anim.Hitboxes.Length; w++)
		{
			HitboxState win = anim.Hitboxes[w];
			if (win == null || win.HitboxData == null || win.HitboxData.Hitboxes == null)
			{
				continue;
			}
			bool damage = false;
			foreach (HitboxElement e in win.HitboxData.Hitboxes)
			{
				if (e != null && e.BaseDamage > 0)
				{
					damage = true;
					break;
				}
			}
			if (!damage)
			{
				continue;
			}
			int end = anim.Duration;   // the window lasts until the next one starts
			for (int n = 0; n < anim.Hitboxes.Length; n++)
			{
				if (anim.Hitboxes[n] != null && anim.Hitboxes[n].AtFrame > win.AtFrame && anim.Hitboxes[n].AtFrame < end)
				{
					end = anim.Hitboxes[n].AtFrame;
				}
			}
			lastEnd = Mathf.Max(lastEnd, end);
			if (win.AtFrame > hitFrame && win.AtFrame < nextStart)
			{
				nextStart = win.AtFrame;
				nextEnd = end;
			}
			if (win.AtFrame <= hitFrame && end >= hitFrame)
			{
				curEnd = Mathf.Max(curEnd, end);
			}
		}
		int deadline = nextEnd >= 0 ? nextEnd : curEnd;
		return deadline >= 0 && a.StateManager.CurrentStateFrame <= Mathf.Min(deadline, lastEnd);
	}

	private void NetsuExHoldTick()
	{
		if (NetsuExHoldKey == 0)
		{
			return;
		}
		NetsuExHoldAge++;
		int grace = GameManager.Instance != null ? GameManager.Instance.NetsuExHoldGraceFrames : 20;
		if (IsKO() || StateManager.CurrentStateType() != StateType.HIT_REACTION || NetsuExHoldAge > grace || !NetsuExStillGoing(GetOpponent(0))
			|| HitstunType >= HitstunType.HARD_KNOCKDOWN)   // Nov 3: a hard knockdown is never held up (it must land)
		{
			NetsuExHoldKey = 0;
			return;
		}
		if (Body != null && !Body.IsOnGround && Body.FixedVelocity.Y < 0)
		{
			Body.FixedVelocity.Y = 0;   // kept up: no falling out of the EX
		}
		if (CanHitstun() && Hitstun.TimeLeft <= 1)
		{
			Hitstun.Start(2u);   // no tech until the EX is over
		}
	}

	// ---------------------------------------------------------------------------------------------
	// Netsu (Oct 28 2026, TamaDeez): float. A hit box with NetsuFloatFrames (Leticia's j.236) makes an opponent hit in the
	// air float: a slow arc that peaks NetsuFloatRise units up, NetsuFloatRiseFrames frames after the hit, until
	// NetsuFloatFrames frames after the hit; then they fall as usual. The hit's untech time (juggle / recovery scaling) still runs, so late
	// in a long combo they tech out of it. Ends early if they land, tech (leave the hit reaction) or are hit by something else. Saved for rollback (SakugaActorState keys 47-49).
	public int NetsuFloatFrame;
	public int NetsuFloatTotal;
	public int NetsuFloatRise;   // rise * 64 + rise frames

	private void NetsuFloatStart(HitboxElement box)
	{
		if (box == null || box.NetsuFloatFrames <= 0 || Body == null || (Body.IsOnGround && !box.NetsuFloatFromGround))
		{
			NetsuFloatFrame = 0;
			return;
		}
		NetsuFloatFrame = 1;
		NetsuFloatTotal = box.NetsuFloatFrames;
		NetsuFloatRise = Mathf.Max(0, box.NetsuFloatRise) * 64 + Mathf.Clamp(box.NetsuFloatRiseFrames, 1, 63);
	}

	// ---------------------------------------------------------------------------------------------
	// Netsu (Oct 29 2026, TamaDeez): carry. A hit box with NetsuCarryUp (Flan's 7/8/9 Star Rush) makes the opponent move
	// with the attacker, at her speed, while she is still rising: they stay where the hit put them (just above / in
	// front of her). At her peak (or if she is hit, blocks or lands) they are let go: no more rising, normal gravity,
	// and at least NetsuCarryReleaseHitstun frames of hitstun left so she can combo. Saved for rollback (key 59).
	public int NetsuCarryFrames;   // 0 = not carried; else 1 + frames carried
	public const int NetsuCarryReleaseHitstun = 22;
	public const int NetsuCarryMaxFrames = 45;

	private void NetsuCarryStart(SakugaActor attacker, HitboxElement box)
	{
		NetsuCarryFrames = (box != null && box.NetsuCarryUp && attacker != null && attacker.GetMaster() == null && GetMaster() == null && Body != null && attacker.Body != null) ? 1 : 0;
	}

	private void NetsuCarryTick()
	{
		if (NetsuCarryFrames <= 0)
		{
			return;
		}
		SakugaActor a = GetOpponent(0);
		bool going = a != null && a.Body != null && a.StateManager != null && Body != null && !IsKO()
			&& StateManager.CurrentStateType() == StateType.HIT_REACTION
			&& a.StateManager.CurrentStateType() != StateType.HIT_REACTION && a.StateManager.CurrentStateType() != StateType.BLOCKING
			&& a.Body.FixedVelocity.Y > 0 && NetsuCarryFrames <= NetsuCarryMaxFrames;
		if (!going)
		{
			bool stillHit = Body != null && !IsKO() && StateManager.CurrentStateType() == StateType.HIT_REACTION;
			NetsuCarryFrames = 0;
			if (stillHit)
			{
				Body.FixedVelocity.Y = Mathf.Min(Body.FixedVelocity.Y, 0);   // the peak: from here they fall
				if (a != null && a.Body != null)
				{
					Body.FixedVelocity.X = a.Body.FixedVelocity.X / 2;
				}
				if (CanHitstun() && Hitstun.TimeLeft < NetsuCarryReleaseHitstun)
				{
					Hitstun.Start((uint)NetsuCarryReleaseHitstun);
				}
			}
			return;
		}
		Body.FixedVelocity = new Vector2I(a.Body.FixedVelocity.X, a.Body.FixedVelocity.Y);
		if (CanHitstun() && Hitstun.TimeLeft <= 1)
		{
			Hitstun.Start(2u);   // no tech while carried
		}
		NetsuCarryFrames++;
	}

	// ---------------------------------------------------------------------------------------------
	// Netsu (Oct 29 2026, TamaDeez): forced air tech. When the untech time of an air hit runs out they ALWAYS air tech
	// (white flash, the usual lockout and invincibility): no more dropping out of a combo and mashing a button straight
	// away. Holding forward techs forward, back techs back, nothing held techs straight down (the forward tech with no
	// sideways motion). Hard knockdowns, throws, floats and other holds don't tech. Saved for rollback (keys 60-63).
	public bool NetsuNeutralTech;

	private void NetsuForcedAirTech()
	{
		if (StanceManager == null || StateManager == null || Body == null || Body.IsOnGround || IsKO() || GetMaster() != null
			|| StateManager.CurrentStateType() != StateType.HIT_REACTION)
		{
			return;
		}
		if ((CanHitstun() && Hitstun.IsRunning()) || NetsuFloatFrame > 0 || NetsuCarryFrames > 0)
		{
			return;
		}
		if (HitstunType != HitstunType.BASIC && HitstunType != HitstunType.KNOCKDOWN)
		{
			return;
		}
		StanceManager.NetsuForceAirTech();
	}

	private void NetsuNeutralTechTick()
	{
		if (!NetsuNeutralTech)
		{
			return;
		}
		string n = StateManager?.GetCurrentState()?.StateName;
		if (n == null || !n.StartsWith("Recovery_Air") || Body == null)
		{
			NetsuNeutralTech = false;
			return;
		}
		Body.FixedVelocity.X = 0;
	}

	// Oct 29: a hit reaction played faster (HitboxElement.NetsuReactionSpeedPercent)
	public int NetsuFastState = -1;
	public int NetsuFastPct;
	public int NetsuFastAcc;

	private void NetsuFastReactionTick()
	{
		if (NetsuFastState < 0 || StateManager == null)
		{
			return;
		}
		if (StateManager.CurrentState != NetsuFastState || StateManager.CurrentStateType() != StateType.HIT_REACTION)
		{
			NetsuFastState = -1;
			return;
		}
		int last = StateManager.GetCurrentState().AnimationData != null ? StateManager.GetCurrentState().AnimationData.Duration - 1 : 0;
		NetsuFastAcc += NetsuFastPct - 100;
		while (NetsuFastAcc >= 100 && StateManager.CurrentStateFrame < last - 1)
		{
			StateManager.CurrentStateFrame++;
			NetsuFastAcc -= 100;
		}
	}

	private void NetsuFloatTick()
	{
		if (NetsuFloatFrame <= 0)
		{
			return;
		}
		if (Body == null || (Body.IsOnGround && NetsuFloatFrame > 1) || IsKO() || StateManager.CurrentStateType() != StateType.HIT_REACTION || NetsuFloatFrame > NetsuFloatTotal)
		{
			NetsuFloatFrame = 0;   // over: normal gravity from here
			return;
		}
		int riseFrames = NetsuFloatRise & 63;
		int rise = NetsuFloatRise >> 6;
		// Oct 28 (TamaDeez): a light, natural float, not a freeze: a slow arc under very low gravity. They rise `rise`
		// units, reaching the top riseFrames frames after the hit, then start sinking just as gently. Their sideways
		// drift from the hit is left alone.
		int v0 = rise * 2 * 60 / riseFrames;
		Body.FixedVelocity.Y = v0 * (riseFrames - (NetsuFloatFrame - 1)) / riseFrames;
		NetsuFloatFrame++;   // Oct 28: the untech time still runs: with enough of it left they can tech out of the float
	}

	public override void LateTick()
	{
		if (IsActive)
		{
			OnHitstop();
		}
	}

	public override void Render()
	{
		// Netsu: the fighter being hit shakes during hitstop (visual only, BlazBlue-style).
		// ~3 px on hit, ~1.5 px on block, flips every 2 frames and fades out with the hitstop.
		float netsuShake = 0f;
		if (Hitstop != null && Hitstun != null && Hitstop.IsRunning() && Hitstun.IsRunning())
		{
			uint t = Hitstop.TimeLeft;
			float amp = (BlockStun ? 0.008f : 0.0165f) * Mathf.Min(1f, t / 6f);
			netsuShake = ((t / 2) % 2 == 0) ? amp : -amp;
		}
		Node3D[] graphics = Graphics;
		foreach (Node3D obj in graphics)
		{
			obj.Visible = IsActive;
			obj.GlobalPosition = GlobalFunctions.ToScaledVector3(Body.FixedPosition) + new Vector3(netsuShake, 0f, 0f);
			obj.GlobalRotation = Vector3.Zero;
			float netsuK = (Data != null && Data.NetsuScale > 0 && GetMaster() == null) ? Data.NetsuScale / 1000f : 1f;   // Netsu: fighter size
			obj.Scale = new Vector3(Body.PlayerSide * netsuK, netsuK, 1f);
		}
		if (Animator != null)
		{
			Animator.SetDepth(LayerSorting);
			Animator.ViewAnimations(NetsuPauseAnimation() ?? StateManager.GetCurrentAnimationSettings(), Body != null && Body.HitBodies.Count > 0);
			AnimationData netsuAnim = StateManager.GetCurrentState().AnimationData;
			Animator.SetAfterimages(netsuAnim != null && netsuAnim.Afterimages, netsuAnim != null && netsuAnim.NetsuSolidAfterimages);
			NetsuSuperFlashLook();
			NetsuChargeFlareLook();
		}
		NetsuStockHud();
		NetsuStarHud();
		NetsuOverdriveHud();
		NetsuJuggleHud();
	}

	// Netsu (Oct 26 c15): the juggle meter under the attacker's combo counter (game/ui/battle_hud/netsu_hud.gd through
	// MatchSetup.netsu_juggle_hud): this fighter's hitstun left / at the last hit, the juggle decay (per mille), the air
	// counter lock and whether the combo has gone invalid. Presentation only; sent when it changes.
	private static readonly StringName NetsuJuggleMethod = new StringName("netsu_juggle_hud");
	private bool _jugChecked;
	private Node _jugHud;
	private long _jugShown = long.MinValue;

	private void NetsuJuggleHud()
	{
		if (GetMaster() != null || Parameters == null || Parameters.Tracker == null)
		{
			return;
		}
		if (!_jugChecked)
		{
			_jugChecked = true;
			_jugHud = (Engine.GetMainLoop() as SceneTree)?.Root.GetNodeOrNull("MatchSetup");
			if (_jugHud != null && !_jugHud.HasMethod(NetsuJuggleMethod))
			{
				_jugHud = null;
			}
		}
		if (_jugHud == null)
		{
			return;
		}
		bool active = Parameters.Tracker.HitCombo > 0 && StateManager.CurrentStateType() == StateType.HIT_REACTION;
		int left = active ? (int)Hitstun.TimeLeft : 0;
		int max = active ? Mathf.Max(1, NetsuUntechMax) : 1;
		int decay = active ? NetsuJuggleDecayPermille() : 0;
		bool locked = active && NetsuAirCounterLock;
		bool invalid = active && Parameters.Tracker.invalidHit;
		bool down = active && HitstunType >= HitstunType.HARD_KNOCKDOWN;
		// c20: lying: the OTG window left (frames they can still be hit on the floor) out of the whole window
		bool lying = active && (NetsuDownFrames > 0 || NetsuLying());
		int otgMax = lying ? NetsuOtgWindow() : 0;
		int otgLeft = lying ? Mathf.Max(0, otgMax - NetsuDownFrames - NetsuOtgSpent) : 0;
		long key = ((long)left << 40) ^ ((long)max << 28) ^ ((long)decay << 12) ^ (locked ? 1L : 0L) ^ (invalid ? 2L : 0L) ^ (active ? 4L : 0L) ^ (down ? 8L : 0L)
			^ ((long)otgLeft << 50) ^ ((long)otgMax << 20) ^ (lying ? 16L : 0L);
		if (key == _jugShown)
		{
			return;
		}
		_jugShown = key;
		_jugHud.Call(NetsuJuggleMethod, (int)playerID, active, left, max, decay, locked, invalid, down, lying, otgLeft, otgMax);
	}

	// Netsu (Oct 26 evening): the Overdrive timer next to the Burst gauge and the stage's dark tint while it runs
	// (netsu_hud.gd / netsu_super_flash.gd through MatchSetup.netsu_overdrive_hud). Sent when the tenths change.
	private static readonly StringName NetsuOverdriveMethod = new StringName("netsu_overdrive_hud");
	private int _odShown = int.MinValue;
	private bool _odChecked;
	private Node _odHud;

	private void NetsuOverdriveHud()
	{
		if (GetMaster() != null || Parameters == null || Data == null)
		{
			return;
		}
		if (!_odChecked)
		{
			_odChecked = true;
			_odHud = (Engine.GetMainLoop() as SceneTree)?.Root.GetNodeOrNull("MatchSetup");
			if (_odHud != null && !_odHud.HasMethod(NetsuOverdriveMethod))
			{
				_odHud = null;
			}
		}
		if (_odHud == null)
		{
			return;
		}
		// Oct 28: bit 1 = in Overdrive (red health bar, flash when it starts), bit 2 = its assist Link is still unused
		int frames = Parameters.InOverdrive() ? 1 : 0;
		if (frames != 0 && (Parameters.NetsuOverdriveLinkPending || (NetsuAssist != null && (NetsuAssist.LinkReady || NetsuAssist.LinkCall))))
		{
			frames |= 2;
		}
		int tenths = frames;
		if (tenths == _odShown)
		{
			return;
		}
		_odShown = tenths;
		_odHud.Call(NetsuOverdriveMethod, (int)playerID, frames);
	}

	// Netsu (Oct 26, TamaDeez): a fighter with a custom variable named "Stock" (Noah: energy stocked by 214 for his
	// Overflow Ray) shows a READY icon under its Burst gauge while it's 1 or more (game/ui/battle_hud/netsu_hud.gd,
	// through MatchSetup.netsu_stock_hud). Presentation only; sent when it changes (and every 15 renders).
	private static readonly StringName NetsuStockMethod = new StringName("netsu_stock_hud");
	private int _stockIndex = -2;
	private int _stockShown = int.MinValue;
	private int _stockQuiet;
	private Node _stockHud;

	private void NetsuStockHud()
	{
		if (_stockIndex == -1 || GetMaster() != null || Parameters == null || Parameters.Variables == null)
		{
			return;
		}
		if (_stockIndex == -2)
		{
			_stockIndex = -1;
			for (int i = 0; i < Parameters.Variables.Length; i++)
			{
				if (Parameters.Variables[i] != null && Parameters.Variables[i].Name == "Stock")
				{
					_stockIndex = i;
					break;
				}
			}
			_stockHud = (Engine.GetMainLoop() as SceneTree)?.Root.GetNodeOrNull("MatchSetup");
			if (_stockHud != null && !_stockHud.HasMethod(NetsuStockMethod))
			{
				_stockHud = null;
			}
			if (_stockIndex < 0 || _stockHud == null)
			{
				_stockIndex = -1;
				return;
			}
		}
		int value = Parameters.Variables[_stockIndex].CurrentValue;
		_stockQuiet++;
		if (value == _stockShown && _stockQuiet < 15)
		{
			return;
		}
		_stockQuiet = 0;
		_stockShown = value;
		_stockHud.Call(NetsuStockMethod, (int)playerID, value);
	}

	/// <summary>Netsu (Oct 25): while the EX / super pause holds the fight (GameManager.NetsuPause) and this fighter
	/// started it with a move that has a NetsuPauseState, her picture plays that state's animation (from its first
	/// frame, looping) instead of standing frozen: Flan's 214 super twirls, charging the punch. Only the picture:
	/// nothing moves, nothing hits. Worked out from the match state every render (rollback needs nothing).</summary>
	private AnimationSettings NetsuPauseAnimation()
	{
		GameManager gm = GameManager.Instance;
		if (gm == null || gm.NetsuPause <= 0 || gm.NetsuPauseSide != (int)playerID || GetMaster() != null
			|| StanceManager == null || StanceManager.CurrentMove < 0 || StateManager == null)
		{
			return null;
		}
		int index = StanceManager.GetCurrentMove().NetsuPauseState;
		if (StanceManager.GetCurrentMove().MoveName == SakugaEngine.StanceManager.NetsuOverdriveName)
		{
			index = NetsuVictoryState();   // Netsu (Oct 26 evening): Overdrive activation = her win pose
		}
		if (index < 0 || Data?.States == null || index >= Data.States.Length)
		{
			return null;
		}
		AnimationData data = Data.States[index].AnimationData;
		if (data?.Animations == null || data.Animations.Length == 0)
		{
			return null;
		}
		int frame = (gm.NetsuPauseTotal - gm.NetsuPause) % Mathf.Max(1, data.Duration);
		int pick = 0;
		for (int i = 0; i < data.Animations.Length; i++)
		{
			if (data.Animations[i] != null && data.Animations[i].AtFrame <= frame)
			{
				pick = i;
			}
		}
		return data.Animations[pick];
	}

	private int _netsuVictoryState = -2;

	/// <summary>Netsu: index of the fighter's state named "Victory" (-1 if none).</summary>
	public int NetsuVictoryState()
	{
		if (_netsuVictoryState == -2)
		{
			_netsuVictoryState = -1;
			for (int i = 0; Data?.States != null && i < Data.States.Length; i++)
			{
				if (Data.States[i] != null && Data.States[i].StateName == "Victory")
				{
					_netsuVictoryState = i;
					break;
				}
			}
		}
		return _netsuVictoryState;
	}

	/// <summary>Netsu (Oct 26 evening): the fight is paused for this fighter's Overdrive activation.</summary>
	private bool NetsuOverdrivePausing()
	{
		GameManager gm = GameManager.Instance;
		return gm != null && gm.NetsuPause > 0 && gm.NetsuPauseSide == (int)playerID && GetMaster() == null
			&& StanceManager != null && StanceManager.CurrentMove >= 0
			&& StanceManager.GetCurrentMove().MoveName == SakugaEngine.StanceManager.NetsuOverdriveName;
	}

	/// <summary>Netsu (Oct 26, TamaDeez): a tech (any "Recovery_" state: air and ground recoveries) turns the
	/// fighter's sprite solid white and flashes it: fully white for the first 4 frames, then blinking (2 frames on,
	/// 2 off) until NetsuTechFlashFrames. 0 = normal, 1 = solid white (AnimationViewer.SetWhite).</summary>
	public const int NetsuTechFlashFrames = 14;

	private float NetsuTechFlash()
	{
		if (StateManager == null || GetMaster() != null)
		{
			return 0f;
		}
		string name = StateManager.GetCurrentState()?.StateName;
		int f = StateManager.CurrentStateFrame;
		if (name == null || !name.StartsWith("Recovery_") || f < 0 || f >= NetsuTechFlashFrames)
		{
			return 0f;
		}
		if (f < 4)
		{
			return 1f;
		}
		return ((f - 4) / 2) % 2 == 0 ? 0f : 0.9f;
	}

	/// <summary>Netsu (Oct 29): a charged move came out: a white flare bursts in front of her for the first
	/// FighterState.NetsuChargeFlash frames of its state. Presentation only, from the state frame.</summary>
	private void NetsuChargeFlareLook()
	{
		FighterState st = StateManager?.GetCurrentState();
		int f = StateManager != null ? StateManager.CurrentStateFrame : -1;
		float scale = 0f;
		float alpha = 0f;
		float phase = 0f;
		if (GetMaster() == null && Body != null && st != null && f >= 0)
		{
			int holdFrom = Mathf.Min(4, st.NetsuChargeAt - 1);   // a quick tap still holds the button a few frames
			if (st.NetsuChargeAt > 0 && st.NetsuChargeHold != null && f >= holdFrom && f < st.NetsuChargeAt && Inputs != null
				&& Inputs.CheckMotionInputs(st.NetsuChargeHold, InputSide()))
			{
				// Oct 29 (3): the charge is being held: a spark that swells on her until the charged move comes out
				float p = (float)(f - holdFrom + 1) / (st.NetsuChargeAt - holdFrom + 1);
				scale = Mathf.Lerp(0.15f, 2.2f, p);
				alpha = 0.6f + 0.4f * p;
				phase = f;
			}
			else if (st.NetsuChargeFlash > 0 && f < st.NetsuChargeFlash)
			{
				// the charged move came out: it keeps swelling until it covers her, holds, then fades
				float t = (float)f / st.NetsuChargeFlash;
				float grow = 1f - (1f - t) * (1f - t) * (1f - t);
				scale = Mathf.Lerp(2.2f, 3.9f, grow);
				alpha = t < 0.65f ? 1f : 1f - (t - 0.65f) / 0.35f;
				phase = 20f + f;
			}
		}
		if (scale <= 0f)
		{
			Animator.SetChargeFlare(0f, 0f, 0f, Vector3.Zero);
			return;
		}
		Vector2I off = st.NetsuChargeFlareOffset;
		Vector2I at = Body.FixedPosition + new Vector2I(off.X * Body.PlayerSide, off.Y);
		Animator.SetChargeFlare(scale, alpha, phase, GlobalFunctions.ToScaledVector3(at));
	}

	/// <summary>Netsu (Oct 26 c15): counter hit = the sprite flashes red for NetsuCounterFlashFrames; an air counter hit
	/// (no tech until landing) pulses purple until she lands. Presentation only, from the saved match state.</summary>
	public static Color NetsuCounterColor = new Color(1f, 0.12f, 0.1f, 1f);
	public static Color NetsuAirCounterColor = new Color(0.72f, 0.2f, 1f, 1f);
	public const int NetsuCounterFlashFrames = 18;

	private void NetsuCounterLook()
	{
		if (GetMaster() != null)
		{
			Animator.SetWhite(0f);
			return;
		}
		int now = GameManager.Instance != null ? GameManager.Instance.Frame : 0;
		if (NetsuAirCounterLock)
		{
			float pulse = 0.5f + 0.5f * Mathf.Sin(now * 0.45f);
			Animator.SetWhite(0.35f + 0.3f * pulse, NetsuAirCounterColor);
			return;
		}
		int age = now - NetsuCounterFlashAt;
		if (age >= 0 && age < NetsuCounterFlashFrames)
		{
			float amount = (age / 3) % 2 == 0 ? 0.65f : 0.3f;
			Animator.SetWhite(amount * (1f - age / (float)NetsuCounterFlashFrames * 0.5f), NetsuCounterColor);
			return;
		}
		Animator.SetWhite(0f);
	}

	// --- Netsu: the look of an EX / super flash (Oct 24) -------------------------------------
	// Presentation only, worked out from the match state every render (SuperFlashing), so rollback
	// needs nothing extra. While one fighter's EX move or super freezes the other:
	//   the frozen side (fighter, its assist, their projectiles) is darkened (NetsuFrozenTint);
	//   as the flash starts (or a new move starts during it: EX into super), MatchSetup.netsu_super_flash()
	//   dims the stage and draws the burst of light at the fighter (game/ui/battle_hud/netsu_super_flash.gd).
	// (Sprite3D modulate can't go above 1, so the fighter doing it isn't brightened here; the burst lights her.)

	/// <summary>Height of a fighter's chest above its origin (units): where the burst is drawn.</summary>
	public const int NetsuChestHeight = 9000;

	/// <summary>Colour multiplied into the sprites of the side frozen by the other's flash.</summary>
	public static Color NetsuFrozenTint = new Color(0.55f, 0.55f, 0.62f, 1f);

	/// <summary>The same during the EX / super pause (GameManager.NetsuPause): darker, so she stands out.</summary>
	public static Color NetsuPauseTint = new Color(0.36f, 0.36f, 0.44f, 1f);

	private bool _netsuFlashSeen;
	private int _netsuFlashMove = -1;

	/// <summary>Netsu: Craft Gauge cost of the move whose flash this fighter started last (2000 EX, 6000 super).
	/// Set by StanceManager.ExecuteMove / NetsuDelayedFlash; read only by the presentation below (a counter
	/// super's move has already ended when its flash is drawn).</summary>
	public int NetsuFlashCost;

	/// <summary>Netsu: aura width in sprite pixels, EX and super.</summary>
	public const float NetsuAuraWidthEx = 5f;
	public const float NetsuAuraWidthSuper = 8f;

	// true from a super's flash until the fighter leaves her attack (the dark backdrop and aura stay up)
	private bool _netsuSuperHold;
	private bool _netsuBackdrop;   // what netsu_cut_in.gd was last told (the backdrop: hold, but not in a NetsuShowStage state)

	private void NetsuSuperFlashLook()
	{
		SakugaActor side = NetsuRoot() ?? this;   // an assist, or a projectile (even an assist's), looks like its fighter
		SakugaActor[] opponents = side.GetOpponents();
		SakugaActor other = (opponents != null && opponents.Length > 0) ? opponents[0] : null;
		bool frozen = side.SuperFlashing;
		bool flashing = !frozen && other != null && other.SuperFlashing;
		bool pausing = GameManager.Instance != null && GameManager.Instance.NetsuPause > 0;   // the EX / super pause
		float tech = frozen ? 0f : NetsuTechFlash();
		Color tint = frozen ? (pausing ? NetsuPauseTint : NetsuFrozenTint) : Colors.White;
		Animator.SetTint(tint);
		if (tech > 0f || frozen)
		{
			Animator.SetWhite(tech);   // the tech flash: the sprite turns solid white and blinks
		}
		else
		{
			NetsuCounterLook();        // Netsu (Oct 26 c15): counter hit red, air counter hit purple
		}
		if (GetMaster() != null)
		{
			return;
		}
		int move = StanceManager != null ? StanceManager.CurrentMove : -1;
		if (flashing && (!_netsuFlashSeen || move != _netsuFlashMove))
		{
			NetsuSuperFlashFx(other);
		}
		_netsuFlashSeen = flashing;
		_netsuFlashMove = move;
		// a super keeps its backdrop and aura until she is out of her attack (EX moves: only during the flash)
		bool super = NetsuFlashCost >= SakugaEngine.StanceManager.NetsuSuperCost;
		bool hold = _netsuSuperHold;
		if (flashing && super)
		{
			hold = true;
		}
		else if (hold && !flashing && (StateManager == null || StateManager.CurrentStateType() != StateType.COMBAT || frozen))
		{
			hold = false;
		}
		_netsuSuperHold = hold;
		// Netsu (Oct 25): the dark backdrop clears in a state that shows the stage (FighterState.NetsuShowStage); the
		// aura stays
		bool backdrop = hold && StateManager?.GetCurrentState()?.NetsuShowStage != true;
		if (backdrop != _netsuBackdrop)
		{
			_netsuBackdrop = backdrop;
			NetsuReport("netsu_super_hold", backdrop);
		}
		bool aura = hold || (flashing && NetsuFlashCost >= SakugaEngine.StanceManager.NetsuExCost);
		if (NetsuOverdrivePausing())
		{
			// Oct 26 evening: Overdrive activation: she glows (her colour, brighter and wider than an EX)
			Color c = NetsuAuraColor().Lerp(Colors.White, 0.35f);
			float pulse = 0.85f + 0.15f * Mathf.Sin(Time.GetTicksMsec() * 0.03f);
			Animator.SetAura(new Color(c.R, c.G, c.B, pulse), NetsuAuraWidthSuper);
		}
		else if (aura)
		{
			Color c = NetsuAuraColor();
			float pulse = 0.78f + 0.17f * Mathf.Sin(Time.GetTicksMsec() * 0.024f);
			Animator.SetAura(new Color(c.R, c.G, c.B, pulse), super ? NetsuAuraWidthSuper : NetsuAuraWidthEx);
		}
		else
		{
			Animator.SetAura(new Color(0f, 0f, 0f, 0f), 0f);
		}
	}

	/// <summary>Netsu: the fighter's presentation colour (FighterProfile.NetsuAuraColor, else her side's colour).</summary>
	public Color NetsuAuraColor()
	{
		FighterProfile profile = Data?.Profile;
		if (profile != null && profile.NetsuAuraColor.A > 0.01f)
		{
			return profile.NetsuAuraColor;
		}
		return playerID == 0 ? new Color(0.3f, 0.62f, 1f) : new Color(1f, 0.25f, 0.38f);
	}

	private void NetsuReport(string method, bool on)
	{
		if (Engine.GetMainLoop() is not SceneTree tree)
		{
			return;
		}
		Node setup = tree.Root.GetNodeOrNull("MatchSetup");
		if (setup != null && setup.HasMethod(method))
		{
			setup.Call(method, (int)playerID, on);
		}
	}

	private void NetsuSuperFlashFx(SakugaActor frozen)
	{
		if (Body == null || Engine.GetMainLoop() is not SceneTree tree)
		{
			return;
		}
		Node setup = tree.Root.GetNodeOrNull("MatchSetup");
		if (setup == null || !setup.HasMethod("netsu_super_flash"))
		{
			return;
		}
		int cost = NetsuFlashCost;
		if (cost <= 0 && StanceManager != null && StanceManager.CurrentMove >= 0 && StanceManager.GetCurrentMove() != null)
		{
			cost = StanceManager.GetCurrentMove().SuperGaugeRequired;
		}
		int frames = (frozen != null && frozen.Hitstop != null) ? (int)frozen.Hitstop.TimeLeft : 20;
		if (GameManager.Instance != null && GameManager.Instance.NetsuPause > 0)
		{
			frames += GameManager.Instance.NetsuPause;   // Netsu: the EX / super pause comes first
		}
		Vector3 chest = GlobalFunctions.ToScaledVector3(Body.FixedPosition + new Vector2I(0, NetsuChestHeight));
		setup.Call("netsu_super_flash", (int)playerID, chest, cost, frames);
	}

	public const int NetsuLaunchGravity = 200000;   // Netsu: the engine's default air-hit knockback gravity

	public void PushActor(int pushDuration, int VelocityX, int VelocityY, int gravity)
	{
		Body.FixedVelocity.X = VelocityX;
		Body.FixedVelocity.Y = VelocityY;
		Body.CurrentGravity = gravity;
		Knockback.Start((uint)pushDuration);
	}

	/// <summary>Oct 27 c28 (TamaDeez): the push the last hit / block put on this fighter (speed, frames), so an attacker
	/// whose opponent is against the wall can be pushed back by exactly that (HitPushback). Set and used in the same
	/// hit, so not saved for rollback.</summary>
	public int NetsuLastPushX;

	/// <summary>Oct 27: set by an OTG hit on this (attacking) fighter, consumed by HitConfirm in the same call chain (not saved: never outlives a frame).</summary>
	public bool NetsuOtgJustHit;
	public int NetsuLastPushTime;

	public void HitPushback(SakugaActor target, int duration, int velX)
	{
		if (!Body.IsOnGround || !target.Body.IsOnWall)
		{
			return;
		}
		if (Body.FixedVelocity.Y > 0)
		{
			// Oct 27 c35: she is already rising: the push sets her vertical speed and gravity to 0
			return;
		}
		if (GetMaster() == null && StanceManager != null && StanceManager.CurrentMove >= 0 && !StanceManager.NetsuIsNormal(StanceManager.CurrentMove))
		{
			// Oct 27 c35 (TamaDeez): specials, EX moves and supers have their own movement. The corner push started a
			// knockback timer, and while it runs MoveX / MoveY do nothing: Flan's DP hit the cornered opponent in its first
			// frames and then never left the ground. Only normals slide back.
			return;
		}
		if (GetMaster() == null)
		{
			// Netsu (Oct 27 c28): universal pushback. Against the wall the opponent can't slide back, so the attacker
			// slides back instead, by exactly the push the opponent got (speed and frames, normals' 60% included): the
			// gap after a hit or a block is the same anywhere on screen. Was the hitbox's flat corner push (30000 for
			// 8 frames, at full strength: about twice a light normal's pushback). A hitbox with its corner push turned
			// off (AllowSelfPushback false, or SelfPushbackForce / Duration 0) still pushes nothing.
			if (velX == 0 || duration <= 0 || target.NetsuLastPushX <= 0)
			{
				return;
			}
			// Oct 27 c29: only GameManager.NetsuCornerPushbackPercent (25%) of it, so corner strings still link
			int percent = GameManager.Instance != null ? GameManager.Instance.NetsuCornerPushbackPercent : 25;
			int speed = target.NetsuLastPushX * percent / 100;
			if (speed <= 0)
			{
				return;
			}
			int away = (Body.FixedPosition.X < target.Body.FixedPosition.X) ? (-1) : 1;
			PushActor(target.NetsuLastPushTime, speed * away, 0, 0);
			return;
		}
		int pushbackSide = ((Body.FixedPosition.X > 0) ? 1 : (-1));
		PushActor(duration, velX * pushbackSide, 0, 0);
	}

	public void StopKnockback(bool keepXVelocity)
	{
		if (!keepXVelocity)
		{
			Body.FixedVelocity.X = 0;
		}
		Knockback.Stop();
	}

	private bool ValidTechState()
	{
		return HitstunType switch
		{
			HitstunType.BASIC => true, 
			HitstunType.KNOCKDOWN => Body != null && Body.IsOnGround, 
			_ => false, 
		};
	}

	public void StartSuperFlash(uint duration)
	{
		SuperFlashing = true;
		Hitstop.Start(duration);
	}

	// Netsu: counter hits (hitting a move in startup/active, or in recovery = punish counter) add this much hitstun.
	public const int NetsuCounterHitstun = 12;
	public int NetsuCounterHitstunBonus;

	/// <summary>Netsu (Oct 26, TamaDeez): the pushback of a ground normal, on hit and on block, is scaled by
	/// GameManager.NetsuNormalPushbackPercent. `attacker` is the fighter whose hitbox connected; its current move
	/// counts as a normal when it costs no meter and has Priority 6 or less (5A...2C, 4A, 6C; specials are 7-8,
	/// EX 9, supers 10). Assists, projectiles and moves without a current move keep their full pushback.</summary>
	public static int NetsuNormalPushback(SakugaActor attacker, int pushX)
	{
		GameManager gm = GameManager.Instance;
		if (gm == null || gm.NetsuNormalPushbackPercent == 100 || attacker == null || attacker.GetMaster() != null
			|| attacker.StanceManager == null || attacker.StanceManager.CurrentMove < 0)
		{
			return pushX;
		}
		MoveSettings move = attacker.StanceManager.GetCurrentMove();
		if (move == null || move.SuperGaugeRequired > 0 || move.Priority > 6)
		{
			return pushX;
		}
		return pushX * gm.NetsuNormalPushbackPercent / 100;
	}

	/// <summary>Oct 26 evening (TamaDeez, after BlazBlue Central Fiction): hit by a fighter in Overdrive, this fighter
	/// can't Burst until the combo ends (back out of hit stun). Saved for rollback (SakugaActorState key 18).</summary>
	public bool NetsuNoBurst;

	/// <summary>Oct 26 late (TamaDeez): a NetsuOncePerJump move (Flan's 623 series) was done since she last stood on
	/// the ground: it can't be done again in the air. Cleared on the ground once she's out of that move. Saved for
	/// rollback (SakugaActorState key 19).</summary>
	public bool NetsuAirMoveUsed;

	/// <summary>Oct 26 late (TamaDeez): the normals (by move index, one bit each) already used in this chain. A normal
	/// can't be cancelled into again until the chain ends (back to neutral, hit or block), so 5C > 2C > 5C loops are
	/// gone. Saved for rollback (SakugaActorState key 20).</summary>
	public ulong NetsuChainUsed;

	/// <summary>Oct 26 late (TamaDeez): a 3-bar super is running (set when it starts, through its follow-up states, until
	/// she's back out of her attack states). Its hits do NetsuSuperDamagePercent. Saved for rollback (key 21).</summary>
	public bool NetsuSuperActive;

	/// <summary>Oct 26 c14 (TamaDeez): the running super has already hit. Its own later hits may then hit an opponent it
	/// knocked down (Flan's Big Bang Crash slams them to the floor before the explosion); only a super that STARTS on a
	/// lying opponent can't pick them up (NetsuSuperOtg). Saved for rollback (key 25).</summary>
	public bool NetsuSuperConnected;

	/// <summary>Oct 26 c15 (TamaDeez): juggle system. NetsuComboFrames = how long the combo on this fighter has lasted
	/// (frames in a hit reaction, hitstop not counted); NetsuUntechMax = the hitstun the last hit gave (for the meter);
	/// NetsuAirCounterLock = an air counter hit: no tech until she lands (purple flash); NetsuCounterFlashAt = the
	/// GameManager frame of the last counter hit (red flash). Saved for rollback (keys 26-29).</summary>
	public int NetsuComboFrames;
	public int NetsuUntechMax;
	public bool NetsuAirCounterLock;
	public int NetsuCounterFlashAt = -1000;

	/// <summary>Frames of hitstun the juggle decay takes off a hit from `attacker` right now.</summary>
	private int NetsuJuggleDecay(SakugaActor attacker)
	{
		GameManager gm = GameManager.Instance;
		if (gm == null)
		{
			return 0;
		}
		int over = NetsuComboFrames - gm.NetsuJuggleGraceFrames;
		if (over <= 0)
		{
			return 0;
		}
		int decay = Mathf.Min(over / Mathf.Max(1, gm.NetsuJuggleDecayEvery), gm.NetsuJuggleMaxDecay);
		SakugaActor root = attacker?.NetsuRoot();
		if (root != null && !attacker.NetsuIsAssistHit() && root.StanceManager != null && root.StanceManager.CurrentMove >= 0
			&& SakugaEngine.StanceManager.NetsuIsExOrSuper(root.StanceManager.GetCurrentMove()))
		{
			decay = decay * (100 - gm.NetsuExDecayIgnorePercent) / 100;   // EX moves / supers extend combos
		}
		return decay;
	}

	/// <summary>Oct 27 c33: this hit comes from a special / EX move (Priority 7-8, not a 3-bar super) of a fighter (not an assist).</summary>
	/// <summary>Oct 27: is this hit from a normal attack (priority 6 or less, no meter cost)? Not an assist.</summary>
	private static bool NetsuIsNormalHit(SakugaActor attacker)
	{
		SakugaActor root = attacker?.NetsuRoot();
		if (root == null || attacker.NetsuIsAssistHit() || root.StanceManager == null || root.StanceManager.CurrentMove < 0)
		{
			return false;
		}
		MoveSettings m = root.StanceManager.GetCurrentMove();
		return m.Priority <= 6 && m.SuperGaugeRequired == 0 && m.WillGaugeRequired == 0;
	}

	/// <summary>Oct 28: the combo's recovery scale on this (defending) fighter, in thousandths. 0 = no hit yet (= 1000).</summary>
	public int NetsuRecoveryScale;

	/// <summary>Oct 28: the base untech frames and the scale multiplier of a hit (hitbox overrides, else the move's
	/// strength: light / medium / heavy normal, special, EX or super; assists count as medium).</summary>
	private static void NetsuRecoveryHit(SakugaActor attacker, HitboxElement box, GameManager gm, out int untech, out int multPermille, out bool ignore)
	{
		untech = gm.NetsuUntechMedium;
		multPermille = gm.NetsuScaleMedium;
		ignore = box.NetsuIgnoreRecoveryScaling;
		SakugaActor root = attacker?.NetsuRoot();
		if (root != null && root.StanceManager != null && root.StanceManager.CurrentMove >= 0 && !attacker.NetsuIsAssistHit())
		{
			MoveSettings m = root.StanceManager.GetCurrentMove();
			if (m.SuperGaugeRequired > 0 || m.WillGaugeRequired > 0)
			{
				untech = gm.NetsuUntechEx;
				multPermille = gm.NetsuScaleEx;
			}
			else if (m.Priority >= 7)
			{
				untech = gm.NetsuUntechSpecial;
				multPermille = gm.NetsuScaleSpecial;
			}
			else
			{
				int s = root.StanceManager.NetsuStrength(root.StanceManager.CurrentMove);
				untech = s == 0 ? gm.NetsuUntechLight : (s == 2 ? gm.NetsuUntechHeavy : gm.NetsuUntechMedium);
				multPermille = s == 0 ? gm.NetsuScaleLight : (s == 2 ? gm.NetsuScaleHeavy : gm.NetsuScaleMedium);
			}
		}
		if (box.NetsuAirUntech > 0)
		{
			untech = box.NetsuAirUntech;
		}
		if (box.NetsuRecoveryScalePermille > 0)
		{
			multPermille = box.NetsuRecoveryScalePermille;
		}
	}

	/// <summary>Oct 27: a special, EX move or super (priority 7+, or any meter cost)?</summary>
	private static bool NetsuIsSpecialOrBetter(SakugaActor attacker)
	{
		SakugaActor root = attacker?.NetsuRoot();
		if (root == null || attacker.NetsuIsAssistHit() || root.StanceManager == null || root.StanceManager.CurrentMove < 0)
		{
			return false;
		}
		MoveSettings m = root.StanceManager.GetCurrentMove();
		return m.Priority >= 7 || m.SuperGaugeRequired > 0;
	}

	private static bool NetsuIsSpecialHit(SakugaActor attacker)
	{
		SakugaActor root = attacker?.NetsuRoot();
		if (root == null || attacker.NetsuIsAssistHit() || root.StanceManager == null || root.StanceManager.CurrentMove < 0)
		{
			return false;
		}
		MoveSettings m = root.StanceManager.GetCurrentMove();
		return (m.Priority == 7 || m.Priority == 8) && m.SuperGaugeRequired < SakugaEngine.StanceManager.NetsuSuperCost && m.WillGaugeRequired == 0;
	}

	/// <summary>Extra hitstun a special (+NetsuSpecialUntechBonus) or EX move (+NetsuExUntechBonus) gives.</summary>
	private static int NetsuMoveUntechBonus(SakugaActor attacker)
	{
		GameManager gm = GameManager.Instance;
		SakugaActor root = attacker?.NetsuRoot();
		if (gm == null || root == null || attacker.NetsuIsAssistHit() || root.StanceManager == null || root.StanceManager.CurrentMove < 0)
		{
			return 0;
		}
		MoveSettings m = root.StanceManager.GetCurrentMove();
		if (SakugaEngine.StanceManager.NetsuIsExMove(m))
		{
			return gm.NetsuExUntechBonus;
		}
		if (m.SuperGaugeRequired == 0 && m.WillGaugeRequired == 0 && (m.Priority == 7 || m.Priority == 8))
		{
			return gm.NetsuSpecialUntechBonus;
		}
		return 0;
	}

	// ---------------------------------------------------------------------------------------------
	// Oct 27 c27 (TamaDeez): repeat proration. Per combo on this fighter, how many times each of the attacker's moves
	// (stance move index 0..63) has been used: a 2-bit count per move (NetsuComboUsedLo = low bits, Hi = high bits,
	// up to 3). A "use" is one execution of the move (StanceManager.ExecutedMoves), so a multi-hit move counts once;
	// a projectile counts as the move that spawned it (NetsuSpawnMove / NetsuSpawnUse, stamped in ObjectPool). The
	// last three uses seen are kept so a projectile's later hits after other hits aren't new uses. Assist hits don't
	// count. Cleared when the combo ends. Saved for rollback (keys 31-37).
	public ulong NetsuComboUsedLo;
	public ulong NetsuComboUsedHi;
	public int NetsuComboUseA;
	public int NetsuComboUseB;
	public int NetsuComboUseC;

	/// <summary>Oct 28 (second pass): damage proration for the same move again in one combo, on top of the usual damage
	/// scaling: 2nd use 85%, 3rd use 65%, 4th and later 45%. NetsuLastRepeatUses = earlier uses of the move behind the
	/// hit being processed (set by NetsuRepeatDecay in the same call; not saved).</summary>
	public static readonly int[] NetsuRepeatDamagePercent = { 100, 85, 65, 45 };
	public int NetsuLastRepeatUses;

	/// <summary>Oct 28: repeat proration multipliers for the 3rd use and for the 4th and later uses of the same move in a
	/// combo (the 2nd use is x1).</summary>
	public const int NetsuRepeatScale3rd = 3;
	public const int NetsuRepeatScale4th = 6;

	/// <summary>On a spawned actor (projectile): the owner's move that spawned it and that use's number (-1 = none).</summary>
	public int NetsuSpawnMove = -1;
	public int NetsuSpawnUse;

	/// <summary>The attacker's move behind this hit (its root fighter's stance move index) and that use's number.</summary>
	private static bool NetsuHitMove(SakugaActor attacker, out SakugaActor root, out int moveIndex, out int useId)
	{
		moveIndex = -1;
		useId = 0;
		root = attacker?.NetsuRoot();
		if (root == null || root.StanceManager == null || attacker.NetsuIsAssistHit())
		{
			return false;
		}
		if (attacker != root)
		{
			moveIndex = attacker.NetsuSpawnMove;
			useId = attacker.NetsuSpawnUse;
		}
		else
		{
			moveIndex = root.StanceManager.CurrentMove;
			useId = root.StanceManager.ExecutedMoves;
		}
		return moveIndex >= 0 && moveIndex < 64;
	}

	/// <summary>Registers this hit's move use in the combo and returns the untech frames it loses for the earlier uses
	/// of the same move (GameManager.NetsuRepeatNormalUntech / NetsuRepeatSpecialUntech per earlier use).</summary>
	private int NetsuRepeatDecay(SakugaActor attacker)
	{
		NetsuLastRepeatUses = 0;
		GameManager gm = GameManager.Instance;
		if (gm == null || !NetsuHitMove(attacker, out SakugaActor root, out int move, out int use))
		{
			return 0;
		}
		ulong bit = 1UL << move;
		int count = ((NetsuComboUsedLo & bit) != 0 ? 1 : 0) + ((NetsuComboUsedHi & bit) != 0 ? 2 : 0);
		NetsuLastRepeatUses = 0;
		int key = (1 << 30) | (move << 22) | (use & 0x3FFFFF);
		int earlier;
		if (key == NetsuComboUseA || key == NetsuComboUseB || key == NetsuComboUseC)
		{
			earlier = Mathf.Max(0, count - 1);   // another hit of a use already counted
		}
		else
		{
			earlier = count;
			int next = Mathf.Min(3, count + 1);
			NetsuComboUsedLo = (next & 1) != 0 ? (NetsuComboUsedLo | bit) : (NetsuComboUsedLo & ~bit);
			NetsuComboUsedHi = (next & 2) != 0 ? (NetsuComboUsedHi | bit) : (NetsuComboUsedHi & ~bit);
			NetsuComboUseC = NetsuComboUseB;
			NetsuComboUseB = NetsuComboUseA;
			NetsuComboUseA = key;
		}
		NetsuLastRepeatUses = Mathf.Max(0, earlier);
		if (earlier <= 0)
		{
			return 0;
		}
		bool normal = root.StanceManager.NetsuIsNormal(move);
		// Oct 28 (TamaDeez): the penalty grows faster than the count. 2nd use: x1, 3rd use: x3, 4th and later: x6 of the
		// per-use value (normals 6 -> 6 / 18 / 36 frames of untech time, specials 12 -> 12 / 36 / 72).
		int scale = earlier >= 3 ? NetsuRepeatScale4th : (earlier == 2 ? NetsuRepeatScale3rd : 1);
		return scale * (normal ? gm.NetsuRepeatNormalUntech : gm.NetsuRepeatSpecialUntech);
	}

	/// <summary>Oct 27 c27: frames an OTG hit takes off the OTG window, by the button of the move (A / B / C).</summary>
	private static int NetsuOtgHitCost(SakugaActor attacker)
	{
		GameManager gm = GameManager.Instance;
		if (gm == null)
		{
			return 0;
		}
		int strength = NetsuHitMove(attacker, out SakugaActor root, out int move, out _) ? root.StanceManager.NetsuStrength(move) : -1;
		return strength == 0 ? gm.NetsuOtgCostA : (strength == 2 ? gm.NetsuOtgCostC : gm.NetsuOtgCostB);
	}

	/// <summary>Juggle decay 0..1000 right now (for the meter's colour).</summary>
	public int NetsuJuggleDecayPermille()
	{
		GameManager gm = GameManager.Instance;
		if (gm == null || gm.NetsuJuggleMaxDecay <= 0)
		{
			return 0;
		}
		int over = NetsuComboFrames - gm.NetsuJuggleGraceFrames;
		if (over <= 0)
		{
			return 0;
		}
		return Mathf.Clamp(over / Mathf.Max(1, gm.NetsuJuggleDecayEvery) * 1000 / gm.NetsuJuggleMaxDecay, 0, 1000);
	}

	/// <summary>Oct 26 late (TamaDeez): landing recovery. A jump with no attack lands with 0 frames; one with an air
	/// normal lands with 2 (A), 3 (B) or 4 (C, the strongest one used) frames in which she can't act or block.
	/// Saved for rollback (keys 22-24).</summary>
	public int NetsuLandLag;
	public int NetsuAirAttackLag;
	public bool NetsuWasAir;

	/// <summary>Netsu (Oct 26 late, TamaDeez): damage of every hit of a 3-bar super (and of anything the fighter spawned
	/// while it runs), in percent of the hitboxes' own numbers, so supers out-damage EX moves. Assists don't count.</summary>
	public const int NetsuSuperDamagePercent = 150;

	/// <summary>Netsu (Oct 29): which combo scaling a hit gets: 0 = normal, 1 = an EX move's, 2 = a super's (their
	/// projectiles and follow-ups count too; assists never do). See GameManager.NetsuExScaling* / NetsuSuperScaling*.</summary>
	private static int NetsuScalingKind(SakugaActor hitter)
	{
		if (hitter == null || hitter.NetsuIsAssistHit())
		{
			return 0;
		}
		SakugaActor root = hitter.NetsuRoot();
		if (root != null && root.NetsuSuperActive)
		{
			return 2;
		}
		if (!hitter.NetsuMeterSpendTag)
		{
			return 0;
		}
		MoveSettings move = hitter.NetsuMeterMove();
		return move != null && move.SuperGaugeRequired >= SakugaEngine.StanceManager.NetsuSuperCost ? 2 : 1;
	}

	private static int NetsuSuperDamage(SakugaActor attacker, int damage)
	{
		if (attacker == null || attacker.NetsuIsAssistHit())
		{
			return damage;
		}
		SakugaActor root = attacker.NetsuRoot();
		if (root != null && root.NetsuSuperActive)
		{
			return damage * NetsuSuperDamagePercent / 100;
		}
		return damage;
	}

	public void HitDamage(SakugaActor target, HitboxElement box, bool isTrade)
	{
		LayerSorting = -1;
		if (target != null)
		{
			target.NetsuOtgJustHit = false;
		}
		NetsuLastPushX = 0;   // Oct 27 c28: set below when this hit pushes them (an OTG hit doesn't)
		SakugaActor netsuAttacker = target?.NetsuRoot();
		// Oct 28: Overdrive is now a low-health state (SakugaParameters.InOverdrive); being hit by it no longer locks Burst
		int netsuBurstRule = target != null && target.NetsuMeterMove() != null ? target.NetsuMeterMove().NetsuBurstRule : 0;
		if (netsuBurstRule == 2 || (netsuBurstRule == 0 && NetsuIsSpecialOrBetter(target)))   // Oct 29: a move can say (MoveSettings.NetsuBurstRule)
		{
			NetsuNoBurst = true;   // Oct 27 (TamaDeez): no Burst out of a special / EX move / super hit (until the combo ends)
		}
		bool netsuRelaunchHit = NetsuRelaunchNow;   // Nov 3: a splash hit picks them up instead (BaseDamage)
		NetsuRelaunchNow = false;
		if (!netsuRelaunchHit && (NetsuDownFrames > 0 || NetsuLying()) && !IsKO())
		{
			// Netsu (Oct 26): hit while lying (BaseDamage only lets it through inside the OTG window, and never from
			// a super): they stay down
			NetsuOtgHit(target, box, isTrade);
			return;
		}
		NetsuKdImpact = box.NetsuKnockdownImpact;   // Oct 27 c34: per-hit overrides of the knockdown timing (0 = global)
		NetsuKdLying = box.NetsuKnockdownLying;
		NetsuKdGetUp = box.NetsuKnockdownGetUp;
		bool netsuWasGrabbed = HitstunType == HitstunType.GRABBED;   // Netsu: a throw's hit isn't an "Invalid" combo
		// Oct 27 c35 (TamaDeez): juggled = launched (knockdown type hitstun) and not yet lying down. A hit on them uses the
		// air properties even when their feet touch the ground (a bounce, the landing frame), and never ends the juggle by
		// putting them back on their feet, unless the hit is made to (NetsuAllowRestand).
		bool netsuJuggled = !IsKO() && !box.NetsuAllowRestand && StateManager != null && StateManager.CurrentStateType() == StateType.HIT_REACTION
			&& (HitstunType == HitstunType.KNOCKDOWN || HitstunType == HitstunType.HARD_KNOCKDOWN) && !NetsuLying();
		bool isGroundHit = !IsKO() && Body != null && !IsAirState() && !netsuJuggled;
		int finalHitstun = (isGroundHit ? box.GroundHitstun : box.AirHitstun);
		NetsuAirCounterLock = false;   // Oct 27: any new hit ends an air counter lock (a new air counter hit below sets it again)
		bool netsuCounter = NetsuCounterHitstunBonus > 0;
		int netsuCounterAdd = NetsuCounterHitstunBonus;   // Oct 28: kept for the recovery scaling (counter bonuses are added to its base)
		finalHitstun += NetsuCounterHitstunBonus;   // Netsu: extra hitstun on counter / punish counter
		// Oct 27 c33 (TamaDeez): a counter hit with a special / EX move is stronger still (see GameManager.NetsuSpecialCounter*)
		bool netsuSpecialCounter = netsuCounter && NetsuIsSpecialHit(target) && GameManager.Instance != null;
		if (netsuSpecialCounter)
		{
			finalHitstun += GameManager.Instance.NetsuSpecialCounterExtraHitstun;
			netsuCounterAdd += GameManager.Instance.NetsuSpecialCounterExtraHitstun;
		}
		NetsuCounterHitstunBonus = 0;
		finalHitstun += NetsuMoveUntechBonus(target);   // Netsu (Oct 26 c15): specials / EX moves extend combos
		if (!isGroundHit && !IsKO() && GameManager.Instance != null)
		{
			finalHitstun += GameManager.Instance.NetsuAirUntechBonus;   // Oct 27 c27: juggles are more forgiving
		}
		int netsuRepeat = NetsuRepeatDecay(target);   // Oct 27 c27: same move again in this combo: less untech time
		int netsuRepeatUses = NetsuLastRepeatUses;   // Oct 28: and less damage
		if (netsuSpecialCounter)
		{
			netsuRepeat = 0;   // a special's counter hit isn't punished by the repeat proration
		}
		if (netsuCounter)
		{
			NetsuCounterFlashAt = GameManager.Instance != null ? GameManager.Instance.Frame : 0;   // red flash
			// Oct 27 (TamaDeez): an air counter hit only happens with a NORMAL (never a special / EX / super), while really airborne
			if (!isGroundHit && !IsKO() && Body != null && !Body.IsOnGround && !netsuSpecialCounter && NetsuIsNormalHit(target))
			{
				NetsuAirCounterLock = true;   // Netsu (Oct 26 c15): air counter: no tech until she lands (purple)
			}
		}
		int finalKnockbackTime = (isGroundHit ? box.GroundHitKnockbackTime : box.AirHitKnockbackTime);
		Vector2I finalDamageKnockback = (isGroundHit ? box.GroundHitKnockback : box.AirHitKnockback);
		if (isGroundHit)
		{
			finalDamageKnockback.X = NetsuNormalPushback(target, finalDamageKnockback.X);   // Netsu (Oct 26): normals push less
		}
		if (netsuSpecialCounter)
		{
			int kbPercent = GameManager.Instance.NetsuSpecialCounterKnockbackPercent;
			int liftPercent = box.NetsuCounterLiftPercent > 0 ? box.NetsuCounterLiftPercent : kbPercent;   // per-hitbox CH lift
			finalDamageKnockback = new Vector2I(finalDamageKnockback.X * kbPercent / 100, finalDamageKnockback.Y * liftPercent / 100);
			finalKnockbackTime = finalKnockbackTime * kbPercent / 100;
		}
		int finalKnockbackGravity = (isGroundHit ? box.GroundHitKnockbackGravity : box.AirHitKnockbackGravity);
		if (finalKnockbackGravity <= 0 && (finalDamageKnockback.Y > 0 || (Body != null && !Body.IsOnGround)))
		{
			// Netsu (Oct 26 c11): a hit that sends them up (or hits them in the air) with no knockback gravity left them
			// floating for good (the body keeps that gravity): Cecilia's 236C finisher only set it for air hits. Use the
			// usual launch gravity. (Gravity 1 = "hold them up", as in her 214C rush, is still honoured.)
			finalKnockbackGravity = NetsuLaunchGravity;
		}
		int finalHitReaction = ((!isGroundHit) ? box.AirHitReaction : (IsCrouchState() ? box.CrouchHitReaction : box.GroundHitReaction));
		// Netsu (Nov 3, TamaDeez): NO RESTANDS. An opponent in the air, or juggled (launched and not lying yet, even if their
		// feet touch the floor), is never put back on their feet by a hit: the standing / crouching / sweep reactions (and
		// the light air reaction, whose end lets them land standing) become the falling air reaction, which always ends
		// in the down state on landing. Only a hit made to restand does (HitboxElement.NetsuAllowRestand). Noah's j.214A
		// blast stood them up this way.
		if (!box.NetsuAllowRestand && (netsuJuggled || !isGroundHit))
		{
			const int netsuAirStrong = 5;   // HitReactions: 0 stand weak, 1 stand strong, 2 crouch, 3 sweep, 4 air weak, 5 air strong, 6 crumple
			if (finalHitReaction <= 3 || (finalHitReaction == 4 && netsuJuggled) || (finalHitReaction == 6 && Body != null && !Body.IsOnGround))
			{
				finalHitReaction = netsuAirStrong;
			}
		}
		HitstunType = (isGroundHit ? box.GroundHitstunType : box.AirHitstunType);
		if (netsuJuggled && HitstunType < HitstunType.KNOCKDOWN)
		{
			HitstunType = HitstunType.KNOCKDOWN;   // Oct 27 c35: still juggled
		}
		if (box.NetsuSoftKnockdown)
		{
			HitstunType = HitstunType.BASIC;   // Oct 28: never a hard knockdown (techable in the air / on landing)
		}
		if (box.NetsuHardKnockdownMinScaling > 0 && HitstunType == HitstunType.HARD_KNOCKDOWN && Parameters != null
			&& Parameters.Prorations != null && Parameters.Prorations.CurrentBaseDamageScaling < box.NetsuHardKnockdownMinScaling)
		{
			HitstunType = HitstunType.KNOCKDOWN;   // Oct 29: too far into the combo for a hard knockdown
		}
		bool canTech = !netsuWasGrabbed && StateManager != null && StateManager.CurrentStateType() == StateType.HIT_REACTION && !OnHitstun() && ValidTechState();
		if (Body != null)
		{
			Body.UpdateSide(!target.Body.IsLeftSide);
			Body.FlipSide();
			Body.IsMovable = false;
		}
		int finalHitstunForReal = Mathf.Max(finalHitstun, 8);
		int decayingKnockback = 0;
		if (Parameters != null)
		{
			// Netsu (Oct 26 c15): BlazBlue-style juggle decay by combo time (was: -1 frame per hit after the 8th hit)
			// Oct 27 c27: + repeat proration on air hits (the untech time); ground hitstun only has the time decay
			finalHitstunForReal = Mathf.Max(finalHitstun - (netsuSpecialCounter ? 0 : NetsuJuggleDecay(target)) - (isGroundHit ? netsuRepeat / 2 : netsuRepeat), isGroundHit ? 8 : 1);   // Oct 27 c33: ground hits lose half the repeat proration
			decayingKnockback = (GameManager.Instance != null ? GameManager.Instance.NetsuGravityDecayPerHit : 2500) * Parameters.Prorations.GravityDecayFactor;   // Nov 3: a setting (was 2500)
		}
		// Oct 28: UNI-style recovery scaling: an air hit REPLACES their untech time with base x the combo's recovery scale
		// (never adding to what was left); then this hit scales the later ones. Ground hits keep their hitstun and only
		// scale the later hits. A throw (grabbed) isn't scaled. The timer is the hitstun timer (it pauses in hitstop).
		GameManager netsuGm = GameManager.Instance;
		if (netsuGm != null && netsuGm.NetsuRecoveryScaling && Parameters != null && !netsuWasGrabbed && !IsKO())
		{
			NetsuRecoveryHit(target, box, netsuGm, out int baseUntech, out int multPermille, out bool ignore);
			int scale = (NetsuRecoveryScale <= 0 || ignore) ? 1000 : NetsuRecoveryScale;
			if (!isGroundHit)
			{
				finalHitstunForReal = Mathf.Max(netsuGm.NetsuMinUntech, (baseUntech + netsuCounterAdd) * scale / 1000);
			}
			if (!ignore)
			{
				NetsuRecoveryScale = Mathf.Max(1, (NetsuRecoveryScale <= 0 ? 1000 : NetsuRecoveryScale) * multPermille / 1000);
			}
		}
		if (CanHitstop())
		{
			if (!isTrade)
			{
				Hitstop.Start((uint)box.OpponentHitStopDuration);
			}
			else
			{
				Hitstop.Stop();
			}
		}
		if (CanHitstun())
		{
			Hitstun.Start((uint)finalHitstunForReal);
		}
		NetsuUntechMax = finalHitstunForReal;
		FrameDataEvent[] onHitReactionEvents = StateManager.GetCurrentState().OnHitReactionEvents;
		for (int i = 0; onHitReactionEvents != null && i < onHitReactionEvents.Length; i++)
		{
			onHitReactionEvents[i].RunEvent(ref actor);
		}
		if (StanceManager != null)
		{
			StanceManager.Clear();
			if (StanceManager.GetCurrentStance().HitReactions != null && StanceManager.GetCurrentStance().HitReactions.Length >= 0)
			{
				finalHitReaction = Mathf.Clamp(finalHitReaction, 0, StanceManager.GetCurrentStance().HitReactions.Length - 1);
				if (StateManager != null)
				{
					StateManager.PlayState(StanceManager.GetCurrentStance().HitReactions[finalHitReaction], reset: true);
					NetsuFastState = box.NetsuReactionSpeedPercent > 100 ? StateManager.CurrentState : -1;   // Oct 29
					NetsuFastPct = box.NetsuReactionSpeedPercent;
					NetsuFastAcc = 0;
				}
			}
		}
		if (canTech)
		{
			GameManager.Instance.PlayHitNotificationByIndex((int)target.playerID, 8);
		}
		NetsuLastPushX = Mathf.Abs(finalDamageKnockback.X);   // Oct 27 c28: for the attacker's corner pushback (HitPushback)
		NetsuLastPushTime = finalKnockbackTime;
		PushActor(finalKnockbackTime, finalDamageKnockback.X * -target.Body.PlayerSide, finalDamageKnockback.Y - decayingKnockback, finalKnockbackGravity);
		NetsuFloatStart(box);   // Netsu (Oct 28): a float hit (Leticia's j.236) holds them up; any other hit ends a float
		NetsuCarryStart(target, box);   // Netsu (Oct 29): Flan's upward Star Rush carries them up with her
		NetsuExHoldStart(target, finalDamageKnockback.Y - decayingKnockback);   // Netsu (Oct 29): an EX move's hit keeps them up until the EX is over (Nov 3: not a slam)
		if (Parameters != null)
		{
			int stunFrame = ((target.StateManager != null) ? (target.StateManager.GetCurrentState().AnimationData.Duration - target.StateManager.CurrentStateFrame) : 0);
			int finalAttack = ((target.Parameters.Prorations != null) ? target.Parameters.Prorations.CurrentAttack : target.Data.BaseAttack);
			int finalDamage = Parameters.CalculateProrations(box.BaseDamage, finalAttack, Parameters.Prorations.CurrentDefense, (ushort)box.DamageScalingSubtract, NetsuScalingKind(target));   // Oct 29: EX / supers scale less
			finalDamage = target.Parameters.OverdriveDamage(finalDamage);   // Netsu: Overdrive damage bonus
			finalDamage = NetsuSuperDamage(target, finalDamage);              // Netsu (Oct 26 late): 3-bar supers hit harder
			finalDamage = finalDamage * NetsuRepeatDamagePercent[Mathf.Clamp(netsuRepeatUses, 0, 3)] / 100;   // Oct 28: same move again
			finalDamage = Parameters.NetsuOverdriveTaken(finalDamage);   // Oct 28: Overdrive takes 10% less
			Parameters.TakeDamage(finalDamage, box.OpponentSuperGaugeGain, box.KillingBlow);
			NetsuMeterOnHit(target, finalDamage);   // Oct 29: Craft Gauge / Burst for both sides
			Parameters.Tracker.UpdateTrackers(finalDamage, stunFrame, finalHitstunForReal, (int)box.HitType, canTech);
			if (target.Parameters.Tracker != null)
			{
				if (isTrade)
				{
					Parameters.Tracker.FrameAdvantage = -finalHitstunForReal;
				}
				else
				{
					target.Parameters.Tracker.FrameAdvantage = -(stunFrame - finalHitstunForReal);
				}
			}
			if (IsAirState())
			{
				Parameters.Prorations.GravityDecayFactor++;
			}
		}
		if (CanBounce())
		{
			if (box.BounceTime > 0)
			{
				int bouncePercent = netsuSpecialCounter ? GameManager.Instance.NetsuSpecialCounterBouncePercent : 100;   // Oct 27 c33
				Bounce.Start((uint)(box.BounceTime * bouncePercent / 100));
				BounceXIntensity = box.BounceXIntensity * bouncePercent / 100;
				BounceYIntensity = box.BounceYIntensity * bouncePercent / 100;
				NetsuWallBounceDistance = box.NetsuWallBounceDistance;
				if (BounceYIntensity > 0 && NetsuGroundBounceRepeat(target))
				{
					BounceYIntensity = 0;   // Oct 29: the same move's second ground bounce in a combo: hard knockdown instead
					HitstunType = HitstunType.HARD_KNOCKDOWN;
				}
			}
			else
			{
				Bounce.Stop();
				BounceXIntensity = 0;
				BounceYIntensity = 0;
				NetsuWallBounceDistance = 0;
			}
		}
	}

	public void BlockHit(SakugaActor target, HitboxElement box, int blockState)
	{
		LayerSorting = -1;
		int num;
		int num2;
		if (!IsKO() && Body != null && IsGroundState())
		{
			num = ((!IsAirState()) ? 1 : 0);
			if (num != 0)
			{
				num2 = box.GroundBlockstun;
				goto IL_003c;
			}
		}
		else
		{
			num = 0;
		}
		num2 = box.AirBlockstun;
		goto IL_003c;
		IL_003c:
		int finalHitstun = num2;
		if (num != 0 && target != null && target.StateManager != null && target.StanceManager != null && !target.NetsuIsAssistHit()
			&& target.StanceManager.NetsuBlockAdvantage(out int netsuAdv))
		{
			// Netsu (Oct 26 late, TamaDeez): universal frame advantage on block. The blockstun is set so the defender
			// recovers netsuAdv frames before (negative) the attacker's move ends: normals A -4, B -5, C -8; specials
			// A -4, B / C -6 (StanceManager.NetsuBlockAdvantage). Different hitstops on both sides are counted in.
			int netsuLeft = target.StateManager.GetCurrentState().AnimationData.Duration - target.StateManager.CurrentStateFrame;
			finalHitstun = Mathf.Max(4, netsuLeft + netsuAdv + (box.SelfHitStopDuration - box.BlockStopDuration));
		}
		int finalKnockbackTime = ((num != 0) ? box.GroundBlockKnockbackTime : box.AirBlockKnockbackTime);
		Vector2I finalDamageKnockback = ((num != 0) ? box.GroundBlockKnockback : box.AirBlockKnockback);
		if (num != 0)
		{
			finalDamageKnockback.X = NetsuNormalPushback(target, finalDamageKnockback.X);   // Netsu (Oct 26): normals push less
		}
		int finalKnockbackGravity = ((num != 0) ? box.GroundBlockKnockbackGravity : box.AirBlockKnockbackGravity);
		BlockStun = true;
		if (Body != null)
		{
			Body.UpdateSide(!target.Body.IsLeftSide);
			Body.FlipSide();
			Body.IsMovable = false;
		}
		bool netsuInstantBlock = IsInstantBlock();   // Oct 29: also decides the block's Craft Gauge
		if (netsuInstantBlock)
		{
			GameManager.Instance.PlayHitNotificationByIndex((int)playerID, 3);
		}
		if (StanceManager != null)
		{
			StanceManager.Clear();
		}
		if (StateManager != null)
		{
			StateManager.PlayState(blockState, reset: true);
		}
		if (CanHitstun())
		{
			Hitstun.Start((uint)finalHitstun);
		}
		if (CanHitstop())
		{
			Hitstop.Start((uint)box.BlockStopDuration);
		}
		NetsuLastPushX = Mathf.Abs(finalDamageKnockback.X);   // Oct 27 c28: for the attacker's corner pushback (HitPushback)
		NetsuLastPushTime = finalKnockbackTime;
		PushActor(finalKnockbackTime, finalDamageKnockback.X * -target.Body.PlayerSide, finalDamageKnockback.X, finalKnockbackGravity);
		if (Parameters != null)
		{
			int stunFrame = ((target.StateManager != null) ? (target.StateManager.GetCurrentState().AnimationData.Duration - target.StateManager.CurrentStateFrame) : 0);
			int finalAttack = ((target.Parameters.Prorations != null) ? target.Parameters.Prorations.CurrentAttack : target.Data.BaseAttack);
			int finalDamage = Parameters.CalculateProrations(box.ChipDamage, finalAttack, Parameters.Prorations.CurrentDefense, 0);
			finalDamage = target.Parameters.OverdriveDamage(finalDamage);   // Netsu: Overdrive damage bonus
			finalDamage = NetsuSuperDamage(target, finalDamage);              // Netsu: supers chip harder too
			finalDamage = Parameters.NetsuOverdriveTaken(finalDamage);         // Oct 28: Overdrive takes 10% less
			Parameters.TakeDamage(finalDamage, 0, box.ChipDeath);
			NetsuMeterOnBlock(target, box.BaseDamage, netsuInstantBlock);   // Oct 29: from the hit's unscaled damage; chip adds nothing
			Parameters.Tracker.UpdateTrackers(finalDamage, stunFrame, finalHitstun, (int)box.HitType, isInvalid: false, isCombo: false);
			if (target.Parameters.Tracker != null)
			{
				target.Parameters.Tracker.FrameAdvantage = -(stunFrame - finalHitstun);
			}
		}
	}

	public void GuardCrush(SakugaActor target, HitboxElement box, int crushState)
	{
		if (Body != null)
		{
			Body.UpdateSide(!target.Body.IsLeftSide);
			Body.FlipSide();
			Body.IsMovable = false;
		}
		if (StanceManager != null)
		{
			StanceManager.Clear();
		}
		if (StateManager != null)
		{
			StateManager.PlayState(crushState, reset: true);
		}
		if (CanHitstun())
		{
			Hitstun.Start(40u);
		}
		if (CanHitstop())
		{
			Hitstop.Start((uint)box.BlockStopDuration);
		}
		if (Parameters != null)
		{
			int stunFrame = target.StateManager.GetCurrentState().AnimationData.Duration - target.StateManager.CurrentStateFrame;
			int finalAttack = ((target.Parameters.Prorations != null) ? target.Parameters.Prorations.CurrentAttack : target.Data.BaseAttack);
			int finalDamage = Parameters.CalculateProrations(box.GuardCrushDamage, finalAttack, Parameters.Prorations.CurrentDefense, (ushort)box.DamageScalingSubtract);
			finalDamage = target.Parameters.OverdriveDamage(finalDamage);   // Netsu: Overdrive damage bonus
			Parameters.TakeDamage(finalDamage, box.OpponentSuperGaugeGain, box.KillingBlow);
			NetsuMeterOnHit(target, finalDamage);   // Oct 29: a guard crush counts as a hit for the gauges
			Parameters.Tracker.UpdateTrackers(finalDamage, stunFrame, 40, (int)box.HitType);
		}
	}

	public void ArmorHit(SakugaActor target, HitboxElement box)
	{
		LayerSorting = -1;
		HitConfirm(target, box.OpponentSuperGaugeGain, (uint)box.ClashHitStopDuration, -1, Vector2I.Zero);
		if (Parameters != null)
		{
			int finalAttack = ((target.Parameters.Prorations != null) ? target.Parameters.Prorations.CurrentAttack : target.Data.BaseAttack);
			int finalDamage = Parameters.CalculateProrations(box.BaseDamage, finalAttack, Parameters.Prorations.CurrentDefense, (ushort)box.DamageScalingSubtract);
			Parameters.ArmorDamage(box.ArmorDamage, finalDamage / 2);
			NetsuMeterOnHit(target, finalDamage / 2);   // Oct 29: an armored hit counts for the damage it really did
		}
	}

	public void ThrowHit(SakugaActor target, HitboxElement box, uint finalHitStop)
	{
		LayerSorting = -1;
		HitstunType = HitstunType.GRABBED;
		if (Parameters.SuperArmor != null)
		{
			Parameters.SuperArmor.SetArmor(0);
		}
		if (Body != null)
		{
			Body.UpdateSide(!target.Body.IsLeftSide);
			Body.FlipSide();
			Body.IsMovable = false;
		}
		if (CanHitstop())
		{
			Hitstop.Start(finalHitStop);
		}
		if (StanceManager != null)
		{
			StanceManager.Clear();
			if (StanceManager.GetCurrentStance().HitReactions != null && StanceManager.GetCurrentStance().HitReactions.Length >= 0 && StateManager != null)
			{
				int finalHitReaction = Mathf.Clamp(box.ThrowHitReaction, 0, StanceManager.GetCurrentStance().HitReactions.Length - 1);
				StateManager.PlayState(StanceManager.GetCurrentStance().HitReactions[finalHitReaction], reset: true);
			}
		}
		if (Parameters != null)
		{
			Parameters.ChangeVariablesBehavior(CustomVariableBehaviorTarget.ON_HIT);
		}
	}

	public void ThrowEscape(SakugaActor target)
	{
		if (Hitstop.IsRunning() && HitstunType >= HitstunType.GRABBED && Inputs.CheckMotionInputs(StanceManager.GetCurrentStance().ThrowEscapeInput, InputSide()))
		{
			HitstunType = HitstunType.NONE;
			ThrowEscapeAction();
			GameManager.Instance.PlayHitNotificationByIndex((int)playerID, 4);
			target.ThrowEscapeAction();
		}
	}

	public void ThrowEscapeAction()
	{
		if (StanceManager != null)
		{
			int selfSelectThrowEscape = (Body.IsOnGround ? StanceManager.GetCurrentStance().GroundThrowEscapeState : StanceManager.GetCurrentStance().AirThrowEscapeState);
			if (CanHitstop())
			{
				Hitstop.Stop();
			}
			if (StateManager != null)
			{
				StateManager.PlayState(selfSelectThrowEscape);
			}
			PushActor(10, -40000 * Body.PlayerSide, 0, 0);
		}
	}

	public void HitConfirm(SakugaActor target, int superGaugeGain, uint hitStopDuration, int hitEffect, Vector2I VFXSpawn)
	{
		LayerSorting = 1;
		if (Body != null)
		{
			Body.IsMovable = false;
		}
		if (CanHitstop())
		{
			Hitstop.Start(hitStopDuration);
		}
		if (hitEffect >= 0 && VFXSpawn != Vector2I.Zero)
		{
			NetsuSpawnVFX(hitEffect, VFXSpawn);   // Netsu: projectiles and assists use their fighter's hit sparks
		}
		if (Parameters != null)
		{
			// Oct 29: Craft Gauge is no longer given here (the hitbox's flat Self/OpponentSuperGaugeGain): see
			// NetsuMeterOnHit / NetsuMeterOnBlock, called where the damage is worked out
			Parameters.HitConfirm(0);
		}
		// Netsu: heavy hits (long hitstop) shake the screen; blocked heavies shake less.
		if (target != null && target != this && hitStopDuration >= 12)
		{
			FighterCamera.Shake(target.BlockStun ? 0.015f : 0.035f, (int)System.Math.Min(hitStopDuration, 14u));
		}
		// Netsu (Oct 27): an OTG hit only does damage, hitstop and meter; the move's on-hit events (hit-grab pulls, "on hit,
		// play the rest of the animation" follow-ups) don't run, so a downed target is never moved or picked up
		bool netsuOtgHit = NetsuOtgJustHit;
		NetsuOtgJustHit = false;
		FrameDataEvent[] onHitConfirmEvents = netsuOtgHit ? null : StateManager.GetCurrentState().OnHitConfirmEvents;
		int netsuStateBefore = StateManager.CurrentState;
		int netsuFrameBefore = StateManager.CurrentStateFrame;
		for (int i = 0; onHitConfirmEvents != null && i < onHitConfirmEvents.Length; i++)
		{
			onHitConfirmEvents[i].RunEvent(ref actor);
		}
		// Netsu (Oct 26 late): if that hit sent this fighter into a follow-up state (a counter's slash, a special's
		// second part...), the new state starts with a clean slate: before this the target was marked "already hit"
		// right after the switch, so the follow-up's first hitbox whiffed through them.
		bool netsuSwitched = StateManager.CurrentState != netsuStateBefore || StateManager.CurrentStateFrame < netsuFrameBefore;
		SakugaActor netsuRootActor = NetsuRoot();
		if (netsuRootActor != null && netsuRootActor.NetsuSuperActive)
		{
			netsuRootActor.NetsuSuperConnected = true;   // Netsu (Oct 26 c14): see NetsuSuperOtg
		}
		if (Body != null && !netsuSwitched)
		{
			Body.AddHitBody(target.Body);
		}
	}

	/// <summary>Netsu: this actor is an assist, or something an assist spawned.</summary>
	public bool NetsuIsAssistHit()
	{
		SakugaActor root = NetsuRoot();
		if (root == this || root == null || root.NetsuAssist == null || root.NetsuAssist.Actor == null)
		{
			return false;
		}
		SakugaActor a = this;
		for (int guard = 0; a != null && a != root && guard < 8; guard++)
		{
			if (a == root.NetsuAssist.Actor)
			{
				return true;
			}
			a = a.GetMaster();
		}
		return false;
	}

	public void BaseDamage(SakugaActor target, HitboxElement box, Vector2I contact)
	{
		// Nov 3 (TamaDeez): a splash hit (HitboxElement.NetsuOtgRelaunch) picks a downed opponent back up: it gets past
		// the wake-up invincibility and the super OTG rule, and HitDamage treats it as a normal hit (not an OTG hit)
		target.NetsuRelaunchNow = false;
		bool netsuRelaunch = box.NetsuOtgRelaunch && !target.IsKO() && (target.NetsuDownFrames > 0 || target.NetsuLying())
			&& (target.FrameProperties & FrameProperties.DAMAGE_IMUNITY) == 0;
		if (!netsuRelaunch && (target.ContainsFrameProperty(FrameProperties.DAMAGE_IMUNITY) || NetsuSuperOtg(target)))
		{
			return;   // (Oct 26 evening: supers can't OTG: they never hit a fighter lying on the ground)
		}
		if (netsuRelaunch)
		{
			target.NetsuRelaunchNow = true;
			target.NetsuDownFrames = 0;
			target.NetsuOtgSpent = 0;
			target.NetsuOtgWindowAtLand = -1;
		}
		if (box.HitType == HitType.UNBLOCKABLE || (box.HitType == HitType.HIGH && target.Body.IsOnGround && target.IsCrouchState()))
		{
			_ = 1;
		}
		else if (box.HitType == HitType.LOW)
		{
			if (target.Body.IsOnGround && target.IsGroundState())
			{
				_ = 1;
			}
			else
				target.IsAirState();
		}
		else
			_ = 0;
		CancelConditions &= ~CancelCondition.WHIFF_CANCEL;
		CancelConditions &= ~CancelCondition.KARA_CANCEL;
		// Netsu (Oct 26 late, TamaDeez): an assist, an assist's projectile or a fighter's projectile is blocked by
		// holding away from the FIGHTER who owns it (where she is at the moment it connects), not from where the
		// assist / projectile is. (Before: away from the assist itself, so an assist from behind was a cross-up.)
		int netsuBlockSide = 0;
		SakugaActor netsuOwner = NetsuRoot();
		if (GetMaster() != null && netsuOwner != null && netsuOwner.Body != null && target.Body != null)
		{
			int dx = netsuOwner.Body.FixedPosition.X - target.Body.FixedPosition.X;
			netsuBlockSide = dx > 0 ? 1 : (dx < 0 ? -1 : 0);
		}
		// Oct 27 (TamaDeez): a state marked NetsuKeepBlockSide (Cecilia's slash-through) is blocked as if she were still on
		// the side she attacked from: she faces toward them, so that is the side opposite her facing
		FighterState netsuKeepState = StateManager?.GetCurrentState();
		if (netsuKeepState != null && netsuKeepState.NetsuKeepBlockSide && Body != null)
		{
			// her facing flips at NetsuKeepBlockSideFlipFrame (the state's ChangeSideAction), so from then on the side she
			// came from is +PlayerSide. Nov 3: was fixed at frame 8, but Cecilia's slash flips at 10 and still hits on
			// frame 8, so that hit had to be blocked the other way (a cross-up).
			netsuBlockSide = StateManager.CurrentStateFrame >= netsuKeepState.NetsuKeepBlockSideFlipFrame ? Body.PlayerSide : -Body.PlayerSide;
		}
		// Netsu (Oct 26 late, TamaDeez): every assist hit (and its projectiles) is a mid: blocked standing or crouching.
		HitType netsuHitType = NetsuIsAssistHit() && box.HitType != HitType.UNBLOCKABLE ? HitType.MEDIUM : box.HitType;
		int blockState = target.StanceManager.GetBlockState(netsuHitType, (byte)((!box.GuardCrush) ? 1u : 2u), netsuBlockSide);
		NetsuLog.Debug(blockState.ToString());
		if (target.Parameters.SuperArmor != null && target.Parameters.SuperArmor.CurrentValue > 0)
		{
			target.ArmorHit(actor, box);
			HitConfirm(target, box.SelfSuperGaugeGain, (uint)box.ClashHitStopDuration, box.ArmorEffectIndex, contact);
			CancelConditions |= CancelCondition.HIT_CANCEL;
			NetsuLog.Debug("Fighter: Armor Hit");
			return;
		}
		int hitFX;
		bool netsuBlocked = false;   // Netsu: blocked hits give half Craft Gauge
		if (target.CanBlock() && blockState >= 0)
		{
			netsuBlocked = !box.GuardCrush;
			if (box.GuardCrush)
			{
				hitFX = box.GuardCrushEffectIndex;
				target.GuardCrush(actor, box, blockState);
				NetsuLog.Debug("Fighter: Guard Crushed!");
				CancelConditions |= CancelCondition.HIT_CANCEL;
			}
			else
			{
				hitFX = box.BlockEffectIndex;
				target.BlockHit(actor, box, blockState);
				if (box.AllowSelfPushback)
				{
					HitPushback(target, box.SelfPushbackDuration, box.SelfPushbackForce);
				}
				NetsuLog.Debug("Fighter: Blocked!");
			}
			CancelConditions |= CancelCondition.BLOCK_CANCEL;
		}
		else
		{
			hitFX = box.HitEffectIndex;
			if (GameManager.Instance.WaitingForFirstStrike())
			{
				GameManager.Instance.PlayHitNotificationByIndex((int)playerID, 0);
			}
			if (IsCounter(target))
			{
				GameManager.Instance.PlayHitNotificationByIndex((int)playerID, 1);
				target.NetsuCounterHitstunBonus = NetsuCounterHitstun;   // Netsu: counter hits add hitstun
			}
			else if (IsPunishCounter(target))
			{
				GameManager.Instance.PlayHitNotificationByIndex((int)playerID, 2);
				target.NetsuCounterHitstunBonus = NetsuCounterHitstun;
			}
			target.HitDamage(actor, box, isTrade: false);
			if (box.AllowSelfPushback)
			{
				HitPushback(target, box.SelfPushbackDuration, box.SelfPushbackForce);
			}
			CancelConditions |= CancelCondition.HIT_CANCEL;
			NetsuLog.Debug("Fighter: Hit!");
		}
		HitConfirm(target, netsuBlocked ? box.SelfSuperGaugeGain / 2 : box.SelfSuperGaugeGain, (uint)box.SelfHitStopDuration, hitFX, contact);
	}

	public void HitTrade(SakugaActor target, HitboxElement box, Vector2I contact)
	{
		GameManager.Instance.PlayHitNotificationByIndex((int)playerID, 1);
		HitDamage(target, box, isTrade: true);
		if (box.HitEffectIndex >= 0 && contact != Vector2I.Zero)
		{
			NetsuSpawnVFX(box.HitEffectIndex, contact);
		}
		NetsuLog.Debug("Fighter: Traded!");
	}

	/// <summary>Netsu: frames after block / hit stun (and after getting up) during which a fighter can't be thrown.</summary>
	/// <summary>Netsu (Oct 25): the side of her opponent an orbit started on (-1 left of them, 1 right, 0 none): Leticia's
	/// Crimson Waltz circles them from there (NetsuOrbitAction). Saved with the match (SakugaActorState).</summary>
	public int NetsuOrbitSide;

	// ---------------------------------------------------------------------------------------------
	// Netsu (Oct 28 2026, TamaDeez): air tech. From the moment she techs in the air (a "Recovery_Air" state):
	//  - she can't act (attack, jump, air dash, special, Burst) for GameManager.NetsuAirTechActDelay frames (the
	//    20-frame tech animation is part of it; landing ends the wait early);
	//  - buttons pressed during that wait are thrown away: for NetsuAirTechFreshFrames frames after it, a button move
	//    only comes out if its button was pressed after the wait ended (mashing doesn't give an instant normal);
	//  - she is invincible (hits, throws, projectiles) until she lands. Doing anything before landing ends it.
	// Saved for rollback (SakugaActorState keys 44-46).
	public const int NetsuAirTechFreshFrames = 8;

	public bool NetsuAirTechInvul;
	public int NetsuAirTechWait;
	public int NetsuAirTechFresh;

	/// <summary>Called when an air tech move starts.</summary>
	public void NetsuAirTechBegin()
	{
		NetsuAirTechInvul = true;
		int delay = GameManager.Instance != null ? GameManager.Instance.NetsuAirTechActDelay : 26;
		NetsuAirTechWait = Mathf.Max(0, delay);
		NetsuAirTechFresh = NetsuAirTechWait > 0 ? 0 : 1;
	}

	public void NetsuAirTechClear()
	{
		NetsuAirTechInvul = false;
		NetsuAirTechWait = 0;
		NetsuAirTechFresh = 0;
	}

	/// <summary>Frames she still can't act after an air tech (StanceManager skips the move check meanwhile).</summary>
	public bool NetsuAirTechLocked()
	{
		return NetsuAirTechWait > 0;
	}

	private void NetsuAirTechTick()
	{
		if (!NetsuAirTechInvul && NetsuAirTechWait == 0 && NetsuAirTechFresh == 0)
		{
			return;
		}
		StateType type = StateManager != null ? StateManager.CurrentStateType() : StateType.NULL;
		if (IsKO() || type == StateType.HIT_REACTION || type == StateType.BLOCKING)
		{
			NetsuAirTechClear();
			return;
		}
		bool onGround = Body != null && Body.IsOnGround;
		if (NetsuAirTechWait > 0)
		{
			NetsuAirTechWait = onGround ? 0 : NetsuAirTechWait - 1;
			if (NetsuAirTechWait == 0)
			{
				NetsuAirTechFresh = 1;   // first frame she may act: only a press on this frame counts
			}
		}
		else if (NetsuAirTechFresh > 0)
		{
			NetsuAirTechFresh = NetsuAirTechFresh >= NetsuAirTechFreshFrames ? 0 : NetsuAirTechFresh + 1;
		}
		if (onGround)
		{
			NetsuAirTechInvul = false;   // landed
		}
	}

	// ---------------------------------------------------------------------------------------------
	// Netsu (Oct 29 2026, TamaDeez): the same move (a charged attack or a normal) ground-bouncing the opponent a second
	// time in one combo gives a hard knockdown instead of the bounce. Moves are told apart like repeat proration (the
	// attacker's move index; more hits of the same use count once). Saved for rollback (SakugaActorState keys 50-52).
	public ulong NetsuBounceUsedLo;
	public ulong NetsuBounceUsedHi;
	public int NetsuBounceUse;

	/// <summary>Registers a ground bounce on this fighter by `attacker`'s current move; true if that move already ground
	/// bounced them earlier in this combo (another use of it).</summary>
	public bool NetsuGroundBounceRepeat(SakugaActor attacker)
	{
		if (!NetsuHitMove(attacker, out SakugaActor root, out int move, out int use))
		{
			return false;
		}
		int key = (1 << 30) | (move << 22) | (use & 0x3FFFFF);
		if (key == NetsuBounceUse)
		{
			return false;   // another hit of the same use
		}
		bool repeat = move < 64 ? (NetsuBounceUsedLo & (1UL << move)) != 0 : (NetsuBounceUsedHi & (1UL << (move - 64))) != 0;
		if (move < 64)
		{
			NetsuBounceUsedLo |= 1UL << move;
		}
		else if (move < 128)
		{
			NetsuBounceUsedHi |= 1UL << (move - 64);
		}
		NetsuBounceUse = key;
		return repeat;
	}

	// Netsu (Oct 29 2026, TamaDeez): star stacks (Flan). 0..Data.NetsuStarStackMax, start each round at 0. Saved for
	// rollback (SakugaActorState key 54). Shown on the HUD under the Burst gauge (match_setup.netsu_star_hud).
	public int NetsuStarStacks;
	private Node _starHud;
	private int _starShown = -1;
	private int _starQuiet;
	private static readonly StringName NetsuStarMethod = new StringName("netsu_star_hud");

	private void NetsuStarHud()
	{
		if (GetMaster() != null || Data == null || Data.NetsuStarStackMax <= 0)
		{
			return;
		}
		if (_starHud == null)
		{
			_starHud = (Engine.GetMainLoop() as SceneTree)?.Root.GetNodeOrNull("MatchSetup");
			if (_starHud == null || !_starHud.HasMethod(NetsuStarMethod))
			{
				_starHud = null;
				return;
			}
		}
		_starQuiet++;
		if (NetsuStarStacks == _starShown && _starQuiet < 15)
		{
			return;
		}
		_starQuiet = 0;
		_starShown = NetsuStarStacks;
		_starHud.Call(NetsuStarMethod, (int)playerID, NetsuStarStacks, Data.NetsuStarStackMax);
	}

	public const int NetsuThrowProtectFrames = 5;

	public int NetsuThrowProtect;

	/// <summary>Netsu: can `target` be thrown right now? Not in block / hit stun, not just out of it, not knocked out.</summary>
	public static bool NetsuThrowable(SakugaActor target)
	{
		if (target == null || target.IsKO() || target.NetsuThrowProtect > 0 || target.StateManager == null)
		{
			return false;
		}
		StateType t = target.StateManager.CurrentStateType();
		return t != StateType.BLOCKING && t != StateType.HIT_REACTION;
	}

	public void ThrowDamage(SakugaActor target, HitboxElement box, Vector2I contact)
	{
		if (target.Data != null && !NetsuThrowable(target))
		{
			return;   // Netsu: a fighter in or just out of stun can't be grabbed (the throw whiffs)
		}
		if (!target.ContainsFrameProperty(FrameProperties.THROW_IMUNITY) && ((target.Body.IsOnGround && box.GroundThrow) || (target.IsAirState() && box.AirThrow) || (box.GroundThrow && box.AirThrow)))
		{
			uint finalHitstop = (uint)box.ThrowHitstop;
			if (target.StateManager.CurrentStateType() == StateType.HIT_REACTION)
			{
				finalHitstop = (uint)box.ThrowHitstopAfterHit;
			}
			target.ThrowHit(this, box, finalHitstop);   // Netsu fix: Mahou passed the thrown fighter itself here, so
			                                            // it turned to face away (and a throw break pushed both one way)
			HitConfirm(target, 0, finalHitstop, -1, Vector2I.Zero);
			NetsuLog.Debug("Fighter: Throw!");
		}
	}

	public void ThrowTrade()
	{
		ThrowEscapeAction();
	}

	public void HitboxClash(SakugaActor target, HitboxElement box, Vector2I contact)
	{
		HitConfirm(target, 0, (uint)box.ClashHitStopDuration, box.ClashEffectIndex, contact);
		CancelConditions |= CancelCondition.HIT_CANCEL;
	}

	public void ProjectileClash(SakugaActor target, HitboxElement box, Vector2I contact)
	{
		HitConfirm(target, 0, 0u, box.ClashEffectIndex, contact);
	}

	public void ProjectileDeflect(SakugaActor target, HitboxElement box, Vector2I contact)
	{
	}

	public void CounterHit(SakugaActor target, HitboxElement box, Vector2I contact)
	{
		HitConfirm(target, box.SelfSuperGaugeGain, (uint)box.SelfHitStopDuration, box.HitEffectIndex, contact);
		target.HitConfirm(target, box.OpponentSuperGaugeGain, (uint)box.OpponentHitStopDuration, -1, Vector2I.Zero);
	}

	public void ProximityBlock(HitboxElement box)
	{
		if (StanceManager == null || StateManager == null)
		{
			return;
		}
		int blockState = StanceManager.GetBlockState(box.HitType, 0);
		if (blockState >= 0)
		{
			if (UseAI && Brain != null)
			{
				Brain.proximityHit = box.HitType;
			}
			if (Body != null)
			{
				Body.ProximityBlocked = true;
			}
			if (CanBlock() && StateManager.CurrentStateType() != StateType.BLOCKING)
			{
				StateManager.PlayState(blockState, reset: true);
				StanceManager.Clear();
			}
		}
	}

	public void OnHitboxExit()
	{
		if (StanceManager != null && StateManager != null && !BlockStun && StateManager.CurrentStateType() == StateType.BLOCKING)
		{
			int blockState = StanceManager.ExitBlockState(SelectBlockStance());
			if (blockState >= 0)
			{
				StateManager.PlayState(blockState, reset: true);
			}
		}
	}

	/// <summary>Netsu (Oct 29): this actor belongs to a move that spent Craft Gauge (set when a fighter starts such a move,
	/// copied to what it spawns). Its hits give the attacker no meter. Saved for rollback (SakugaActorState key 55).</summary>
	public bool NetsuMeterSpendTag;

	/// <summary>Netsu (Oct 29): gauges for a real hit. `this` = the one hit, hitter = what hit it (fighter, projectile, assist).</summary>
	public void NetsuMeterOnHit(SakugaActor hitter, int actualDamage)
	{
		if (Parameters == null || actualDamage <= 0)
		{
			return;
		}
		Parameters.NetsuDefenderHit(actualDamage);
		NetsuMeterAttacker(hitter, actualDamage, blocked: false);
	}

	/// <summary>Netsu (Oct 29): gauges for a blocked hit (baseDamage = the hit's damage before scaling).</summary>
	public void NetsuMeterOnBlock(SakugaActor hitter, int baseDamage, bool instantBlock)
	{
		if (Parameters == null || baseDamage <= 0)
		{
			return;
		}
		Parameters.NetsuDefenderBlock(baseDamage, instantBlock);
		NetsuMeterAttacker(hitter, baseDamage, blocked: true);
	}

	private static void NetsuMeterAttacker(SakugaActor hitter, int damage, bool blocked)
	{
		if (hitter == null)
		{
			return;
		}
		SakugaActor root = hitter.NetsuRoot();
		if (root == null || root.Parameters == null)
		{
			return;
		}
		MoveSettings move = hitter.NetsuMeterMove();
		if (hitter.NetsuMeterSpendTag && (move == null || !move.NetsuMeterGainOnSpend))
		{
			root.Parameters.NetsuAttackerNoGain(blocked);
			return;
		}
		decimal moveMod = move != null && move.NetsuMeterGainPercent > 0 ? move.NetsuMeterGainPercent / 100m : 1m;
		root.Parameters.NetsuAttackerGain(damage, blocked, moveMod, hitter.NetsuIsAssistHit());
	}

	/// <summary>The move this actor's hit belongs to: a fighter's current move, a projectile's spawning move.</summary>
	private MoveSettings NetsuMeterMove()
	{
		SakugaActor root = NetsuRoot();
		if (root == null || root.StanceManager == null || root.StanceManager.GetCurrentStance() == null)
		{
			return null;
		}
		MoveSettings[] moves = root.StanceManager.GetCurrentStance().Moves;
		int index = root == this ? root.StanceManager.CurrentMove : (NetsuIsAssistHit() ? -1 : NetsuSpawnMove);
		return moves != null && index >= 0 && index < moves.Length ? moves[index] : null;
	}

	/// <summary>Netsu (Oct 29): why Burst can or can't be used right now (debug read-out).</summary>
	public string NetsuBurstStatus()
	{
		if (Parameters == null || Parameters.Will == null)
		{
			return "no";
		}
		if (IsKO())
		{
			return "no (KO)";
		}
		if (Parameters.Will.CurrentValue < Parameters.Will.MaxValue)
		{
			return "no (gauge not full)";
		}
		if (Parameters.Will.State != WillState.WORKING)
		{
			return "no (gauge locked)";
		}
		if (StateManager == null || StateManager.CurrentStateType() != StateType.HIT_REACTION)
		{
			return "ready (only while being hit)";
		}
		if (NetsuNoBurst)
		{
			return "no (this combo's hit doesn't allow Burst)";
		}
		return "YES";
	}

	/// <summary>Netsu: the fighter at the top of the master chain (itself for a fighter).</summary>
	public SakugaActor NetsuRoot()
	{
		SakugaActor a = this;
		int guard = 0;
		while (a.GetMaster() != null && a.GetMaster() != a && guard++ < 8)
		{
			a = a.GetMaster();
		}
		return a;
	}

	/// <summary>Netsu: spawns hit sparks from the first pool up the master chain that has effects
	/// (an assist or its projectile has none of its own and borrows its fighter's).</summary>
	public void NetsuSpawnVFX(int index, Vector2I position)
	{
		SakugaActor a = this;
		int guard = 0;
		while (a != null && guard++ < 8)
		{
			if (a.Pool != null && a.Pool.VFXCount > index)
			{
				a.Pool.SpawnVFX(index, position, Body.PlayerSide, attached: false);
				return;
			}
			if (a.GetMaster() == a)
			{
				return;
			}
			a = a.GetMaster();
		}
	}

	public string DebugInfo()
	{
		return "Position: " + Body.FixedPosition.ToString() + "\nVelocity: " + Body.FixedVelocity.ToString() + "\nStance: " + StanceManager.CurrentStance + "\nCurrent State: " + StateManager.CurrentState + "\nState Name: " + StateManager.GetCurrentState().StateName + "\nCurrent Move: " + StanceManager.CurrentMove + "\nBuffered Move: " + StanceManager.BufferedMove + "\nFrame: " + StateManager.CurrentStateFrame + "\nHitstun Type: " + HitstunType.ToString() + "\nHealth: " + Parameters.Health.CurrentValue + "/" + Data.MaxHealth + "\nSuper Gauge: " + Parameters.SuperGauge.CurrentValue + "/" + Data.MaxSuperGauge + "\nWill: " + Parameters.Will.CurrentValue + "/" + Data.MaxWill + "\nSuper Armor: " + Parameters.SuperArmor.CurrentValue + "\nOn Blockstun: " + BlockStun + "\nInput Side: " + InputSide() + "\nFrame Properties: " + FrameProperties.ToString() + "\nHit Stop: (" + Hitstop.IsRunning() + ") " + Hitstop.TimeLeft + "\nHit Stun: (" + Hitstun.IsRunning() + ") " + Hitstun.TimeLeft + "\nMove Buffer: (" + StanceManager.MoveBuffer.IsRunning() + ") " + StanceManager.MoveBuffer.TimeLeft + "\nBounce: (" + Bounce.TimeLeft + ", X:" + BounceXIntensity + ", Y:" + BounceYIntensity + ")\nCharge Buffers: " + Inputs.hCharge + " | " + Inputs.vCharge + "\nBlocking: " + BlockStun + Parameters.NetsuMeterDebug();
	}

	public Vector2I GenerateTargetPosition(Vector2I Target, int index, RelativeTo xRelative, RelativeTo yRelative)
	{
		int relativePosX = 0;
		int relativePosY = 0;
		switch (xRelative)
		{
		case RelativeTo.SELF:
			relativePosX = Body.FixedPosition.X;
			Target.X *= Body.PlayerSide;
			break;
		case RelativeTo.OPPONENT:
			relativePosX = GetOpponents()[0].Body.FixedPosition.X;
			Target.X *= GetOpponents()[0].Body.PlayerSide;
			break;
		case RelativeTo.FIGHTER:
			switch (index)
			{
			case 0:
				relativePosX = Body.FixedPosition.X;
				Target.X *= Body.PlayerSide;
				break;
			case 1:
				relativePosX = GetOpponents()[0].Body.FixedPosition.X;
				Target.X *= GetOpponents()[0].Body.PlayerSide;
				break;
			}
			break;
		case RelativeTo.SPAWNABLE:
			relativePosX = Pool.GetActiveSpawnByIndex(index).Body.FixedPosition.X;
			Target.X *= Pool.GetActiveSpawnByIndex(index).Body.PlayerSide;
			break;
		}
		switch (yRelative)
		{
		case RelativeTo.SELF:
			relativePosY = Body.FixedPosition.Y;
			break;
		case RelativeTo.OPPONENT:
			relativePosY = GetOpponents()[0].Body.FixedPosition.Y;
			break;
		case RelativeTo.FIGHTER:
			switch (index)
			{
			case 0:
				relativePosY = Body.FixedPosition.Y;
				break;
			case 1:
				relativePosY = GetOpponents()[0].Body.FixedPosition.Y;
				break;
			}
			break;
		case RelativeTo.SPAWNABLE:
			relativePosY = Pool.GetActiveSpawnByIndex(index).Body.FixedPosition.Y;
			break;
		}
		return new Vector2I(Target.X + relativePosX, Target.Y + relativePosY);
	}

	public void PlayIntro(string opponentName)
	{
		if (Data.Intros == null || Data.Intros.Length == 0)
		{
			return;
		}
		if (Data.Intros.Length == 1)
		{
			StateManager.PlayState(Data.Intros[0].StateIndex);
			return;
		}
		FighterIntro introToPlay = null;
		for (int i = 0; i < Data.VictoryPoses.Length; i++)
		{
			if (Data.VictoryPoses[i].ForOpponent == opponentName)
			{
				introToPlay = Data.VictoryPoses[i];
				break;
			}
			if (Data.VictoryPoses[i].ForOpponent == "")
			{
				introToPlay = Data.VictoryPoses[i];
			}
		}
		StateManager.PlayState(introToPlay.StateIndex);
	}

	public void PlayOutro(string opponentName, out string VictoryMessage)
	{
		VictoryMessage = Data.Profile.ShortName + " is winner!";
		if (Data.Outros == null || Data.Outros.Length == 0)
		{
			return;
		}
		if (Data.Outros.Length == 1)
		{
			StateManager.PlayState(Data.Outros[0].StateIndex);
			VictoryMessage = Data.Outros[0].FinalMessage;
			return;
		}
		FighterOutro outroToPlay = null;
		for (int i = 0; i < Data.Outros.Length; i++)
		{
			if (Data.Outros[i].ForOpponent == opponentName)
			{
				outroToPlay = Data.Outros[i];
				break;
			}
			if (Data.Outros[i].ForOpponent == "")
			{
				outroToPlay = Data.Outros[i];
			}
		}
		// Netsu fix: nobody matched and there's no generic ("") outro -> use the first one
		// instead of crashing at the end of the match.
		if (outroToPlay == null)
		{
			outroToPlay = Data.Outros[0];
		}
		StateManager.PlayState(outroToPlay.StateIndex);
		VictoryMessage = outroToPlay.FinalMessage;
	}

	public void PlayVictoryPose(string opponentName)
	{
		if (Data.VictoryPoses == null || Data.VictoryPoses.Length == 0)
		{
			return;
		}
		if (Data.VictoryPoses.Length == 1)
		{
			StateManager.PlayState(Data.VictoryPoses[0].StateIndex);
			return;
		}
		FighterIntro introToPlay = null;
		for (int i = 0; i < Data.VictoryPoses.Length; i++)
		{
			if (Data.VictoryPoses[i].ForOpponent == opponentName)
			{
				introToPlay = Data.VictoryPoses[i];
				break;
			}
			if (Data.VictoryPoses[i].ForOpponent == "")
			{
				introToPlay = Data.VictoryPoses[i];
			}
		}
		StateManager.PlayState(introToPlay.StateIndex);
	}

	public void PlayDefeatPose()
	{
		StateManager.PlayState(Data.DefeatPose);
	}

	public override byte[] GetStateData()
	{
		State.GetStateData(ref actor);
		return MessagePackSerializer.Serialize(State);
	}

	public override void SetStateData(byte[] stateBuffer)
	{
		State = MessagePackSerializer.Deserialize<SakugaActorState>(stateBuffer);
		State.SetStateData(ref actor);
		if (Body != null)
		{
			Body.UpdateColliders();
		}
	}
}
