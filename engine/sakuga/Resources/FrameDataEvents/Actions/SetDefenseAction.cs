using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class SetDefenseAction : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	private bool Reset;

	[Export(PropertyHint.None, "")]
	private int Value;

	public override void Execute(ref SakugaActor Actor)
	{
		if (Actor.Parameters != null && Actor.Parameters.Prorations != null)
		{
			if (Reset)
			{
				Actor.Parameters.Prorations.CurrentDefense = Actor.Parameters.Prorations.BaseDefense;
			}
			else
			{
				Actor.Parameters.Prorations.CurrentDefense = (ushort)Value;
			}
		}
	}
}
