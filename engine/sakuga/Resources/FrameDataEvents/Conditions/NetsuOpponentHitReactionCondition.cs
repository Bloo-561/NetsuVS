using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

/// <summary>
/// Netsu (Oct 26 c6, TamaDeez): true while the opponent is still in a hit reaction (hitstun, launched, falling, lying
/// down, getting up). Not = the other way round. Cecilia's counter super holds its last frame with this (GoToFrame)
/// so she can't move until the opponent has recovered.
/// </summary>
[GlobalClass]
public partial class NetsuOpponentHitReactionCondition : FrameDataCondition
{
	[Export(PropertyHint.None, "")]
	private bool Not;

	public override bool Check(ref SakugaActor Actor)
	{
		SakugaActor opponent = Actor.GetOpponent(0);
		bool reacting = opponent != null && opponent.StateManager != null
			&& (opponent.StateManager.CurrentStateType() == StateType.HIT_REACTION || opponent.OnHitstun());
		return Not ? !reacting : reacting;
	}
}
