using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class MoveXAction : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	private int Velocity;

	[Export(PropertyHint.None, "")]
	public bool UseInertia;

	[Export(PropertyHint.None, "")]
	public bool UseInput;

	public override void Execute(ref SakugaActor Actor)
	{
		if (Actor.Body == null || Actor.OnKnockback())
		{
			return;
		}
		if (UseInput && Actor.Inputs != null)
		{
			int InputSide = 0;
			if (Actor.Inputs.IsBeingPressed(Actor.Inputs.CurrentHistory, PlayerInputs.RIGHT))
			{
				InputSide = 1;
			}
			else if (Actor.Inputs.IsBeingPressed(Actor.Inputs.CurrentHistory, PlayerInputs.LEFT))
			{
				InputSide = -1;
			}
			if (UseInertia)
			{
				Actor.Body.AddLateralAcceleration(Velocity * InputSide);
			}
			else
			{
				Actor.Body.SetLateralVelocity(Velocity * InputSide);
			}
		}
		else if (UseInertia)
		{
			Actor.Body.AddLateralAcceleration(Velocity * Actor.InputSide());
		}
		else
		{
			Actor.Body.SetLateralVelocity(Velocity * Actor.InputSide());
		}
	}
}
