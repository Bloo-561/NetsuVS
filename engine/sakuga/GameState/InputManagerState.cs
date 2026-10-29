using MessagePack;
using SakugaEngine.Global;

namespace SakugaEngine.GameState;

[MessagePackObject(false)]
public struct InputManagerState
{
	[Key(0)]
	public PlayerInputs[] RawInputs;

	[Key(1)]
	public ushort[] Durations;

	[Key(2)]
	public short hCharge;

	[Key(3)]
	public short vCharge;

	[Key(4)]
	public int CurrentHistory;

	public void GetStateData(ref InputManager reference)
	{
		if (reference != null)
		{
			RawInputs = new PlayerInputs[16];
			Durations = new ushort[16];
			for (int i = 0; i < 16; i++)
			{
				RawInputs[i] = reference.InputHistory[i].rawInput;
				Durations[i] = reference.InputHistory[i].duration;
			}
			hCharge = reference.hCharge;
			vCharge = reference.vCharge;
			CurrentHistory = reference.CurrentHistory;
		}
	}

	public void SetStateData(ref InputManager reference)
	{
		if (reference != null)
		{
			for (int i = 0; i < 16; i++)
			{
				reference.InputHistory[i].rawInput = RawInputs[i];
				reference.InputHistory[i].duration = Durations[i];
			}
			reference.hCharge = hCharge;
			reference.vCharge = vCharge;
			reference.CurrentHistory = CurrentHistory;
		}
	}
}
