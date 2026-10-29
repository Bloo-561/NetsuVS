using MessagePack;
using SakugaEngine.Game;

namespace SakugaEngine.GameState;

[MessagePackObject(false)]
public struct GameManagerState
{
	[Key(0)]
	public InputManagerState[] Inputs;

	[Key(1)]
	public int Frame;

	[Key(2)]
	public GameMonitorState GameMonitor;

	[Key(3)]
	public byte[][] SakugaNodes;

	[Key(4)]
	public Vector3IState RandomTest;

	[Key(5)]
	public HitNotifications[] Notifs;

	// Netsu (Oct 24 late): the EX / super pause (GameManager.NetsuPause). The formatter is hand-written in
	// engine/messagepack/GeneratedMessagePackResolver.cs (GameManagerStateFormatter): keep the two in step.
	[Key(6)]
	public int NetsuPause;

	[Key(7)]
	public int NetsuPauseSide;

	[Key(8)]
	public int NetsuPauseTotal;

	public void GetStateData(ref GameManager reference)
	{
		if (reference != null)
		{
			Inputs = new InputManagerState[reference.Inputs.Length];
			for (int i = 0; i < reference.Inputs.Length; i++)
			{
				Inputs[i].GetStateData(ref reference.Inputs[i]);
			}
			Frame = reference.Frame;
			GameMonitor.GetStateData(ref reference.Monitor);
			SakugaNodes = new byte[reference.Nodes.Count][];
			for (int j = 0; j < reference.Nodes.Count; j++)
			{
				SakugaNodes[j] = reference.Nodes[j].GetStateData();
			}
			RandomTest.GetStateData(ref reference.randomTest);
			Notifs = reference.Notifs;
			NetsuPause = reference.NetsuPause;
			NetsuPauseSide = reference.NetsuPauseSide;
			NetsuPauseTotal = reference.NetsuPauseTotal;
		}
	}

	public void SetStateData(ref GameManager reference)
	{
		if (reference != null)
		{
			for (int i = 0; i < reference.Inputs.Length; i++)
			{
				Inputs[i].SetStateData(ref reference.Inputs[i]);
			}
			reference.Frame = Frame;
			GameMonitor.SetStateData(ref reference.Monitor);
			for (int j = 0; j < reference.Nodes.Count; j++)
			{
				reference.Nodes[j].SetStateData(SakugaNodes[j]);
			}
			RandomTest.SetStateData(ref reference.randomTest);
			reference.Notifs = Notifs;
			reference.NetsuPause = NetsuPause;
			reference.NetsuPauseSide = NetsuPauseSide;
			reference.NetsuPauseTotal = NetsuPauseTotal;
		}
	}
}
