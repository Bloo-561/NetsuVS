using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class StageList : Resource
{
	[Export(PropertyHint.None, "")]
	public StageElement[] elements;
}
