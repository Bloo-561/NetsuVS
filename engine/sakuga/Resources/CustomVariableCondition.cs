using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class CustomVariableCondition : Resource
{
	[Export(PropertyHint.None, "")]
	public int ByIndex;

	[Export(PropertyHint.None, "")]
	public string ByName = "";

	[Export(PropertyHint.None, "")]
	public CustomVariableMode Mode;

	[Export(PropertyHint.None, "")]
	public int Value;

	[Export(PropertyHint.None, "")]
	public CompareMode CompareMode;
}
