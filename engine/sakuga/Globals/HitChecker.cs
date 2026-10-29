using System;

namespace SakugaEngine.Global;

[Flags]
public enum HitChecker : byte
{
	NONE = 0,
	MASTER = 1,
	ALLIES = 3,
	OPPONENTS = 4
}
