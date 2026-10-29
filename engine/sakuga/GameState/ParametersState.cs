using MessagePack;
using MahouSensou.Custom;
using SakugaEngine.Global;

namespace SakugaEngine.GameState;

[MessagePackObject(false)]
public struct ParametersState
{
	[Key(0)]
	public int CurrentHealth;

	[Key(1)]
	public int LostHealth;

	[Key(2)]
	public int RecoveryHealth;

	[Key(3)]
	public int CurrentSuperGauge;

	[Key(4)]
	public int CurrentWill;

	[Key(5)]
	public WillState CurrentWillState;

	[Key(6)]
	public int CurrentSuperArmor;

	[Key(7)]
	public ProrationsState Prorations;

	[Key(8)]
	public CombatTrackerState CombatTracker;

	[Key(9)]
	public int NetsuOverdriveDrain;   // Netsu (Oct 26 evening): this Overdrive's drain per frame (WillGauge.NetsuDrain)

	[Key(10)]
	public bool NetsuOverdriveOn;   // Netsu (Oct 28): Overdrive started this round

	[Key(11)]
	public bool NetsuOverdriveLinkPending;

	[Key(12)]
	public int NetsuMeterCooldown;   // Netsu (Oct 29): BBCF-style meter

	[Key(13)]
	public int NetsuMeterRoundFrame;

	[Key(14)]
	public int NetsuBurstHalf;

	[Key(15)]
	public long NetsuBurstDamageRest;

	[Key(50)]
	public FrameTimerState[] Timers;

	[Key(51)]
	public CustomVariableState[] Variables;

	public void GetStateData(ref SakugaParameters reference)
	{
		if (reference != null)
		{
			if (reference.Health != null)
			{
				CurrentHealth = reference.Health.CurrentValue;
				LostHealth = reference.Health.LostValue;
				RecoveryHealth = reference.Health.RecoverableValue;
			}
			if (reference.SuperGauge != null)
			{
				CurrentSuperGauge = reference.SuperGauge.CurrentValue;
			}
			if (reference.SuperArmor != null)
			{
				CurrentSuperArmor = reference.SuperArmor.CurrentValue;
			}
			if (reference.Will != null)
			{
				CurrentWill = reference.Will.CurrentValue;
			}
			if (reference.Will != null)
			{
				CurrentWillState = reference.Will.State;
				NetsuOverdriveDrain = reference.Will.NetsuDrain;
			}
			{
				NetsuOverdriveOn = reference.NetsuOverdriveOn;
				NetsuOverdriveLinkPending = reference.NetsuOverdriveLinkPending;
				NetsuMeterCooldown = reference.NetsuMeterCooldown;
				NetsuMeterRoundFrame = reference.NetsuMeterRoundFrame;
				NetsuBurstHalf = reference.NetsuBurstHalf;
				NetsuBurstDamageRest = reference.NetsuBurstDamageRest;
			}
			if (reference.Prorations != null)
			{
				Prorations.GetStateData(ref reference.Prorations);
			}
			if (reference.Tracker != null)
			{
				CombatTracker.GetStateData(ref reference.Tracker);
			}
			Timers = new FrameTimerState[reference.Timers.Length];
			for (int t = 0; t < reference.Timers.Length; t++)
			{
				Timers[t].GetStateData(ref reference.Timers[t]);
			}
			Variables = new CustomVariableState[reference.Variables.Length];
			for (int i = 0; i < reference.Variables.Length; i++)
			{
				Variables[i].GetStateData(ref reference.Variables[i]);
			}
		}
	}

	public void SetStateData(ref SakugaParameters reference)
	{
		if (reference != null)
		{
			if (reference.Health != null)
			{
				reference.Health.CurrentValue = CurrentHealth;
				reference.Health.LostValue = LostHealth;
				reference.Health.RecoverableValue = RecoveryHealth;
			}
			if (reference.SuperGauge != null)
			{
				reference.SuperGauge.CurrentValue = CurrentSuperGauge;
			}
			if (reference.SuperArmor != null)
			{
				reference.SuperArmor.CurrentValue = CurrentSuperArmor;
			}
			if (reference.Will != null)
			{
				reference.Will.CurrentValue = CurrentWill;
			}
			if (reference.Will != null)
			{
				reference.Will.State = CurrentWillState;
				reference.Will.NetsuDrain = NetsuOverdriveDrain > 0 ? NetsuOverdriveDrain : WillGauge.OverdriveDrainPerFrame;
			}
			{
				reference.NetsuOverdriveOn = NetsuOverdriveOn;
				reference.NetsuOverdriveLinkPending = NetsuOverdriveLinkPending;
				reference.NetsuMeterCooldown = NetsuMeterCooldown;
				reference.NetsuMeterRoundFrame = NetsuMeterRoundFrame;
				reference.NetsuBurstHalf = NetsuBurstHalf;
				reference.NetsuBurstDamageRest = NetsuBurstDamageRest;
			}
			if (reference.Prorations != null)
			{
				Prorations.SetStateData(ref reference.Prorations);
			}
			if (reference.Tracker != null)
			{
				CombatTracker.SetStateData(ref reference.Tracker);
			}
			for (int t = 0; t < reference.Timers.Length; t++)
			{
				Timers[t].SetStateData(ref reference.Timers[t]);
			}
			for (int i = 0; i < reference.Variables.Length; i++)
			{
				Variables[i].SetStateData(ref reference.Variables[i]);
			}
		}
	}
}
