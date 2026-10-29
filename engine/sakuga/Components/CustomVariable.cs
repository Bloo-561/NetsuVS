using System.IO;
using Godot;
using SakugaEngine.Global;
using SakugaEngine.Resources;

namespace SakugaEngine;

[GlobalClass]
public partial class CustomVariable : Node
{
	[Export(PropertyHint.None, "")]
	public bool Reset;

	[Export(PropertyHint.None, "")]
	private int MaxValue;

	[Export(PropertyHint.None, "")]
	private int StartingValue;

	[Export(PropertyHint.None, "")]
	private int StartingFactor;

	[Export(PropertyHint.None, "")]
	private CustomVariableMode StartingMode;

	[Export(PropertyHint.None, "")]
	private CustomVariableBehavior[] Behaviors;

	public int CurrentValue;

	public int CurrentFactor;

	public CustomVariableMode CurrentMode;

	public void Initialize()
	{
		CurrentValue = StartingValue;
		CurrentFactor = StartingFactor;
		CurrentMode = StartingMode;
	}

	public void Add(int value)
	{
		CurrentValue += value;
		if (CurrentValue >= MaxValue)
		{
			ChangeBehavior(CustomVariableBehaviorTarget.ON_FULL);
		}
		CurrentValue = Mathf.Clamp(CurrentValue, 0, MaxValue);
	}

	public void Subtract(int value)
	{
		CurrentValue -= value;
		if (CurrentValue <= 0)
		{
			ChangeBehavior(CustomVariableBehaviorTarget.ON_EMPTY);
		}
		CurrentValue = Mathf.Clamp(CurrentValue, 0, MaxValue);
	}

	public void Set(int value)
	{
		CurrentValue = value;
		if (CurrentValue >= MaxValue)
		{
			ChangeBehavior(CustomVariableBehaviorTarget.ON_FULL);
		}
		else if (CurrentValue <= 0)
		{
			ChangeBehavior(CustomVariableBehaviorTarget.ON_EMPTY);
		}
		CurrentValue = Mathf.Clamp(CurrentValue, 0, MaxValue);
	}

	public bool CompareValue(int CompareTo, CompareMode mode)
	{
		return mode switch
		{
			CompareMode.EQUAL => CurrentValue == CompareTo, 
			CompareMode.DIFFERENT => CurrentValue != CompareTo, 
			CompareMode.GREATER => CurrentValue > CompareTo, 
			CompareMode.GREATER_EQUAL => CurrentValue >= CompareTo, 
			CompareMode.LESS => CurrentValue < CompareTo, 
			CompareMode.LESS_EQUAL => CurrentValue <= CompareTo, 
			_ => false, 
		};
	}

	public void ChangeBehavior(CustomVariableBehaviorTarget CompareTarget)
	{
		if (Behaviors == null || Behaviors.Length == 0)
		{
			return;
		}
		CustomVariableBehavior[] behaviors = Behaviors;
		foreach (CustomVariableBehavior behavior in behaviors)
		{
			if (behavior.Target == CompareTarget)
			{
				SetVariable(behavior);
				break;
			}
		}
	}

	private void SetVariable(CustomVariableBehavior behavior)
	{
		if (behavior.SetValue)
		{
			if (behavior.IsRandom)
			{
				CurrentValue = RNG.Next(behavior.Value, behavior.Range);
			}
			else
			{
				CurrentValue = behavior.Value;
			}
		}
		CurrentFactor = behavior.Factor;
		CurrentMode = behavior.Mode;
	}

	public bool CompareVariable(CustomVariableCondition CompareTo)
	{
		if (CompareTo == null)
		{
			return false;
		}
		if (CompareTo.Value < 0)
		{
			return false;
		}
		if (CurrentMode != CompareTo.Mode)
		{
			return false;
		}
		if (!CompareValue(CompareTo.Value, CompareTo.CompareMode))
		{
			return false;
		}
		return true;
	}

	public void ChangeVariable(CustomVariableChange ToChange)
	{
		if (ToChange != null)
		{
			int val = ToChange.Value;
			if (ToChange.IsRandom)
			{
				val = RNG.Next(ToChange.Value, ToChange.Range);
			}
			switch ((byte)ToChange.Mode)
			{
			case 0:
				Set(val);
				break;
			case 1:
				Add(val);
				break;
			case 2:
				Subtract(val);
				break;
			}
		}
	}

	public void Serialize(BinaryWriter bw)
	{
		bw.Write(CurrentValue);
		bw.Write(CurrentFactor);
		bw.Write((byte)CurrentMode);
	}

	public void Deserialize(BinaryReader br)
	{
		CurrentValue = br.ReadInt32();
		CurrentFactor = br.ReadInt32();
		CurrentMode = (CustomVariableMode)br.ReadByte();
	}
}
