using SakugaEngine.Global;

namespace SakugaEngine.Resources;

/// <summary>Netsu: positions the Netsu actions and conditions aim at.</summary>
public static class NetsuTargets
{
	public static int X(SakugaActor actor, RelativeTo target)
	{
		switch (target)
		{
		case RelativeTo.OPPONENT:
		{
			SakugaActor[] opponents = actor.GetOpponents();
			return (opponents != null && opponents.Length > 0) ? opponents[0].Body.FixedPosition.X : 0;
		}
		case RelativeTo.FIGHTER:
			return actor.NetsuRoot().Body.FixedPosition.X;
		case RelativeTo.SELF:
			return actor.Body.FixedPosition.X;
		default:
			return 0;
		}
	}

	public static int Y(SakugaActor actor, RelativeTo target)
	{
		switch (target)
		{
		case RelativeTo.OPPONENT:
		{
			SakugaActor[] opponents = actor.GetOpponents();
			return (opponents != null && opponents.Length > 0) ? opponents[0].Body.FixedPosition.Y : 0;
		}
		case RelativeTo.FIGHTER:
			return actor.NetsuRoot().Body.FixedPosition.Y;
		case RelativeTo.SELF:
			return actor.Body.FixedPosition.Y;
		default:
			return 0;
		}
	}
}
