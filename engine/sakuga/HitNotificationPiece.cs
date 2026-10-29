using MessagePack;

namespace SakugaEngine;

[MessagePackObject(false)]
public struct HitNotificationPiece
{
	[Key(0)]
	public bool Active;

	[Key(1)]
	public string NotifName;
}
