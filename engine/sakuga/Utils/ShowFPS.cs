using Godot;

public partial class ShowFPS : Label
{
	public override void _Process(double delta)
	{
		base.Text = Engine.GetFramesPerSecond() + " fps";
	}
}
