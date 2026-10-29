using MessagePack;

namespace PleaseResync;

[MessagePackObject(false)]
public class DeviceSyncConfirmMessage : DeviceMessage
{
	[Key(1)]
	public uint DeviceId;

	[Key(2)]
	public uint PlayerCount;

	[Key(3)]
	public uint RandomResponse;

	public override string ToString()
	{
		return $"{typeof(DeviceSyncConfirmMessage)}: {new { DeviceId, PlayerCount, RandomResponse }}";
	}
}
