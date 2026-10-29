using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class AICondition : Resource
{
	[Export(PropertyHint.None, "")]
	public Vector2I Distance;

	[Export(PropertyHint.None, "")]
	public bool UseOnGround;

	[Export(PropertyHint.None, "")]
	public bool UseOnAir;

	[Export(PropertyHint.None, "")]
	public int SuperGaugeRequired;

	[Export(PropertyHint.None, "")]
	public int Probability = 10;

	[Export(PropertyHint.None, "")]
	public BotMode ActionMode;

	[Export(PropertyHint.None, "")]
	public int[] ActionsList;

	/// <summary>Netsu: for a reaction (CounterFlags, Probability 0): its chance in 10, on top of the
	/// behaviour's PredictionQuality (10 = just PredictionQuality). Keeps a costly read (a counter super)
	/// rarer than an anti-air.</summary>
	[Export(PropertyHint.None, "")]
	public int ReactChance = 10;

	/// <summary>Netsu: for an anti-air: frames from its button press to its first hit, as the opponent sees
	/// them (0 for an EX / super whose flash freezes the opponent before the hit). The CPU fires it that long,
	/// plus the time to input it, before the jumper is in reach. -1 = 7.</summary>
	[Export(PropertyHint.None, "")]
	public int NetsuStartup = -1;

	[ExportSubgroup("AI Flags", "")]
	[Export(PropertyHint.None, "")]
	public AIFlags CounterFlags;
}
