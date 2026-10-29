using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class AIActionPack : Resource
{
	[Export(PropertyHint.None, "")]
	public int HorizontalDistance;

	[Export(PropertyHint.None, "")]
	public AICondition[] Conditions;
}
