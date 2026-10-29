using System;

namespace SakugaEngine.Global;

[Flags]
public enum ButtonInputs : ushort
{
	FACE_A = 1,
	FACE_B = 2,
	FACE_C = 4,
	FACE_D = 8,
	FACE_E = 0x10,
	FACE_F = 0x20,
	FACE_G = 0x40,
	FACE_H = 0x80,
	ANY_BUTTON = FACE_A | FACE_B | FACE_C | FACE_D | FACE_E | FACE_F | FACE_G | FACE_H
}
