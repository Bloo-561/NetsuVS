using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

/// <summary>
/// Netsu: true when the actor is between MinDistance and MaxDistance from Target, measured along
/// the actor's facing: positive = it is past the target (in front of it), negative = still short.
/// Target: OPPONENT, FIGHTER (the fighter who owns this assist/projectile), WORLD (x 0).
/// e.g. Adin's 6S run: MinDistance 50000 = "5 m past the opponent" -> off the screen.
/// </summary>
[GlobalClass]
public partial class NetsuRelativeXCondition : FrameDataCondition
{
	[Export(PropertyHint.None, "")]
	private RelativeTo Target = RelativeTo.OPPONENT;

	[Export(PropertyHint.None, "")]
	private int MinDistance = -1000000;

	[Export(PropertyHint.None, "")]
	private int MaxDistance = 1000000;

	[Export(PropertyHint.None, "")]
	private bool Not;

	public override bool Check(ref SakugaActor Actor)
	{
		if (Actor.Body == null)
		{
			return false;
		}
		int d = (Actor.Body.FixedPosition.X - NetsuTargets.X(Actor, Target)) * Actor.Body.PlayerSide;
		bool inside = d >= MinDistance && d <= MaxDistance;
		return Not ? !inside : inside;
	}
}
