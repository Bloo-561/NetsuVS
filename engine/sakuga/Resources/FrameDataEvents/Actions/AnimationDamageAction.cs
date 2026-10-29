using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class AnimationDamageAction : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	private int Damage;

	[Export(PropertyHint.None, "")]
	private HitstunType HitstunType;

	[Export(PropertyHint.None, "")]
	private bool KillingBlow;

	[Export(PropertyHint.None, "")]
	private bool UseProrations;

	[Export(PropertyHint.None, "")]
	private bool AffectDamageTracker;

	public override void Execute(ref SakugaActor Actor)
	{
		if (Actor.Parameters != null)
		{
			Actor.HitstunType = HitstunType;
			int finalDamage = Damage;
			if (UseProrations && Actor.Parameters.Prorations != null)
			{
				finalDamage = Actor.Parameters.CalculateProrations(Damage, 100, Actor.Parameters.Prorations.CurrentDefense, 0);
			}
			Actor.Parameters.TakeDamage(finalDamage, 0, KillingBlow);
			if (AffectDamageTracker && Actor.Parameters.Tracker != null)
			{
				Actor.Parameters.Tracker.UpdateTrackers(finalDamage, 0, 1, 3);
			}
		}
	}
}
