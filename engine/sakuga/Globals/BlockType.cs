using System;

namespace SakugaEngine.Global;

[Flags]
public enum BlockType : byte
{
	HIGH = 1,
	MEDIUM = 2,
	LOW = 4
}
