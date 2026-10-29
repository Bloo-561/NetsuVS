using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class MoveCancelSettings : Resource
{
	[Export(PropertyHint.None, "")]
	public int MoveIndex;

	[Export(PropertyHint.None, "")]
	public CancelCondition Conditions;

	[Export(PropertyHint.None, "")]
	public Vector2I FrameThreshold;

	/// <summary>Netsu (Oct 26 2026, TamaDeez): this cancel only works while the fighter is in Overdrive (Flan's
	/// 623 series jump-cancels in Overdrive).</summary>
	[Export(PropertyHint.None, "")]
	public bool NetsuOverdriveOnly;
}
