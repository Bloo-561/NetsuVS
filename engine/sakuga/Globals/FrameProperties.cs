using System;

namespace SakugaEngine.Global;

[Flags]
public enum FrameProperties : byte
{
	DAMAGE_IMUNITY = 1,
	THROW_IMUNITY = 2,
	PROJECTILE_IMUNITY = 4,
	LOCK_MOVE = 0x10
}
