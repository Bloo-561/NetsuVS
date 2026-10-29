using Godot;

namespace SakugaEngine;

[GlobalClass]
public partial class FrameTimer : Node
{
	[Export(PropertyHint.None, "")]
	public bool Manual;

	[Export(PropertyHint.None, "")]
	public uint WaitTime;

	public uint TimeLeft;

	public bool Paused;

	public void Start(uint startingTime = 0u)
	{
		Paused = false;
		TimeLeft = ((startingTime == 0) ? WaitTime : startingTime);
	}

	public void Run()
	{
		if (TimeLeft != 0 && !Paused)
		{
			TimeLeft--;
		}
	}

	public void Pause()
	{
		Paused = true;
	}

	public void Resume()
	{
		Paused = false;
	}

	public void Stop()
	{
		TimeLeft = 0u;
		Paused = false;
	}

	public bool IsRunning()
	{
		return TimeLeft != 0;
	}

	public bool IsCounting()
	{
		if (TimeLeft != 0)
		{
			return !Paused;
		}
		return false;
	}

	public bool IsPaused()
	{
		return Paused;
	}
}
