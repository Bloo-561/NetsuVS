using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class SetActiveAction : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	private bool Active;

	public override void Execute(ref SakugaActor Actor)
	{
		Actor.IsActive = Active;
	}
}
