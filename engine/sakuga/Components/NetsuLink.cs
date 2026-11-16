using System.Collections.Generic;
using System.Reflection;
using Godot;
using MessagePack;
using SakugaEngine.Game;
using SakugaEngine.GameState;
using SakugaEngine.Global;
using SakugaEngine.Resources;

namespace SakugaEngine;

/// <summary>
/// NETSU LINK BREAK (Nov 8 2026, second design): the party mechanic. One per fighter, made by GameManager.CreateFighter
/// after the fighter's two partners (NetsuAssist slot 0 = S1, slot 1 = S2).
///
/// The rules:
///  1. Each party member places one CREST.
///     - the fighter: a D special that hits (a special, Priority 7-8, whose input uses the D button: Cecilia's 214D), or
///       the Air Throw (a hit-grab that ends combos: it places the crest but can never spend it);
///     - a fighting partner (Eren, Adin, Harie): its move hits (one crest per call);
///     - a support partner (Mary): by acting (her buff starts), no hit needed.
///     Crests stay until a Break uses them or the round ends.
///  2. A partner hit while acting is OUT for the round (NetsuAssist.Out). The other partner fills its slot (it may place
///     two crests). Both partners out = no Breaks this round.
///  3. Three crests = LINK READY (both partners' cooldowns refresh). The player picks the LINK BREAK:
///     - D + S1 / D + S2: that partner leads ("Link Call S1 / S2" stance moves: the fighter poses, the partner comes
///       at once, free). Its hit is its Link version (PartnerVersions); Mary's buff lasts twice as long and staggers.
///     - C + D: the fighter's own Link Break (a stance move whose name starts with "Link Break": Cecilia's Moonlit
///       Stillness, a slash-through that leaves them standing in a long stagger; hold back as it ends to land on
///       their front side instead of behind them).
///     The Link moves only come out while Ready (LinkMoveAllowed); otherwise the buttons do what they always do. They
///     cancel from normals and specials (StanceManager.NetsuLinkCancel). On hit the opponent is Unbalanced: no Burst
///     until the combo ends (SakugaActor.NetsuNoBurst).
///
/// Per-character settings are the tables below (by assist name) and the move names, so the generated data files
/// (tools/sprite_port/assists.py, the fighters' move files) don't need new fields.
/// Saved for rollback (NetsuLinkState). The battle HUD reads it through MatchSetup.netsu_link_hud().
/// </summary>
public partial class NetsuLink : SakugaNode
{
	// who leads a Break (Leader)
	public const int LeadNone = 0;
	public const int LeadFighter = 1;
	public const int LeadPartner1 = 2;   // slot 0 (S1)
	public const int LeadPartner2 = 3;   // slot 1 (S2)

	// Link versions (how the leading hit changes)
	public const int VersionNone = 0;
	public const int VersionWallBounce = 1;
	public const int VersionRestand = 2;
	public const int VersionGroundBounce = 3;
	/// <summary>Nov 9 (Adin): into the wall, back toward you, then down to the floor with no floor bounce.</summary>
	public const int VersionWallSplat = 4;

	// HUD events (EventKind)
	public const int EventCrest = 1;
	public const int EventReady = 2;
	public const int EventBreak = 3;
	public const int EventOut = 4;

	/// <summary>Stance moves: the fighter's own Break (C + D) and the two partner Breaks (D + S1 / D + S2).</summary>
	public const string FighterBreakPrefix = "Link Break";
	public const string CallS1Name = "Link Call S1";
	public const string CallS2Name = "Link Call S2";

	/// <summary>The fighter's own Break leaves them standing in this long a stagger (Link version "restand").</summary>
	public const int FighterBreakStagger = 60;

	/// <summary>Partners that place their crest by acting (no hit needed).</summary>
	private static readonly HashSet<string> Supports = new HashSet<string> { "Mary", "Doris" };

	/// <summary>A fighting partner's Link version when it leads the Break.</summary>
	private static readonly Dictionary<string, int> PartnerVersions = new Dictionary<string, int>
	{
		{ "Eren", VersionWallBounce },
		{ "Adin", VersionWallSplat },    // Nov 9: Shield Rush slams them into the wall, back to you, then to the floor
		{ "Harie", VersionWallBounce },
	};

	/// <summary>A support leading the Break: its buff lasts this much longer (percent).</summary>
	public const int SupportLinkBuffPercent = 200;

	/// <summary>Nov 8: the Unbalance stops the whole fight this long (frames) for its Cold Steel style cut-in (the kanji
	/// stamp and the Link Attack bands: game/ui/battle_hud/netsu_link_fx.gd). GameManager.NetsuStartPause.</summary>
	public const int BreakPauseFrames = 48;

	/// <summary>A support's Break staggers a free opponent this long (frames).</summary>
	public const int SupportStaggerFrames = 50;

	public SakugaActor Fighter;

	// --- match state (saved for rollback) ------------------------------------------------
	public bool CrestFighter;
	public int CrestP0;
	public int CrestP1;
	public bool Ready;
	public int Leader;
	public bool LinkMoveWasOn;
	public bool BreakLanded;
	public int EventSeq;
	public int EventKind;
	public int EventWho;
	public int Breaks;
	/// <summary>Nov 8: after a partner's wall bounce Break the opponent can't air tech until they touch the ground, however
	/// many hits come after it (Tick keeps their air counter lock on).</summary>
	public bool NoTechTillGround;
	public int NoTechWait;
	public int NoTechGround;
	public bool NoTechAirborne;

	private NetsuLinkState _state;

	public static NetsuLink Create(SakugaActor fighter)
	{
		if (fighter == null)
		{
			return null;
		}
		NetsuLink link = new NetsuLink { Fighter = fighter };
		link.Name = fighter.playerID + "_NetsuLink";
		GameManager.Instance.AddActor(link, isPhysicsBody: false);
		link.ResetRound();
		return link;
	}

	public void ResetRound()
	{
		CrestFighter = false;
		CrestP0 = 0;
		CrestP1 = 0;
		Ready = false;
		Leader = LeadNone;
		LinkMoveWasOn = false;
		BreakLanded = false;
		NoTechTillGround = false;
		NoTechWait = 0;
		NoTechGround = 0;
		NoTechAirborne = false;
	}

	// --- helpers -------------------------------------------------------------------------------

	public NetsuAssist Partner(int slot)
	{
		if (Fighter == null)
		{
			return null;
		}
		return slot == 0 ? Fighter.NetsuAssist : Fighter.NetsuAssist2;
	}

	private static bool PartnerIn(NetsuAssist p)
	{
		return p != null && p.Element != null && !p.Out;
	}

	public static bool IsSupport(NetsuAssist p)
	{
		return p != null && p.Element != null && Supports.Contains(p.Element.AssistName);
	}

	public static bool IsFighterBreak(MoveSettings m)
	{
		return m != null && m.MoveName != null && m.MoveName.StartsWith(FighterBreakPrefix);
	}

	/// <summary>-1 = not a partner Break move, else the partner slot (0 = S1, 1 = S2).</summary>
	public static int CallSlot(MoveSettings m)
	{
		if (m == null || m.MoveName == null)
		{
			return -1;
		}
		return m.MoveName == CallS1Name ? 0 : (m.MoveName == CallS2Name ? 1 : -1);
	}

	public static bool IsLinkMove(MoveSettings m)
	{
		return IsFighterBreak(m) || CallSlot(m) >= 0;
	}

	/// <summary>StanceManager.CheckMoveConditions: the Link moves only exist while LINK READY (and a partner Break needs that
	/// partner in and ready). Every other move: true.</summary>
	public static bool LinkMoveAllowed(SakugaActor owner, MoveSettings m)
	{
		if (!IsLinkMove(m))
		{
			return true;
		}
		NetsuLink link = owner?.NetsuLink;
		if (link == null || !link.Ready || link.Leader != LeadNone)
		{
			return false;
		}
		int slot = CallSlot(m);
		if (slot < 0)
		{
			return true;
		}
		NetsuAssist p = link.Partner(slot);
		return p != null && p.CanLead();
	}

	/// <summary>The fighter's current move if it is a Link move (and she is still in its state), else null.</summary>
	private static MoveSettings CurrentLinkMove(SakugaActor f)
	{
		if (f == null || f.StanceManager == null || f.StanceManager.CurrentMove < 0 || f.StateManager == null)
		{
			return null;
		}
		MoveSettings m = f.StanceManager.GetCurrentMove();
		return IsLinkMove(m) && f.StateManager.CurrentState == m.MoveState ? m : null;
	}

	private static readonly Dictionary<MoveSettings, bool> _dSpecials = new Dictionary<MoveSettings, bool>();

	/// <summary>A D special: a special (Priority 7-8) whose input uses the D button (ButtonInputs.FACE_E).</summary>
	public static bool IsDSpecial(MoveSettings m)
	{
		if (m == null || m.Priority < 7 || m.Priority > 8 || m.Inputs == null)
		{
			return false;
		}
		if (_dSpecials.TryGetValue(m, out bool known))
		{
			return known;
		}
		bool d = false;
		if (m.Inputs.ValidInputs != null)
		{
			foreach (InputOption option in m.Inputs.ValidInputs)
			{
				if (option?.Inputs == null)
				{
					continue;
				}
				foreach (InputSequence step in option.Inputs)
				{
					if (step != null && (step.Buttons & ButtonInputs.FACE_E) != 0)
					{
						d = true;
					}
				}
			}
		}
		_dSpecials[m] = d;
		return d;
	}

	private void Event(int kind, int who)
	{
		EventSeq++;
		EventKind = kind;
		EventWho = who;
	}

	private int PartnerCrests => CrestP0 + CrestP1;

	// --- every frame ---------------------------------------------------------------------------

	public override void Tick()
	{
		if (Fighter == null)
		{
			return;
		}
		MoveSettings m = CurrentLinkMove(Fighter);
		bool on = m != null;
		if (on && !LinkMoveWasOn && Ready && Leader == LeadNone)
		{
			int slot = CallSlot(m);
			if (slot >= 0)
			{
				// D + S1 / D + S2: that partner comes at once and leads the Break
				NetsuAssist p = Partner(slot);
				if (p != null && p.CanLead())
				{
					StartBreak(LeadPartner1 + slot);
					p.BreakCall();
				}
			}
			else
			{
				StartBreak(LeadFighter);   // C + D: her own Break
			}
		}
		if (!on && LinkMoveWasOn && Leader == LeadFighter)
		{
			if (BreakLanded)
			{
				ChooseSide();
			}
			Leader = LeadNone;   // her Break move is over (it hit or not)
		}
		LinkMoveWasOn = on;
		if (Leader == LeadPartner1 || Leader == LeadPartner2)
		{
			NetsuAssist p = Partner(Leader - LeadPartner1);
			if (p == null || !p.LinkLead)
			{
				Leader = LeadNone;   // the leading partner has left
			}
		}
		if (NoTechTillGround)
		{
			SakugaActor o = Fighter.GetOpponent(0);
			// Nov 9: it only counts down / looks for the landing once they have actually left the floor. (Before: the
			// Break hit's hitstop kept them on the floor for 16 frames, which already counted as "landed": the lock was
			// gone before they flew, and they teched in the air.)
			bool frozen = o != null && o.OnHitstop();
			bool onFloor = o != null && o.Body != null && o.Body.IsOnGround;
			if (!frozen)
			{
				if (!onFloor)
				{
					NoTechAirborne = true;
				}
				if (!NoTechAirborne && NoTechWait > 0)
				{
					NoTechWait--;
				}
				// "landed" = on the floor for a few frames in a row (a floor bounce touches it for a frame and goes on)
				NoTechGround = NoTechAirborne && onFloor ? NoTechGround + 1 : 0;
			}
			if (o == null || o.Body == null || o.IsKO() || NoTechGround >= 4 || (!NoTechAirborne && NoTechWait <= 0)
				|| o.StateManager == null || o.StateManager.CurrentStateType() != StateType.HIT_REACTION)
			{
				NoTechTillGround = false;
			}
			else if (!o.Body.IsOnGround)
			{
				o.NetsuAirCounterLock = true;   // (also the purple look of the juggle meter)
			}
		}
		TrainingFill();
		UpdateReady();
	}

	/// <summary>Her own Break has ended after a hit: holding back (away from them) puts her on their front side instead of
	/// behind them (where the slash-through leaves her).</summary>
	private void ChooseSide()
	{
		SakugaActor o = Fighter.GetOpponent(0);
		if (o == null || o.Body == null || Fighter.Body == null || Fighter.Inputs == null || Fighter.Inputs.InputHistory == null)
		{
			return;
		}
		int ox = o.Body.FixedPosition.X;
		int fx = Fighter.Body.FixedPosition.X;
		PlayerInputs back = fx < ox ? PlayerInputs.LEFT : PlayerInputs.RIGHT;
		if (!Fighter.Inputs.IsBeingPressed(Fighter.Inputs.CurrentHistory, back))
		{
			return;
		}
		int nx = Mathf.Clamp(2 * ox - fx, -NetsuAssist.SpawnLimitX, NetsuAssist.SpawnLimitX);
		Fighter.Body.MoveTo(new Vector2I(nx, Fighter.Body.FixedPosition.Y));
		Fighter.Body.UpdateSide(nx < ox);
		Fighter.Body.FlipSide();
	}

	/// <summary>Training Menu "Unbalance: Always Ready" (NetsuTraining.LinkReady): every crest a partner still in can give
	/// is lit, so the fighter is LINK READY whenever no Break is running.</summary>
	private void TrainingFill()
	{
		GameManager gm = GameManager.Instance;
		if (gm == null || gm.Training == null || !gm.Training.LinkReady || Leader != LeadNone)
		{
			return;
		}
		bool in0 = PartnerIn(Partner(0));
		bool in1 = PartnerIn(Partner(1));
		if (!in0 && !in1)
		{
			return;
		}
		CrestFighter = true;
		CrestP0 = in0 ? (in1 ? 1 : 2) : 0;
		CrestP1 = in1 ? (in0 ? 1 : 2) : 0;
	}

	private void UpdateReady()
	{
		NetsuAssist p0 = Partner(0);
		NetsuAssist p1 = Partner(1);
		bool anyPartner = PartnerIn(p0) || PartnerIn(p1);
		bool ready = anyPartner && Leader == LeadNone && CrestFighter && PartnerCrests >= 2;
		if (ready && !Ready)
		{
			// LINK READY: the party regroups, both partners are ready to lead
			p0?.LinkRefresh();
			p1?.LinkRefresh();
			Event(EventReady, 0);
		}
		Ready = ready;
	}

	private void StartBreak(int leader)
	{
		Ready = false;
		CrestFighter = false;
		CrestP0 = 0;
		CrestP1 = 0;
		Leader = leader;
		BreakLanded = false;
	}

	// --- crests --------------------------------------------------------------------------------

	private void AddFighterCrest()
	{
		if (!CrestFighter)
		{
			CrestFighter = true;
			Event(EventCrest, LeadFighter);
		}
	}

	private void AddPartnerCrest(NetsuAssist p)
	{
		if (p == null || PartnerCrests >= 2)
		{
			return;
		}
		NetsuAssist other = Partner(1 - p.Slot);
		int cap = PartnerIn(other) ? 1 : 2;   // the other one is out (or missing): this one fills its slot
		if (p.Slot == 0 && CrestP0 < cap)
		{
			CrestP0++;
			Event(EventCrest, LeadPartner1);
		}
		else if (p.Slot == 1 && CrestP1 < cap)
		{
			CrestP1++;
			Event(EventCrest, LeadPartner2);
		}
	}

	/// <summary>NetsuAssist.Call (a normal call): a new call places a new crest.</summary>
	public void OnPartnerCalled(NetsuAssist p)
	{
		if (p == null)
		{
			return;
		}
		p.Acted = false;
		p.LinkLead = false;
	}

	/// <summary>A support's effect happened (Mary's buff starts: NetsuAssist.StartBuff). Returns true if it leads the Break.</summary>
	public bool OnPartnerActed(NetsuAssist p)
	{
		if (p == null || p.Acted)
		{
			return false;
		}
		p.Acted = true;
		if (p.LinkLead)
		{
			SakugaActor opponent = Fighter.GetOpponent(0);
			Break(opponent, stagger: true);
			return true;
		}
		if (IsSupport(p))
		{
			AddPartnerCrest(p);
		}
		return false;
	}

	/// <summary>NetsuAssist.Leave after its move ended normally. A support that never reached its effect still placed its
	/// crest by being there; a leader that never connected wasted the Break.</summary>
	public void OnPartnerFinished(NetsuAssist p)
	{
		if (p == null)
		{
			return;
		}
		if (!p.Acted && !p.LinkLead && IsSupport(p))
		{
			p.Acted = true;
			AddPartnerCrest(p);
		}
		p.LinkLead = false;
	}

	/// <summary>NetsuAssist.KnockOut: a partner was hit while acting.</summary>
	public void OnPartnerOut(NetsuAssist p)
	{
		if (p == null)
		{
			return;
		}
		p.LinkLead = false;
		Event(EventOut, LeadPartner1 + p.Slot);
	}

	/// <summary>SakugaActor.ThrowDamage: her Air Throw (hit-grab) connected: it places her crest, never a Break.</summary>
	public void OnAirThrow()
	{
		AddFighterCrest();
	}

	/// <summary>SakugaActor.BaseDamage: a hit from this fighter's side landed (not blocked).</summary>
	public void OnLanded(SakugaActor attacker, SakugaActor target, bool assistHit)
	{
		if (attacker == null || target == null)
		{
			return;
		}
		if (assistHit)
		{
			NetsuAssist p = Fighter.NetsuPartnerOf(attacker);
			if (p == null)
			{
				return;
			}
			if (p.LinkLead)
			{
				Break(target, stagger: false);
				p.Acted = true;
				return;
			}
			if (!p.Acted && !IsSupport(p))
			{
				p.Acted = true;   // one crest per call, on its first hit
				AddPartnerCrest(p);
			}
			return;
		}
		if (attacker != Fighter || Fighter.StanceManager == null || Fighter.StanceManager.CurrentMove < 0)
		{
			return;
		}
		MoveSettings m = Fighter.StanceManager.GetCurrentMove();
		if (Leader == LeadFighter && IsFighterBreak(m))
		{
			Break(target, stagger: false);
		}
		else if (IsDSpecial(m))
		{
			AddFighterCrest();
		}
	}

	/// <summary>The Break connects: the opponent is Unbalanced (no Burst until the combo ends).</summary>
	private void Break(SakugaActor target, bool stagger)
	{
		if (target == null || target.IsKO())
		{
			return;
		}
		if (stagger && target.StateManager != null && target.StateManager.CurrentStateType() != StateType.HIT_REACTION
			&& !target.OnHitstun() && !target.IsGrabbed())
		{
			target.HitDamage(Fighter, StaggerBox(), isTrade: false);
		}
		target.NetsuNoBurst = true;
		NetsuAssist leader = Leader >= LeadPartner1 ? Partner(Leader - LeadPartner1) : null;
		int version = VersionNone;
		if (leader != null && leader.Element != null)
		{
			PartnerVersions.TryGetValue(leader.Element.AssistName, out version);
		}
		if (version == VersionWallBounce || version == VersionWallSplat)
		{
			// Nov 8: a partner's wall bounce Break: no air tech until they touch the ground (an extended combo); the
			// air counter lock (cleared on landing, or by the next hit) does exactly that
			target.NetsuAirCounterLock = true;
			NoTechTillGround = true;   // kept on through the follow-up hits (Tick) until they land
			NoTechWait = 90;           // safety: if they never leave the floor (a whiff of physics), it ends anyway
			NoTechGround = 0;
			NoTechAirborne = false;
		}
		if (!BreakLanded)
		{
			BreakLanded = true;
			Breaks++;
			Event(EventBreak, Leader);
			GameManager.Instance?.NetsuStartPause((int)Fighter.playerID, 0, BreakPauseFrames);   // the Unbalance cut-in
		}
	}

	// --- Link versions -------------------------------------------------------------------------

	/// <summary>SakugaActor.BaseDamage, before the hit: the leading hit of a Break becomes its Link version.</summary>
	public static HitboxElement LinkBox(SakugaActor attacker, HitboxElement box)
	{
		if (attacker == null || box == null)
		{
			return box;
		}
		SakugaActor root = attacker.NetsuRoot();
		NetsuLink link = root?.NetsuLink;
		if (link == null || link.Leader == LeadNone)
		{
			return box;
		}
		int version = VersionNone;
		if (link.Leader == LeadFighter)
		{
			if (attacker == root && root.StanceManager != null && root.StanceManager.CurrentMove >= 0
				&& IsFighterBreak(root.StanceManager.GetCurrentMove()))
			{
				version = VersionRestand;
			}
		}
		else
		{
			NetsuAssist p = root.NetsuPartnerOf(attacker);
			if (p != null && p.LinkLead && p.Slot == link.Leader - LeadPartner1 && p.Element != null)
			{
				PartnerVersions.TryGetValue(p.Element.AssistName, out version);
			}
		}
		return version == VersionNone ? box : Variant(box, version);
	}

	private static readonly Dictionary<HitboxElement, HitboxElement>[] _variants =
	{
		new Dictionary<HitboxElement, HitboxElement>(),
		new Dictionary<HitboxElement, HitboxElement>(),
		new Dictionary<HitboxElement, HitboxElement>(),
		new Dictionary<HitboxElement, HitboxElement>(),
		new Dictionary<HitboxElement, HitboxElement>(),
	};

	private static FieldInfo[] _boxFields;

	private static HitboxElement Copy(HitboxElement box)
	{
		_boxFields ??= typeof(HitboxElement).GetFields(BindingFlags.Public | BindingFlags.Instance | BindingFlags.DeclaredOnly);
		HitboxElement c = new HitboxElement();
		foreach (FieldInfo f in _boxFields)
		{
			f.SetValue(c, f.GetValue(box));
		}
		return c;
	}

	/// <summary>The same hitbox with the Link version's hit reaction (made once per box and version).</summary>
	private static HitboxElement Variant(HitboxElement box, int version)
	{
		Dictionary<HitboxElement, HitboxElement> cache = _variants[version];
		if (cache.TryGetValue(box, out HitboxElement v))
		{
			return v;
		}
		v = Copy(box);
		v.OpponentHitStopDuration = Mathf.Max(v.OpponentHitStopDuration, 16);
		v.SelfHitStopDuration = Mathf.Max(v.SelfHitStopDuration, 12);
		v.NetsuSoftKnockdown = false;
		v.NetsuCounterLiftPercent = 100;   // Nov 9: a counter hit doesn't throw a Break's arc off (it sent them sky-high)
		switch (version)
		{
		case VersionWallSplat:
			// Nov 9 (Adin): a flatter, heavier arc into the wall; back off it toward you and down to the floor: no floor
			// bounce, so they land in a knockdown (no tech before that: NoTechTillGround)
			v.BounceTime = 120;
			v.BounceXIntensity = 40;
			v.BounceYIntensity = 0;
			v.NetsuAllowRestand = false;
			v.GroundHitstunType = HitstunType.KNOCKDOWN;
			v.AirHitstunType = HitstunType.KNOCKDOWN;
			v.GroundHitReaction = 7;
			v.CrouchHitReaction = 7;
			v.AirHitReaction = 7;
			v.GroundHitKnockback = new Vector2I(-130000, 38000);
			v.AirHitKnockback = new Vector2I(-130000, 38000);
			v.GroundHitKnockbackGravity = 200000;
			v.AirHitKnockbackGravity = 200000;
			v.GroundHitstun = 40;
			v.AirHitstun = 40;
			break;
		case VersionWallBounce:
			// like Eren's old Link Chase finisher (Cecilia's 236C last hit)
			v.BounceTime = 120;
			v.BounceXIntensity = 40;
			v.BounceYIntensity = 100;
			v.NetsuAllowRestand = false;
			v.GroundHitstunType = HitstunType.KNOCKDOWN;
			v.AirHitstunType = HitstunType.KNOCKDOWN;
			v.GroundHitReaction = 7;
			v.CrouchHitReaction = 7;
			v.AirHitReaction = 7;
			// Nov 8: a higher, slower arc than Eren's old chase (45000 up, gravity 300000): they used to hit the floor
			// before reaching the wall (a ground bounce instead), mostly after Adin's Shield Rush
			v.GroundHitKnockback = new Vector2I(-120000, 60000);
			v.AirHitKnockback = new Vector2I(-120000, 60000);
			v.GroundHitKnockbackGravity = 220000;
			v.AirHitKnockbackGravity = 220000;
			v.GroundHitstun = 40;
			v.AirHitstun = 40;
			break;
		case VersionRestand:
			// puts them back on their feet in a long stagger: time for a mix-up
			v.BounceTime = 0;
			v.BounceXIntensity = 0;
			v.BounceYIntensity = 0;
			v.NetsuAllowRestand = true;
			v.GroundHitstunType = HitstunType.BASIC;
			v.AirHitstunType = HitstunType.BASIC;
			v.GroundHitReaction = 1;
			v.CrouchHitReaction = 2;
			v.AirHitReaction = 1;
			v.GroundHitKnockback = Vector2I.Zero;
			v.AirHitKnockback = Vector2I.Zero;
			v.GroundHitstun = FighterBreakStagger;
			v.AirHitstun = FighterBreakStagger;
			break;
		case VersionGroundBounce:
			// slams them into the floor: they bounce back up
			v.BounceTime = 120;
			v.BounceXIntensity = 0;
			v.BounceYIntensity = 100;
			v.NetsuAllowRestand = false;
			v.GroundHitstunType = HitstunType.KNOCKDOWN;
			v.AirHitstunType = HitstunType.KNOCKDOWN;
			v.GroundHitReaction = 9;
			v.CrouchHitReaction = 9;
			v.AirHitReaction = 9;
			v.GroundHitKnockback = new Vector2I(-5000, -150000);
			v.AirHitKnockback = new Vector2I(-5000, -160000);
			v.GroundHitstun = 40;
			v.AirHitstun = 40;
			break;
		}
		cache[box] = v;
		return v;
	}

	private static HitboxElement _stagger;

	/// <summary>A support's Break on a free opponent: no damage, a long standing stagger.</summary>
	private static HitboxElement StaggerBox()
	{
		if (_stagger != null)
		{
			return _stagger;
		}
		_stagger = new HitboxElement
		{
			HitboxType = HitboxType.HITBOX,
			HitType = HitType.UNBLOCKABLE,
			BaseDamage = 0,
			KillingBlow = false,
			SelfSuperGaugeGain = 0,
			OpponentSuperGaugeGain = 0,
			OpponentHitStopDuration = 16,
			SelfHitStopDuration = 0,
			DamageScalingSubtract = 0,
			GroundHitstunType = HitstunType.BASIC,
			AirHitstunType = HitstunType.BASIC,
			GroundHitReaction = 1,
			CrouchHitReaction = 2,
			AirHitReaction = 1,
			GroundHitKnockback = Vector2I.Zero,
			AirHitKnockback = Vector2I.Zero,
			GroundHitstun = SupportStaggerFrames,
			AirHitstun = SupportStaggerFrames,
			NetsuAllowRestand = true,
			BounceTime = 0,
			BounceXIntensity = 0,
			BounceYIntensity = 0,
			AllowSelfPushback = false
		};
		return _stagger;
	}

	// --- rollback --------------------------------------------------------------------------------

	public override byte[] GetStateData()
	{
		_state.GetStateData(this);
		return MessagePackSerializer.Serialize(_state);
	}

	public override void SetStateData(byte[] stateBuffer)
	{
		_state = MessagePackSerializer.Deserialize<NetsuLinkState>(stateBuffer);
		_state.SetStateData(this);
	}

	// --- presentation ----------------------------------------------------------------------------

	private static readonly StringName NetsuHudMethod = new StringName("netsu_link_hud");
	private static readonly StringName NetsuBreakMethod = new StringName("netsu_link_break");
	private int _fxSeq = -1;   // presentation only: the last event the cut-in was shown for (-1 = not looked yet)
	private Node _hud;
	private bool _hudChecked;
	private string _hudKey = "";
	private int _hudQuiet;

	public override void Render()
	{
		if (Fighter == null)
		{
			return;
		}
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
		NetsuAssist p0 = Partner(0);
		NetsuAssist p1 = Partner(1);
		bool out0 = p0 == null || p0.Out;
		bool out1 = p1 == null || p1.Out;
		string key = (CrestFighter ? "1" : "0") + CrestP0 + CrestP1 + (Ready ? "R" : "-") + Leader + (out0 ? "x" : "o")
			+ (out1 ? "x" : "o") + "/" + EventSeq;
		_hudQuiet++;
		if (key == _hudKey && _hudQuiet < 15)
		{
			return;
		}
		_hudQuiet = 0;
		_hudKey = key;
		if (EventSeq != _fxSeq)
		{
			// Nov 8: a new Break: the Unbalance stamp + cut-in (once per Break, even when rollback replays frames)
			if (EventKind == EventBreak && _fxSeq >= 0 && _hud.HasMethod(NetsuBreakMethod))
			{
				SakugaActor o = Fighter.GetOpponent(0);
				Vector3 pos = o != null && o.Body != null
					? GlobalFunctions.ToScaledVector3(o.Body.FixedPosition + new Vector2I(0, SakugaActor.NetsuChestHeight)) : Vector3.Zero;
				_hud.Call(NetsuBreakMethod, (int)Fighter.playerID, pos, EventWho);
			}
			_fxSeq = EventSeq;
		}
		_hud.Call(NetsuHudMethod, (int)Fighter.playerID, CrestFighter, CrestP0, CrestP1, Ready, Leader, out0, out1,
			EventSeq, EventKind, EventWho);
	}
}
