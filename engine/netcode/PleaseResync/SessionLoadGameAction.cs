namespace PleaseResync;

public class SessionLoadGameAction : SessionAction
{
	private readonly StateStorage _storage;

	internal SessionLoadGameAction(int frame, StateStorage storage)
	{
		Frame = frame;
		_storage = storage;
	}

	public byte[] Load()
	{
		return _storage.LoadFrame(Frame).Buffer;
	}

	public override string ToString()
	{
		return $"{typeof(SessionLoadGameAction)}: {new { Frame, _storage }}";
	}
}
