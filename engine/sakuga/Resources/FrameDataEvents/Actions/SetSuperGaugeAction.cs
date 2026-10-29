using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class SetSuperGaugeAction : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	private int Value;

	[Export(PropertyHint.None, "")]
	private bool Absolute;

	public override void Execute(ref SakugaActor Actor)
	{
		if (Value != 0 && Actor.Parameters != null && Actor.Parameters.SuperGauge != null)
		{
			if (Absolute)
			{
				Actor.Parameters.SuperGauge.SetSuperGauge(Mathf.Abs(Value));
			}
			else if (Value > 0)
			{
				Actor.Parameters.SuperGauge.AddSuperGauge(Mathf.Abs(Value));
			}
			else if (Value < 0)
			{
				Actor.Parameters.NetsuSpendMeter(Mathf.Abs(Value));   // Oct 29: spending starts the meter cooldown
			}
		}
	}
}
