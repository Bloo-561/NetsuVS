using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class CustomVariableBehavior : Resource
{
	[Export(PropertyHint.None, "")]
	public CustomVariableBehaviorTarget Target;

	[Export(PropertyHint.None, "")]
	public bool SetValue;

	[Export(PropertyHint.None, "")]
	public int Factor;

	[Export(PropertyHint.None, "")]
	public int Value;

	[Export(PropertyHint.None, "")]
	public bool IsRandom;

	[Export(PropertyHint.None, "")]
	public int Range;

	[Export(PropertyHint.None, "")]
	public CustomVariableMode Mode;
}
