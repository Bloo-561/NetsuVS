using Godot;
using Godot.Collections;

namespace SakugaEngine.Utils;

public partial class InputRemapperWidget : Control
{
	[Export(PropertyHint.None, "")]
	private InputRemapper Remapper;

	[Export(PropertyHint.None, "")]
	private string Prefix;

	[Export(PropertyHint.Enum, "Keyboard,Gamepad")]
	private int DeviceType;

	[Export(PropertyHint.None, "")]
	private int deviceID;

	[Export(PropertyHint.None, "")]
	private InputRemapperButton[] Buttons;

	[Export(PropertyHint.None, "")]
	private Color DefaultColor;

	[Export(PropertyHint.None, "")]
	private Color SelectedColor;

	[Export(PropertyHint.None, "")]
	private Color RemappingColor;

	[Export(PropertyHint.None, "")]
	private Timer TimeFrame;

	[Export(PropertyHint.None, "")]
	private InputRemapperWidget WaitFor;

	private bool remapping;

	private int Selected;

	public bool IsRemapping => remapping;

	public override void _Ready()
	{
		for (int i = 0; i < Buttons.Length; i++)
		{
			UpdateText(i);
		}
		SetColors();
	}

	public override void _Process(double delta)
	{
		if (base.Visible)
		{
			base._Process(delta);
			if (remapping && TimeFrame.TimeLeft <= 0.0)
			{
				AudioManager.Instance.PlayMenuClip(2);
				remapping = false;
				UpdateText(Selected);
				SetColors();
			}
		}
	}

	public override void _UnhandledInput(InputEvent @event)
	{
		if (!base.Visible || (WaitFor != null && WaitFor.IsRemapping))
		{
			return;
		}
		if (!remapping)
		{
			if (@event.IsActionPressed(Prefix + "up"))
			{
				Selected--;
				Selected = Mathf.Clamp(Selected, 0, Buttons.Length - 1);
				SetColors();
				AudioManager.Instance.PlayMenuClip(0);
			}
			if (@event.IsActionPressed(Prefix + "down"))
			{
				AudioManager.Instance.PlayMenuClip(0);
				Selected++;
				Selected = Mathf.Clamp(Selected, 0, Buttons.Length - 1);
				SetColors();
			}
			if (@event.IsActionPressed(Prefix + "accept"))
			{
				AudioManager.Instance.PlayMenuClip(1);
				Buttons[Selected].SetKey("Awaiting Input...");
				remapping = true;
				TimeFrame.Start();
				SetColors();
			}
			if (@event.IsActionPressed(Prefix + "return") || @event.IsActionPressed(Prefix + "options"))
			{
				AudioManager.Instance.PlayMenuClip(2);
				remapping = false;
				base.Visible = false;
			}
			if (@event.IsActionPressed(Prefix + "extra1"))
			{
				AudioManager.Instance.PlayMenuClip(2);
				ClearMapping();
			}
			if (@event.IsActionPressed(Prefix + "extra2"))
			{
				AudioManager.Instance.PlayMenuClip(2);
				Array<StringName> actions = new Array<StringName>();
				InputRemapperButton[] buttons = Buttons;
				foreach (InputRemapperButton button in buttons)
				{
					actions.Add(Prefix + button.GetAction());
				}
				Remapper.ReturnToDefaultKeymaps(actions);
				for (int j = 0; j < Buttons.Length; j++)
				{
					UpdateText(j);
				}
			}
		}
		else
		{
			switch (DeviceType)
			{
			case 0:
				RemapKeyboard(@event);
				break;
			case 1:
				RemapController(@event, deviceID);
				break;
			}
		}
	}

	private void SetColors()
	{
		for (int i = 0; i < Buttons.Length; i++)
		{
			if (i == Selected)
			{
				Buttons[i].SetColor(remapping ? RemappingColor : SelectedColor);
			}
			else
			{
				Buttons[i].SetColor(DefaultColor);
			}
		}
	}

	private void RemapKeyboard(InputEvent @event)
	{
		if (@event is InputEventKey { Pressed: not false } eventKey)
		{
			InputMap.ActionEraseEvents(Prefix + Buttons[Selected].GetAction());
			InputMap.ActionAddEvent(Prefix + Buttons[Selected].GetAction(), eventKey);
			ReleaseFocus();
			UpdateText(Selected);
			Array<InputEvent> eventArray = new Array<InputEvent>();
			eventArray.Add(eventKey);
			Remapper.Remap(Prefix + Buttons[Selected].GetAction(), eventArray);
			Remapper.SaveKeymap();
			AudioManager.Instance.PlayMenuClip(3);
			remapping = false;
			SetColors();
		}
	}

	private void RemapController(InputEvent @event, int deviceID)
	{
		if (@event.Device != deviceID)
		{
			return;
		}
		if (@event is InputEventJoypadButton eventPad)
		{
			if (eventPad.Pressed)
			{
				InputMap.ActionEraseEvents(Prefix + Buttons[Selected].GetAction());
				InputMap.ActionAddEvent(Prefix + Buttons[Selected].GetAction(), eventPad);
				ReleaseFocus();
				UpdateText(Selected);
				Array<InputEvent> eventArray = new Array<InputEvent>();
				eventArray.Add(eventPad);
				Remapper.Remap(Prefix + Buttons[Selected].GetAction(), eventArray);
				Remapper.SaveKeymap();
				AudioManager.Instance.PlayMenuClip(3);
				remapping = false;
				SetColors();
			}
		}
		else if (@event is InputEventJoypadMotion eventMotion && Mathf.Abs(eventMotion.AxisValue) > 0.2f)
		{
			InputMap.ActionEraseEvents(Prefix + Buttons[Selected].GetAction());
			InputMap.ActionAddEvent(Prefix + Buttons[Selected].GetAction(), eventMotion);
			ReleaseFocus();
			UpdateText(Selected);
			Array<InputEvent> eventArray2 = new Array<InputEvent>();
			eventArray2.Add(eventMotion);
			Remapper.Remap(Prefix + Buttons[Selected].GetAction(), eventArray2);
			Remapper.SaveKeymap();
			AudioManager.Instance.PlayMenuClip(3);
			remapping = false;
			SetColors();
		}
	}

	private void ClearMapping()
	{
		InputMap.ActionEraseEvents(Prefix + Buttons[Selected].GetAction());
		ReleaseFocus();
		Buttons[Selected].SetKey(" ");
		Remapper.Remap(Prefix + Buttons[Selected].GetAction(), null);
		Remapper.SaveKeymap();
	}

	private void UpdateText(int selected)
	{
		string actionStr = InputMap.ActionGetEvents(Prefix + Buttons[selected].GetAction())[0].AsText();
		if (DeviceType > 0)
		{
			actionStr = GetSimplifiedGamepadButton(actionStr);
		}
		Buttons[selected].SetKey(actionStr);
	}

	private string GetSimplifiedGamepadButton(string action)
	{
		if (action.Contains("Joypad Button 0"))
		{
			return "Button A";
		}
		if (action.Contains("Joypad Button 1 "))
		{
			return "Button B";
		}
		if (action.Contains("Joypad Button 2 "))
		{
			return "Button X";
		}
		if (action.Contains("Joypad Button 3 "))
		{
			return "Button Y";
		}
		if (action.Contains("Joypad Button 4 "))
		{
			return "Button Back";
		}
		if (action.Contains("Joypad Button 5 "))
		{
			return "Button Home";
		}
		if (action.Contains("Joypad Button 6 "))
		{
			return "Button Start";
		}
		if (action.Contains("Joypad Button 7 "))
		{
			return "L.TB. Button";
		}
		if (action.Contains("Joypad Button 8 "))
		{
			return "R.TB. Button";
		}
		if (action.Contains("Joypad Button 9 "))
		{
			return "L. Shoulder";
		}
		if (action.Contains("Joypad Button 10"))
		{
			return "R. Shoulder";
		}
		if (action.Contains("Joypad Button 11"))
		{
			return "D-Pad Up";
		}
		if (action.Contains("Joypad Button 12"))
		{
			return "D-Pad Down";
		}
		if (action.Contains("Joypad Button 13"))
		{
			return "D-Pad Left";
		}
		if (action.Contains("Joypad Button 14"))
		{
			return "D-Pad Right";
		}
		if (action.Contains("Joypad Motion on Axis 1") && action.Contains("with Value -0"))
		{
			return "L.TB. Up";
		}
		if (action.Contains("Joypad Motion on Axis 1") && action.Contains("with Value 0"))
		{
			return "L.TB. Down";
		}
		if (action.Contains("Joypad Motion on Axis 0") && action.Contains("with Value -0"))
		{
			return "L.TB. Left";
		}
		if (action.Contains("Joypad Motion on Axis 0") && action.Contains("with Value 0"))
		{
			return "L.TB. Right";
		}
		if (action.Contains("Joypad Motion on Axis 3") && action.Contains("with Value -0"))
		{
			return "R.TB. Up";
		}
		if (action.Contains("Joypad Motion on Axis 3") && action.Contains("with Value 0"))
		{
			return "R.TB. Down";
		}
		if (action.Contains("Joypad Motion on Axis 2") && action.Contains("with Value -0"))
		{
			return "R.TB. Left";
		}
		if (action.Contains("Joypad Motion on Axis 2") && action.Contains("with Value 0"))
		{
			return "R.TB. Right";
		}
		if (action.Contains("Joypad Motion on Axis 4"))
		{
			return "Left Trigger";
		}
		if (action.Contains("Joypad Motion on Axis 5"))
		{
			return "Right Trigger";
		}
		return "";
	}
}
