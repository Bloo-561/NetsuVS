using MessagePack;

namespace PleaseResync;

[MessagePackObject(false)]
public class PingMessage : DeviceMessage
{
	[Key(1)]
	public uint PingTime;

	[Key(2)]
	public bool Returning;

	public override string ToString()
	{
		return $"{typeof(PingMessage)}: {new { PingTime, Returning }}";
	}
}
