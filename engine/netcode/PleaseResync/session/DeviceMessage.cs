using MessagePack;

namespace PleaseResync;

[Union(0, typeof(DeviceSyncMessage))]
[Union(1, typeof(DeviceSyncConfirmMessage))]
[Union(2, typeof(DeviceInputMessage))]
[Union(3, typeof(DeviceInputAckMessage))]
[Union(4, typeof(HealthCheckMessage))]
[Union(5, typeof(PingMessage))]
[Union(6, typeof(LobbyChatMessage))]
[Union(7, typeof(LobbyMatchRequest))]
[Union(8, typeof(LobbyMatchAccepted))]
[Union(9, typeof(LobbyMatchRejected))]
[Union(10, typeof(LobbyMatchQuit))]
[Union(11, typeof(LobbyGotKicked))]
[MessagePackObject(false)]
public abstract class DeviceMessage
{
	[Key(0)]
	public uint SequenceNumber;
}
