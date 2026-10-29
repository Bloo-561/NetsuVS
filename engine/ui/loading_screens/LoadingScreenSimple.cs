using Godot;

public partial class LoadingScreenSimple : Control
{
	[Export(PropertyHint.None, "")]
	private Control star;

	[Export(PropertyHint.None, "")]
	private Label loadingText;

	private int timer;

	public override void _PhysicsProcess(double delta)
	{
		if (base.Visible)
		{
			star.Rotation += 3f * (float)delta;
			timer++;
			if (timer == 30)
			{
				loadingText.Text = "Loading..";
			}
			else if (timer == 60)
			{
				loadingText.Text = "Loading...";
			}
			else if (timer == 90)
			{
				loadingText.Text = "Loading";
			}
			else if (timer == 120)
			{
				timer = 0;
				loadingText.Text = "Loading.";
			}
		}
	}
}
