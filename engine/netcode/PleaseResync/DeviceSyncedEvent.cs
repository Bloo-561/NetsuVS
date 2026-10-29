namespace PleaseResync;

public class DeviceSyncedEvent : SessionEvent
{
	public uint DeviceId;

	public override string Desc()
	{
		return $"Device {DeviceId} Has Been Synced And Ready To Operate";
	}
}
