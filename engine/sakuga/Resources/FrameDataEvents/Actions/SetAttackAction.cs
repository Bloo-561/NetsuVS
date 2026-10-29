using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class SetAttackAction : FrameDataAction
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
				Actor.Parameters.Prorations.CurrentAttack = Actor.Parameters.Prorations.BaseAttack;
			}
			else
			{
				Actor.Parameters.Prorations.CurrentAttack = (ushort)Value;
			}
		}
	}
}
