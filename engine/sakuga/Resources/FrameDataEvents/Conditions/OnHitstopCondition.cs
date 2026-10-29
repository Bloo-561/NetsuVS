using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class OnHitstopCondition : FrameDataCondition
{
	[Export(PropertyHint.None, "")]
	private bool Not;

	public override bool Check(ref SakugaActor Actor)
	{
		if (!Actor.CanHitstop())
		{
			return false;
		}
		if (Not)
		{
			return !Actor.OnHitstop();
		}
		return Actor.OnHitstop();
	}
}
