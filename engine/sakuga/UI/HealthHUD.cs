using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.UI;

public partial class HealthHUD : Control
{
	[ExportCategory("Player 1")]
	[Export(PropertyHint.None, "")]
	private TextureRect P1Portrait;

	[Export(PropertyHint.None, "")]
	private TextureProgressBar P1Health;

	[Export(PropertyHint.None, "")]
	private TextureProgressBar P1LostHealth;

	[Export(PropertyHint.None, "")]
	private TextureProgressBar P1Will;

	[Export(PropertyHint.None, "")]
	private TextureRect P1WillLock;

	[Export(PropertyHint.None, "")]
	private RoundsCounter P1Rounds;

	[Export(PropertyHint.None, "")]
	private ComboCounter P1Combo;

	[Export(PropertyHint.None, "")]
	private Label P1Name;

	[Export(PropertyHint.None, "")]
	private HitNotificationController P1Notif;

	[ExportCategory("Player 2")]
	[Export(PropertyHint.None, "")]
	private TextureRect P2Portrait;

	[Export(PropertyHint.None, "")]
	private TextureProgressBar P2Health;

	[Export(PropertyHint.None, "")]
	private TextureProgressBar P2LostHealth;

	[Export(PropertyHint.None, "")]
	private TextureProgressBar P2Will;

	[Export(PropertyHint.None, "")]
	private TextureRect P2WillLock;

	[Export(PropertyHint.None, "")]
	private RoundsCounter P2Rounds;

	[Export(PropertyHint.None, "")]
	private ComboCounter P2Combo;

	[Export(PropertyHint.None, "")]
	private Label P2Name;

	[Export(PropertyHint.None, "")]
	private HitNotificationController P2Notif;

	[ExportCategory("Extra")]
	[Export(PropertyHint.None, "")]
	private Label Timer;

	[Export(PropertyHint.None, "")]
	private Label P1Debug;

	[Export(PropertyHint.None, "")]
	private Label P2Debug;

	public void Setup(SakugaActor[] fighters)
	{
		P1Health.MaxValue = fighters[0].Data.MaxHealth;
		P2Health.MaxValue = fighters[1].Data.MaxHealth;
		P1Will.MaxValue = fighters[0].Data.MaxWill;
		P2Will.MaxValue = fighters[1].Data.MaxWill;
		if (fighters[0].Data.Profile.Portrait != null)
		{
			P1Portrait.Texture = fighters[0].Data.Profile.Portrait;
			P1Name.Text = fighters[0].Data.Profile.ShortName;
		}
		if (fighters[1].Data.Profile.Portrait != null)
		{
			P2Portrait.Texture = fighters[1].Data.Profile.Portrait;
			P2Name.Text = fighters[1].Data.Profile.ShortName;
		}
		P1Rounds.Setup();
		P2Rounds.Setup();
	}

	public void UpdateHealthBars(SakugaActor[] fighters, GameMonitor monitor)
	{
		P1Health.Value = fighters[0].Parameters.Health.CurrentValue;
		P2Health.Value = fighters[1].Parameters.Health.CurrentValue;
		P1LostHealth.Value = fighters[0].Parameters.Health.LostValue;
		P2LostHealth.Value = fighters[1].Parameters.Health.LostValue;
		P1Will.Value = fighters[0].Parameters.Will.CurrentValue;
		P1WillLock.Visible = fighters[0].Parameters.Will.State != WillState.WORKING;
		if (fighters[0].Parameters.Will.State == WillState.LOCKED)
		{
			P1WillLock.Modulate = Colors.Red;
		}
		else if (fighters[0].Parameters.Will.State == WillState.DISABLED)
		{
			P1WillLock.Modulate = Colors.Black;
		}
		P2Will.Value = fighters[1].Parameters.Will.CurrentValue;
		P2WillLock.Visible = fighters[1].Parameters.Will.State != WillState.WORKING;
		if (fighters[1].Parameters.Will.State == WillState.LOCKED)
		{
			P2WillLock.Modulate = Colors.Red;
		}
		else if (fighters[1].Parameters.Will.State == WillState.DISABLED)
		{
			P2WillLock.Modulate = Colors.Black;
		}
		UpdateTimer(monitor);
		P1Rounds.ShowRounds(monitor.VictoryCounter[0]);
		P2Rounds.ShowRounds(monitor.VictoryCounter[1]);
		P1Combo.Visible = fighters[1].Parameters.Tracker.HitCombo > 0;
		P2Combo.Visible = fighters[0].Parameters.Tracker.HitCombo > 0;
		P1Combo.UpdateCounter((int)fighters[1].Hitstun.TimeLeft, fighters[1].Parameters.Tracker);
		P2Combo.UpdateCounter((int)fighters[0].Hitstun.TimeLeft, fighters[0].Parameters.Tracker);
		UpdateDebug(fighters);
	}

	public void UpdateDebug(SakugaActor[] fighters)
	{
		// Oct 25: the debug read-out is a long string per fighter; it was built every frame even hidden
		if (P1Debug.IsVisibleInTree())
		{
			P1Debug.Text = fighters[0].DebugInfo();
		}
		if (P2Debug.IsVisibleInTree())
		{
			P2Debug.Text = fighters[1].DebugInfo();
		}
	}

	private int _netsuTime = int.MinValue;

	public void UpdateTimer(GameMonitor monitor)
	{
		if (monitor.ClockLimit < 0)
		{
			if (_netsuTime != -1)
			{
				_netsuTime = -1;
				Timer.Text = "--";
			}
			return;
		}
		int time = monitor.Clock / 60;
		time = Mathf.Clamp(time, 0, monitor.ClockLimit);
		if (time != _netsuTime)   // Oct 25: a new string only when the number changes
		{
			_netsuTime = time;
			Timer.Text = time.ToString();
		}
	}

	public void UpdateHitNotifications(HitNotifications[] notifs)
	{
		P1Notif.View(notifs[0].Elements);
		P2Notif.View(notifs[1].Elements);
	}
}
