using System;
using Godot;
using SakugaEngine.Resources;

namespace SakugaEngine.UI;

public partial class ColorSelectMenu : Control
{
	[Export(PropertyHint.None, "")]
	private PackedScene menuElement;

	[Export(PropertyHint.None, "")]
	private ScrollContainer scroll;

	[Export(PropertyHint.None, "")]
	private Control contents;

	private ColorSelectionElement[] elements;

	public void Activate(FighterElement fighter)
	{
		base.Visible = true;
		elements = new ColorSelectionElement[fighter.ColorPalettes.Length];
		for (int i = 0; i < fighter.ColorPalettes.Length; i++)
		{
			ColorSelectionElement element = menuElement.Instantiate(PackedScene.GenEditState.Disabled) as ColorSelectionElement;
			element.Set($"{i + 1}: {fighter.ColorPalettes[i].PaletteName}");
			contents.AddChild(element, forceReadableName: false, InternalMode.Disabled);
			elements[i] = element;
		}
		SelectElement(0);
		scroll.GetVScrollBar().Scale = Vector2.Zero;
	}

	public void Deactivate()
	{
		foreach (Control child in contents.GetChildren())
		{
			child.QueueFree();
		}
		elements = Array.Empty<ColorSelectionElement>();
		base.Visible = false;
	}

	public void SelectElement(int index)
	{
		ColorSelectionElement[] array = elements;
		for (int i = 0; i < array.Length; i++)
		{
			array[i].Deselect();
		}
		elements[index].Select();
		scroll.EnsureControlVisible(elements[index]);
	}
}
