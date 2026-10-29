using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class MotionInputs : Resource
{
	[Export(PropertyHint.None, "")]
	public InputOption[] ValidInputs;

	[Export(PropertyHint.None, "")]
	public bool AbsoluteDirection;

	[Export(PropertyHint.None, "")]
	public int InputBuffer = 8;

	[Export(PropertyHint.None, "")]
	public int DirectionalChargeLimit;

	[Export(PropertyHint.None, "")]
	public int ButtonChargeLimit;
}
