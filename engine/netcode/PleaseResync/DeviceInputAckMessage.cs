using MessagePack;

namespace PleaseResync;

[MessagePackObject(false)]
public class DeviceInputAckMessage : DeviceMessage
{
	[Key(1)]
	public uint Frame;

	public override string ToString()
	{
		return $"{typeof(DeviceInputAckMessage)}: {new { Frame }}";
	}
}
