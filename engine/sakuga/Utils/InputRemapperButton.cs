using Godot;

public partial class InputRemapperButton : HBoxContainer
{
	[Export(PropertyHint.None, "")]
	private string Title;

	[Export(PropertyHint.None, "")]
	private string Action;

	[Export(PropertyHint.None, "")]
	private Label TitleLabel;

	[Export(PropertyHint.None, "")]
	private ColorRect Field;

	[Export(PropertyHint.None, "")]
	private Label KeyLabel;

	public override void _Ready()
	{
		base._Ready();
		TitleLabel.Text = Title;
	}

	public void SetColor(Color color)
	{
		Field.Color = color;
	}

	public void SetKey(string text)
	{
		KeyLabel.Text = text;
	}

	public string GetAction()
	{
		return Action;
	}
}
