namespace PleaseResync;

public class WaitSuggestionEvent : SessionEvent
{
	public uint Frames;

	public override string Desc()
	{
		return "Wait Suggestion Event. Frames: " + Frames;
	}
}
