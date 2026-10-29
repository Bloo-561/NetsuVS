using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class CheckCustomVariableCondition : FrameDataCondition
{
	[Export(PropertyHint.None, "")]
	private int ByIndex;

	[Export(PropertyHint.None, "")]
	private string ByName;

	[Export(PropertyHint.None, "")]
	private int Value;

	[Export(PropertyHint.None, "")]
	public CustomVariableMode Mode;

	[Export(PropertyHint.None, "")]
	public CompareMode CompareMode;

	public override bool Check(ref SakugaActor Actor)
	{
		if (Actor.Parameters == null)
		{
			return false;
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
		if (variable == null)
		{
			return false;
		}
		bool num = variable.CompareValue(Value, CompareMode);
		bool compareMode = variable.CurrentMode == Mode;
		return num & compareMode;
	}
}
