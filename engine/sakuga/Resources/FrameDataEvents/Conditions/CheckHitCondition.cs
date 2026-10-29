using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class CheckHitCondition : FrameDataCondition
{
	[Export(PropertyHint.None, "")]
	private CancelCondition HitCheck;

	[Export(PropertyHint.None, "")]
	private bool Not;

	public override bool Check(ref SakugaActor Actor)
	{
		if (Not)
		{
			return (Actor.CancelConditions & HitCheck) == 0;
		}
		return (Actor.CancelConditions & HitCheck) != 0;
	}
}
