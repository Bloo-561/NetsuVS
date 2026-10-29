using MessagePack;

namespace PleaseResync;

[MessagePackObject(false)]
public class LobbyMatchRejected : DeviceMessage
{
	[Key(1)]
	public string Message = "";

	public override string ToString()
	{
		return $"{typeof(LobbyMatchAccepted)}: {new { Message }}";
	}
}
