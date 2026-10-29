using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class SetKnockoutStateAction : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	private bool Not;

	public override void Execute(ref SakugaActor Actor)
	{
		SakugaEngine.Global.NetsuLog.Debug("Should be dead for good...");
	}
}
