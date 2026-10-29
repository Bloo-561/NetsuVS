using Godot;

namespace SakugaEngine.Resources;

/// <summary>
/// Netsu (Oct 26 c6, TamaDeez): freezes the opponent (hitstop) for Frames frames, whatever state it's in. Cecilia's
/// counter super uses it so the fighter she countered stays frozen in its attack while she slowly draws her blade
/// (a counter puts the opponent in no hit reaction, so it would otherwise recover and walk away before the slashes).
/// </summary>
[GlobalClass]
public partial class NetsuFreezeOpponentAction : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	public int Frames = 20;

	public override void Execute(ref SakugaActor Actor)
	{
		SakugaActor opponent = Actor.GetOpponent(0);
		if (Frames > 0 && opponent != null && opponent.CanHitstop())
		{
			opponent.Hitstop.Start((uint)Frames);
		}
	}
}
