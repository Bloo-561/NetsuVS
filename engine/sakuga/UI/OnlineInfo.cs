using Godot;
using SakugaEngine.Resources;

namespace SakugaEngine.UI;

public partial class OnlineInfo : Control
{
	[Export(PropertyHint.None, "")]
	private Label P1Name;

	[Export(PropertyHint.None, "")]
	private Label P2Name;

	[Export(PropertyHint.None, "")]
	private TextureRect P1Platform;

	[Export(PropertyHint.None, "")]
	private TextureRect P2Platform;

	public void Set(MatchSettings match)
	{
		P1Name.Text = match.OnlineP1Name;
		P2Name.Text = match.OnlineP2Name;
		if (match.OnlineP1PlatformIcon != null)
		{
			P1Platform.Texture = match.OnlineP1PlatformIcon;
		}
		if (match.OnlineP2PlatformIcon != null)
		{
			P2Platform.Texture = match.OnlineP2PlatformIcon;
		}
	}
}
