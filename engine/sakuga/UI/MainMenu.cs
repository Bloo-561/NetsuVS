using Godot;

namespace SakugaEngine.UI;

public partial class MainMenu : Control
{
	[Export(PropertyHint.None, "")]
	private MainMenuManager Manager;

	[Export(PropertyHint.None, "")]
	private Button firstButton;

	private Button lastButton;

	public override void _Ready()
	{
		base._Ready();
		firstButton.GrabFocus();
		AudioManager.Instance.PlayAnnouncerClip(0);
	}

	public void GoTo()
	{
		base.Visible = true;
		firstButton.GrabFocus();
	}

	public void _OnOnlineButtonPressed()
	{
		Manager.matchSettings.SelectedMode = 2;
		Manager.matchSettings.P2SelectedDevice = -1;
		base.Visible = false;
		Manager.inputMenu.GoTo();
		AudioManager.Instance.PlayMenuClip(1);
		AudioManager.Instance.PlayAnnouncerClip(1);
	}

	public void _OnArcadeButtonPressed()
	{
		Manager.matchSettings.SelectedMode = 0;
		Manager.matchSettings.TimeLimit = 99;
		base.Visible = false;
		Manager.inputMenu.GoTo();
		AudioManager.Instance.PlayMenuClip(1);
	}

	public void _OnVersusButtonPressed()
	{
		Manager.matchSettings.SelectedMode = 1;
		Manager.matchSettings.TimeLimit = 99;
		base.Visible = false;
		Manager.matchMenu.GoTo();
		AudioManager.Instance.PlayMenuClip(1);
		AudioManager.Instance.PlayAnnouncerClip(2);
	}

	public void _OnTrainingButtonPressed()
	{
		Manager.matchSettings.SelectedMode = 3;
		Manager.matchSettings.TimeLimit = -1;
		base.Visible = false;
		Manager.inputMenu.GoTo();
		AudioManager.Instance.PlayMenuClip(1);
		AudioManager.Instance.PlayAnnouncerClip(3);
	}

	public void _OnCreditsButtonPressed()
	{
		base.Visible = false;
		AudioManager.Instance.PlayMenuClip(1);
		Manager.Credits.Visible = true;
	}

	public void _OnReplayButtonPressed()
	{
		Manager.matchSettings.SelectedMode = 4;
		Manager.matchSettings.P1SelectedDevice = -1;
		Manager.matchSettings.P2SelectedDevice = -1;
		Manager.matchSettings.TimeLimit = 99;
	}

	public void _OnQuitButtonPressed()
	{
		AudioManager.Instance.PlayMenuClip(2);
		AudioManager.Instance.PlayAnnouncerClip(4);
		GetTree().Quit();
	}
}
