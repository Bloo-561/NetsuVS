using MessagePack;

namespace SakugaEngine.GameState;

[MessagePackObject(false)]
public struct StateManagerState
{
	[Key(0)]
	public int CurrentState;

	[Key(1)]
	public int CurrentStateFrame;

	public void GetStateData(ref StateManager reference)
	{
		if (reference != null)
		{
			CurrentState = reference.CurrentState;
			CurrentStateFrame = reference.CurrentStateFrame;
		}
	}

	public void SetStateData(ref StateManager reference)
	{
		if (reference != null)
		{
			reference.CurrentState = CurrentState;
			reference.CurrentStateFrame = CurrentStateFrame;
		}
	}
}
