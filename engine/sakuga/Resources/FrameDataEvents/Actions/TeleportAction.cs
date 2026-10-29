using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class TeleportAction : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	private int Index;

	[Export(PropertyHint.None, "")]
	private Vector2I TargetPosition = Vector2I.Zero;

	[Export(PropertyHint.None, "")]
	private RelativeTo xRelativeTo;

	[Export(PropertyHint.None, "")]
	private RelativeTo yRelativeTo;

	public override void Execute(ref SakugaActor Actor)
	{
		if (Actor.Body != null)
		{
			Actor.Body.MoveTo(Actor.GenerateTargetPosition(TargetPosition, Index, xRelativeTo, yRelativeTo));
		}
	}
}
