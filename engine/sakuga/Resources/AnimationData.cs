using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
[Tool]
public partial class AnimationData : Resource
{
	[Export(PropertyHint.None, "")]
	public int Duration;

	[Export(PropertyHint.None, "")]
	public int HitstunHold = -1;

	[Export(PropertyHint.None, "")]
	public AnimationSettings[] Animations;

	[Export(PropertyHint.None, "")]
	public HitboxState[] Hitboxes;

	[Export(PropertyHint.None, "")]
	public AttackProfile[] AttackProfiles;

	// Netsu: draw fading afterimages behind the fighter while this animation plays (dashes, slides).
	[Export(PropertyHint.None, "")]
	public bool Afterimages;

	// Netsu (Oct 29): draw those afterimages as solid tinted silhouettes (bright, easy to see) instead of the usual
	// faint copies. Only Flan's charged 236B (Star Cross) uses it.
	[Export(PropertyHint.None, "")]
	public bool NetsuSolidAfterimages;
}
