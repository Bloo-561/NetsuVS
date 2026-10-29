using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class FighterIntro : Resource
{
	[Export(PropertyHint.None, "")]
	public int StateIndex;

	[Export(PropertyHint.None, "")]
	public string ForOpponent = "";
}
