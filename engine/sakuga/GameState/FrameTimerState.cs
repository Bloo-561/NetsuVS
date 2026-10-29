using MessagePack;

namespace SakugaEngine.GameState;

[MessagePackObject(false)]
public struct FrameTimerState
{
	[Key(0)]
	public uint WaitTime;

	[Key(1)]
	public uint TimeLeft;

	[Key(2)]
	public bool Paused;

	public void GetStateData(ref FrameTimer reference)
	{
		if (reference != null)
		{
			WaitTime = reference.WaitTime;
			TimeLeft = reference.TimeLeft;
			Paused = reference.Paused;
		}
	}

	public void SetStateData(ref FrameTimer reference)
	{
		if (reference != null)
		{
			reference.WaitTime = WaitTime;
			reference.TimeLeft = TimeLeft;
			reference.Paused = Paused;
		}
	}
}
