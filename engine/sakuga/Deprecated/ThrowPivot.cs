using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class ThrowPivot : Resource
{
	[Export(PropertyHint.None, "")]
	public int Frame;

	[Export(PropertyHint.None, "")]
	public Vector2I PivotPosition = Vector2I.Zero;

	[Export(PropertyHint.None, "")]
	public int ThrowState = -1;

	[Export(PropertyHint.None, "")]
	public ThrowDetachmentSettings ThrowDetach;
}
