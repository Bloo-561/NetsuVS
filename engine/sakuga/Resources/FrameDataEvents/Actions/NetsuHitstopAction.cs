using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

/// <summary>
/// Netsu (Oct 26 2026, TamaDeez): sets the hitstop (freeze) of this fighter and / or its opponent to a number of
/// frames, replacing the hit's own. Put it in a state's OnHitConfirmEvents (it runs right after the hit started its
/// hitstop). Flan's Spiral Star (623C) uses it so both hold the pose for 1.5 seconds on hit, and Radiant Breaker keeps
/// the opponent frozen while the energy charges around her fist. -1 leaves that side alone. The opponent is only frozen
/// while it's in a hit reaction (not on block, not after a Burst).
/// </summary>
[GlobalClass]
public partial class NetsuHitstopAction : FrameDataAction
{
	/// <summary>Frames of hitstop for this fighter (-1 = leave it).</summary>
	[Export(PropertyHint.None, "")]
	public int Self = -1;

	/// <summary>Frames of hitstop for the opponent (-1 = leave it).</summary>
	[Export(PropertyHint.None, "")]
	public int Opponent = -1;

	public override void Execute(ref SakugaActor Actor)
	{
		if (Self >= 0 && Actor.CanHitstop())
		{
			Actor.Hitstop.Start((uint)Self);
		}
		SakugaActor opponent = Actor.GetOpponent(0);
		if (Opponent >= 0 && opponent != null && opponent.CanHitstop() && opponent.StateManager != null
			&& opponent.StateManager.CurrentStateType() == StateType.HIT_REACTION)
		{
			opponent.Hitstop.Start((uint)Opponent);
		}
	}
}
