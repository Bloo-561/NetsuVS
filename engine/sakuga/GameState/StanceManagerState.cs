using MessagePack;

namespace SakugaEngine.GameState;

[MessagePackObject(false)]
public struct StanceManagerState
{
	[Key(0)]
	public int CurrentStance;

	[Key(1)]
	public int BufferedMove;

	[Key(2)]
	public int CurrentMove;

	[Key(3)]
	public bool CancelBuffer;

	[Key(4)]
	public int ExecutedMoves;   // Netsu (Oct 27 c27): counts move uses (repeat proration tells one use from the next)

	public void GetStateData(ref StanceManager reference)
	{
		if (reference != null)
		{
			CurrentStance = reference.CurrentStance;
			BufferedMove = reference.BufferedMove;
			CurrentMove = reference.CurrentMove;
			CancelBuffer = reference.CancelBuffer;
			ExecutedMoves = reference.ExecutedMoves;
		}
	}

	public void SetStateData(ref StanceManager reference)
	{
		if (reference != null)
		{
			reference.CurrentStance = CurrentStance;
			reference.BufferedMove = BufferedMove;
			reference.CurrentMove = CurrentMove;
			reference.CancelBuffer = CancelBuffer;
			reference.ExecutedMoves = ExecutedMoves;
		}
	}
}
