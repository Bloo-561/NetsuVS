using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class MatchSettings : Resource
{
	[ExportCategory("Main Settings")]
	[Export(PropertyHint.None, "")]
	public GameModeSettings[] GameModes;

	[Export(PropertyHint.None, "")]
	public int SelectedMode;

	[Export(PropertyHint.None, "")]
	public int TimeLimit = -1;

	[Export(PropertyHint.None, "")]
	public int RoundsToWin = 1;

	[Export(PropertyHint.None, "")]
	public int SelectedStage;

	[Export(PropertyHint.None, "")]
	public int SelectedBGM;

	[Export(PropertyHint.None, "")]
	public BotDifficulty Difficulty = BotDifficulty.MEDIUM;

	[ExportCategory("Player 1")]
	[Export(PropertyHint.None, "")]
	public int P1SelectedCharacter;

	[Export(PropertyHint.None, "")]
	public int P1SelectedColor;

	[Export(PropertyHint.None, "")]
	public int P1SelectedDevice = -1;

	/// <summary>Netsu: Player 1's assist (index in data/assist_list.tres), -1 = none.</summary>
	[Export(PropertyHint.None, "")]
	public int P1SelectedAssist = -1;

	[ExportCategory("Player 2")]
	[Export(PropertyHint.None, "")]
	public int P2SelectedCharacter;

	[Export(PropertyHint.None, "")]
	public int P2SelectedColor;

	[Export(PropertyHint.None, "")]
	public int P2SelectedDevice = -1;

	/// <summary>Netsu: Player 2's assist (index in data/assist_list.tres), -1 = none.</summary>
	[Export(PropertyHint.None, "")]
	public int P2SelectedAssist = -1;

	[ExportCategory("Online Settings")]
	[Export(PropertyHint.None, "")]
	public string OnlineP1Name;

	[Export(PropertyHint.None, "")]
	public Texture2D OnlineP1PlatformIcon;

	[Export(PropertyHint.None, "")]
	public string OnlineP2Name;

	[Export(PropertyHint.None, "")]
	public Texture2D OnlineP2PlatformIcon;

	[Export(PropertyHint.None, "")]
	public bool IsSpectator;

	[Export(PropertyHint.None, "")]
	public int PlayerID;

	[Export(PropertyHint.None, "")]
	public int SpectatorCount;

	public GameModeSettings SelectedModeSettings => GameModes[SelectedMode];
}
