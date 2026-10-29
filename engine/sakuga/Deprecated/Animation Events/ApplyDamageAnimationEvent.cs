using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class ApplyDamageAnimationEvent : AnimationEvent
{
	[Export(PropertyHint.None, "")]
	public int Index;

	[Export(PropertyHint.None, "")]
	public ParameterChange HealthChange;

	[Export(PropertyHint.None, "")]
	public int Value;

	[Export(PropertyHint.None, "")]
	public bool AffectedByModifiers;

	[Export(PropertyHint.None, "")]
	public bool AffectDamageTracker;

	[Export(PropertyHint.None, "")]
	public bool KillingBlow;
}
