using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class FighterList : Resource
{
	[Export(PropertyHint.None, "")]
	public FighterElement[] elements;
}
