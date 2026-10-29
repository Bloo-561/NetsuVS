using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class SpawnsList : Resource
{
	[Export(PropertyHint.None, "")]
	public SpawnObject[] SpawnObjects;
}
