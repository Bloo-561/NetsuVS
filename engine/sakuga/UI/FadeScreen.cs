using Godot;

namespace SakugaEngine.UI;

[Tool]
public partial class FadeScreen : ColorRect
{
	[Export(PropertyHint.Range, "0, 100")]
	public int FadeIntensity;

	public override void _Process(double delta)
	{
		float alpha = (float)FadeIntensity / 100f;
		base.Color = new Color(base.Color.R, base.Color.G, base.Color.B, alpha);
	}
}
