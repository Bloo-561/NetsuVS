using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class CheckYVelocityCondition : FrameDataCondition
{
	[Export(PropertyHint.None, "")]
	private bool Absolute;

	[Export(PropertyHint.None, "")]
	private int Value;

	[Export(PropertyHint.None, "")]
	private CompareMode CompareMode;

	public override bool Check(ref SakugaActor Actor)
	{
		if (Actor.Body == null)
		{
			return false;
		}
		int vel = (Absolute ? Mathf.Abs(Actor.Body.FixedVelocity.Y) : Actor.Body.FixedVelocity.Y);
		return CompareMode switch
		{
			CompareMode.EQUAL => vel == Value, 
			CompareMode.DIFFERENT => vel != Value, 
			CompareMode.GREATER => vel > Value, 
			CompareMode.GREATER_EQUAL => vel >= Value, 
			CompareMode.LESS => vel < Value, 
			CompareMode.LESS_EQUAL => vel <= Value, 
			_ => false, 
		};
	}
}
