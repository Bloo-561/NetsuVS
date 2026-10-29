using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class FighterState : Resource
{
	[Export(PropertyHint.None, "")]
	public string StateName;

	[Export(PropertyHint.None, "")]
	public MasterStance BaseStance;

	[Export(PropertyHint.None, "")]
	public StateType Type;

	[Export(PropertyHint.None, "")]
	public AnimationData AnimationData;

	[Export(PropertyHint.None, "")]
	public FrameDataEvent[] TransitionEvents;

	[Export(PropertyHint.None, "")]
	public FrameDataEvent[] OnEnterEvents;

	[Export(PropertyHint.None, "")]
	public FrameDataEvent[] OnTickEvents;

	[Export(PropertyHint.None, "")]
	public FrameDataEvent[] OnExitEvents;

	[Export(PropertyHint.None, "")]
	public FrameDataEvent[] OnHitConfirmEvents;

	[Export(PropertyHint.None, "")]
	public FrameDataEvent[] OnHitReactionEvents;

	/// <summary>Netsu (Oct 25): a super's dark smoke backdrop (netsu_cut_in.gd) clears while the fighter is in this
	/// state, so the stage shows: Flan's Big Bang Crash flies up into the sky over it. Presentation only.</summary>
	[Export(PropertyHint.None, "")]
	public bool NetsuShowStage;

	/// <summary>Netsu (Oct 27): while this state runs, the opponent blocks as if the fighter were still on the side she
	/// faces FROM (before she passed through them), so a slash-through that ends up behind them is not a cross-up.</summary>
	[Export(PropertyHint.None, "")]
	public bool NetsuKeepBlockSide;

	[ExportSubgroup("AI Flags", "")]
	[Export(PropertyHint.None, "")]
	public AIFlags AIFlags;
}
