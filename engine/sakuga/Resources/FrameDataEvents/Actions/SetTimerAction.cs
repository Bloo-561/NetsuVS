using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class SetTimerAction : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	private int ByIndex = -1;

	[Export(PropertyHint.None, "")]
	private string ByName;

	[Export(PropertyHint.Enum, "Play,Pause,Stop")]
	private int TimerMode;

	[Export(PropertyHint.None, "")]
	private uint Time;

	public override void Execute(ref SakugaActor Actor)
	{
		if (Actor.Parameters != null)
		{
			FrameTimer timer = null;
			if (ByIndex >= 0)
			{
				Actor.Parameters.GetTimer(ByIndex);
			}
			else if (ByName != "")
			{
				timer = Actor.Parameters.GetTimer(ByName);
			}
			timer?.Start(Time);
		}
	}
}
