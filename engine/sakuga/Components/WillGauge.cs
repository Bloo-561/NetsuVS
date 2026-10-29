using Godot;
using SakugaEngine.Global;
using SakugaEngine.Resources;

namespace MahouSensou.Custom;

[GlobalClass]
public partial class WillGauge : Node
{
	[Export(PropertyHint.None, "")]
	private bool UseDataContainer;

	[Export(PropertyHint.None, "")]
	public int MaxValue;

	public WillState State;

	public int CurrentValue;

	public void Initialize(DataContainer data)
	{
		if (UseDataContainer)
		{
			MaxValue = data.MaxWill;
		}
		State = WillState.WORKING;
		CurrentValue = MaxValue;   // Netsu: Brave Burst gauge starts the match full
	}

	/// <summary>Overdrive drains this many points per frame (6000 / 12 = 500 frames, about 8 seconds).</summary>
	public const int OverdriveDrainPerFrame = 12;

	/// <summary>Netsu (Oct 26 evening): this Overdrive's drain per frame, set when it starts from the fighter's health
	/// (SakugaParameters.StartOverdrive: the lower the health, the longer it lasts). Saved for rollback
	/// (ParametersState key 9).</summary>
	public int NetsuDrain = OverdriveDrainPerFrame;

	/// <summary>The Burst gauge refills slowly over time (1 point per frame while the round runs).
	/// During Overdrive (State LOCKED) it drains instead, and Overdrive ends when it is empty.</summary>
	public void Tick()
	{
		if (State == WillState.LOCKED)
		{
			CurrentValue -= Mathf.Max(1, NetsuDrain);
			if (CurrentValue <= 0)
			{
				CurrentValue = 0;
				State = WillState.WORKING;
			}
			return;
		}
		if (State != WillState.DISABLED && CurrentValue < MaxValue)
		{
			CurrentValue++;
		}
	}

	public void SetWillGauge(int value)
	{
		if (State != WillState.DISABLED)
		{
			CurrentValue = value;
			CurrentValue = Mathf.Clamp(CurrentValue, 0, MaxValue);
		}
	}

	public void AddWillGauge(int value)
	{
		if (State == WillState.WORKING)
		{
			CurrentValue += value;
			CurrentValue = Mathf.Clamp(CurrentValue, 0, MaxValue);
		}
	}

	public void SpendWillGauge(int value)
	{
		if (State != WillState.DISABLED)
		{
			CurrentValue -= value;
			CurrentValue = Mathf.Clamp(CurrentValue, 0, MaxValue);
		}
	}
}
