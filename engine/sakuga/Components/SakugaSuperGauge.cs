using Godot;
using SakugaEngine.Resources;

namespace SakugaEngine;

[GlobalClass]
public partial class SakugaSuperGauge : Node
{
	[Export(PropertyHint.None, "")]
	private bool UseDataContainer;

	[Export(PropertyHint.None, "")]
	private bool StartFull;

	[Export(PropertyHint.None, "")]
	private bool CanReset = true;

	[Export(PropertyHint.None, "")]
	public int MaxValue;

	[Export(PropertyHint.None, "")]
	public int AutoFill;

	public int CurrentValue;

	public void Initialize(DataContainer data)
	{
		if (UseDataContainer)
		{
			MaxValue = data.MaxSuperGauge;
			AutoFill = data.SuperGaugeChargeRate;
		}
		CurrentValue = (StartFull ? MaxValue : 0);
	}

	public void Reset()
	{
		if (CanReset)
		{
			CurrentValue = (StartFull ? MaxValue : 0);
		}
	}

	public void Tick()
	{
		if (AutoFill != 0)
		{
			CurrentValue += AutoFill;
		}
		if (CurrentValue > MaxValue)
		{
			CurrentValue = MaxValue;
		}
	}

	public void SetSuperGauge(int value)
	{
		CurrentValue = value;
		CurrentValue = Mathf.Clamp(CurrentValue, 0, MaxValue);
	}

	public void AddSuperGauge(int value)
	{
		CurrentValue += value;
		CurrentValue = Mathf.Clamp(CurrentValue, 0, MaxValue);
	}

	public void SpendSuperGauge(int value)
	{
		CurrentValue -= value;
		CurrentValue = Mathf.Clamp(CurrentValue, 0, MaxValue);
	}
}
