using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class FighterOutro : Resource
{
	[Export(PropertyHint.None, "")]
	public int StateIndex;

	[Export(PropertyHint.None, "")]
	public string ForOpponent = "";

	[Export(PropertyHint.MultilineText, "")]
	public string FinalMessage;
}
