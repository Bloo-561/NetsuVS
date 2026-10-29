using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class ButtonChargeSequence : Resource
{
	[Export(PropertyHint.None, "")]
	public Vector2I Threshold;

	[Export(PropertyHint.None, "")]
	public int SequenceMove;
}
