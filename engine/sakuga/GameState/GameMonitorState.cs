using MessagePack;
using SakugaEngine.Global;

namespace SakugaEngine.GameState;

[MessagePackObject(false)]
public struct GameMonitorState
{
	[Key(1)]
	public FrameTimerState DelayTimer;

	[Key(2)]
	public int Clock;

	[Key(3)]
	public int CurrentRound;

	[Key(4)]
	public int Winner;

	[Key(0)]
	public FadeScreenMode FadeMode;

	[Key(5)]
	public int FadeScreenIntensity;

	[Key(6)]
	public int FadeTime;

	[Key(7)]
	public int FadeProgress;

	[Key(8)]
	public MatchState MatchState;

	[Key(9)]
	public int RoundWinner;

	[Key(10)]
	public int CardsCurrentAnimation;

	[Key(11)]
	public int CardsCurrentFrame;

	[Key(12)]
	public int[] VictoryCounter;

	public void GetStateData(ref GameMonitor reference)
	{
		if (reference != null)
		{
			DelayTimer.GetStateData(ref reference.DelayTimer);
			Clock = reference.Clock;
			CurrentRound = reference.CurrentRound;
			Winner = reference.Winner;
			FadeMode = reference.FadeMode;
			FadeScreenIntensity = reference.FadeScreenIntensity;
			FadeTime = reference.FadeTime;
			FadeProgress = reference.FadeProgress;
			MatchState = reference.MatchState;
			CurrentRound = reference.CurrentRound;
			RoundWinner = reference.RoundWinner;
			CardsCurrentAnimation = reference.Cards.CurrentAnimation;
			CardsCurrentFrame = reference.Cards.Frame;
			VictoryCounter = reference.VictoryCounter;
		}
	}

	public void SetStateData(ref GameMonitor reference)
	{
		if (reference != null)
		{
			DelayTimer.SetStateData(ref reference.DelayTimer);
			reference.Clock = Clock;
			reference.CurrentRound = CurrentRound;
			reference.Winner = Winner;
			reference.FadeMode = FadeMode;
			reference.FadeScreenIntensity = FadeScreenIntensity;
			reference.FadeTime = FadeTime;
			reference.FadeProgress = FadeProgress;
			reference.MatchState = MatchState;
			reference.CurrentRound = CurrentRound;
			reference.RoundWinner = RoundWinner;
			reference.Cards.CurrentAnimation = CardsCurrentAnimation;
			reference.Cards.Frame = CardsCurrentFrame;
			reference.VictoryCounter = VictoryCounter;
		}
	}
}
