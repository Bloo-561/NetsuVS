using System.Text;
using Godot;
using PleaseResync;

public partial class ChecksumCalculator : Control
{
	[Export(PropertyHint.None, "")]
	private LineEdit TextToConvert;

	[Export(PropertyHint.None, "")]
	private LineEdit ChecksumField;

	public override void _Ready()
	{
	}

	public override void _Process(double delta)
	{
	}

	public void _on_button_pressed()
	{
		byte[] seedArray = Encoding.ASCII.GetBytes(TextToConvert.Text);
		ChecksumField.Text = Platform.GetChecksum(seedArray).ToString();
	}
}
