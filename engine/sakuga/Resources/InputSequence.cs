using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class InputSequence : Resource
{
	[ExportSubgroup("Directional Inputs", "")]
	[Export(PropertyHint.None, "")]
	public DirectionalInputs Directional;

	[Export(PropertyHint.None, "")]
	public ButtonMode DirectionalMode;

	[ExportSubgroup("Face Button Inputs", "")]
	[Export(PropertyHint.None, "")]
	public ButtonInputs Buttons;

	[Export(PropertyHint.None, "")]
	public ButtonMode ButtonMode;
}
