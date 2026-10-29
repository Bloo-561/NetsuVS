namespace PleaseResync;

internal class StateStorage
{
	private const int MAX_STORAGE_SIZE = 24;

	private readonly int _size;

	private readonly StateStorageEntry[] _states;

	public StateStorage(int maxRollbackFrames)
	{
		_size = maxRollbackFrames + 24;
		_states = new StateStorageEntry[_size];
		for (int i = 0; i < _size; i++)
		{
			_states[i] = new StateStorageEntry();
		}
	}

	public void SaveFrame(int frame, byte[] stateBuffer, uint stateChecksum = 0u)
	{
		_states[frame % _size].Buffer = Platform.CloneByteArray(stateBuffer);
		_states[frame % _size].Checksum = stateChecksum;
	}

	public StateStorageEntry LoadFrame(int frame)
	{
		return _states[frame % _size];
	}

	public bool CompareChecksums(int frame, uint checksum)
	{
		if (_states[frame % _size].Checksum == 0 || checksum == 0)
		{
			return true;
		}
		return _states[frame % _size].Checksum == checksum;
	}

	public uint GetChecksum(int frame)
	{
		return _states[frame % _size].Checksum;
	}
}
