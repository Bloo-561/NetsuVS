using MessagePack;

namespace SakugaEngine.GameState;

/// <summary>Netsu (Nov 8, Link Break): everything about a fighter's crests and Break that rollback has to save.</summary>
[MessagePackObject(false)]
public struct NetsuLinkState
{
	[Key(0)]
	public bool CrestFighter;

	[Key(1)]
	public int CrestP0;

	[Key(2)]
	public int CrestP1;

	[Key(3)]
	public bool Ready;

	[Key(4)]
	public int Leader;

	[Key(5)]
	public bool LinkMoveWasOn;

	[Key(6)]
	public bool BreakLanded;

	[Key(7)]
	public int EventSeq;

	[Key(8)]
	public int EventKind;

	[Key(9)]
	public int EventWho;

	[Key(10)]
	public int Breaks;

	[Key(11)]
	public bool NoTechTillGround;

	[Key(12)]
	public int NoTechWait;

	[Key(13)]
	public int NoTechGround;

	[Key(14)]
	public bool NoTechAirborne;

	public void GetStateData(NetsuLink reference)
	{
		if (reference == null)
		{
			return;
		}
		CrestFighter = reference.CrestFighter;
		CrestP0 = reference.CrestP0;
		CrestP1 = reference.CrestP1;
		Ready = reference.Ready;
		Leader = reference.Leader;
		LinkMoveWasOn = reference.LinkMoveWasOn;
		BreakLanded = reference.BreakLanded;
		EventSeq = reference.EventSeq;
		EventKind = reference.EventKind;
		EventWho = reference.EventWho;
		Breaks = reference.Breaks;
		NoTechTillGround = reference.NoTechTillGround;
		NoTechWait = reference.NoTechWait;
		NoTechGround = reference.NoTechGround;
		NoTechAirborne = reference.NoTechAirborne;
	}

	public void SetStateData(NetsuLink reference)
	{
		if (reference == null)
		{
			return;
		}
		reference.CrestFighter = CrestFighter;
		reference.CrestP0 = CrestP0;
		reference.CrestP1 = CrestP1;
		reference.Ready = Ready;
		reference.Leader = Leader;
		reference.LinkMoveWasOn = LinkMoveWasOn;
		reference.BreakLanded = BreakLanded;
		reference.EventSeq = EventSeq;
		reference.EventKind = EventKind;
		reference.EventWho = EventWho;
		reference.Breaks = Breaks;
		reference.NoTechTillGround = NoTechTillGround;
		reference.NoTechWait = NoTechWait;
		reference.NoTechGround = NoTechGround;
		reference.NoTechAirborne = NoTechAirborne;
	}
}
