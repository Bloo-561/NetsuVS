using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.UI;

public partial class MatchSettingsMenu : Control
{
	[Export(PropertyHint.None, "")]
	private MainMenuManager Manager;

	[Export(PropertyHint.None, "")]
	private Button firstButton;

	[Export(PropertyHint.None, "")]
	private OptionButton TimeLimitOp;

	[Export(PropertyHint.None, "")]
	private OptionButton RoundsOp;

	[Export(PropertyHint.None, "")]
	private OptionButton BotDiffOp;

	public void GoTo()
	{
		base.Visible = true;
		firstButton.GrabFocus();
	}

	public void _OnGoButtonPressed()
	{
		base.Visible = false;
		int finalRoundTime = -1;
		switch (TimeLimitOp.Selected)
		{
		case 0:
			finalRoundTime = 99;
			break;
		case 1:
			finalRoundTime = 90;
			break;
		case 2:
			finalRoundTime = 60;
			break;
		case 3:
			finalRoundTime = 30;
			break;
		case 4:
			finalRoundTime = 10;
			break;
		}
		Manager.matchSettings.TimeLimit = finalRoundTime;
		Manager.matchSettings.RoundsToWin = RoundsOp.Selected + 1;
		Manager.matchSettings.Difficulty = (BotDifficulty)BotDiffOp.Selected;
		Manager.inputMenu.GoTo();
	}

	public void _OnBackButtonPressed()
	{
		base.Visible = false;
		Manager.mainMenu.GoTo();
	}
}
