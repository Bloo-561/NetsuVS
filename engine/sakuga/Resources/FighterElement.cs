using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class FighterElement : Resource
{
	[Export(PropertyHint.None, "")]
	public FighterProfile Profile;

	[Export(PropertyHint.None, "")]
	public ColorPaletteElement[] ColorPalettes;
}
