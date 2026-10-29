using Godot;
using MahouSensou.Custom;
using SakugaEngine.Game;
using SakugaEngine.Global;
using SakugaEngine.Resources;

namespace SakugaEngine;

[GlobalClass]
public partial class SakugaParameters : Node
{
	protected SakugaActor _owner;

	[Export(PropertyHint.None, "")]
	public SakugaHealth Health;

	[Export(PropertyHint.None, "")]
	public SakugaSuperGauge SuperGauge;

	[Export(PropertyHint.None, "")]
	public SakugaSuperArmor SuperArmor;

	[Export(PropertyHint.None, "")]
	public WillGauge Will;

	[Export(PropertyHint.None, "")]
	public SakugaProrations Prorations;

	[Export(PropertyHint.None, "")]
	public CombatTracker Tracker;

	[Export(PropertyHint.None, "")]
	public FrameTimer[] Timers;

	[Export(PropertyHint.None, "")]
	public CustomVariable[] Variables;

	[Export(PropertyHint.None, "")]
	public SoundQueue[] SoundSources;

	public void Initialize(SakugaActor owner)
	{
		_owner = owner;
		if (Health != null)
		{
			Health.Initialize(_owner.Data);
		}
		if (SuperGauge != null)
		{
			SuperGauge.Initialize(_owner.Data);
		}
		if (Will != null)
		{
			Will.Initialize(_owner.Data);
		}
		if (SuperArmor != null)
		{
			SuperArmor.Initialize();
		}
		if (Prorations != null)
		{
			Prorations.Initialize(_owner.Data);
		}
		if (Tracker != null)
		{
			Tracker.Initialize(_owner);
		}
		if (HasVariables())
		{
			for (int v = 0; v < Variables.Length; v++)
			{
				Variables[v].Initialize();
			}
		}
	}

	public void Reset()
	{
		if (Health != null)
		{
			Health.Initialize(_owner.Data);
		}
		// Netsu: the Craft Gauge and the Burst gauge carry over between rounds
		// (they are filled/emptied once, in Initialize, at the start of the match).
		// An Overdrive that is still running ends with the round.
		if (Will != null && Will.State == WillState.LOCKED)
		{
			Will.State = WillState.WORKING;
		}
		NetsuOverdriveOn = false;   // Oct 28: Overdrive is once per round
		NetsuMeterRoundFrame = 0;   // Oct 29: the low-health trickle's frame counter starts again each round
		NetsuMeterCooldown = 0;     // Oct 29: no cooldown carried into a new round
		NetsuOverdriveLinkPending = false;
		if (SuperArmor != null)
		{
			SuperArmor.Initialize();
		}
		if (Prorations != null)
		{
			Prorations.Initialize(_owner.Data);
		}
		if (Tracker != null)
		{
			Tracker.Reset();
		}
		if (HasTimers())
		{
			for (int t = 0; t < Timers.Length; t++)
			{
				Timers[t].Stop();
			}
		}
		if (!HasVariables())
		{
			return;
		}
		for (int v = 0; v < Variables.Length; v++)
		{
			if (Variables[v].Reset)
			{
				Variables[v].Initialize();
			}
		}
	}

	public void Tick()
	{
		if (GameManager.Instance.Monitor.MatchState == MatchState.ROUND_RUNNING)
		{
			if (SuperGauge != null)
			{
				SuperGauge.Tick();
				// Oct 29: no more Craft Gauge for walking forward (meter only comes from hits, blocks and low health)
			}
			// Oct 29: the Burst gauge (and the meter cooldown) tick in NetsuResourceTick, which also runs during
			// hitstop and the super flash
			NetsuCheckOverdrive();
		}
		UpdateProrations();
		UpdateVariables();
		UpdateTimers();
		if (Tracker != null)
		{
			Tracker.UpdateFrameData();
		}
	}

	public void Clear()
	{
		if (Tracker != null)
		{
			Tracker.Reset();
		}
		if (Health != null)
		{
			Health.UpdateLostHealth();
		}
		if (Prorations != null)
		{
			Prorations.ResetProrations();
		}
	}

	// --- Netsu systems -----------------------------------------------------------------
	// OVERDRIVE (A+B+C, "offensive burst"): spends a FULL Burst gauge. While it runs the
	// Burst gauge drains (see WillGauge.Tick) and the fighter deals more damage and
	// builds Craft Gauge faster. It ends when the gauge is empty or the round ends.
	// While Overdrive runs the Burst gauge's state is WillState.LOCKED (saved for rollback).
	public const int OverdriveDamagePercent = 120;     // deals 120% damage
	public const int OverdriveGaugePercent = 130;      // gains 130% Craft Gauge
	/// <summary>Craft Gauge trickle per frame while walking or dashing forward.</summary>
	public const int ForwardGaugePerFrame = 2;

	/// <summary>Oct 28 (second pass, TamaDeez): OVERDRIVE, the comeback state.
	///  - Starts by itself, once per round, the first frame the fighter is at OverdriveHealthPercent health or lower
	///    and out of hitstun and blockstun (not in a hit / block reaction). Lasts until the round ends.
	///  - On activation: +1 Craft Gauge segment (OverdriveGaugeBonus, capped at the maximum) and one Overdrive Link
	///    (NetsuOverdriveLinkPending, picked up by NetsuAssist: the next assist call gets half its cooldown back
	///    once the assist has left).
	///  - While active: takes OverdriveDamageTakenPercent damage (NetsuOverdriveTaken).
	///  - No damage or meter-gain bonus, no Burst / cancel changes. Character Overdrive extras (Flan) are off
	///    (OverdriveCharacterExtras).
	/// Saved for rollback (ParametersState keys 10, 11). The HUD: portrait flash, brighter Craft Gauge frame, red
	/// health bar, a Link marker by the assist.</summary>
	public const int OverdriveHealthPercent = 30;
	public const int OverdriveGaugeBonus = 10000;   // Oct 29: 1 bar of the new 40,000 gauge (was 2000 of 8000)
	public const int OverdriveDamageTakenPercent = 90;
	public const bool OverdriveCharacterExtras = false;

	/// <summary>Overdrive has started this round (and stays on until the round ends).</summary>
	public bool NetsuOverdriveOn;

	/// <summary>Overdrive's Link, not yet handed to the assist (NetsuAssist takes it).</summary>
	public bool NetsuOverdriveLinkPending;

	public bool InOverdrive()
	{
		return NetsuOverdriveOn;
	}

	/// <summary>Damage this fighter TAKES, after Overdrive's reduction.</summary>
	public int NetsuOverdriveTaken(int damage)
	{
		return NetsuOverdriveOn && damage > 0 ? Mathf.Max(1, damage * OverdriveDamageTakenPercent / 100) : damage;
	}

	private void NetsuCheckOverdrive()
	{
		if (NetsuOverdriveOn || Health == null || _owner == null || _owner.Data == null || _owner.Data.MaxHealth <= 0)
		{
			return;
		}
		if (_owner.GetMaster() != null || _owner.IsKO() || _owner.StateManager == null)
		{
			return;   // fighters only (not projectiles / assists)
		}
		int hp = Health.CurrentValue;
		if (hp < 0 || (long)hp * 100 > (long)_owner.Data.MaxHealth * OverdriveHealthPercent)
		{
			return;
		}
		StateType t = _owner.StateManager.CurrentStateType();
		if (t == StateType.HIT_REACTION || t == StateType.BLOCKING || _owner.OnHitstun())
		{
			return;   // after leaving hitstun and blockstun
		}
		NetsuOverdriveOn = true;
		NetsuOverdriveLinkPending = true;
		if (SuperGauge != null)
		{
			SuperGauge.SetSuperGauge(SuperGauge.CurrentValue + OverdriveGaugeBonus);
		}
	}

	/// <summary>Netsu (Oct 26 evening, after BlazBlue Central Fiction): how long an Overdrive lasts depends on the
	/// fighter's health when it starts: OverdriveFramesFullHealth at full health, up to OverdriveFramesNoHealth near
	/// zero (straight line in between).</summary>
	public const int OverdriveFramesFullHealth = 240;   // 4 seconds
	public const int OverdriveFramesNoHealth = 600;     // 10 seconds

	/// <summary>Starts Overdrive: called when the Overdrive move is used (StanceManager.ExecuteMove).</summary>
	public void StartOverdrive()
	{
		if (Will == null)
		{
			return;
		}
		Will.CurrentValue = Will.MaxValue;   // the move's cost was taken; the full gauge now drains as the timer
		Will.State = WillState.LOCKED;
		int frames = OverdriveFramesFullHealth;
		if (Health != null && _owner != null && _owner.Data != null && _owner.Data.MaxHealth > 0)
		{
			int hp = Mathf.Clamp(Health.CurrentValue, 0, _owner.Data.MaxHealth);
			frames = OverdriveFramesNoHealth - (OverdriveFramesNoHealth - OverdriveFramesFullHealth) * hp / _owner.Data.MaxHealth;
		}
		Will.NetsuDrain = Mathf.Max(1, (Will.MaxValue + frames - 1) / Mathf.Max(1, frames));
	}

	/// <summary>Netsu: frames of Overdrive left (0 when it isn't running). Presentation (the HUD timer).</summary>
	public int OverdriveFramesLeft()
	{
		if (Will == null || Will.State != WillState.LOCKED)
		{
			return 0;   // Oct 28: the old timed Overdrive (never started any more)
		}
		int drain = Mathf.Max(1, Will.NetsuDrain);
		return (Will.CurrentValue + drain - 1) / drain;
	}

	/// <summary>Damage this fighter deals, after its Overdrive bonus (and an assist's buff, e.g. Mary's 5S).
	/// For a projectile or an assist this asks the fighter at the top of its chain (NetsuRoot).</summary>
	public int OverdriveDamage(int damage)
	{
		SakugaParameters p = NetsuRootParameters();
		int d = damage;   // Oct 28: Overdrive no longer adds damage
		if (p._owner != null && p._owner.NetsuAssist != null)
		{
			d = p._owner.NetsuAssist.BuffDamage(d);
		}
		return d;
	}

	private int OverdriveGain(int gain)
	{
		int g = gain;   // Oct 28: Overdrive no longer adds meter gain
		if (_owner != null && _owner.NetsuAssist != null)
		{
			g = _owner.NetsuAssist.BuffGain(g);
		}
		return g;
	}

	/// <summary>Netsu: Craft Gauge this fighter gets, after its Overdrive bonus and assist buff
	/// (used when a projectile or an assist passes its meter up to the fighter).</summary>
	public int NetsuGain(int gain)
	{
		return OverdriveGain(gain);
	}

	private SakugaParameters NetsuRootParameters()
	{
		if (_owner == null)
		{
			return this;
		}
		SakugaActor root = _owner.NetsuRoot();
		return (root != null && root != _owner && root.Parameters != null) ? root.Parameters : this;
	}


	// --- Netsu (Oct 29): BBCF-style Craft Gauge and Burst -------------------------------------------------------
	// CRAFT GAUGE: 0..NetsuMeterMax (40,000). 100 units = 1%, 10,000 = one bar. Carries over between rounds.
	//  Hit:   attacker + normalizedDamage x 2.88, defender + normalizedDamage x 1.60  (once per real hit)
	//  Block: attacker + normalizedBaseDamage x 0.72, defender + normalizedBaseDamage x 0.40
	//         Instant Block: defender + normalizedBaseDamage x 0.80 + 400 instead
	//  normalizedDamage = actualDamage x 10,000 / NetsuReferenceHP (base damage = the hit's damage before scaling).
	//  Order: raw -> global multiplier -> character / move / assist modifiers -> cooldown -> floor ONCE -> clamp.
	//  A meter-spending attack (and its projectiles / follow-ups) gives its attacker 0 (the defender still gains),
	//  unless the move sets MoveSettings.NetsuMeterGainOnSpend.
	//  Spending meter starts a cooldown (NetsuMeterCooldownFrames, 180, or the move's own NetsuMeterCooldown): during it
	//  hit/block gains are x0.25 and the low-health trickle is off. A new spend restarts it.
	//  Low health (below 35%), no cooldown: +4 a frame and +8 more every 10th frame.
	// BURST: 0..10,000, starts the match full, carries over. Needs a full gauge, spends all of it.
	//  Passive: health above 55% -> 1 a frame, above 40% -> 1.5, 40% or less -> 2.
	//  Taking a hit: actualDamage / NetsuReferenceHP x 3,000 (never for block, chip, self-damage or training resets).
	// Every number is an int or decimal: the same on every machine (rollback).

	public const int NetsuMeterMax = 40000;
	public const int NetsuBurstMax = 10000;
	public const int NetsuMeterCooldownFrames = 180;
	public const decimal NetsuMeterGlobalMultiplier = 1.0m;
	public const decimal NetsuMeterAssistMultiplier = 1.0m;
	public const decimal NetsuMeterHitAttacker = 2.88m;
	public const decimal NetsuMeterHitDefender = 1.60m;
	public const decimal NetsuMeterBlockAttacker = 0.72m;
	public const decimal NetsuMeterBlockDefender = 0.40m;
	public const decimal NetsuMeterInstantBlockDefender = 0.80m;
	public const int NetsuMeterInstantBlockBonus = 400;
	public const decimal NetsuMeterCooldownMultiplier = 0.25m;
	public const int NetsuLowHealthPercent = 35;
	public const int NetsuLowHealthPerFrame = 4;
	public const int NetsuLowHealthEvery10th = 8;
	public const int NetsuBurstFromDamage = 3000;
	public const decimal NetsuBurstGainFromDamageMultiplier = 1.0m;

	/// <summary>Frames of meter cooldown left (saved for rollback).</summary>
	public int NetsuMeterCooldown;
	/// <summary>Frames this round, for the low-health trickle's "every 10th frame" (saved for rollback).</summary>
	public int NetsuMeterRoundFrame;
	/// <summary>Half-points of passive Burst not yet added (the 1.5 a frame tier) (saved for rollback).</summary>
	public int NetsuBurstHalf;
	/// <summary>Leftover of the damage-based Burst gain, in units of 1 / NetsuReferenceHP (saved for rollback).</summary>
	public long NetsuBurstDamageRest;

	// debug read-out only (not gameplay, not saved)
	public int NetsuLastMeterAward;
	public string NetsuLastMeterSource = "-";
	public int NetsuLastBurstAward;

	private static int NetsuRefHP => Mathf.Max(1, GlobalVariables.NetsuReferenceHP);

	private bool NetsuIsFighter()
	{
		return _owner != null && _owner.GetMaster() == null && SuperGauge != null;
	}

	/// <summary>Starts (or restarts) the meter cooldown: called whenever Craft Gauge is spent.</summary>
	public void NetsuStartMeterCooldown(int frames = -1)
	{
		NetsuMeterCooldown = frames >= 0 ? frames : NetsuMeterCooldownFrames;
	}

	/// <summary>Spends Craft Gauge (move costs, assist cancels, SetSuperGaugeAction) and starts the cooldown.</summary>
	public void NetsuSpendMeter(int amount, int cooldownFrames = -1)
	{
		if (SuperGauge == null || amount <= 0)
		{
			return;
		}
		SuperGauge.CurrentValue = Mathf.Clamp(SuperGauge.CurrentValue - amount, 0, SuperGauge.MaxValue);
		NetsuStartMeterCooldown(cooldownFrames);
	}

	/// <summary>Adds a gain worked out by the formula: modifiers, cooldown, floor once, clamp.</summary>
	private int NetsuAwardMeter(decimal raw, decimal modifiers, string source)
	{
		if (SuperGauge == null || raw <= 0m)
		{
			return 0;
		}
		decimal g = raw * NetsuMeterGlobalMultiplier * modifiers;
		if (NetsuMeterCooldown > 0)
		{
			g *= NetsuMeterCooldownMultiplier;
		}
		int gain = (int)decimal.Floor(g);
		int before = SuperGauge.CurrentValue;
		SuperGauge.CurrentValue = Mathf.Clamp(before + gain, 0, SuperGauge.MaxValue);
		NetsuLastMeterAward = gain;
		NetsuLastMeterSource = source + (NetsuMeterCooldown > 0 ? " (cooldown x0.25)" : "");
		return gain;
	}

	private decimal NetsuCharacterModifier()
	{
		return _owner != null && _owner.Data != null && _owner.Data.NetsuMeterGainPercent > 0 ? _owner.Data.NetsuMeterGainPercent / 100m : 1m;
	}

	/// <summary>The defender's side of a real hit: Craft Gauge x1.60 and Burst from the damage. `this` = the one hit.</summary>
	public void NetsuDefenderHit(int actualDamage)
	{
		if (!NetsuIsFighter() || actualDamage <= 0)
		{
			return;
		}
		decimal normalized = actualDamage * 10000m / NetsuRefHP;
		NetsuAwardMeter(normalized * NetsuMeterHitDefender, NetsuCharacterModifier(), "hit taken");
		if (Will != null && Will.State == WillState.WORKING && !_owner.IsKO())
		{
			// actualDamage / referenceHP x 3000, with the remainder carried to the next hit
			decimal scaled = (long)actualDamage * NetsuBurstFromDamage * NetsuBurstGainFromDamageMultiplier + NetsuBurstDamageRest;
			long whole = (long)decimal.Floor(scaled / NetsuRefHP);
			NetsuBurstDamageRest = (long)decimal.Floor(scaled - whole * NetsuRefHP);
			NetsuBurstDamageRest = System.Math.Clamp(NetsuBurstDamageRest, 0, NetsuRefHP - 1);
			Will.CurrentValue = Mathf.Clamp(Will.CurrentValue + (int)whole, 0, Will.MaxValue);
			NetsuLastBurstAward = (int)whole;
		}
	}

	/// <summary>The defender's side of a blocked hit: x0.40, or x0.80 + 400 for an Instant Block.</summary>
	public void NetsuDefenderBlock(int baseDamage, bool instantBlock)
	{
		if (!NetsuIsFighter() || baseDamage <= 0)
		{
			return;
		}
		decimal normalized = baseDamage * 10000m / NetsuRefHP;
		if (instantBlock)
		{
			NetsuAwardMeter(normalized * NetsuMeterInstantBlockDefender + NetsuMeterInstantBlockBonus, NetsuCharacterModifier(), "instant block");
		}
		else
		{
			NetsuAwardMeter(normalized * NetsuMeterBlockDefender, NetsuCharacterModifier(), "blocked");
		}
	}

	/// <summary>The attacker's side (`this` = the fighter at the top of the chain). damage: the actual damage for a
	/// hit, the base damage for a block. moveModifier: the move's NetsuMeterGainPercent / 100. assist: the hit
	/// came from the assist (or its projectile).</summary>
	public void NetsuAttackerGain(int damage, bool blocked, decimal moveModifier, bool assist)
	{
		if (!NetsuIsFighter() || damage <= 0)
		{
			return;
		}
		decimal normalized = damage * 10000m / NetsuRefHP;
		decimal raw = normalized * (blocked ? NetsuMeterBlockAttacker : NetsuMeterHitAttacker);
		decimal mods = NetsuCharacterModifier() * moveModifier * (assist ? NetsuMeterAssistMultiplier : 1m);
		NetsuAwardMeter(raw, mods, (assist ? "assist " : "") + (blocked ? "attack blocked" : "attack hit"));
	}

	/// <summary>Records that a meter-spending attack connected (the attacker gets nothing): for the debug read-out.</summary>
	public void NetsuAttackerNoGain(bool blocked)
	{
		NetsuLastMeterAward = 0;
		NetsuLastMeterSource = blocked ? "meter attack blocked (no gain)" : "meter attack hit (no gain)";
	}

	/// <summary>Per-frame gauge work that also runs during hitstop and the EX / super flash (not while paused, between
	/// rounds or after a KO): the meter cooldown, the low-health trickle and the Burst recharge. Fighters only.</summary>
	public void NetsuResourceTick()
	{
		if (!NetsuIsFighter() || GameManager.Instance == null || GameManager.Instance.Monitor == null
			|| GameManager.Instance.Monitor.MatchState != MatchState.ROUND_RUNNING)
		{
			return;
		}
		if (_owner.IsKO())
		{
			return;
		}
		NetsuMeterRoundFrame++;
		bool cooling = NetsuMeterCooldown > 0;
		if (cooling)
		{
			NetsuMeterCooldown--;
		}
		int maxHp = _owner.Data != null ? _owner.Data.MaxHealth : 0;
		int hp = Health != null ? Mathf.Max(0, Health.CurrentValue) : 0;
		if (!cooling && maxHp > 0 && (long)hp * 100 < (long)maxHp * NetsuLowHealthPercent && SuperGauge != null)
		{
			int add = NetsuLowHealthPerFrame + (NetsuMeterRoundFrame % 10 == 0 ? NetsuLowHealthEvery10th : 0);
			SuperGauge.CurrentValue = Mathf.Clamp(SuperGauge.CurrentValue + add, 0, SuperGauge.MaxValue);
		}
		if (Will == null)
		{
			return;
		}
		if (Will.State == WillState.LOCKED)
		{
			Will.Tick();   // the old timed Overdrive's drain (not started any more)
			return;
		}
		if (Will.State == WillState.DISABLED || Will.CurrentValue >= Will.MaxValue)
		{
			NetsuBurstHalf = 0;
			return;
		}
		int halves = NetsuBurstHalvesPerFrame(hp, maxHp) + NetsuBurstHalf;
		NetsuBurstHalf = halves % 2;
		Will.CurrentValue = Mathf.Clamp(Will.CurrentValue + halves / 2, 0, Will.MaxValue);
	}

	/// <summary>Passive Burst recharge in half-points a frame: above 55% health 2 (= 1), above 40% 3 (= 1.5), else 4 (= 2).</summary>
	private static int NetsuBurstHalvesPerFrame(int hp, int maxHp)
	{
		if (maxHp <= 0)
		{
			return 2;
		}
		if ((long)hp * 100 > (long)maxHp * 55)
		{
			return 2;
		}
		if ((long)hp * 100 > (long)maxHp * 40)
		{
			return 3;
		}
		return 4;
	}

	/// <summary>Debug read-out (F-key debug panel): Craft Gauge and Burst.</summary>
	public string NetsuMeterDebug()
	{
		if (SuperGauge == null)
		{
			return "";
		}
		int maxHp = _owner != null && _owner.Data != null ? _owner.Data.MaxHealth : 0;
		int hp = Health != null ? Mathf.Max(0, Health.CurrentValue) : 0;
		bool low = maxHp > 0 && (long)hp * 100 < (long)maxHp * NetsuLowHealthPercent;
		string auto = !low ? "off (health 35%+)" : (NetsuMeterCooldown > 0 ? "off (cooldown)" : "ON (+4/f, +8 every 10th)");
		string text = "\n-- Craft Gauge --"
			+ "\nMeter: " + (SuperGauge.CurrentValue / 100f).ToString("0.00") + "% / " + (SuperGauge.MaxValue / 100) + "%"
			+ "\nLast award: " + (NetsuLastMeterAward / 100f).ToString("0.00") + "% (" + NetsuLastMeterSource + ")"
			+ "\nCooldown: " + NetsuMeterCooldown + "f"
			+ "\nLow-HP auto gain: " + auto;
		if (Will != null)
		{
			int halves = NetsuBurstHalvesPerFrame(hp, maxHp);
			string rate = Will.CurrentValue >= Will.MaxValue ? "full" : (halves / 2f).ToString("0.0") + "/f";
			text += "\n-- Burst --"
				+ "\nBurst: " + (Will.CurrentValue * 100f / Mathf.Max(1, Will.MaxValue)).ToString("0.0") + "%"
				+ "\nRecharge: " + rate
				+ "\nLast damage award: " + (NetsuLastBurstAward / 100f).ToString("0.00") + "%"
				+ "\nAvailable: " + (_owner != null ? _owner.NetsuBurstStatus() : "?");
		}
		return text;
	}

	public void TakeDamage(int damage, int superGaugeGain, bool isKilingBlow)
	{
		if (Health != null)
		{
			if (!isKilingBlow && Health.CurrentValue - damage < 0)
			{
				Health.SetHealth(0);   // Netsu (Oct 27): a non-killing hit leaves you at 0, alive
			}
			else
			{
				Health.RemoveHealth(damage);
			}
		}
		// Oct 29: Craft Gauge and Burst from being hit now come from NetsuMeterOnHit / NetsuMeterOnBlock
		// (the hitbox's OpponentSuperGaugeGain is no longer used)
		ChangeVariablesBehavior(CustomVariableBehaviorTarget.ON_DAMAGE);
	}

	public void HitConfirm(int superGaugeGain)
	{
		// Oct 29: the attacker's Craft Gauge now comes from NetsuMeterOnHit / NetsuMeterOnBlock (SelfSuperGaugeGain unused)
		ChangeVariablesBehavior(CustomVariableBehaviorTarget.ON_HIT);
	}

	public int CalculateProrations(int damage, int attack, int defense, ushort damageScalingLoss, int kind = 0)
	{
		int finalDamage = damage;
		if (Prorations != null)
		{
			finalDamage = Prorations.CalculateCompleteDamage(damage, attack, defense, damageScalingLoss, kind);
		}
		return finalDamage;
	}

	public void ArmorDamage(int damage, int healthDamage)
	{
		SuperArmor.RemoveArmor(damage);
		Health.RemoveHealth(healthDamage);
	}

	public FrameTimer GetTimer(int index)
	{
		return Timers[index];
	}

	public FrameTimer GetTimer(string name)
	{
		for (int i = 0; i < Timers.Length; i++)
		{
			if (Timers[i].Name == (StringName)name)
			{
				return Timers[i];
			}
		}
		return null;
	}

	public CustomVariable GetVariable(int index)
	{
		return Variables[index];
	}

	public CustomVariable GetVariable(string name)
	{
		for (int i = 0; i < Variables.Length; i++)
		{
			if (Variables[i].Name == (StringName)name)
			{
				return Variables[i];
			}
		}
		return null;
	}

	public void UpdateTimers()
	{
		if (!HasTimers())
		{
			return;
		}
		for (int t = 0; t < Timers.Length; t++)
		{
			FrameTimer timer = Timers[t];
			if (!timer.Manual)
			{
				timer.Run();
			}
		}
	}

	public void UpdateVariables()
	{
		if (!HasVariables())
		{
			return;
		}
		for (int v = 0; v < Variables.Length; v++)
		{
			switch (Variables[v].CurrentMode)
			{
			case CustomVariableMode.INCREASE:
				Variables[v].Add(Variables[v].CurrentFactor);
				break;
			case CustomVariableMode.DECREASE:
				Variables[v].Subtract(Variables[v].CurrentFactor);
				break;
			}
		}
	}

	public void UpdateProrations()
	{
		if (Prorations != null)
		{
			Prorations.UpdateDamageScaling(_owner.Body != null && _owner.Body.IsOnWall);
		}
	}

	public void ChangeVariablesBehavior(CustomVariableBehaviorTarget CompareTarget)
	{
		if (HasVariables())
		{
			for (int v = 0; v < Variables.Length; v++)
			{
				Variables[v].ChangeBehavior(CompareTarget);
			}
		}
	}

	public void SetVariables(CustomVariableChange[] ChangeConditions)
	{
		if (ChangeConditions == null || ChangeConditions.Length == 0)
		{
			return;
		}
		foreach (CustomVariableChange condition in ChangeConditions)
		{
			CustomVariable variable = null;
			if (condition.ByIndex >= 0)
			{
				variable = GetVariable(condition.ByIndex);
			}
			else if (condition.ByName == "")
			{
				variable = GetVariable(condition.ByName);
			}
			if (variable == null)
			{
				break;
			}
			variable.ChangeVariable(condition);
		}
	}

	public bool CompareVariables(CustomVariableCondition[] CompareConditions)
	{
		if (CompareConditions == null || CompareConditions.Length == 0)
		{
			return true;
		}
		foreach (CustomVariableCondition condition in CompareConditions)
		{
			CustomVariable variable = null;
			if (condition.ByIndex >= 0)
			{
				variable = GetVariable(condition.ByIndex);
			}
			else if (condition.ByName == "")
			{
				variable = GetVariable(condition.ByName);
			}
			if (!variable.CompareVariable(condition))
			{
				return false;
			}
		}
		return true;
	}

	public void PlaySound(int soundChannel, AudioStream sound)
	{
		if (HasSounds())
		{
			SoundSources[soundChannel].QueueSound(sound);
		}
	}

	public bool HasTimers()
	{
		if (Timers != null)
		{
			return Timers.Length != 0;
		}
		return false;
	}

	public bool HasVariables()
	{
		if (Variables != null)
		{
			return Variables.Length != 0;
		}
		return false;
	}

	public bool HasSounds()
	{
		if (SoundSources != null)
		{
			return SoundSources.Length != 0;
		}
		return false;
	}
}
