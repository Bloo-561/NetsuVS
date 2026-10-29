using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class BGMList : Resource
{
	[Export(PropertyHint.None, "")]
	public BGMElement[] elements;
}
