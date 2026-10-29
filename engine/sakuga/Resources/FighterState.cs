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

	/// <summary>Netsu (Oct 29): while the fighter is in this state, an opponent lying on the floor can't get up (the same
	/// hold a 3-bar super gets). Noah's j.214A landing: they stay down until the drain is absorbed and he has recovered.</summary>
	[Export(PropertyHint.None, "")]
	public bool NetsuHoldDown;

	/// <summary>Netsu (Oct 29): a charged move's state: a white flare bursts in front of the fighter for this many frames
	/// as it starts, so both players see the charged version came out (0 = none). Flan's charged 236B, Leticia's charged
	/// j.C. NetsuChargeFlareOffset: its centre (units; X along her facing, Y above her feet).</summary>
	[Export(PropertyHint.None, "")]
	public int NetsuChargeFlash;

	/// <summary>Netsu (Oct 29): the state a charge is held in (Flan's 236B, Leticia's j.C): while NetsuChargeHold is held,
	/// from frame 1 until NetsuChargeAt (the frame the charged version comes out), the flare already grows on her, so the
	/// charge shows the moment it starts. 0 / null = not a chargeable state.</summary>
	[Export(PropertyHint.None, "")]
	public int NetsuChargeAt;

	[Export(PropertyHint.None, "")]
	public MotionInputs NetsuChargeHold;

	[Export(PropertyHint.None, "")]
	public Vector2I NetsuChargeFlareOffset = new Vector2I(1500, 7000);   // Oct 29 (2): centred on her body

	[ExportSubgroup("AI Flags", "")]
	[Export(PropertyHint.None, "")]
	public AIFlags AIFlags;
}
