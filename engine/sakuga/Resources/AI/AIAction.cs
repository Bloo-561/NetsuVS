using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class AIAction : Resource
{
	[Export(PropertyHint.None, "")]
	private string InputName;

	[Export(PropertyHint.None, "")]
	public AIInput[] Inputs;

	/// <summary>Go straight on to the next action once the inputs are done
	/// (movement: jumps, dashes). Attacks leave this off: the CPU then waits for
	/// the attack to connect before inputting the next part of the combo.</summary>
	[Export(PropertyHint.None, "")]
	public bool AutoAdvance;

	/// <summary>Frames to wait before starting this action's inputs (e.g. a jump-in
	/// attack that should come out on the way down, or a rekka follow-up).</summary>
	[Export(PropertyHint.None, "")]
	public int StartDelay;
}
