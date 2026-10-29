using System;

namespace SakugaEngine.Global;

[Flags]
public enum AIFlags : ushort
{
	IDLE = 1,
	GROUND_ACTION = 2,
	AIR_ACTION = 4,
	MOVEMENT_STATE = 8,
	ATTACK_STATE = 0x10,
	HITSTUN_STATE = 0x20,
	BLOCKSTUN_STATE = 0x40,
	KNOCKED_DOWN = 0x80,
	HIGH_ACTION = 0x100,
	LOW_ACTION = 0x200,
	CLOSE_ACTION = 0x400,
	FAR_ACTION = 0x800,
	INVULNERABLE = 0x1000,
	/// <summary>Netsu: not a state flag. The CPU (AIBrain) adds it to the opponent's flags while the opponent
	/// is in the recovery of an attack (nothing more comes out of it): a "counter" condition with it is a punish.</summary>
	NETSU_RECOVERY = 0x2000
}
