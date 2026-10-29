using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class FighterProfile : Resource
{
	[Export(PropertyHint.None, "")]
	public string FighterName;

	[Export(PropertyHint.None, "")]
	public string ShortName;

	[Export(PropertyHint.None, "")]
	public Texture2D Render;

	[Export(PropertyHint.None, "")]
	public Texture2D Portrait;

	[Export(PropertyHint.None, "")]
	public Texture2D VictoryRender;

	[Export(PropertyHint.None, "")]
	public Texture2D OnlineIcon;

	[Export(PropertyHint.MultilineText, "")]
	public string Bio;

	[Export(PropertyHint.None, "")]
	public int AutoStage;

	[Export(PropertyHint.None, "")]
	public int AutoBGM;

	/// <summary>Netsu (Oct 24): the colour of this fighter's EX / super presentation: the outline around her
	/// sprite while the move flashes and the smoke behind a super (game/ui/battle_hud/netsu_cut_in.gd).
	/// Fully transparent = use the side's colour (Player 1 blue, Player 2 red).</summary>
	[Export(PropertyHint.None, "")]
	public Color NetsuAuraColor = new Color(0f, 0f, 0f, 0f);
}
