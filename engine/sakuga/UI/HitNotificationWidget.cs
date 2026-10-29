using Godot;

namespace SakugaEngine.UI;

public partial class HitNotificationWidget : Control
{
	[Export(PropertyHint.None, "")]
	private Label NotifLabel;

	public void View(HitNotificationPiece element)
	{
		base.Visible = element.Active;
		NotifLabel.Text = element.NotifName;
	}
}
