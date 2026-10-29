using MessagePack;

namespace PleaseResync;

[MessagePackObject(false)]
public class HealthCheckMessage : DeviceMessage
{
	[Key(1)]
	public int Frame;

	[Key(2)]
	public uint Checksum;

	public override string ToString()
	{
		return $"{typeof(HealthCheckMessage)}: {new { Frame, Checksum }}";
	}
}
