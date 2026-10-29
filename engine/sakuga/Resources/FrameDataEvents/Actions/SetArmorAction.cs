using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class SetArmorAction : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	private int Value;

	public override void Execute(ref SakugaActor Actor)
	{
		if (Value != 0 && Actor.Parameters != null && Actor.Parameters.SuperArmor != null)
		{
			Actor.Parameters.SuperArmor.SetArmor(Value);
		}
	}
}
