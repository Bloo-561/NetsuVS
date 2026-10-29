using Godot;
using SakugaEngine.Game;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class RoundRunningCondition : FrameDataCondition
{
	[Export(PropertyHint.None, "")]
	private bool Not;

	public override bool Check(ref SakugaActor Actor)
	{
		if (GameManager.Instance == null)
		{
			return false;
		}
		if (Not)
		{
			return GameManager.Instance.Monitor.MatchState != MatchState.ROUND_RUNNING;
		}
		return GameManager.Instance.Monitor.MatchState == MatchState.ROUND_RUNNING;
	}
}
