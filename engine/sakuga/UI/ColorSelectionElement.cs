using Godot;

namespace SakugaEngine.UI;

public partial class ColorSelectionElement : ColorRect
{
	[Export(PropertyHint.None, "")]
	private Label ColorName;

	[Export(PropertyHint.None, "")]
	private Color DefaultColor;

	[Export(PropertyHint.None, "")]
	private Color SelectedColor;

	public void Set(string colorName)
	{
		ColorName.Text = colorName;
		base.Color = DefaultColor;
	}

	public void Select()
	{
		base.Color = SelectedColor;
	}

	public void Deselect()
	{
		base.Color = DefaultColor;
	}
}
