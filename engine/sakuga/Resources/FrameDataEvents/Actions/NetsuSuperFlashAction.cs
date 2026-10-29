using Godot;

namespace SakugaEngine.Resources;

/// <summary>
/// Netsu (Oct 24 2026): starts the super flash from a state instead of when the move starts.
/// For counter supers (Cecilia's Counter · Thunderclap): the stance itself shows nothing, so it can't be
/// read; the flash (the opponent freezes Frames frames, the stage darkens) and the cut-in come when the
/// counter catches something. The move has NetsuFlashOnHit on (no flash or cut-in at its start); its
/// counter-hit state runs this on enter.
/// </summary>
[GlobalClass]
public partial class NetsuSuperFlashAction : FrameDataAction
{
	/// <summary>How long the opponent is frozen.</summary>
	[Export(PropertyHint.None, "")]
	public int Frames = 20;

	/// <summary>Also show the EX / super cut-in of the move being done.</summary>
	[Export(PropertyHint.None, "")]
	public bool CutIn = true;

	public override void Execute(ref SakugaActor Actor)
	{
		Actor.StanceManager?.NetsuDelayedFlash(Frames, CutIn);
	}
}
