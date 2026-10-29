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
				if (_owner != null && _owner.Body != null && _owner.StateManager != null
					&& _owner.StateManager.CurrentStateType() == StateType.MOVEMENT
					&& _owner.Body.FixedVelocity.X * _owner.Body.PlayerSide > 0)
				{
					SuperGauge.AddSuperGauge(OverdriveGain(ForwardGaugePerFrame));
				}
			}
			if (Will != null)
			{
				Will.Tick();
			}
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
	public const int OverdriveGaugeBonus = 2000;
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
		if (SuperGauge != null)
		{
			SuperGauge.AddSuperGauge(OverdriveGain(superGaugeGain));
		}
		if (Will != null)
		{
			Will.AddWillGauge(damage);   // the Burst gauge refills as you take damage (not during Overdrive)
		}
		ChangeVariablesBehavior(CustomVariableBehaviorTarget.ON_DAMAGE);
	}

	public void HitConfirm(int superGaugeGain)
	{
		if (SuperGauge != null)
		{
			SuperGauge.AddSuperGauge(OverdriveGain(superGaugeGain));
		}
		ChangeVariablesBehavior(CustomVariableBehaviorTarget.ON_HIT);
	}

	public int CalculateProrations(int damage, int attack, int defense, ushort damageScalingLoss)
	{
		int finalDamage = damage;
		if (Prorations != null)
		{
			finalDamage = Prorations.CalculateCompleteDamage(damage, attack, defense, damageScalingLoss);
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
