using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class CheckInputCondition : FrameDataCondition
{
	[Export(PropertyHint.None, "")]
	private InputSideCheck SideCheck = InputSideCheck.CHARACTER_RELATIVE;

	[Export(PropertyHint.None, "")]
	private MotionInputs Input;

	[Export(PropertyHint.None, "")]
	private bool Not;

	public override bool Check(ref SakugaActor Actor)
	{
		if (Actor.Inputs == null)
		{
			return false;
		}
		if (Not)
		{
			return !Actor.Inputs.CheckMotionInputs(Input, Actor.InputSide(SideCheck));
		}
		return Actor.Inputs.CheckMotionInputs(Input, Actor.InputSide(SideCheck));
	}
}
