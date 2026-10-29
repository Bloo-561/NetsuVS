using Godot;
using PleaseResync;
using SakugaEngine.Global;

namespace SakugaEngine.Game;

public partial class SakugaRollbackManager : PleaseResyncManager
{
	[Export(PropertyHint.None, "")]
	private GameManager GameManager;

	public override void _Ready()
	{
		base._Ready();
		GameManager.InputSize = InputSize;
		UseLAN = GameManager.Match.SelectedModeSettings.UseLAN;
		GD.Print("Starting " + GameManager.Match.SelectedModeSettings.ModeName + " mode.");
		if (GameManager.Match.SelectedModeSettings.AutoStart)
		{
			switch (GameManager.Match.SelectedModeSettings.NetcodeMode)
			{
			case NetcodeMode.LOCAL:
				LocalGame(2u);
				break;
			case NetcodeMode.ONLINE:
				OnlineGame(GameManager.Match.IsSpectator, 2u, (uint)GameManager.Match.SpectatorCount, (uint)GameManager.Match.PlayerID);
				break;
			case NetcodeMode.REPLAY:
				ReplayMode(2u);
				break;
			}
		}
	}

	public override void OnlineGame(bool spectate, uint players, uint spectators, uint ID)
	{
		StartOnlineGame(GameManager, spectate, players, spectators, ID);
	}

	public override void LocalGame(uint players)
	{
		StartOfflineGame(GameManager, players);
	}

	public override void ReplayMode(uint players)
	{
		StartReplay(GameManager, players);
	}
}
