using System;

namespace SakugaEngine.Global;

[Flags]
public enum DirectionalInputs : ushort
{
	DOWN = 1,
	LEFT = 2,
	RIGHT = 4,
	UP = 8,
	DOWN_LEFT = DOWN | LEFT,
	DOWN_RIGHT = DOWN | RIGHT,
	UP_LEFT = LEFT | UP,
	UP_RIGHT = RIGHT | UP,
	ANY_DIRECTION = DOWN_LEFT | UP_RIGHT
}
