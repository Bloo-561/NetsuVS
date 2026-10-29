using Godot;

namespace SakugaEngine.UI;

public partial class MetersHUD : Control
{
	[Export(PropertyHint.None, "")]
	private TextureProgressBar P1Meter;

	[Export(PropertyHint.None, "")]
	private TextureProgressBar P2Meter;

	[Export(PropertyHint.None, "")]
	private Label P1MeterCount;

	[Export(PropertyHint.None, "")]
	private Label P2MeterCount;

	[Export(PropertyHint.None, "")]
	private Label P1TrainingInfo;

	[Export(PropertyHint.None, "")]
	private Label P2TrainingInfo;

	[Export(PropertyHint.None, "")]
	private InputHistory P1InputHistory;

	[Export(PropertyHint.None, "")]
	private InputHistory P2InputHistory;

	private int CurrentFrameAdvantage;

	public void Setup(SakugaActor[] fighters)
	{
		P1Meter.MaxValue = fighters[0].Data.MaxSuperGauge;
		P2Meter.MaxValue = fighters[1].Data.MaxSuperGauge;
	}

	public void UpdateMeters(SakugaActor[] fighters)
	{
		P1Meter.Value = fighters[0].Parameters.SuperGauge.CurrentValue;
		P2Meter.Value = fighters[1].Parameters.SuperGauge.CurrentValue;
		// Oct 25: the texts are only rebuilt when what they show changes (new strings every frame were garbage for
		// the collector, whose pauses were hitches). The battle HUD reads the training info's text (combo damage).
		int bars1 = (int)P1Meter.Value / 2000;
		int bars2 = (int)P2Meter.Value / 2000;
		if (bars1 != _bars[0])
		{
			_bars[0] = bars1;
			P1MeterCount.Text = bars1.ToString();
		}
		if (bars2 != _bars[1])
		{
			_bars[1] = bars2;
			P2MeterCount.Text = bars2.ToString();
		}
		GetFrameAdvantage(fighters);
		P1InputHistory.SetHistoryList(fighters[0].Inputs);
		P2InputHistory.SetHistoryList(fighters[1].Inputs);
		if (TrainingInfoChanged(0, fighters[0], fighters[1]))
		{
			P1TrainingInfo.Text = TrainingInfoText(fighters[0], fighters[1]);
		}
		if (TrainingInfoChanged(1, fighters[1], fighters[0]))
		{
			P2TrainingInfo.Text = TrainingInfoText(fighters[1], fighters[0]);
		}
	}

	private readonly int[] _bars = { int.MinValue, int.MinValue };
	private readonly int[,] _infoShown = new int[2, 7];
	private readonly bool[] _infoSet = new bool[2];

	/// <summary>Has anything the training info line shows changed since it was last written?</summary>
	private bool TrainingInfoChanged(int side, SakugaActor owner, SakugaActor reference)
	{
		CombatTracker t = reference.Parameters.Tracker;
		CombatTracker o = owner.Parameters.Tracker;
		int a0 = t.LastHitType, a1 = o.FrameAdvantage, a2 = t.LastDamage, a3 = t.CurrentCombo, a4 = t.HighestCombo;
		int a5 = reference.Parameters.Prorations.CurrentDamageScaling, a6 = o.FrameData;
		if (_infoSet[side] && _infoShown[side, 0] == a0 && _infoShown[side, 1] == a1 && _infoShown[side, 2] == a2
			&& _infoShown[side, 3] == a3 && _infoShown[side, 4] == a4 && _infoShown[side, 5] == a5 && _infoShown[side, 6] == a6)
		{
			return false;
		}
		_infoSet[side] = true;
		_infoShown[side, 0] = a0; _infoShown[side, 1] = a1; _infoShown[side, 2] = a2; _infoShown[side, 3] = a3;
		_infoShown[side, 4] = a4; _infoShown[side, 5] = a5; _infoShown[side, 6] = a6;
		return true;
	}

	private void GetFrameAdvantage(SakugaActor[] fighters)
	{
		for (int i = 0; i < fighters.Length; i++)
		{
			if (fighters[i].Parameters.Tracker.FrameAdvantage != 0)
			{
				CurrentFrameAdvantage = fighters[i].Parameters.Tracker.FrameAdvantage;
			}
		}
	}

	private string TrainingInfoText(SakugaActor owner, SakugaActor reference)
	{
		string hitTypeText = "";
		switch (reference.Parameters.Tracker.LastHitType)
		{
		case 0:
			hitTypeText = "HIGH";
			break;
		case 1:
			hitTypeText = "MID";
			break;
		case 2:
			hitTypeText = "LOW";
			break;
		case 3:
			hitTypeText = "UNBL.";
			break;
		}
		int finalFrameAdv = owner.Parameters.Tracker.FrameAdvantage;
		string frameAdvantageInfo = ((finalFrameAdv >= 0) ? ("+" + finalFrameAdv) : (finalFrameAdv.ToString() ?? ""));
		string frameAdvText = "(" + frameAdvantageInfo + ")";
		return reference.Parameters.Tracker.LastDamage + "\n" + reference.Parameters.Tracker.CurrentCombo + "\n" + reference.Parameters.Tracker.HighestCombo + "\n" + hitTypeText + "\n" + reference.Parameters.Prorations.CurrentDamageScaling + "%\n" + owner.Parameters.Tracker.FrameData + frameAdvText;
	}
}
