using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class SetWillGaugeAction : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	private int Value;

	[Export(PropertyHint.None, "")]
	private bool Absolute;

	[Export(PropertyHint.None, "")]
	private bool SetWillState;

	[Export(PropertyHint.None, "")]
	private WillState ChangeState;

	public override void Execute(ref SakugaActor Actor)
	{
		if (Actor.Parameters == null || Actor.Parameters.Will == null)
		{
			return;
		}
		if (Absolute)
		{
			Actor.Parameters.Will.SetWillGauge(Mathf.Abs(Value));
			if (SetWillState)
			{
				Actor.Parameters.Will.State = ChangeState;
			}
			return;
		}
		if (Value > 0)
		{
			Actor.Parameters.Will.AddWillGauge(Mathf.Abs(Value));
		}
		else if (Value < 0)
		{
			Actor.Parameters.Will.SpendWillGauge(Mathf.Abs(Value));
		}
		if (SetWillState)
		{
			Actor.Parameters.Will.State = ChangeState;
		}
	}
}
