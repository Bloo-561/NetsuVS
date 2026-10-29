using MessagePack;

namespace PleaseResync;

[MessagePackObject(false)]
public class LobbyMatchQuit : DeviceMessage
{
	[Key(1)]
	public bool IsSpectator;

	public override string ToString()
	{
		return $"{typeof(LobbyMatchQuit)}: {new { IsSpectator }}";
	}
}
