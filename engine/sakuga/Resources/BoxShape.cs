using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
[Tool]
public partial class BoxShape : Resource
{
	[Export(PropertyHint.None, "")]
	public Vector2I Center;

	[Export(PropertyHint.None, "")]
	public Vector2I Size;
}
