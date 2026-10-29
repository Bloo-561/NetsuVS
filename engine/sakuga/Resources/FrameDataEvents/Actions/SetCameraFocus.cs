using Godot;
using SakugaEngine.Game;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class SetCameraFocus : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	public CameraSelectFocus NewTarget;

	public override void Execute(ref SakugaActor Actor)
	{
		if (GameManager.Instance == null || GameManager.Instance.Camera == null)
		{
			return;
		}
		switch (NewTarget)
		{
		case CameraSelectFocus.CENTER:
			GameManager.Instance.Camera.CurrentFocus = CameraFocus.CENTER;
			break;
		case CameraSelectFocus.SELF:
			if (Actor.playerID == 0)
			{
				GameManager.Instance.Camera.CurrentFocus = CameraFocus.PLAYER1;
			}
			else
			{
				GameManager.Instance.Camera.CurrentFocus = CameraFocus.PLAYER2;
			}
			break;
		case CameraSelectFocus.OPPONENT:
			if (Actor.playerID == 1)
			{
				GameManager.Instance.Camera.CurrentFocus = CameraFocus.PLAYER2;
			}
			else
			{
				GameManager.Instance.Camera.CurrentFocus = CameraFocus.PLAYER1;
			}
			break;
		}
	}
}
