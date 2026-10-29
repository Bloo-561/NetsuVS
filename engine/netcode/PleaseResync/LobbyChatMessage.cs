using MessagePack;

namespace PleaseResync;

[MessagePackObject(false)]
public class LobbyChatMessage : DeviceMessage
{
	[Key(1)]
	public string Message = "";

	public override string ToString()
	{
		return $"{typeof(LobbyChatMessage)}: {new { Message }}";
	}
}
