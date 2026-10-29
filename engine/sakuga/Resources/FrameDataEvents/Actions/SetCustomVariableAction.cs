using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class SetCustomVariableAction : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	private int ByIndex;

	[Export(PropertyHint.None, "")]
	private string ByName;

	[Export(PropertyHint.None, "")]
	public CustomVariableMode ChangeMode;

	[Export(PropertyHint.None, "")]
	private int NewValue;

	[Export(PropertyHint.None, "")]
	private bool IsRandom;

	[Export(PropertyHint.None, "")]
	private int RandomRange;

	public override void Execute(ref SakugaActor Actor)
	{
		if (Actor.Parameters == null)
		{
			return;
		}
		CustomVariable variable = null;
		if (ByIndex >= 0)
		{
			variable = Actor.Parameters.GetVariable(ByIndex);
		}
		else if (ByName != "")
		{
			variable = Actor.Parameters.GetVariable(ByName);
		}
		if (variable != null)
		{
			int finalValue = (IsRandom ? RNG.Next(NewValue, RandomRange) : NewValue);
			switch (ChangeMode)
			{
			case CustomVariableMode.IDLE:
				variable.Set(finalValue);
				break;
			case CustomVariableMode.INCREASE:
				variable.Add(finalValue);
				break;
			case CustomVariableMode.DECREASE:
				variable.Subtract(finalValue);
				break;
			}
		}
	}
}
