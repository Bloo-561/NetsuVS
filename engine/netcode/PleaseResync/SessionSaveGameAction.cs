namespace PleaseResync;

public class SessionSaveGameAction : SessionAction
{
	private readonly StateStorage _storage;

	internal SessionSaveGameAction(int frame, StateStorage storage)
	{
		Frame = frame;
		_storage = storage;
	}

	public void Save(byte[] stateBuffer, uint checksum = 0u)
	{
		_storage.SaveFrame(Frame, stateBuffer, checksum);
	}

	public override string ToString()
	{
		return $"{typeof(SessionSaveGameAction)}: {new { Frame, _storage }}";
	}
}
