using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class StateTransitionSettings : Resource
{
	[Export(PropertyHint.None, "")]
	public int StateIndex = -1;

	[Export(PropertyHint.None, "")]
	public TransitionCondition Condition;

	[Export(PropertyHint.None, "")]
	public int AtFrame = -1;

	[Export(PropertyHint.None, "")]
	public MotionInputs Inputs;

	[Export(PropertyHint.None, "")]
	public Vector2I DistanceArea = new Vector2I(0, 999999);
}
