using System;
using System.Collections.Generic;
using System.Threading;
using Godot;

namespace PleaseResync;

public partial class PleaseResyncManager : Node
{
	[Export(PropertyHint.None, "")]
	public bool SyncTest;

	private Label SimulationInfo;

	private Label RollbackInfo;

	private Label PingInfo;

	private bool Spectating;

	private bool Started;

	private bool Replay;

	public bool UseLAN;

	[Export(PropertyHint.None, "")]
	protected bool UseSeparateThread;

	[Export(PropertyHint.None, "")]
	protected ushort FrameDelay = 2;

	[Export(PropertyHint.None, "")]
	protected ushort SimulatedFrameDelay;

	[Export(PropertyHint.None, "")]
	protected ushort SpectatorDelay = 30;

	[Export(PropertyHint.None, "")]
	public uint MaxPlayers = 2u;

	[Export(PropertyHint.None, "")]
	public uint MaxSpectators = 8u;

	[Export(PropertyHint.None, "")]
	protected uint InputSize = 1u;

	private uint DEVICE_ID;

	private uint PingId;

	private string[] PlayerAddresses = new string[2] { "127.0.0.1", "127.0.0.1" };

	private string[] SpectatorAddresses = new string[2] { "127.0.0.1", "127.0.0.1" };

	private int[] PlayerPorts = new int[2] { 7001, 7002 };

	private int[] SpectatorPorts = new int[2] { 8001, 8002 };

	public IGameState sessionState;

	private SessionAdapter adapter;

	private Session session;

	private byte[] LastInput;

	private List<SessionAction> sessionActions;

	private string InputDebug;

	private string SimulationText;

	private string PingText;

	private string RollbackText;

	private List<ReplayInputs> RecordedInputs = new List<ReplayInputs>();

	private Thread GameThread;

	private System.Threading.Mutex mutex = new System.Threading.Mutex();

	// Netsu (Oct 25): group lobbies. Player 1's computer streams the match's settled frames (both players' inputs)
	// to the lobby (NetsuOnline.StreamInputs); the players who aren't fighting play that stream back here instead
	// of running a session of their own (they send nothing).
	private bool _netsuStream;      // player 1 of a lobby match: streams it
	private int _streamMatch;       // (its number)
	private int _streamSent;        // frames streamed so far
	private int _streamTicks;
	private bool _netsuSpectate;    // watching a lobby match
	private int _specMatch;
	private int _specFrame;         // frames played back so far
	private bool _specPlaying;

	/// <summary>Spectators: frames of the stream to have in hand before the playback starts (and after it ran dry).</summary>
	[Export(PropertyHint.None, "")]
	public int NetsuSpecBuffer = 12;

	/// <summary>Spectators: more frames than this waiting = play 2 a frame until it's back to this (catching up).</summary>
	[Export(PropertyHint.None, "")]
	public int NetsuSpecLag = 24;

	private string ShowPingInfo(uint id)
	{
		return session.AllDevices[id].GetRTT().ToString();
	}

	public override void _Ready()
	{
		SimulationInfo = GetTree().Root.GetNode<Label>("Root/CanvasLayer/PleaseResync_UI/Connection_Status/Simulation_Info");
		RollbackInfo = GetTree().Root.GetNode<Label>("Root/CanvasLayer/GameHUD_Foreground/ConnectionStatus/RollbackInfo");
		PingInfo = GetTree().Root.GetNode<Label>("Root/CanvasLayer/GameHUD_Foreground/ConnectionStatus/PingInfo");
		RecordedInputs.Add(new ReplayInputs());
		if (SimulationInfo != null)
		{
			SimulationInfo.Text = "";
		}
		if (RollbackInfo != null)
		{
			RollbackInfo.Text = "";
		}
		if (PingInfo != null)
		{
			PingInfo.Text = "";
		}
	}

	// Oct 25: the frame-counter / input / rollback read-outs are only built while their labels are on screen
	// (a few strings every frame were garbage for the collector, whose pauses were hitches).
	private volatile bool _netsuShowSim;
	private volatile bool _netsuShowNet;

	public override void _PhysicsProcess(double delta)
	{
		if (Started)
		{
			_netsuShowSim = SimulationInfo != null && SimulationInfo.IsVisibleInTree();
			_netsuShowNet = (RollbackInfo != null && RollbackInfo.IsVisibleInTree()) || (PingInfo != null && PingInfo.IsVisibleInTree());
			if (!UseSeparateThread)
			{
				GameLoop();
			}
			mutex.WaitOne();
			sessionState.Render();
			mutex.ReleaseMutex();
			if (SimulationInfo != null)
			{
				SimulationInfo.Text = NotificationText();
			}
			if (RollbackInfo != null)
			{
				RollbackInfo.Text = RollbackText;
			}
			if (PingInfo != null)
			{
				PingInfo.Text = PingText;
			}
		}
	}

	private void OnDestroy()
	{
		CloseGame();
	}

	public void CreatePlayerConnections(string[] IPAdresses, ushort[] ports)
	{
		for (uint i = 0u; i < IPAdresses.Length; i++)
		{
			if (IPAdresses[i] != "")
			{
				PlayerAddresses[i] = IPAdresses[i];
			}
			if (ports[i] > 0)
			{
				PlayerPorts[i] = ports[i];
			}
		}
	}

	public void CreateSpectatorConnections(string[] IPAdresses, ushort[] ports)
	{
		for (uint i = 0u; i < IPAdresses.Length; i++)
		{
			if (IPAdresses[i] != "")
			{
				SpectatorAddresses[i] = IPAdresses[i];
			}
			if (ports[i] > 0)
			{
				SpectatorPorts[i] = ports[i];
			}
		}
	}

	protected void StartOnlineGame(IGameState state, bool spectate, uint playerCount, uint spectatorCount, uint ID)
	{
		DEVICE_ID = ID;
		sessionState = state;
		sessionState.Setup();
		LastInput = new byte[InputSize];
		// NetsuVS: Epic Online Services was removed, so online play always uses
		// a direct LiteNetLib connection (IP address + port).
		UseLAN = true;
		// Oct 24: a fight started from the online lobby uses the lobby's own connection (NetsuOnline autoload);
		// without one, the old direct mode (PlayerAddresses / PlayerPorts) is still there.
		// Oct 25 (group lobbies): the match's two players (NetsuOnline.SetMatch) fight over it, everyone else in the
		// lobby watches the stream player 1's computer sends (no session of their own).
		NetsuVS.Online.NetsuOnline online = NetsuVS.Online.NetsuOnline.Instance;
		_netsuStream = false;
		_netsuSpectate = false;
		if (online != null && online.InLobby && (spectate || online.MyDevice < 0))
		{
			_netsuSpectate = true;
			_specMatch = online.MatchId;
			_specFrame = 0;
			_specPlaying = false;
			Spectating = true;
			Replay = false;
			Started = true;
			SimulationText = "Spectating...";
			RollbackText = "";
			PingText = "";
			GD.Print($"[online] watching match {_specMatch}");
			return;
		}
		if (online != null && online.InLobby)
		{
			if (DEVICE_ID != (uint)online.MyDevice)
			{
				GD.PushWarning($"PleaseResyncManager: playing side {online.MyDevice} of the lobby match (not {DEVICE_ID})");
				DEVICE_ID = (uint)online.MyDevice;
			}
			adapter = online.CreateSessionAdapter();
			_netsuStream = DEVICE_ID == 0u;
			_streamMatch = online.MatchId;
			_streamSent = 0;
			_streamTicks = 0;
		}
		else
		{
			adapter = new LiteNetLibSessionAdapter(PlayerAddresses[DEVICE_ID], (ushort)PlayerPorts[DEVICE_ID]);
		}
		if (!spectate)
		{
			session = new Peer2PeerSession(InputSize, playerCount, MaxPlayers, offline: false, adapter);
			session.SetLocalDevice(DEVICE_ID, 1u, FrameDelay);
			for (uint i = 0u; i < playerCount; i++)
			{
				if (i != DEVICE_ID)
				{
					session.AddRemoteDevice(i, 1u, LiteNetLibSessionAdapter.CreateRemoteConfig(PlayerAddresses[i], (ushort)PlayerPorts[i]));
					PingId = i;
					GD.Print($"Device {i} created");
				}
			}
			if (DEVICE_ID < playerCount)
			{
				for (uint i2 = 0u; i2 < spectatorCount; i2++)
				{
					if (i2 % playerCount == DEVICE_ID)
					{
						session.AddSpectatorDevice(LiteNetLibSessionAdapter.CreateRemoteConfig(SpectatorAddresses[i2], (ushort)SpectatorPorts[i2]));
					}
				}
			}
		}
		else
		{
			session = new SpectatorSession(InputSize, playerCount, adapter, SpectatorDelay);
			uint targetDevice = DEVICE_ID % playerCount;
			session.AddRemoteDevice(targetDevice, playerCount, LiteNetLibSessionAdapter.CreateRemoteConfig(PlayerAddresses[targetDevice], (ushort)PlayerPorts[targetDevice]));
			GD.Print($"Spectator device id {DEVICE_ID} connected to player ID {targetDevice}");
		}
		Spectating = spectate;
		Replay = false;
		Started = true;
		StartGameThread();
	}

	protected void StartOfflineGame(IGameState state, uint playerCount)
	{
		sessionState = state;
		sessionState.Setup();
		session = new Peer2PeerSession(InputSize, 1u, playerCount, offline: true, null);
		LastInput = new byte[playerCount * InputSize];
		session.SetLocalDevice(0u, playerCount, SimulatedFrameDelay);
		if (RollbackInfo != null)
		{
			RollbackInfo.Text = "";
		}
		if (PingInfo != null)
		{
			PingInfo.Text = "";
		}
		Spectating = false;
		Replay = false;
		Started = true;
		StartGameThread();
	}

	protected void StartReplay(IGameState state, uint playerCount)
	{
		sessionState = state;
		sessionState.Setup();
		session = new Peer2PeerSession(InputSize, 1u, playerCount, offline: true, null);
		LastInput = new byte[playerCount * InputSize];
		session.SetLocalDevice(0u, playerCount, SimulatedFrameDelay);
		if (RollbackInfo != null)
		{
			RollbackInfo.Text = "";
		}
		if (PingInfo != null)
		{
			PingInfo.Text = "";
		}
		Spectating = false;
		Replay = true;
		Started = true;
		StartGameThread();
	}

	private void GameThreadLoop()
	{
		while (Started)
		{
			long threadStartTime = Platform.GetCurrentTimeMS();
			mutex.WaitOne();
			GameLoop();
			mutex.ReleaseMutex();
			long num = Platform.GetCurrentTimeMS();
			int sleepTime = 16;
			int threadTime = (int)(num - threadStartTime);
			Thread.Sleep(Math.Max(sleepTime - threadTime, 0));
		}
	}

	private void GameLoop()
	{
		if (_netsuSpectate)
		{
			NetsuSpectateLoop();
			return;
		}
		if (!session.IsOffline())
		{
			session.Poll();
		}
		if (!session.IsRunning())
		{
			return;
		}
		if (Replay)
		{
			LastInput = ReadInputs(session.Frame());
		}
		else
		{
			for (int i = 0; i < LastInput.Length / InputSize; i++)
			{
				byte[] inputs = (SyncTest ? GetRandomInput() : sessionState.GetLocalInput(i, (int)InputSize));
				Array.Copy(inputs, 0L, LastInput, i * InputSize, inputs.Length);
			}
		}
		sessionActions = session.AdvanceFrame(LastInput);
		foreach (SessionAction action in sessionActions)
		{
			if (!(action is SessionAdvanceFrameAction AFAction))
			{
				if (!(action is SessionLoadGameAction LGAction))
				{
					if (action is SessionSaveGameAction SGAction)
					{
						byte[] state = sessionState.SaveState();
						SGAction.Save(state, Platform.GetChecksum(state));
					}
				}
				else
				{
					sessionState.LoadState(LGAction.Load());
				}
			}
			else
			{
				if (_netsuShowSim)
				{
					InputDebug = InputConstructor(AFAction.Inputs);
				}
				sessionState.GameLoop(AFAction.Inputs);
				if (!Replay)
				{
					RecordInput(AFAction.Frame, AFAction.Inputs);
				}
			}
		}
		if (_netsuStream && session is Peer2PeerSession p2p)
		{
			NetsuStreamSettled(p2p.ConfirmedFrame());
		}
		if (Spectating)
		{
			SimulationText = "Spectating...";
			RollbackText = "";
			PingText = "";
		}
		else
		{
			if (_netsuShowSim)
			{
				string FrameCounter = (session.IsOffline() ? $"{session.Frame()}" : $"{session.Frame()} ({session.RemoteFrame()} | {session.FrameAdvantage()} | {session.RemoteFrameAdvantage()})");
				SimulationText = FrameCounter + " || ( " + InputDebug + " )";
			}
			if (!session.IsOffline() && _netsuShowNet)
			{
				RollbackText = "RBF: " + session.AverageRollbackFrames();
				PingText = "Ping: " + ShowPingInfo(PingId) + " ms";
			}
		}
		if (Replay && session.Frame() >= RecordedInputs.Count)
		{
			CloseGame();
		}
	}

	/// <summary>Player 1 of a lobby match: the frames settled since last time (as they were played: RecordedInputs),
	/// a few at a time, to the lobby's spectators.</summary>
	private void NetsuStreamSettled(int settled)
	{
		NetsuVS.Online.NetsuOnline online = NetsuVS.Online.NetsuOnline.Instance;
		if (online == null)
		{
			return;
		}
		settled = Math.Min(settled, RecordedInputs.Count - 1);
		int count = settled - _streamSent;
		_streamTicks++;
		if (count <= 0 || (count < 3 && _streamTicks < 6))
		{
			return;
		}
		int size = (int)(InputSize * MaxPlayers);
		byte[] data = new byte[count * size];
		for (int i = 0; i < count; i++)
		{
			byte[] inputs = RecordedInputs[_streamSent + 1 + i].inputs;
			if (inputs != null)
			{
				Array.Copy(inputs, 0, data, i * size, Math.Min(size, inputs.Length));
			}
		}
		online.StreamInputs(_streamMatch, _streamSent + 1, data, count);
		_streamSent = settled;
		_streamTicks = 0;
	}

	/// <summary>Watching a lobby match: the next frames of the stream, played a moment behind the players (a small
	/// buffer smooths out uneven packets; when far behind, e.g. after coming in during the match, it plays faster
	/// until it has caught up).</summary>
	private void NetsuSpectateLoop()
	{
		NetsuVS.Online.NetsuOnline online = NetsuVS.Online.NetsuOnline.Instance;
		int have = online != null ? online.StreamFrames(_specMatch) : 0;
		int behind = have - _specFrame;
		if (!_specPlaying)
		{
			if (behind < Math.Max(1, _specFrame == 0 ? NetsuSpecBuffer : NetsuSpecBuffer / 2))
			{
				SimulationText = _specFrame == 0 ? "Waiting for the match..." : "Spectating... (waiting for the players)";
				return;
			}
			_specPlaying = true;
		}
		if (behind <= 0)
		{
			_specPlaying = false;   // ran dry: buffer again
			return;
		}
		int steps = behind > 600 ? 12 : (behind > 120 ? 4 : (behind > NetsuSpecLag ? 2 : 1));
		for (int i = 0; i < steps; i++)
		{
			if (!online.TryGetStreamInput(_specMatch, _specFrame + 1, out byte[] input))
			{
				break;
			}
			_specFrame++;
			sessionState.GameLoop(input);
		}
		SimulationText = "Spectating...";
	}

	/// <summary>Netsu: watching a lobby match (no session: the lobby's stream).</summary>
	public bool NetsuWatching => _netsuSpectate;

	/// <summary>Netsu: watching: frames of the stream not played yet.</summary>
	public int NetsuWatchBehind()
	{
		NetsuVS.Online.NetsuOnline online = NetsuVS.Online.NetsuOnline.Instance;
		return online != null ? online.StreamFrames(_specMatch) - _specFrame : 0;
	}

	private void StartGameThread()
	{
		SakugaEngine.Game.NetsuGc.FightStarted();   // Oct 25: no full blocking garbage collections during the fight
		if (UseSeparateThread)
		{
			GameThread = new Thread((ThreadStart)delegate
			{
				GameThreadLoop();
			});
			GameThread.IsBackground = true;
			GameThread.Start();
		}
	}

	private string NotificationText()
	{
		if (Spectating)
		{
			return SimulationText;
		}
		return session.State() switch
		{
			0 => "Syncing...", 
			1 => SimulationText, 
			2 => "Connection lost.", 
			3 => "Fatal desync detected.", 
			_ => "", 
		};
	}

	public void CloseGame()
	{
		_netsuSpectate = false;
		_netsuStream = false;
		Spectating = false;
		Started = false;
		Replay = false;
		sessionState = null;
		if (adapter != null)
		{
			adapter.Close();
			adapter = null;
		}
		if (SimulationInfo != null && IsInstanceValid(SimulationInfo))
		{
			SimulationInfo.Text = "Disconnected";
		}
	}

	// Netsu (Oct 24): leaving the fight closes the session (an online fight hands the connection back to the lobby)
	public override void _ExitTree()
	{
		if (Started || adapter != null)
		{
			CloseGame();
		}
		SakugaEngine.Game.NetsuGc.FightEnded();
	}

	private string InputConstructor(byte[] PlayerInputs)
	{
		string finalString = " ";
		for (int i = 0; i < PlayerInputs.Length; i++)
		{
			finalString = finalString + PlayerInputs[i] + " ";
			if (i < PlayerInputs.Length - 1)
			{
				finalString += ":: ";
			}
		}
		return finalString;
	}

	private void RecordInput(int frame, byte[] inputs)
	{
		// Netsu fix: the session can advance more than one frame between recordings
		// (catch-up after a hitch), which used to add only ONE slot and then crash with
		// "Index was out of range" every frame - the fight froze. Fill every missing slot.
		if (frame < 0)
		{
			return;
		}
		while (frame >= RecordedInputs.Count)
		{
			RecordedInputs.Add(new ReplayInputs());
		}
		RecordedInputs[frame] = new ReplayInputs(inputs);
	}

	private byte[] ReadInputs(int frame)
	{
		if (frame < 0 || frame >= RecordedInputs.Count)
		{
			return new byte[LastInput.Length];
		}
		byte[] recorded = RecordedInputs[frame].inputs;
		return (recorded == null || recorded.Length == 0) ? new byte[LastInput.Length] : recorded;
	}

	private byte[] GetRandomInput()
	{
		byte[] cnv = new byte[InputSize];
		for (int i = 0; i < cnv.Length; i++)
		{
			cnv[i] = (byte)Platform.GetRandomUnsignedShort();
		}
		return cnv;
	}

	public virtual void OnlineGame(bool spectate, uint players, uint spectators, uint ID)
	{
	}

	public virtual void LocalGame(uint players)
	{
	}

	public virtual void ReplayMode(uint players)
	{
	}
}
