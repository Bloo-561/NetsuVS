using System.Collections.Generic;

namespace PleaseResync;

public abstract class Session
{
	public const uint LIMIT_INPUT_SIZE = 32u;

	public const uint LIMIT_DEVICE_COUNT = 4u;

	public const uint LIMIT_TOTAL_PLAYER_COUNT = 24u;

	protected bool OfflinePlay;

	protected uint InputSize;

	protected readonly uint DeviceCount;

	protected readonly uint TotalPlayerCount;

	protected internal abstract Device LocalDevice { get; }

	protected internal abstract Device[] AllDevices { get; }

	public Session(uint inputSize, uint deviceCount, uint totalPlayerCount, bool offline)
	{
		OfflinePlay = offline;
		InputSize = inputSize;
		DeviceCount = deviceCount;
		TotalPlayerCount = totalPlayerCount;
	}

	public abstract void SetLocalDevice(uint deviceId, uint playerCount, uint frameDelay);

	public abstract void AddRemoteDevice(uint deviceId, uint playerCount, object remoteConfiguration);

	public abstract void AddSpectatorDevice(object remoteConfiguration);

	public abstract void Poll();

	public abstract bool IsRunning();

	public abstract List<SessionAction> AdvanceFrame(byte[] localInput);

	protected internal abstract uint SendMessageTo(uint deviceId, DeviceMessage message);

	protected internal abstract void AddRemoteInput(uint deviceId, DeviceInputMessage message);

	public bool IsOffline()
	{
		return OfflinePlay;
	}

	public abstract int Frame();

	public abstract int RemoteFrame();

	public abstract int FrameAdvantage();

	public abstract int RemoteFrameAdvantage();

	public abstract int FrameAdvantageDifference();

	public abstract uint RollbackFrames();

	public abstract uint AverageRollbackFrames();

	public abstract int State();
}
