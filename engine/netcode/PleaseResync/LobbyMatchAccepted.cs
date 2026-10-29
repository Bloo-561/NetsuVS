using MessagePack;

namespace PleaseResync;

[MessagePackObject(false)]
public class LobbyMatchAccepted : DeviceMessage
{
	[Key(1)]
	public long MatchID;

	[Key(2)]
	public bool AsSpectator;

	[Key(3)]
	public byte Index;

	public override string ToString()
	{
		return $"{typeof(LobbyMatchAccepted)}: {new { MatchID, AsSpectator, Index }}";
	}
}
