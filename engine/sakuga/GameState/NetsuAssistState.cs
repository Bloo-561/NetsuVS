using MessagePack;

namespace SakugaEngine.GameState;

/// <summary>Netsu: everything about an assist gauge that rollback has to save and restore.
/// (The assist character itself is a SakugaActor and saves itself.)</summary>
[MessagePackObject(false)]
public struct NetsuAssistState
{
	[Key(0)]
	public int Gauge;

	[Key(1)]
	public int GaugeMax;

	[Key(2)]
	public int Phase;

	[Key(3)]
	public int Buffer;

	[Key(4)]
	public int BufferedMove;

	[Key(5)]
	public int OnScreen;

	[Key(6)]
	public int BuffFrames;

	[Key(7)]
	public int BuffTotal;

	[Key(8)]
	public int BuffDamagePercent;

	[Key(9)]
	public int BuffGainPercent;

	[Key(10)]
	public int AIWait;

	[Key(11)]
	public int LastMove;

	[Key(12)]
	public int Calls;

	[Key(13)]
	public int PendingMove;   // Netsu (Oct 26 late): a called assist waiting to appear (-1 none)

	[Key(14)]
	public int PendingFrames;

	[Key(15)]
	public int PendingSide;   // Netsu (Oct 27 c29): the fighter's facing when the assist was called

	[Key(16)]
	public bool LinkReady;   // Netsu (Oct 28): Overdrive Link not used yet

	[Key(17)]
	public bool LinkCall;    // Netsu (Oct 28): the assist on screen was called with the Link

	public void GetStateData(NetsuAssist reference)
	{
		if (reference == null)
		{
			return;
		}
		Gauge = reference.Gauge;
		GaugeMax = reference.GaugeMax;
		Phase = reference.Phase;
		Buffer = reference.Buffer;
		BufferedMove = reference.BufferedMove;
		OnScreen = reference.OnScreen;
		BuffFrames = reference.BuffFrames;
		BuffTotal = reference.BuffTotal;
		BuffDamagePercent = reference.BuffDamagePercent;
		BuffGainPercent = reference.BuffGainPercent;
		AIWait = reference.AIWait;
		LastMove = reference.LastMove;
		Calls = reference.Calls;
		PendingMove = reference.PendingMove;
		PendingFrames = reference.PendingFrames;
		PendingSide = reference.PendingSide;
		LinkReady = reference.LinkReady;
		LinkCall = reference.LinkCall;
	}

	public void SetStateData(NetsuAssist reference)
	{
		if (reference == null)
		{
			return;
		}
		reference.Gauge = Gauge;
		reference.GaugeMax = GaugeMax;
		reference.Phase = Phase;
		reference.Buffer = Buffer;
		reference.BufferedMove = BufferedMove;
		reference.OnScreen = OnScreen;
		reference.BuffFrames = BuffFrames;
		reference.BuffTotal = BuffTotal;
		reference.BuffDamagePercent = BuffDamagePercent;
		reference.BuffGainPercent = BuffGainPercent;
		reference.AIWait = AIWait;
		reference.LastMove = LastMove;
		reference.Calls = Calls;
		reference.PendingMove = PendingMove;
		reference.PendingFrames = PendingFrames;
		reference.PendingSide = PendingSide == 0 ? 1 : PendingSide;
		reference.LinkReady = LinkReady;
		reference.LinkCall = LinkCall;
	}
}
