using MessagePack;

namespace PleaseResync;

[MessagePackObject(false)]
public class LobbyMatchRequest : DeviceMessage
{
	[Key(1)]
	public long MatchID;

	[Key(2)]
	public bool Spectate;

	public override string ToString()
	{
		return $"{typeof(LobbyMatchRequest)}: {new { MatchID, Spectate }}";
	}
}
