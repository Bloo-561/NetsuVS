using MessagePack;

namespace PleaseResync;

[MessagePackObject(false)]
public class LobbyGotKicked : DeviceMessage
{
	public override string ToString()
	{
		return $"{typeof(LobbyGotKicked)}: {new { }}";
	}
}
