using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class SpawnObject : Resource
{
	[Export(PropertyHint.None, "")]
	public string Key;

	[Export(PropertyHint.None, "")]
	public PackedScene Instance;

	[Export(PropertyHint.None, "")]
	public int PoolSize;
}
