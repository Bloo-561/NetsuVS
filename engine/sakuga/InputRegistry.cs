using SakugaEngine.Global;

namespace SakugaEngine;

public struct InputRegistry
{
	public PlayerInputs rawInput;

	public ushort duration;

	public bool IsNull => rawInput == PlayerInputs.NEUTRAL;

	public override string ToString()
	{
		return $"({rawInput}, {duration})";
	}
}
