using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.UI;

public partial class InputSelectMenu : Control
{
	[Export(PropertyHint.None, "")]
	private MainMenuManager Manager;

	[Export(PropertyHint.None, "")]
	private Control DeviceWidgetKeyboard1;

	[Export(PropertyHint.None, "")]
	private Control DeviceWidgetKeyboard2;

	[Export(PropertyHint.None, "")]
	private Control DeviceWidgetController1;

	[Export(PropertyHint.None, "")]
	private Control DeviceWidgetController2;

	[Export(PropertyHint.None, "")]
	private Control PivotP1;

	[Export(PropertyHint.None, "")]
	private Control PivotP2;

	private Vector2 k1Pos;

	private Vector2 k2Pos;

	private Vector2 j1Pos;

	private Vector2 j2Pos;

	public override void _Ready()
	{
		k1Pos = DeviceWidgetKeyboard1.Position;
		k2Pos = DeviceWidgetKeyboard2.Position;
		j1Pos = DeviceWidgetController1.Position;
		j2Pos = DeviceWidgetController2.Position;
		Manager.matchSettings.P1SelectedDevice = -1;
		Manager.matchSettings.P2SelectedDevice = -1;
	}

	public override void _Process(double delta)
	{
		base._Process(delta);
		InputSelectionScreen();
	}

	public void GoTo()
	{
		base.Visible = true;
	}

	private void InputSelectionScreen()
	{
		if (!base.Visible)
		{
			return;
		}
		if (Input.IsActionJustPressed("k1_left"))
		{
			AudioManager.Instance.PlayMenuClip(0);
			if (Manager.matchSettings.P2SelectedDevice == 0)
			{
				Manager.matchSettings.P2SelectedDevice = -1;
			}
			else if (Manager.matchSettings.P1SelectedDevice == -1)
			{
				Manager.matchSettings.P1SelectedDevice = 0;
			}
		}
		if (Input.IsActionJustPressed("k1_right"))
		{
			AudioManager.Instance.PlayMenuClip(0);
			if (Manager.matchSettings.P1SelectedDevice == 0)
			{
				Manager.matchSettings.P1SelectedDevice = -1;
			}
			else if (Manager.matchSettings.P2SelectedDevice == -1)
			{
				Manager.matchSettings.P2SelectedDevice = 0;
			}
		}
		if (Manager.matchSettings.P2SelectedDevice == 0)
		{
			DeviceWidgetKeyboard1.Position = PivotP2.Position;
		}
		else if (Manager.matchSettings.P1SelectedDevice == 0)
		{
			DeviceWidgetKeyboard1.Position = PivotP1.Position;
		}
		else
		{
			DeviceWidgetKeyboard1.Position = k1Pos;
		}
		if (Input.IsActionJustPressed("k2_left"))
		{
			AudioManager.Instance.PlayMenuClip(0);
			if (Manager.matchSettings.P2SelectedDevice == 1)
			{
				Manager.matchSettings.P2SelectedDevice = -1;
			}
			else if (Manager.matchSettings.P1SelectedDevice == -1)
			{
				Manager.matchSettings.P1SelectedDevice = 1;
			}
		}
		if (Input.IsActionJustPressed("k2_right"))
		{
			AudioManager.Instance.PlayMenuClip(0);
			if (Manager.matchSettings.P1SelectedDevice == 1)
			{
				Manager.matchSettings.P1SelectedDevice = -1;
			}
			else if (Manager.matchSettings.P2SelectedDevice == -1)
			{
				Manager.matchSettings.P2SelectedDevice = 1;
			}
		}
		if (Manager.matchSettings.P2SelectedDevice == 1)
		{
			DeviceWidgetKeyboard2.Position = PivotP2.Position;
		}
		else if (Manager.matchSettings.P1SelectedDevice == 1)
		{
			DeviceWidgetKeyboard2.Position = PivotP1.Position;
		}
		else
		{
			DeviceWidgetKeyboard2.Position = k2Pos;
		}
		if (Input.IsActionJustPressed("j1_left"))
		{
			AudioManager.Instance.PlayMenuClip(0);
			if (Manager.matchSettings.P2SelectedDevice == 2)
			{
				Manager.matchSettings.P2SelectedDevice = -1;
			}
			else if (Manager.matchSettings.P1SelectedDevice == -1)
			{
				Manager.matchSettings.P1SelectedDevice = 2;
			}
		}
		if (Input.IsActionJustPressed("j1_right"))
		{
			AudioManager.Instance.PlayMenuClip(0);
			if (Manager.matchSettings.P1SelectedDevice == 2)
			{
				Manager.matchSettings.P1SelectedDevice = -1;
			}
			else if (Manager.matchSettings.P2SelectedDevice == -1)
			{
				Manager.matchSettings.P2SelectedDevice = 2;
			}
		}
		if (Manager.matchSettings.P2SelectedDevice == 2)
		{
			DeviceWidgetController1.Position = PivotP2.Position;
		}
		else if (Manager.matchSettings.P1SelectedDevice == 2)
		{
			DeviceWidgetController1.Position = PivotP1.Position;
		}
		else
		{
			DeviceWidgetController1.Position = j1Pos;
		}
		if (Input.IsActionJustPressed("j2_left"))
		{
			AudioManager.Instance.PlayMenuClip(0);
			if (Manager.matchSettings.P2SelectedDevice == 3)
			{
				Manager.matchSettings.P2SelectedDevice = -1;
			}
			else if (Manager.matchSettings.P1SelectedDevice == -1)
			{
				Manager.matchSettings.P1SelectedDevice = 3;
			}
		}
		if (Input.IsActionJustPressed("j2_right"))
		{
			AudioManager.Instance.PlayMenuClip(0);
			if (Manager.matchSettings.P1SelectedDevice == 3)
			{
				Manager.matchSettings.P1SelectedDevice = -1;
			}
			else if (Manager.matchSettings.P2SelectedDevice == -1)
			{
				Manager.matchSettings.P2SelectedDevice = 3;
			}
		}
		if (Manager.matchSettings.P2SelectedDevice == 3)
		{
			DeviceWidgetController2.Position = PivotP2.Position;
		}
		else if (Manager.matchSettings.P1SelectedDevice == 3)
		{
			DeviceWidgetController2.Position = PivotP1.Position;
		}
		else
		{
			DeviceWidgetController2.Position = j2Pos;
		}
		bool num = (Manager.matchSettings.P1SelectedDevice == 0 || Manager.matchSettings.P2SelectedDevice == 0) && Input.IsActionJustPressed("k1_accept");
		bool key2Confirm = (Manager.matchSettings.P1SelectedDevice == 1 || Manager.matchSettings.P2SelectedDevice == 1) && Input.IsActionJustPressed("k2_accept");
		bool joy1Confirm = (Manager.matchSettings.P1SelectedDevice == 2 || Manager.matchSettings.P2SelectedDevice == 2) && Input.IsActionJustPressed("j1_accept");
		bool joy2Confirm = (Manager.matchSettings.P1SelectedDevice == 3 || Manager.matchSettings.P2SelectedDevice == 3) && Input.IsActionJustPressed("j2_accept");
		if (Input.IsActionJustPressed("k1_return") || Input.IsActionJustPressed("k2_return") || Input.IsActionJustPressed("j1_return") || Input.IsActionJustPressed("j2_return"))
		{
			AudioManager.Instance.PlayMenuClip(2);
			base.Visible = false;
			Manager.mainMenu.GoTo();
		}
		if (num | key2Confirm | joy1Confirm | joy2Confirm)
		{
			AudioManager.Instance.PlayMenuClip(3);
			if (Manager.matchSettings.SelectedModeSettings.NetcodeMode == NetcodeMode.ONLINE)
			{
				LoadingScreenManager.Instance.LoadScene("res://scenes/main_menu/main_menu.tscn");
			}
			else
			{
				LoadingScreenManager.Instance.LoadScene("res://scenes/character_select/character_select.tscn");
			}
		}
	}
}
