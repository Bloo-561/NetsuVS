using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class InputOption : Resource
{
	[Export(PropertyHint.None, "")]
	public InputSequence[] Inputs;
}
