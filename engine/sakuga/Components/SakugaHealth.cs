using Godot;
using SakugaEngine.Resources;

namespace SakugaEngine;

[GlobalClass]
public partial class SakugaHealth : Node
{
	[Export(PropertyHint.None, "")]
	private bool UseDataContainer;

	[Export(PropertyHint.None, "")]
	public int MaxValue;

	public int CurrentValue;

	// Netsu (Oct 27): 0 HP is still alive; the floor is -1 and IsKO() is "below zero"
	public const int NetsuMinValue = -1;

	public int LostValue;

	public int RecoverableValue;

	public void Initialize(DataContainer data)
	{
		if (UseDataContainer)
		{
			MaxValue = data.MaxHealth;
		}
		CurrentValue = MaxValue;
		LostValue = CurrentValue;
	}

	public void Tick()
	{
		UpdateLostHealth();
	}

	public void SetHealth(int value)
	{
		CurrentValue = value;
		CurrentValue = Mathf.Clamp(CurrentValue, NetsuMinValue, MaxValue);
		if (CurrentValue <= 0 || CurrentValue == MaxValue)
		{
			LostValue = Mathf.Max(0, CurrentValue);
		}
	}

	public void AddHealth(int value)
	{
		CurrentValue += value;
		CurrentValue = Mathf.Clamp(CurrentValue, NetsuMinValue, MaxValue);
		if (CurrentValue <= 0 || CurrentValue == MaxValue)
		{
			LostValue = Mathf.Max(0, CurrentValue);
		}
	}

	public void RemoveHealth(int value)
	{
		CurrentValue -= value;
		CurrentValue = Mathf.Clamp(CurrentValue, NetsuMinValue, MaxValue);
		if (CurrentValue <= 0 || CurrentValue == MaxValue)
		{
			LostValue = Mathf.Max(0, CurrentValue);
		}
	}

	public void UpdateLostHealth()
	{
		if (LostValue > CurrentValue)
		{
			LostValue -= MaxValue / 100;
		}
		else if (LostValue < CurrentValue)
		{
			LostValue = CurrentValue;
		}
	}
}
