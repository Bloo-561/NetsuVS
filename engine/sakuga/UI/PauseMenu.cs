using Godot;
using SakugaEngine.Game;

namespace SakugaEngine.UI;

public partial class PauseMenu : Control
{
	[Export(PropertyHint.None, "")]
	private Button firstButton;

	public void CallPauseMenu(bool paused)
	{
		base.Visible = paused;
		if (paused)
		{
			firstButton.GrabFocus();
		}
	}

	private void _on_button_resume_pressed()
	{
		if (base.Visible)
		{
			GameManager.Instance.PauseControl(pause: false);
		}
	}

	private void _on_button_restart_pressed()
	{
		if (base.Visible)
		{
			LoadingScreenManager.Instance.LoadScene("res://scenes/battle/battle.tscn");
			base.Visible = false;
		}
	}

	private void _on_button_char_select_pressed()
	{
		if (base.Visible)
		{
			LoadingScreenManager.Instance.LoadScene("res://scenes/character_select/character_select.tscn");
			base.Visible = false;
		}
	}

	private void _on_button_main_menu_pressed()
	{
		if (base.Visible)
		{
			LoadingScreenManager.Instance.LoadScene("res://scenes/main_menu/main_menu.tscn");
			base.Visible = false;
		}
	}
}
