using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class AddGravityAction : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	private bool SetValue;

	[Export(PropertyHint.None, "")]
	private bool UseDefault;

	[Export(PropertyHint.None, "")]
	private int Force;

	public override void Execute(ref SakugaActor Actor)
	{
		if (Actor.Body != null)
		{
			if (SetValue)
			{
				Actor.Body.CurrentGravity = (UseDefault ? 260000 : Force);
			}
			Actor.Body.AddGravity();
		}
	}
}
