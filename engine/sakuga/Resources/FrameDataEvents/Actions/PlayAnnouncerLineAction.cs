using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class PlayAnnouncerLineAction : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	public int Index;

	public override void Execute(ref SakugaActor Actor)
	{
		if (AudioManager.Instance != null)
		{
			AudioManager.Instance.PlayAnnouncerClip(Index);
		}
	}
}
