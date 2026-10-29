using Godot;

namespace SakugaEngine.Resources;

/// <summary>
/// Netsu (Oct 29 2026, TamaDeez): true while the opponent is standing or lying on the floor (Not = while they're in
/// the air). Cecilia's EX Crescent Slash holds her sheathe pose with this until the opponent has landed.
/// </summary>
[GlobalClass]
public partial class NetsuOpponentOnGroundCondition : FrameDataCondition
{
	[Export(PropertyHint.None, "")]
	private bool Not;

	public override bool Check(ref SakugaActor Actor)
	{
		SakugaActor opponent = Actor.GetOpponent(0);
		bool grounded = opponent == null || opponent.Body == null || opponent.Body.IsOnGround;
		return Not ? !grounded : grounded;
	}
}
