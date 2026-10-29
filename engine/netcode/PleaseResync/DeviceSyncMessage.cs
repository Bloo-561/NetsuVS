using MessagePack;

namespace PleaseResync;

[MessagePackObject(false)]
public class DeviceSyncMessage : DeviceMessage
{
	[Key(1)]
	public uint DeviceId;

	[Key(2)]
	public uint PlayerCount;

	[Key(3)]
	public uint RandomRequest;

	public override string ToString()
	{
		return $"{typeof(DeviceSyncMessage)}: {new { DeviceId, PlayerCount, RandomRequest }}";
	}
}
