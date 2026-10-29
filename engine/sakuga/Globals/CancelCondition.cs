using System;

namespace SakugaEngine.Global;

[Flags]
public enum CancelCondition : byte
{
	WHIFF_CANCEL = 1,
	HIT_CANCEL = 2,
	BLOCK_CANCEL = 4,
	KARA_CANCEL = 8
}
