using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class CheckTimerCondition : FrameDataCondition
{
	[Export(PropertyHint.None, "")]
	private int ByIndex = -1;

	[Export(PropertyHint.None, "")]
	private string ByName;

	[Export(PropertyHint.None, "")]
	private bool Not;

	public override bool Check(ref SakugaActor Actor)
	{
		if (Actor.Parameters == null)
		{
			return false;
		}
		FrameTimer timer = null;
		if (ByIndex >= 0)
		{
			Actor.Parameters.GetTimer(ByIndex);
		}
		else if (ByName != "")
		{
			timer = Actor.Parameters.GetTimer(ByName);
		}
		if (timer == null)
		{
			return false;
		}
		if (Not)
		{
			return !timer.IsRunning();
		}
		return timer.IsRunning();
	}
}
