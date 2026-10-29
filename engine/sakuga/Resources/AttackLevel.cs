using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
[Tool]
public partial class AttackLevel : Resource
{
	[Export(PropertyHint.None, "")]
	public int Priority;

	[Export(PropertyHint.None, "")]
	public int ArmorDamage = 1;

	[Export(PropertyHint.None, "")]
	public int Hitstun = 8;

	[Export(PropertyHint.None, "")]
	public int Blockstun = 8;

	[Export(PropertyHint.None, "")]
	public int HitEffectIndex;

	[Export(PropertyHint.None, "")]
	public int GroundHitReaction;

	[Export(PropertyHint.None, "")]
	public int CrouchHitReaction = 1;

	[Export(PropertyHint.None, "")]
	public int AirHitReaction = 2;

	[Export(PropertyHint.None, "")]
	public int CornerPushback = 30000;
}
