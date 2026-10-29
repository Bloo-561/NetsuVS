using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class SetHealthAction : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	private int Value;

	[Export(PropertyHint.None, "")]
	private bool Absolute;

	[Export(PropertyHint.None, "")]
	private bool KillingBlow;

	public override void Execute(ref SakugaActor Actor)
	{
		if (Value == 0 || Actor.Parameters == null || Actor.Parameters.Health == null)
		{
			return;
		}
		if (Absolute)
		{
			Actor.Parameters.Health.SetHealth(Mathf.Abs(Value));
		}
		else if (Value > 0)
		{
			Actor.Parameters.Health.AddHealth(Mathf.Abs(Value));
		}
		else if (Value < 0)
		{
			Actor.Parameters.Health.RemoveHealth(Mathf.Abs(Value));
			if (KillingBlow && Actor.Parameters.Health.CurrentValue < 0)
			{
				Actor.Parameters.Health.SetHealth(0);
			}
		}
	}
}
