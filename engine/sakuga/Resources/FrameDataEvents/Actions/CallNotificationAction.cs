using Godot;
using SakugaEngine.Game;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class CallNotificationAction : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	private int Index;

	public override void Execute(ref SakugaActor Actor)
	{
		if (GameManager.Instance != null)
		{
			GameManager.Instance.PlayHitNotificationByIndex((int)Actor.playerID, Index);
		}
	}
}
