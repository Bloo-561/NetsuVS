using Godot;
using Godot.Collections;

namespace SakugaEngine.Utils;

public partial class InputRemapper : Control
{
	private const string KeymapDir = "user://keymaps.dat";

	private const string DefaultDir = "user://keymaps_default.dat";

	private Dictionary<StringName, Array<InputEvent>> Keymaps = new Dictionary<StringName, Array<InputEvent>>();

	[Export(PropertyHint.None, "")]
	private Control[] InputMappingChildren;

	[Export(PropertyHint.None, "")]
	private Control P1Pivot;

	[Export(PropertyHint.None, "")]
	private Control P2Pivot;

	[Export(PropertyHint.None, "")]
	private Control P1CurrentActiveInputMapping;

	[Export(PropertyHint.None, "")]
	private Control P2CurrentActiveInputMapping;

	public bool IsP1Remapping
	{
		get
		{
			if (P1CurrentActiveInputMapping != null)
			{
				return P1CurrentActiveInputMapping.Visible;
			}
			return false;
		}
	}

	public bool IsP2Remapping
	{
		get
		{
			if (P2CurrentActiveInputMapping != null)
			{
				return P2CurrentActiveInputMapping.Visible;
			}
			return false;
		}
	}

	public override void _Ready()
	{
		foreach (StringName action in InputMap.GetActions())
		{
			if (InputMap.ActionGetEvents(action).Count != 0)
			{
				Keymaps.Add(action, InputMap.ActionGetEvents(action));
			}
		}
		CreateDefaultKeymaps();
		LoadKeymap();
	}

	public void ToggleInputMapperP1(int index)
	{
		P1CurrentActiveInputMapping = InputMappingChildren[index];
		P1CurrentActiveInputMapping.Position = P1Pivot.Position;
		P1CurrentActiveInputMapping.Visible = !P1CurrentActiveInputMapping.Visible;
		P1CurrentActiveInputMapping._Ready();
	}

	public void ToggleInputMapperP2(int index)
	{
		P2CurrentActiveInputMapping = InputMappingChildren[index];
		P2CurrentActiveInputMapping.Position = P2Pivot.Position;
		P2CurrentActiveInputMapping.Visible = !P2CurrentActiveInputMapping.Visible;
		P2CurrentActiveInputMapping._Ready();
	}

	public void CreateDefaultKeymaps()
	{
		if (!FileAccess.FileExists("user://keymaps_default.dat"))
		{
			FileAccess fileAccess = FileAccess.Open("user://keymaps_default.dat", FileAccess.ModeFlags.Write);
			fileAccess.StoreVar(Keymaps, fullObjects: true);
			fileAccess.Close();
		}
	}

	public void ReturnToDefaultKeymaps(Array<StringName> actions)
	{
		FileAccess fileAccess = FileAccess.Open("user://keymaps_default.dat", FileAccess.ModeFlags.Read);
		Dictionary<StringName, Array<InputEvent>> tempKeymap = (Dictionary<StringName, Array<InputEvent>>)fileAccess.GetVar(allowObjects: true);
		fileAccess.Close();
		foreach (StringName action in actions)
		{
			if (!tempKeymap.TryGetValue(action, out var ev))
			{
				continue;
			}
			Remap(action, ev);
			InputMap.ActionEraseEvents(action);
			foreach (InputEvent newEv in ev)
			{
				InputMap.ActionAddEvent(action, newEv);
			}
		}
		SaveKeymap();
	}

	public void Remap(StringName action, Array<InputEvent> ev)
	{
		if (!Keymaps.ContainsKey(action))
		{
			Keymaps.Add(action, ev);
		}
		else
		{
			Keymaps[action] = ev;
		}
	}

	public void SaveKeymap()
	{
		FileAccess fileAccess = FileAccess.Open("user://keymaps.dat", FileAccess.ModeFlags.Write);
		fileAccess.StoreVar(Keymaps, fullObjects: true);
		fileAccess.Close();
	}

	public void LoadKeymap()
	{
		if (!FileAccess.FileExists("user://keymaps.dat"))
		{
			SaveKeymap();
			return;
		}
		FileAccess fileAccess = FileAccess.Open("user://keymaps.dat", FileAccess.ModeFlags.Read);
		Dictionary<StringName, Array<InputEvent>> tempKeymap = (Dictionary<StringName, Array<InputEvent>>)fileAccess.GetVar(allowObjects: true);
		fileAccess.Close();
		foreach (StringName action in InputMap.GetActions())
		{
			if (!tempKeymap.TryGetValue(action, out var ev))
			{
				continue;
			}
			Remap(action, ev);
			InputMap.ActionEraseEvents(action);
			foreach (InputEvent newEv in ev)
			{
				InputMap.ActionAddEvent(action, newEv);
			}
		}
	}
}
