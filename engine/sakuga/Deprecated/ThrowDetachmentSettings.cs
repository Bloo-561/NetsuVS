using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class ThrowDetachmentSettings : Resource
{
	[Export(PropertyHint.None, "")]
	public bool InvertSide;

	[Export(PropertyHint.None, "")]
	public HitstunType HitstunType;

	[Export(PropertyHint.None, "")]
	public Vector2I HitKnockback;

	[Export(PropertyHint.None, "")]
	public int HitKnockbackGravity;

	[Export(PropertyHint.None, "")]
	public int HitKnockbackTime = 8;

	[Export(PropertyHint.None, "")]
	public bool HitKnockbackInertia;

	[Export(PropertyHint.None, "")]
	public int Hitstun = 8;

	[Export(PropertyHint.None, "")]
	public int HorizontalBounce;

	[Export(PropertyHint.None, "")]
	public int HorizontalBounceIntensity;

	[Export(PropertyHint.None, "")]
	public int VerticalBounce;

	[Export(PropertyHint.None, "")]
	public int VerticalBounceIntensity;
}
