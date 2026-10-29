namespace PleaseResync;

public class SessionAdvanceFrameAction : SessionAction
{
	public byte[] Inputs;

	internal SessionAdvanceFrameAction(int frame, byte[] inputs)
	{
		Frame = frame;
		Inputs = inputs;
	}

	public override string ToString()
	{
		return $"{typeof(SessionAdvanceFrameAction)}: {new { Frame, Inputs }}";
	}
}
