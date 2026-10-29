using Godot;

namespace SakugaEngine.Resources;

/// <summary>
/// Netsu: an assist's buff on the fighter who called it (Mary's 5S). Put it in the assist's state
/// at the frame the buff should start. While it lasts the fighter deals DamagePercent damage and
/// gains GaugePercent Craft Gauge, and wears the assist's aura (NetsuAssistElement.BuffAura).
/// AddGauge gives Craft Gauge at once (2000 = 1 bar).
/// </summary>
[GlobalClass]
public partial class NetsuAssistBuffAction : FrameDataAction
{
	/// <summary>How long the buff lasts, in frames (60 = 1 second).</summary>
	[Export(PropertyHint.None, "")]
	private int Duration = 480;

	[Export(PropertyHint.None, "")]
	private int DamagePercent = 115;

	[Export(PropertyHint.None, "")]
	private int GaugePercent = 100;

	[Export(PropertyHint.None, "")]
	private int AddGauge;

	public override void Execute(ref SakugaActor Actor)
	{
		SakugaActor fighter = Actor.NetsuRoot();
		if (fighter == null || fighter == Actor)
		{
			return;
		}
		if (fighter.NetsuAssist != null)
		{
			fighter.NetsuAssist.StartBuff(Duration, DamagePercent, GaugePercent);
		}
		if (AddGauge > 0 && fighter.Parameters != null && fighter.Parameters.SuperGauge != null)
		{
			fighter.Parameters.SuperGauge.AddSuperGauge(AddGauge);
		}
	}
}
