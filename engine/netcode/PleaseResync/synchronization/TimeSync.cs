namespace PleaseResync;

internal class TimeSync
{
	public const int InitialFrame = 0;

	public const int MaxRollbackFrames = 8;

	public const int FrameAdvantageLimit = 2;

	public int SyncFrame;

	public int LocalFrame;

	public int RemoteFrame;

	public int LocalFrameAdvantage;

	public int RemoteFrameAdvantage;

	public int FrameAdvantageDifference;

	public TimeSync()
	{
		SyncFrame = 0;
		LocalFrame = 0;
		RemoteFrame = 0;
		RemoteFrameAdvantage = 0;
		LocalFrameAdvantage = 0;
	}

	public bool IsTimeSynced(Device[] devices)
	{
		int minRemoteFrame = int.MaxValue;
		int maxRemoteFrameAdvantage = int.MinValue;
		foreach (Device device in devices)
		{
			if (device.Type == Device.DeviceType.Remote)
			{
				if (device.RemoteFrame < minRemoteFrame)
				{
					minRemoteFrame = device.RemoteFrame;
				}
				if (device.RemoteFrameAdvantage > maxRemoteFrameAdvantage)
				{
					maxRemoteFrameAdvantage = device.RemoteFrameAdvantage;
				}
			}
		}
		RemoteFrame = minRemoteFrame;
		RemoteFrameAdvantage = maxRemoteFrameAdvantage;
		LocalFrameAdvantage = LocalFrame - RemoteFrame;
		FrameAdvantageDifference = LocalFrameAdvantage - RemoteFrameAdvantage;
		if (LocalFrameAdvantage < 8)
		{
			return FrameAdvantageDifference <= 2;
		}
		return false;
	}

	public bool ShouldRollback()
	{
		if (LocalFrame > SyncFrame)
		{
			return RemoteFrame > SyncFrame;
		}
		return false;
	}
}
