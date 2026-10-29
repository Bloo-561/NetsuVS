using System;

namespace SakugaEngine.Global;

[Flags]
public enum PlayerInputs : ushort
{
	NEUTRAL = 0,
	UP = 1,
	DOWN = 2,
	LEFT = 4,
	RIGHT = 8,
	FACE_A = 0x10,
	FACE_B = 0x20,
	FACE_C = 0x40,
	FACE_D = 0x80,
	FACE_E = 0x100,
	FACE_F = 0x200,
	FACE_G = 0x400,
	FACE_H = 0x800,
	MENU = 0x4000,
	BACK = 0x8000,
	ANY_DIRECTION = UP | DOWN | LEFT | RIGHT,
	ANY_BUTTON = FACE_A | FACE_B | FACE_C | FACE_D | FACE_E | FACE_F | FACE_G | FACE_H
}
