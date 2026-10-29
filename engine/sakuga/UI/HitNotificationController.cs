using Godot;

namespace SakugaEngine.UI;

public partial class HitNotificationController : Control
{
	[Export(PropertyHint.None, "")]
	private HitNotificationWidget[] Widgets;

	public void View(HitNotificationPiece[] elements)
	{
		for (int i = 0; i < Widgets.Length; i++)
		{
			Widgets[i].View(elements[i]);
		}
	}
}
