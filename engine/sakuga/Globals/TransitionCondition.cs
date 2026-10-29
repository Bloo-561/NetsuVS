using System;

namespace SakugaEngine.Global;

[Flags]
public enum TransitionCondition : byte
{
	STATE_END = 1,
	AT_FRAME = 2,
	ON_GROUND = 4,
	ON_WALLS = 8,
	ON_FALL = 0x10,
	ON_LIFE_END = 0x20,
	ON_INPUT_COMMAND = 0x40,
	ON_DISTANCE = 0x80
}
