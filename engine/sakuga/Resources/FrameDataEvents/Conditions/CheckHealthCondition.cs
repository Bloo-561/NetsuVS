using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class CheckHealthCondition : FrameDataCondition
{
	[Export(PropertyHint.None, "")]
	private int Value;

	[Export(PropertyHint.None, "")]
	private CompareMode CompareMode;

	public override bool Check(ref SakugaActor Actor)
	{
		if (Actor.Parameters == null)
		{
			return false;
		}
		if (Actor.Parameters.Health == null)
		{
			return false;
		}
		return CompareMode switch
		{
			CompareMode.EQUAL => Actor.Parameters.Health.CurrentValue == Value, 
			CompareMode.DIFFERENT => Actor.Parameters.Health.CurrentValue != Value, 
			CompareMode.GREATER => Actor.Parameters.Health.CurrentValue > Value, 
			CompareMode.GREATER_EQUAL => Actor.Parameters.Health.CurrentValue >= Value, 
			CompareMode.LESS => Actor.Parameters.Health.CurrentValue < Value, 
			CompareMode.LESS_EQUAL => Actor.Parameters.Health.CurrentValue <= Value, 
			_ => false, 
		};
	}
}
