using MessagePack;
using SakugaEngine.Global;

namespace SakugaEngine.GameState;

[MessagePackObject(false)]
public struct CustomVariableState
{
	[Key(0)]
	public int Value;

	[Key(1)]
	public int Factor;

	[Key(2)]
	public CustomVariableMode Mode;

	public void GetStateData(ref CustomVariable reference)
	{
		if (reference != null)
		{
			Value = reference.CurrentValue;
			Factor = reference.CurrentFactor;
			Mode = reference.CurrentMode;
		}
	}

	public void SetStateData(ref CustomVariable reference)
	{
		if (reference != null)
		{
			reference.CurrentValue = Value;
			reference.CurrentFactor = Factor;
			reference.CurrentMode = Mode;
		}
	}
}
