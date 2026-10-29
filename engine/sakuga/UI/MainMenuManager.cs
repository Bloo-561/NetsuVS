using Godot;
using SakugaEngine.Resources;

namespace SakugaEngine.UI;

public partial class MainMenuManager : Node
{
	[Export(PropertyHint.None, "")]
	public MatchSettings matchSettings;

	[Export(PropertyHint.None, "")]
	public MainMenu mainMenu;

	[Export(PropertyHint.None, "")]
	public InputSelectMenu inputMenu;

	[Export(PropertyHint.None, "")]
	public MatchSettingsMenu matchMenu;

	[Export(PropertyHint.None, "")]
	public Control Credits;

	[Export(PropertyHint.None, "")]
	private AudioStream BGM;

	public override void _Ready()
	{
		AudioManager.Instance.PlayBGM(BGM);
	}

	public override void _Process(double delta)
	{
		if (Credits.Visible && Input.IsActionPressed("ui_cancel"))
		{
			Credits.Visible = false;
			mainMenu.GoTo();
		}
	}
}
