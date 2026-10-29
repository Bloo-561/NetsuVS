using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class AIInput : Resource
{
	[ExportSubgroup("Directional Inputs", "")]
	[Export(PropertyHint.None, "")]
	public DirectionalInputs Direction;

	[ExportSubgroup("Face Button Inputs", "")]
	[Export(PropertyHint.None, "")]
	public ButtonInputs Buttons;
}
