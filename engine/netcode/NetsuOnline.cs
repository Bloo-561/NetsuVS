using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Net;
using System.Net.NetworkInformation;
using System.Net.Sockets;
using System.Text;
using System.Threading.Tasks;
using Godot;
using LiteNetLib;
using MessagePack;
using PleaseResync;

namespace NetsuVS.Online;

/// <summary>
/// NETSU ONLINE (Oct 24 2026; group lobbies Oct 25): lobbies with a join code, then rollback fights (PleaseResync)
/// over the same connections. Autoload "NetsuOnline" (project.godot); the room's rules (who plays, the queue,
/// spectators) are game/autoloads/online_room.gd, the screens scenes/online/online_lobby.gd.
///
///   Host(port)        opens a lobby on a UDP port (default 7777), works out the address other players reach
///                     this computer at (UPnP on the router, else a STUN server says what the internet sees) and
///                     gets a LOBBY CODE: a 5-digit number ("48213"), posted with that address on a public
///                     message board (ntfy.sh, below). CodeReady fires. LongCode = the address itself in
///                     12 letters / numbers ("K7Q2-M9X4-PA3D"): the backup, and the code when the board can't
///                     be reached. Up to MaxMembers - 1 other players can be in it (a star: everyone is connected to
///                     the host).
///   Join(code)        connects to a lobby: a 5-digit number (looked up on the board), a long code, or a plain
///                     "address:port" (LAN / port forwarding / testing). With a number the joiner also posts
///                     its own address, so the host calls it at the same time (that gets through most home
///                     routers, with nothing for the players to do). Once in, the host gives it an id
///                     (MyId; the host is 0) and Connected fires.
///   AcceptReply(code) the same by hand, for long codes: a joiner's REPLY CODE, typed in by the host.
///   Send(dictionary)  a lobby message (JSON, reliable): from a player to the host, or from the host to everyone
///                     (SendTo(id, ...): one player). MessageReceived on the other side; the host's copy says who
///                     sent it ("from").
///   Leave()           closes everything (removes the UPnP port mapping, marks the number closed).
/// Host: MemberJoined(id) / MemberLeft(id, reason) as players come and go.
///
/// Fights: SetMatch(match, p1, p2) says which two players fight (their ids); PleaseResyncManager then uses
/// CreateSessionAdapter() on those two computers: the fight's packets go straight between them when one is the host,
/// else through the host (it passes them on). Packets: 'G' fight (unreliable), 'L' lobby message, 'H' / 'W' joining
/// (a player's hello, the host's welcome with its id), 'S' the spectator stream.
/// Spectators: player 1's computer streams the fight's confirmed inputs (both players', frame by frame) to the host
/// (StreamInputs); the host keeps the whole match (a late spectator gets it from the start) and passes it to everyone
/// who isn't fighting; their PleaseResyncManager plays it back (NetsuSpectatorSession) a moment behind.
/// Ending a fight keeps every connection: everyone goes back to the lobby for the next match.
///
/// The board (Oct 24 late): https://ntfy.sh, a free public message board (no account). A lobby number is
/// the topic LobbyTopicPrefix + number; the host posts {"t":"host", its addresses} there (again every 4
/// minutes while there's room in the lobby), a joiner reads the last 10 minutes and posts {"t":"join", its address},
/// the host listens to the topic and calls that address; leaving posts {"t":"closed"}. Anyone who knows a number
/// can read what's posted under it (the addresses: the same thing the long code holds). NETSU_LOBBY_SERVER
/// (environment) points the game at another ntfy server (your own, or a test one).
/// </summary>
public partial class NetsuOnline : Node
{
	public const int DefaultPort = 7777;

	/// <summary>Everyone needs the same game: this goes into the connection request (LiteNetLib key).
	/// (2 = group lobbies, Oct 25: a copy of the game from before can't join, and says so.
	/// 3 = Oct 25 evening: Big Bang Crash / Crimson Waltz keep new values in the saved match.)</summary>
	public const string ProtocolVersion = "netsu-vs-online-3";

	/// <summary>What the connection request really carries: the version and which changes the frame data
	/// spreadsheets make (NetsuFrameData.OnlineSignature; "fd0" = none), worked out when a lobby is opened or joined.
	/// Two copies with different spreadsheets would play different games, so they can't connect.</summary>
	public static string ConnectKey { get; private set; } = ProtocolVersion + "|fd0";

	private static void RefreshKey()
	{
		string fd = "fd0";
		try
		{
			fd = SakugaEngine.Game.NetsuFrameData.OnlineSignature();
		}
		catch (Exception ex)
		{
			GD.PushWarning("Frame data signature: " + ex.Message);
		}
		ConnectKey = ProtocolVersion + "|" + fd;
	}

	/// <summary>null when their key is ours, else what to tell the player.</summary>
	private static string KeyProblem(string theirs, string who)
	{
		if (theirs == ConnectKey)
		{
			return null;
		}
		string version = theirs != null && theirs.Contains('|') ? theirs.Substring(0, theirs.IndexOf('|')) : theirs;
		if (version == ProtocolVersion)
		{
			return who + " different frame data (the spreadsheets in data/frame_data). Everyone needs the same spreadsheets.";
		}
		return who + " a different version of the game. Everyone needs the same version.";
	}

	/// <summary>Players in one lobby, the host included.</summary>
	public const int MaxMembers = 8;

	[Signal] public delegate void StatusChangedEventHandler(string text);
	[Signal] public delegate void CodeReadyEventHandler(string code, string lanCode, string note);
	[Signal] public delegate void ReplyCodeReadyEventHandler(string code);
	[Signal] public delegate void ConnectedEventHandler(bool host);
	[Signal] public delegate void DisconnectedEventHandler(string reason);
	[Signal] public delegate void MessageReceivedEventHandler(Godot.Collections.Dictionary message);
	[Signal] public delegate void MemberJoinedEventHandler(int id);
	[Signal] public delegate void MemberLeftEventHandler(int id, string reason);

	public static NetsuOnline Instance { get; private set; }

	public bool IsHost { get; private set; }
	public bool IsActive => _net != null && _net.IsRunning;

	/// <summary>A player: connected to the host and welcomed. The host: at least one player is in.</summary>
	public bool IsConnected => IsHost ? _members.Count > 0 : (_peer != null && _peer.ConnectionState == ConnectionState.Connected && MyId > 0);

	/// <summary>In a lobby: the host's is open, or this player is in one.</summary>
	public bool InLobby => IsHost ? IsActive : IsConnected;

	/// <summary>0 = the host; a player's id comes with the host's welcome (-1 until then).</summary>
	public int MyId { get; private set; } = -1;

	/// <summary>Host: the players in the lobby (not counting the host).</summary>
	public int MemberCount => _members.Count;

	public int LocalPort => _net != null ? _net.LocalPort : 0;

	/// <summary>A player: its ping to the host (ms). The host: -1 (see PingOf).</summary>
	public int Ping => !IsHost && _peer != null ? _peer.Ping : -1;
	public string Code { get; private set; } = "";
	public string LanCode { get; private set; } = "";
	public string ReplyCode { get; private set; } = "";
	public string LastStatus { get; private set; } = "";

	/// <summary>Host: the address code (12 letters / numbers): the backup for the 5-digit code, or the code
	/// itself when the board couldn't be reached.</summary>
	public string LongCode { get; private set; } = "";

	/// <summary>Host: Code is a 5-digit number on the board (not the long code).</summary>
	public bool HasLobbyNumber => _ownTopic != null;

	private NetManager _net;
	private Listener _listener;
	private NetPeer _peer;                     // a player: the host
	private readonly ConcurrentQueue<Action> _main = new ConcurrentQueue<Action>();
	private readonly List<(uint size, uint deviceId, DeviceMessage message)> _game = new List<(uint, uint, DeviceMessage)>();
	private bool _sessionOpen;

	// host: the players (id <-> connection; a new connection is in once it says hello)
	private readonly Dictionary<int, NetPeer> _members = new Dictionary<int, NetPeer>();
	private readonly Dictionary<NetPeer, int> _memberOf = new Dictionary<NetPeer, int>();
	private readonly Dictionary<int, string> _memberNonce = new Dictionary<int, string>();
	private int _nextMemberId = 1;
	private string _myNonce = "";

	// the match being fought: its number and the two players' ids (device 0 = p1, 1 = p2)
	private int _matchId;
	private int _matchP1 = -1;
	private int _matchP2 = -1;
	private bool _matchRunning;

	// the spectator streams of the last few matches: frame -> both players' inputs (frames start at 1). Player 1's
	// computer sends its match's; the host keeps each whole (a late spectator gets it from the start); everyone
	// keeps what they're sent. A match's stream outlives the next match starting (a spectator a moment behind
	// still needs the end of the last one).
	private sealed class MatchStream
	{
		public int P1, P2;
		public readonly List<byte[]> Frames = new List<byte[]>();   // index = frame - 1
	}
	private readonly Dictionary<int, MatchStream> _streams = new Dictionary<int, MatchStream>();
	private const int StreamsKept = 3;

	// testing: NETSU_ONLINE_LAG="ms[,jitter ms[,loss %]]" holds back (and drops some of) the fight packets this
	// computer receives, to try the rollback with a bad connection on one machine or a LAN
	private readonly int _lagMs, _lagJitterMs, _lossPercent;
	private readonly List<(long due, uint size, uint device, DeviceMessage message)> _held = new List<(long, uint, uint, DeviceMessage)>();
	private readonly Random _lagRng = new Random();

	public NetsuOnline()
	{
		string lag = System.Environment.GetEnvironmentVariable("NETSU_ONLINE_LAG");
		if (!string.IsNullOrEmpty(lag))
		{
			string[] p = lag.Split(',');
			int.TryParse(p[0], out _lagMs);
			if (p.Length > 1) int.TryParse(p[1], out _lagJitterMs);
			if (p.Length > 2) int.TryParse(p[2], out _lossPercent);
		}
	}

	// joining / punching: a player calls the host (_target / _target2); the host calls players whose address came
	// from the board or a reply code (_calls), all of them at the same time
	private IPEndPoint _target;
	private IPEndPoint _target2;     // a second address called at the same time (the host's LAN address)
	private double _connectTimer;
	private double _connectFor;
	private bool _joinFailedShown;

	private sealed class Call
	{
		public IPEndPoint A, B;
		public double Timer, For;
		public bool FromBoard;
		public string Nonce = "";   // the joiner's (its hello says it too: in = done)
	}
	private readonly List<Call> _calls = new List<Call>();

	// the board (lobby numbers)
	private string _ownTopic;        // host: the topic of our number
	private string _hostNonce = "";
	private string _hostPayload = "";
	private bool _claiming;
	private double _heartbeat;
	private System.Threading.CancellationTokenSource _listenCts;
	private string _joinTopic;       // joiner: the lobby we looked up
	private string _joinNumber = "";
	private bool _lookupDone;
	private bool _joinPosted;
	private bool _joinPostOk;
	private IPEndPoint _replyEndpoint;   // joiner: our internet address (STUN)

	// public address discovery
	private IPEndPoint _publicEndpoint;
	private IPEndPoint _lanEndpoint;
	private bool _upnpDone;
	private bool _stunDone;
	private bool _upnpMapped;
	private int _upnpPort;
	private string _note = "";
	private byte[] _stunTx;
	private readonly List<IPEndPoint> _stunServers = new List<IPEndPoint>();
	private int _stunIndex;
	private double _stunTimer;
	private int _generation;   // bumps on Leave: late results from old threads are dropped

	private static readonly string[] StunHosts = { "stun.l.google.com:19302", "stun1.l.google.com:19302", "stun.cloudflare.com:3478" };

	public override void _Ready()
	{
		Instance = this;
		ProcessMode = ProcessModeEnum.Always;
	}

	public override void _ExitTree()
	{
		Leave();
		if (Instance == this)
		{
			Instance = null;
		}
	}

	// --- lobby ------------------------------------------------------------------------------

	/// <summary>Opens a lobby. Returns false when no port in port..port+9 could be opened.</summary>
	public bool Host(int port = DefaultPort)
	{
		Leave();
		IsHost = true;
		MyId = 0;
		if (!StartNet(port <= 0 ? DefaultPort : port, 10))
		{
			Status("Couldn't open a network port (" + port + "). Is another copy of the game running?");
			return false;
		}
		Status("Opening the lobby...");
		FindAddresses(true);
		return true;
	}

	/// <summary>Connects to a lobby (a 5-digit number, a long code, or "address:port"). Returns false when the
	/// code can't be read.</summary>
	public bool Join(string code)
	{
		string number = LobbyNumber(code);
		if (number != null)
		{
			return JoinNumber(number);
		}
		IPEndPoint target = ParseCode(code);
		if (target == null)
		{
			Status("That code doesn't look right. Check it and try again.");
			return false;
		}
		Leave();
		IsHost = false;
		if (!StartNet(0, 1))
		{
			Status("Couldn't open a network port.");
			return false;
		}
		_target = target;
		_connectFor = 9.0;
		_connectTimer = 0.0;
		_joinFailedShown = false;
		_myNonce = NewNonce();
		Status("Connecting to " + Describe(target) + "...");
		_net.Connect(target, ConnectKey);
		FindAddresses(false);
		return true;
	}

	/// <summary>Joining with a lobby number: look it up on the board, then call the address posted there (and the
	/// host's LAN address, for players on the same network); our own address goes on the board for the host.</summary>
	private bool JoinNumber(string number)
	{
		Leave();
		IsHost = false;
		if (!StartNet(0, 1))
		{
			Status("Couldn't open a network port.");
			return false;
		}
		_joinNumber = number;
		_joinTopic = LobbyTopicPrefix + number;
		_myNonce = NewNonce();
		_lookupDone = false;
		_joinPosted = false;
		_joinPostOk = false;
		_joinFailedShown = false;
		Status("Looking up lobby " + number + "...");
		FindAddresses(false);   // our internet address (STUN), for the host to call
		int gen = _generation;
		string topic = _joinTopic;
		Task.Run(async () =>
		{
			List<BoardPost> posts = await BoardPoll(topic, "10m");
			Post(gen, () => OnLookup(posts));
		});
		return true;
	}

	private void OnLookup(List<BoardPost> posts)
	{
		if (_net == null || IsHost)
		{
			return;
		}
		string number = _joinNumber;
		if (posts == null)
		{
			JoinFailed("Couldn't reach the lobby-code service (ntfy.sh). Ask the host for their backup code (S on their screen) and type that instead.");
			return;
		}
		BoardPost host = LatestHost(posts);
		if (host == null)
		{
			JoinFailed("No lobby with the code " + number + ". Check the number with the host (a lobby closes when its screen is left).");
			return;
		}
		string problem = KeyProblem(host.Get("v"), "Lobby " + number + " is on");
		if (problem != null)
		{
			JoinFailed(problem);
			return;
		}
		IPEndPoint pub = ParseEndpoint(host.Get("pub"));
		IPEndPoint lan = ParseEndpoint(host.Get("lan"));
		_target = pub ?? lan;
		_target2 = pub != null && lan != null && !lan.Equals(pub) ? lan : null;
		if (_target == null)
		{
			JoinFailed("Lobby " + number + " didn't post an address that can be read.");
			return;
		}
		_lookupDone = true;
		_connectFor = 20.0;
		_connectTimer = 0.0;
		Status("Connecting to lobby " + number + "...");
		_net.Connect(_target, ConnectKey);
		if (_target2 != null)
		{
			_net.Connect(_target2, ConnectKey);
		}
		MaybeSendJoin();
	}

	private void JoinFailed(string text)
	{
		Leave();
		Status(text);
		EmitSignal(SignalName.Disconnected, text);
	}

	/// <summary>Joiner: once the lobby is found and our own address is known (or can't be), post it for the host.</summary>
	private void MaybeSendJoin()
	{
		if (IsHost || _joinTopic == null || _joinPosted || !_lookupDone || !_stunDone || _net == null || _peer != null)
		{
			return;
		}
		_joinPosted = true;
		var data = new Dictionary<string, string>
		{
			["t"] = "join",
			["v"] = ConnectKey,
			["pub"] = _replyEndpoint != null ? Describe(_replyEndpoint) : "",
			["lan"] = _lanEndpoint != null ? Describe(_lanEndpoint) : "",
			["n"] = _myNonce,
		};
		int gen = _generation;
		string topic = _joinTopic;
		string body = System.Text.Json.JsonSerializer.Serialize(data);
		Task.Run(async () =>
		{
			string id = await BoardPublish(topic, body);
			Post(gen, () => _joinPostOk = id != null);
		});
	}

	/// <summary>Host side: a joiner's reply code. Both computers now call each other for a while (hole punching).</summary>
	public bool AcceptReply(string code)
	{
		IPEndPoint target = ParseCode(code);
		if (target == null || !IsActive || !IsHost)
		{
			Status("That reply code doesn't look right.");
			return false;
		}
		if (LobbyFull)
		{
			Status("The lobby is full (" + MaxMembers + " players).");
			return false;
		}
		AddCall(target, null, 30.0, false, "");
		Status("Calling the player at " + Describe(target) + "...");
		return true;
	}

	private bool LobbyFull => _members.Count >= MaxMembers - 1;

	private void AddCall(IPEndPoint a, IPEndPoint b, double seconds, bool fromBoard, string nonce)
	{
		if (nonce != "" && _memberNonce.ContainsValue(nonce))
		{
			return;   // already in
		}
		foreach (Call c in _calls)
		{
			if (a.Equals(c.A) || a.Equals(c.B))
			{
				c.Timer = 0.0;   // the same player again: call it a while longer
				return;
			}
		}
		_calls.Add(new Call { A = a, B = b, For = seconds, FromBoard = fromBoard, Nonce = nonce ?? "" });
		_net.Connect(a, ConnectKey);
		if (b != null)
		{
			_net.Connect(b, ConnectKey);
		}
	}

	/// <summary>Host: a joiner posted its address on the board: call it (the joiner is calling us too).</summary>
	private void OnJoinPost(BoardPost p)
	{
		if (!IsHost || _net == null || p.Get("t") != "join")
		{
			return;
		}
		string problem = KeyProblem(p.Get("v"), "Someone tried to join with");
		if (problem != null)
		{
			Status(problem);
			return;
		}
		if (LobbyFull)
		{
			return;
		}
		IPEndPoint pub = ParseEndpoint(p.Get("pub"));
		IPEndPoint lan = ParseEndpoint(p.Get("lan"));
		// same internet address as ours: they're on our network, where their LAN address is the one that works
		bool sameNetwork = pub != null && _publicEndpoint != null && pub.Address.Equals(_publicEndpoint.Address);
		IPEndPoint a = pub ?? lan;
		IPEndPoint b = (sameNetwork || pub == null) && lan != null && !lan.Equals(a) ? lan : null;
		if (a == null)
		{
			return;
		}
		Status("A player is joining...");
		AddCall(a, b, 30.0, true, p.Get("n"));
	}

	/// <summary>Closes the lobby / connection.</summary>
	public void Leave()
	{
		_generation++;
		_sessionOpen = false;
		_game.Clear();
		_held.Clear();
		_target = null;
		_target2 = null;
		_calls.Clear();
		_listenCts?.Cancel();
		_listenCts = null;
		if (_ownTopic != null)
		{
			// the number is free again (best effort: if this never arrives, it goes stale in 10 minutes)
			string topic = _ownTopic;
			string body = System.Text.Json.JsonSerializer.Serialize(new Dictionary<string, string> { ["t"] = "closed", ["n"] = _hostNonce });
			Task.Run(async () => await BoardPublish(topic, body));
			_ownTopic = null;
		}
		_claiming = false;
		_hostPayload = "";
		_joinTopic = null;
		_joinNumber = "";
		_lookupDone = false;
		_joinPosted = false;
		_joinPostOk = false;
		_replyEndpoint = null;
		LongCode = "";
		if (_net != null)
		{
			try
			{
				_net.DisconnectAll();
				_net.Stop();
			}
			catch (Exception e)
			{
				GD.PushWarning("NetsuOnline: " + e.Message);
			}
			_net = null;
		}
		_peer = null;
		_members.Clear();
		_memberOf.Clear();
		_memberNonce.Clear();
		_nextMemberId = 1;
		_myNonce = "";
		MyId = -1;
		_matchId = 0;
		_matchP1 = -1;
		_matchP2 = -1;
		_matchRunning = false;
		_streams.Clear();
		if (_upnpMapped)
		{
			int port = _upnpPort;
			Task.Run(() =>
			{
				try
				{
					Upnp upnp = new Upnp();
					if (upnp.Discover(1500, 2, "InternetGatewayDevice") == (int)Upnp.UpnpResult.Success)
					{
						upnp.DeletePortMapping(port, "UDP");
					}
				}
				catch (Exception)
				{
				}
			});
			_upnpMapped = false;
		}
		Code = "";
		LanCode = "";
		ReplyCode = "";
		_publicEndpoint = null;
		_lanEndpoint = null;
	}

	/// <summary>A lobby message (reliable, in order): a player's goes to the host, the host's to every player.</summary>
	public bool Send(Godot.Collections.Dictionary message)
	{
		byte[] packet = Packet('L', Encoding.UTF8.GetBytes(Json.Stringify(message)));
		if (IsHost)
		{
			foreach (NetPeer p in _members.Values)
			{
				p.Send(packet, DeliveryMethod.ReliableOrdered);
			}
			return _members.Count > 0;
		}
		if (!IsConnected)
		{
			return false;
		}
		_peer.Send(packet, DeliveryMethod.ReliableOrdered);
		return true;
	}

	/// <summary>The host: a lobby message to one player (id). A player: only the host (0) can be sent to.</summary>
	public bool SendTo(int id, Godot.Collections.Dictionary message)
	{
		byte[] packet = Packet('L', Encoding.UTF8.GetBytes(Json.Stringify(message)));
		if (IsHost)
		{
			if (!_members.TryGetValue(id, out NetPeer p))
			{
				return false;
			}
			p.Send(packet, DeliveryMethod.ReliableOrdered);
			return true;
		}
		if (id != 0 || !IsConnected)
		{
			return false;
		}
		_peer.Send(packet, DeliveryMethod.ReliableOrdered);
		return true;
	}

	/// <summary>Host: a player's ping (ms), -1 if not in the lobby. A player: id 0 = its ping to the host.</summary>
	public int PingOf(int id)
	{
		if (IsHost)
		{
			return _members.TryGetValue(id, out NetPeer p) ? p.Ping : -1;
		}
		return id == 0 && _peer != null ? _peer.Ping : -1;
	}

	private static byte[] Packet(char tag, byte[] body)
	{
		byte[] packet = new byte[body.Length + 1];
		packet[0] = (byte)tag;
		Buffer.BlockCopy(body, 0, packet, 1, body.Length);
		return packet;
	}

	// --- fights -------------------------------------------------------------------------------

	/// <summary>Everyone: the match `match` is player `p1` (device 0) against `p2` (device 1), by id (the fight's packets
	/// go between those two). Its spectator stream is kept from here.</summary>
	public void SetMatch(int match, int p1, int p2)
	{
		if (match != _matchId)
		{
			_held.Clear();
			_game.Clear();
		}
		_matchId = match;
		_matchP1 = p1;
		_matchP2 = p2;
		_matchRunning = true;
		StreamOf(match, true).P1 = p1;
		_streams[match].P2 = p2;
	}

	/// <summary>A match's stream (made when `make`; the oldest ones are let go).</summary>
	private MatchStream StreamOf(int match, bool make)
	{
		if (_streams.TryGetValue(match, out MatchStream ms) || !make)
		{
			return ms;
		}
		ms = new MatchStream { P1 = -1, P2 = -1 };
		_streams[match] = ms;
		while (_streams.Count > StreamsKept)
		{
			int oldest = int.MaxValue;
			foreach (int k in _streams.Keys)
			{
				oldest = Math.Min(oldest, k);
			}
			_streams.Remove(oldest);
		}
		return ms;
	}

	/// <summary>The match being fought (its number: SetMatch), 0 = none yet.</summary>
	public int MatchId => _matchId;

	/// <summary>This computer's side in the match being fought: 0 / 1, or -1 (not fighting: a spectator).</summary>
	public int MyDevice => !_matchRunning || MyId < 0 ? -1 : (MyId == _matchP1 ? 0 : (MyId == _matchP2 ? 1 : -1));

	/// <summary>PleaseResyncManager: the adapter that carries the fight over the lobby's connections.</summary>
	public SessionAdapter CreateSessionAdapter()
	{
		_game.Clear();
		_held.Clear();
		_sessionOpen = true;
		return new NetsuOnlineAdapter(this);
	}

	internal void EndSession()
	{
		_sessionOpen = false;
		_game.Clear();
		_held.Clear();
	}

	private int MemberOfDevice(uint device) => device == 0 ? _matchP1 : (device == 1 ? _matchP2 : -1);

	internal uint SendGame(uint device, DeviceMessage message)
	{
		int dst = MemberOfDevice(device);
		if (dst < 0 || MyId < 0 || dst == MyId)
		{
			return 0u;
		}
		byte[] body = MessagePackSerializer.Serialize(message);
		byte[] packet = new byte[body.Length + 3];
		packet[0] = (byte)'G';
		packet[1] = (byte)dst;
		packet[2] = (byte)MyId;
		Buffer.BlockCopy(body, 0, packet, 3, body.Length);
		NetPeer to = IsHost ? (_members.TryGetValue(dst, out NetPeer p) ? p : null) : _peer;   // a player: through the host
		if (to == null || to.ConnectionState != ConnectionState.Connected)
		{
			return 0u;
		}
		to.Send(packet, DeliveryMethod.Unreliable);
		return (uint)packet.Length;
	}

	internal List<(uint size, uint deviceId, DeviceMessage message)> TakeGameMessages()
	{
		_net?.PollEvents();
		if (_held.Count > 0)
		{
			long now = (long)Time.GetTicksMsec();
			for (int i = 0; i < _held.Count; i++)
			{
				if (_held[i].due <= now)
				{
					_game.Add((_held[i].size, _held[i].device, _held[i].message));
					_held.RemoveAt(i);
					i--;
				}
			}
		}
		var result = new List<(uint, uint, DeviceMessage)>(_game);
		_game.Clear();
		return result;
	}

	// --- the spectator stream -----------------------------------------------------------------

	/// <summary>Player 1's PleaseResyncManager: the settled inputs of match `match`, frames start..start+count-1 (both
	/// players', `data` = count x the frame's input bytes), in order.</summary>
	public void StreamInputs(int match, int start, byte[] data, int count)
	{
		if (count <= 0 || match <= 0)
		{
			return;
		}
		byte[] body = StreamBody(match, start, data, count);
		if (IsHost)
		{
			OnStream(body, -1);
		}
		else if (IsConnected)
		{
			_peer.Send(Packet('S', body), DeliveryMethod.ReliableOrdered);
		}
	}

	private static byte[] StreamBody(int match, int start, byte[] data, int count)
	{
		byte[] body = new byte[10 + data.Length];
		BitConverter.GetBytes(match).CopyTo(body, 0);
		BitConverter.GetBytes(start).CopyTo(body, 4);
		BitConverter.GetBytes((ushort)count).CopyTo(body, 8);
		Buffer.BlockCopy(data, 0, body, 10, data.Length);
		return body;
	}

	/// <summary>A piece of the stream (from player 1's computer, or the host's own): kept, and the host passes it on
	/// to everyone who isn't fighting.</summary>
	private void OnStream(byte[] body, int from)
	{
		if (body.Length < 10)
		{
			return;
		}
		int match = BitConverter.ToInt32(body, 0);
		int start = BitConverter.ToInt32(body, 4);
		int count = BitConverter.ToUInt16(body, 8);
		if (count <= 0 || (body.Length - 10) % count != 0)
		{
			return;
		}
		// the host: only from that match's player 1 (or itself), for a match it set; the others: what the host sends
		MatchStream ms = StreamOf(match, !IsHost);
		if (ms == null || (IsHost && from >= 0 && from != ms.P1))
		{
			return;
		}
		int size = (body.Length - 10) / count;
		for (int i = 0; i < count; i++)
		{
			int frame = start + i;
			if (frame != ms.Frames.Count + 1)
			{
				continue;   // already have it (or a gap: can't happen on a reliable, ordered channel)
			}
			byte[] input = new byte[size];
			Buffer.BlockCopy(body, 10 + i * size, input, 0, size);
			ms.Frames.Add(input);
		}
		if (IsHost)
		{
			byte[] packet = Packet('S', body);
			foreach (var kv in _members)
			{
				if (kv.Key != ms.P1 && kv.Key != ms.P2 && kv.Key != from)
				{
					kv.Value.Send(packet, DeliveryMethod.ReliableOrdered);
				}
			}
		}
	}

	/// <summary>Host: everything streamed of the match so far, to one player who came in during it (after the room
	/// that tells them about the match: online_room.gd), so they can watch it from the start.</summary>
	public void SendStreamTo(int id)
	{
		MatchStream ms = StreamOf(_matchId, false);
		if (!IsHost || ms == null || !_members.TryGetValue(id, out NetPeer p) || ms.Frames.Count == 0 || id == ms.P1 || id == ms.P2)
		{
			return;
		}
		const int chunk = 300;
		for (int s0 = 0; s0 < ms.Frames.Count; s0 += chunk)
		{
			int n = Math.Min(chunk, ms.Frames.Count - s0);
			int size = ms.Frames[s0].Length;
			byte[] data = new byte[n * size];
			for (int i = 0; i < n; i++)
			{
				Buffer.BlockCopy(ms.Frames[s0 + i], 0, data, i * size, size);
			}
			p.Send(Packet('S', StreamBody(_matchId, s0 + 1, data, n)), DeliveryMethod.ReliableOrdered);
		}
	}

	/// <summary>How many frames of a match's stream are here (1..n, in order; 0 = none).</summary>
	public int StreamFrames(int match)
	{
		MatchStream ms = StreamOf(match, false);
		return ms != null ? ms.Frames.Count : 0;
	}

	/// <summary>Both players' inputs of a frame of a match's stream (frames start at 1).</summary>
	public bool TryGetStreamInput(int match, int frame, out byte[] input)
	{
		MatchStream ms = StreamOf(match, false);
		if (ms != null && frame >= 1 && frame <= ms.Frames.Count)
		{
			input = ms.Frames[frame - 1];
			return true;
		}
		input = null;
		return false;
	}

	// --- every frame --------------------------------------------------------------------------

	public override void _PhysicsProcess(double delta)
	{
		_net?.PollEvents();   // the host passes fight packets on: the sooner the better
	}

	public override void _Process(double delta)
	{
		while (_main.TryDequeue(out Action work))
		{
			work();
		}
		if (_net == null)
		{
			return;
		}
		_net.PollEvents();
		if (_net == null)
		{
			return;   // a disconnect event closed it
		}
		if (!IsHost && _target != null && _peer == null)
		{
			// a player: keep calling the host until connected (both sides punching through)
			_connectTimer += delta;
			if (_connectTimer < _connectFor)
			{
				if ((int)(_connectTimer * 2.0) != (int)((_connectTimer - delta) * 2.0))
				{
					_net.Connect(_target, ConnectKey);   // every half second (LiteNetLib drops repeats)
					if (_target2 != null)
					{
						_net.Connect(_target2, ConnectKey);
					}
				}
			}
			else if (!_joinFailedShown)
			{
				_joinFailedShown = true;
				if (_joinTopic != null && _joinPostOk)
				{
					// the host has our address and is calling too: give it a little longer
					_connectFor = _connectTimer + 25.0;
					Status("Still trying to reach the host... If it doesn't connect, their router is blocking it: the host can forward UDP port "
						+ _target.Port + " on their router (or turn on UPnP), then open a new lobby.");
				}
				else if (ReplyCode != "")
				{
					_connectFor = _connectTimer + 60.0;   // keep trying while the host enters the reply code
					Status("Couldn't reach the host directly. Send them your REPLY CODE: " + ReplyCode + " (keep this screen open)");
					EmitSignal(SignalName.ReplyCodeReady, ReplyCode);
				}
				else
				{
					_connectFor = _connectTimer + 60.0;
					Status("Couldn't reach the host. Check the code, or ask them to forward UDP port " + _target.Port + " on their router.");
				}
			}
		}
		if (IsHost)
		{
			// the host: keep calling each player that's joining until it's in, or give up on it
			for (int i = _calls.Count - 1; i >= 0; i--)
			{
				Call c = _calls[i];
				c.Timer += delta;
				if (c.Timer >= c.For)
				{
					_calls.RemoveAt(i);
					if (c.Nonce != "" && _memberNonce.ContainsValue(c.Nonce))
					{
						continue;   // they got in another way (a different address than the one they posted)
					}
					Status(c.FromBoard
						? "Couldn't connect to a player who tried to join: a router is blocking it. Forward UDP port " + LocalPort + " on your router (or turn on UPnP)."
						: "The player didn't answer. Check the reply code and try again.");
					continue;
				}
				if ((int)(c.Timer * 2.0) != (int)((c.Timer - delta) * 2.0))
				{
					_net.Connect(c.A, ConnectKey);
					if (c.B != null)
					{
						_net.Connect(c.B, ConnectKey);
					}
				}
			}
			// the number stays fresh on the board while there's room (joiners only trust the last 10 minutes)
			if (_ownTopic != null && !LobbyFull)
			{
				_heartbeat += delta;
				if (_heartbeat >= 240.0)
				{
					_heartbeat = 0.0;
					string topic = _ownTopic, body = _hostPayload;
					Task.Run(async () => await BoardPublish(topic, body));
				}
			}
		}
		StunTick(delta);
	}

	// --- connection events (LiteNetLib, on the main thread through PollEvents) ----------------

	private sealed class Listener : INetEventListener
	{
		private readonly NetsuOnline _o;

		public Listener(NetsuOnline o)
		{
			_o = o;
		}

		public void OnPeerConnected(NetPeer peer)
		{
			_o.PeerConnected(peer);
		}

		public void OnPeerDisconnected(NetPeer peer, DisconnectInfo info)
		{
			_o.PeerDisconnected(peer, info);
		}

		public void OnNetworkError(IPEndPoint endPoint, SocketError socketError)
		{
		}

		public void OnNetworkReceive(NetPeer peer, NetPacketReader reader, byte channel, DeliveryMethod deliveryMethod)
		{
			_o.Receive(peer, reader.GetRemainingBytes());
			reader.Recycle();
		}

		public void OnNetworkReceiveUnconnected(IPEndPoint remoteEndPoint, NetPacketReader reader, UnconnectedMessageType messageType)
		{
		}

		public void OnNetworkLatencyUpdate(NetPeer peer, int latency)
		{
		}

		public void OnConnectionRequest(ConnectionRequest request)
		{
			// the host: up to MaxMembers in the lobby; a player only takes the host's call; a different game version
			// is turned away
			bool full = _o.IsHost ? _o.LobbyFull : (_o._peer != null && _o._peer.ConnectionState == ConnectionState.Connected);
			if (full)
			{
				request.Reject(Encoding.UTF8.GetBytes("full"));
				return;
			}
			if (request.AcceptIfKey(ConnectKey) == null)
			{
				_o.Status("Someone tried to join with a different version of the game or different frame data.");
			}
		}
	}

	private void PeerConnected(NetPeer peer)
	{
		if (IsHost)
		{
			// a new connection: in once it says hello (a player calling on two addresses at once connects twice:
			// the second hello is turned away)
			if (_memberOf.ContainsKey(peer))
			{
				return;
			}
			for (int i = _calls.Count - 1; i >= 0; i--)
			{
				if (peer.Equals(_calls[i].A) || peer.Equals(_calls[i].B))
				{
					_calls.RemoveAt(i);
				}
			}
			return;
		}
		if (_peer != null && _peer != peer && _peer.ConnectionState == ConnectionState.Connected)
		{
			peer.Disconnect();
			return;
		}
		_peer = peer;
		_target = null;
		_target2 = null;
		if (_myNonce == "")
		{
			_myNonce = NewNonce();
		}
		peer.Send(Packet('H', Encoding.UTF8.GetBytes(_myNonce)), DeliveryMethod.ReliableOrdered);
		Status("Connected. Joining the lobby...");
	}

	private void PeerDisconnected(NetPeer peer, DisconnectInfo info)
	{
		if (IsHost)
		{
			if (!_memberOf.TryGetValue(peer, out int id))
			{
				return;   // a spare connection from punching, or one that never said hello
			}
			_memberOf.Remove(peer);
			_members.Remove(id);
			_memberNonce.Remove(id);
			string why = info.Reason switch
			{
				DisconnectReason.RemoteConnectionClose => "left",
				DisconnectReason.DisconnectPeerCalled => "was removed",
				DisconnectReason.Timeout => "lost the connection",
				_ => "lost the connection",
			};
			EmitSignal(SignalName.MemberLeft, id, why);
			return;
		}
		if (_peer != null && peer != _peer)
		{
			return;   // a spare connection attempt from punching
		}
		bool wasConnected = _peer != null;
		_peer = null;
		_sessionOpen = false;
		_game.Clear();
		if (!wasConnected)
		{
			if (info.Reason == DisconnectReason.ConnectionRejected)
			{
				string why = info.AdditionalData != null && info.AdditionalData.AvailableBytes > 0 ? info.AdditionalData.GetString() : "";
				_target = null;
				_target2 = null;
				string text = why == "full" ? "That lobby is full (" + MaxMembers + " players)." : "The lobby turned the connection down (different game version?).";
				Status(text);
				EmitSignal(SignalName.Disconnected, text);
			}
			return;   // a connection attempt that didn't get through: the retry loop goes on
		}
		string reason = info.Reason switch
		{
			DisconnectReason.RemoteConnectionClose => "The host closed the lobby.",
			DisconnectReason.DisconnectPeerCalled => "Disconnected.",
			DisconnectReason.Timeout => "The connection to the host timed out.",
			_ => "The connection was lost (" + info.Reason + ").",
		};
		MyId = -1;
		Status(reason);
		EmitSignal(SignalName.Disconnected, reason);
	}

	private void Receive(NetPeer peer, byte[] data)
	{
		if (data.Length < 1)
		{
			return;
		}
		char tag = (char)data[0];
		if (IsHost)
		{
			if (tag == 'H')
			{
				Hello(peer, Encoding.UTF8.GetString(data, 1, data.Length - 1));
				return;
			}
			if (!_memberOf.TryGetValue(peer, out int from))
			{
				return;   // not in yet
			}
			switch (tag)
			{
			case 'L':
				Variant parsed = Json.ParseString(Encoding.UTF8.GetString(data, 1, data.Length - 1));
				if (parsed.VariantType == Variant.Type.Dictionary)
				{
					Godot.Collections.Dictionary m = parsed.AsGodotDictionary();
					m["from"] = from;
					EmitSignal(SignalName.MessageReceived, m);
				}
				break;
			case 'G':
				if (data.Length < 4 || data[2] != from)
				{
					return;
				}
				if (data[1] == 0)
				{
					DeliverGame(data, from);
				}
				else if (_members.TryGetValue(data[1], out NetPeer to) && (from == _matchP1 || from == _matchP2))
				{
					to.Send(data, DeliveryMethod.Unreliable);   // between two players: passed on as it is
				}
				break;
			case 'S':
				OnStream(Slice(data), from);
				break;
			}
			return;
		}
		if (peer != _peer)
		{
			return;
		}
		switch (tag)
		{
		case 'W':
			if (data.Length >= 5)
			{
				MyId = BitConverter.ToInt32(data, 1);
				Status("Joined the lobby!");
				EmitSignal(SignalName.Connected, false);
			}
			break;
		case 'L':
			Variant parsed = Json.ParseString(Encoding.UTF8.GetString(data, 1, data.Length - 1));
			if (parsed.VariantType == Variant.Type.Dictionary)
			{
				EmitSignal(SignalName.MessageReceived, parsed.AsGodotDictionary());
			}
			break;
		case 'G':
			if (data.Length >= 4 && data[1] == MyId)
			{
				DeliverGame(data, data[2]);
			}
			break;
		case 'S':
			OnStream(Slice(data), 0);
			break;
		}
	}

	private static byte[] Slice(byte[] data)
	{
		byte[] body = new byte[data.Length - 1];
		Buffer.BlockCopy(data, 1, body, 0, body.Length);
		return body;
	}

	/// <summary>Host: a new connection said hello: a new player (an id, the welcome) or a second connection of one
	/// that's in already (closed).</summary>
	private void Hello(NetPeer peer, string nonce)
	{
		if (_memberOf.ContainsKey(peer))
		{
			return;
		}
		foreach (var kv in _memberNonce)
		{
			if (kv.Value == nonce && nonce != "")
			{
				peer.Disconnect();   // the same player on its other address
				return;
			}
		}
		if (LobbyFull)
		{
			peer.Disconnect(Encoding.UTF8.GetBytes("full"));
			return;
		}
		int id = _nextMemberId++;
		_members[id] = peer;
		_memberOf[peer] = id;
		_memberNonce[id] = nonce;
		_calls.RemoveAll(c => c.Nonce != "" && c.Nonce == nonce);   // in: stop calling them
		peer.Send(Packet('W', BitConverter.GetBytes(id)), DeliveryMethod.ReliableOrdered);
		Status("A player joined!");
		EmitSignal(SignalName.MemberJoined, id);
		if (_members.Count == 1)
		{
			EmitSignal(SignalName.Connected, true);
		}
	}

	/// <summary>A fight packet for this computer, from player `from` (its device: 0 = p1, 1 = p2).</summary>
	private void DeliverGame(byte[] data, int from)
	{
		if (!_sessionOpen || _game.Count > 1024)
		{
			return;
		}
		uint device = from == _matchP1 ? 0u : (from == _matchP2 ? 1u : 99u);
		if (device == 99u)
		{
			return;
		}
		try
		{
			DeviceMessage message = MessagePackSerializer.Deserialize<DeviceMessage>(new ReadOnlyMemory<byte>(data, 3, data.Length - 3));
			if (_lagMs > 0 || _lossPercent > 0)
			{
				if (_lossPercent > 0 && _lagRng.Next(100) < _lossPercent)
				{
					return;
				}
				long due = (long)Time.GetTicksMsec() + _lagMs + (_lagJitterMs > 0 ? _lagRng.Next(_lagJitterMs + 1) : 0);
				_held.Add((due, (uint)data.Length, device, message));
				return;
			}
			_game.Add(((uint)data.Length, device, message));
		}
		catch (Exception e)
		{
			GD.PushWarning("NetsuOnline: bad fight packet: " + e.Message);
		}
	}

	// --- setup ----------------------------------------------------------------------------------

	private bool StartNet(int port, int tries)
	{
		RefreshKey();   // the spreadsheets as they are now
		_listener = new Listener(this);
		_net = new NetManager(_listener)
		{
			AutoRecycle = false,
			DisconnectTimeout = 8000,
			ReconnectDelay = 400,
			MaxConnectAttempts = 15,
			IPv6Enabled = false,
		};
		_net.NetsuRawReceive = OnRawPacket;
		for (int i = 0; i < Math.Max(1, tries); i++)
		{
			if (_net.Start(port == 0 ? 0 : port + i))
			{
				return true;
			}
		}
		_net = null;
		return false;
	}

	private void Status(string text)
	{
		LastStatus = text;
		GD.Print("[online] " + text);
		EmitSignal(SignalName.StatusChanged, text);
	}

	private void Post(int generation, Action work)
	{
		_main.Enqueue(() =>
		{
			if (generation == _generation)
			{
				work();
			}
		});
	}

	/// <summary>The LAN address now; UPnP (host only) and STUN in the background; the code once they're done.</summary>
	private void FindAddresses(bool host)
	{
		int gen = _generation;
		int port = _net.LocalPort;
		IPAddress lan = LanAddress();
		_lanEndpoint = new IPEndPoint(lan ?? IPAddress.Loopback, port);
		LanCode = Encode(_lanEndpoint);
		_upnpDone = !host;
		_stunDone = false;
		_note = "";
		if (host)
		{
			Task.Run(() =>
			{
				string external = "";
				bool mapped = false;
				try
				{
					Upnp upnp = new Upnp();
					if (upnp.Discover(2000, 2, "InternetGatewayDevice") == (int)Upnp.UpnpResult.Success && upnp.GetGateway() != null && upnp.GetGateway().IsValidGateway())
					{
						mapped = upnp.AddPortMapping(port, port, "Netsu VS lobby", "UDP", 0) == (int)Upnp.UpnpResult.Success;
						external = upnp.QueryExternalAddress();
					}
				}
				catch (Exception)
				{
				}
				Post(gen, () =>
				{
					_upnpDone = true;
					_upnpMapped = mapped;
					_upnpPort = port;
					if (mapped && IPAddress.TryParse(external, out IPAddress ip) && ip.AddressFamily == AddressFamily.InterNetwork && !IsPrivate(ip))
					{
						_publicEndpoint = new IPEndPoint(ip, port);
						_note = "Router port opened automatically (UPnP).";
					}
					MaybeFinishCode();
				});
			});
		}
		// STUN servers: resolved in the background, asked from the game's own socket (same address the opponent sees)
		Task.Run(() =>
		{
			var servers = new List<IPEndPoint>();
			foreach (string hp in StunHosts)
			{
				try
				{
					string[] parts = hp.Split(':');
					foreach (IPAddress a in Dns.GetHostAddresses(parts[0]))
					{
						if (a.AddressFamily == AddressFamily.InterNetwork)
						{
							servers.Add(new IPEndPoint(a, int.Parse(parts[1])));
							break;
						}
					}
				}
				catch (Exception)
				{
				}
			}
			Post(gen, () =>
			{
				_stunServers.Clear();
				_stunServers.AddRange(servers);
				_stunIndex = 0;
				_stunTimer = 0.0;
				if (_stunServers.Count == 0)
				{
					_stunDone = true;
					MaybeFinishCode();
				}
				else
				{
					SendStun();
				}
			});
		});
	}

	private void SendStun()
	{
		if (_net == null || _stunIndex >= _stunServers.Count)
		{
			_stunDone = true;
			MaybeFinishCode();
			return;
		}
		IPEndPoint server = _stunServers[_stunIndex];
		_stunTx = new byte[12];
		System.Security.Cryptography.RandomNumberGenerator.Fill(_stunTx);
		byte[] request = new byte[20];
		request[1] = 0x01;                       // Binding request, no attributes
		request[4] = 0x21; request[5] = 0x12; request[6] = 0xA4; request[7] = 0x42;   // magic cookie
		Buffer.BlockCopy(_stunTx, 0, request, 8, 12);
		_net.NetsuRawEndpoints[server] = true;
		_net.NetsuSendRaw(request, server);
		_stunTimer = 0.0;
	}

	private void StunTick(double delta)
	{
		if (_stunDone || _stunServers.Count == 0 || _net == null)
		{
			return;
		}
		_stunTimer += delta;
		if (_stunTimer > 1.5)
		{
			_stunIndex++;
			SendStun();
		}
	}

	private void OnRawPacket(IPEndPoint from, byte[] data)
	{
		int gen = _generation;
		Post(gen, () =>
		{
			if (_stunDone || _stunTx == null)
			{
				return;
			}
			IPEndPoint mapped = ParseStun(data, _stunTx);
			if (mapped == null)
			{
				return;
			}
			_stunDone = true;
			if (IsHost)
			{
				if (_publicEndpoint == null)
				{
					_publicEndpoint = mapped;
					_note = mapped.Port == _net.LocalPort
						? "If your opponent can't get in, forward UDP port " + mapped.Port + " on your router, or use their reply code."
						: "Your router changes the port: if your opponent can't get in, use their reply code.";
				}
			}
			else
			{
				ReplyCode = Encode(mapped);
				_replyEndpoint = mapped;
				if (_joinFailedShown && !IsConnected && !(_joinTopic != null && _joinPostOk))
				{
					Status("Couldn't reach the host directly. Send them your REPLY CODE: " + ReplyCode + " (keep this screen open)");
					EmitSignal(SignalName.ReplyCodeReady, ReplyCode);
				}
			}
			MaybeFinishCode();
		});
	}

	/// <summary>Host: once UPnP and STUN are done, a lobby number on the board (the long code if the board can't
	/// be reached). Joiner: posts its address for the host (lobby numbers).</summary>
	private void MaybeFinishCode()
	{
		if (!IsHost)
		{
			MaybeSendJoin();
			return;
		}
		if (Code != "" || _claiming || !_upnpDone || !_stunDone)
		{
			return;
		}
		if (_publicEndpoint != null)
		{
			LongCode = Encode(_publicEndpoint);
		}
		else
		{
			LongCode = LanCode;
			_note = "Couldn't find your internet address: this lobby works on your own network only (or forward UDP port " + LocalPort + ").";
		}
		_claiming = true;
		Status("Getting a lobby code...");
		_hostNonce = NewNonce();
		_hostPayload = System.Text.Json.JsonSerializer.Serialize(new Dictionary<string, string>
		{
			["t"] = "host",
			["v"] = ConnectKey,
			["pub"] = _publicEndpoint != null ? Describe(_publicEndpoint) : "",
			["lan"] = _lanEndpoint != null ? Describe(_lanEndpoint) : "",
			["n"] = _hostNonce,
		});
		int gen = _generation;
		string payload = _hostPayload;
		Task.Run(async () =>
		{
			(string number, string id) claim = await BoardClaim(payload);
			Post(gen, () => FinishCode(claim.number, claim.id));
		});
	}

	private void FinishCode(string number, string postId)
	{
		_claiming = false;
		if (_net == null)
		{
			return;
		}
		bool local = _publicEndpoint == null;
		if (number != null)
		{
			Code = number;
			_ownTopic = LobbyTopicPrefix + number;
			_heartbeat = 0.0;
			GD.Print("[online] lobby code " + number);
			BoardListen(_ownTopic, postId);
			Status(local ? "Lobby open (local network). Waiting for players..." : "Lobby open. Waiting for players...");
			EmitSignal(SignalName.CodeReady, Code, "", _note);
			return;
		}
		Code = LongCode;
		_note = (_note != "" ? _note + "\n" : "") + "Couldn't reach the lobby-code service (ntfy.sh), so this is the long code: it works the same.";
		Status(local ? "Lobby open (local network). Waiting for players..." : "Lobby open. Waiting for players...");
		EmitSignal(SignalName.CodeReady, Code, LanCode, _note);
	}

	// --- the board: lobby numbers on ntfy.sh -----------------------------------------------------

	/// <summary>The public message board the lobby numbers live on (ntfy: https://docs.ntfy.sh).</summary>
	public const string LobbyServerDefault = "https://ntfy.sh";

	/// <summary>A lobby number's topic is this + the number (the prefix keeps us apart from other ntfy users).</summary>
	public const string LobbyTopicPrefix = "netsu-vs-lobby-q7k3-";

	private static string LobbyServer
	{
		get
		{
			string s = System.Environment.GetEnvironmentVariable("NETSU_LOBBY_SERVER");
			return string.IsNullOrWhiteSpace(s) ? LobbyServerDefault : s.Trim().TrimEnd('/');
		}
	}

	private static readonly System.Net.Http.HttpClient BoardHttp = MakeHttp(TimeSpan.FromSeconds(8));
	private static readonly System.Net.Http.HttpClient BoardStreamHttp = MakeHttp(System.Threading.Timeout.InfiniteTimeSpan);

	private static System.Net.Http.HttpClient MakeHttp(TimeSpan timeout)
	{
		var http = new System.Net.Http.HttpClient { Timeout = timeout };
		http.DefaultRequestHeaders.UserAgent.ParseAdd("NetsuVS/1");
		return http;
	}

	/// <summary>One message on the board: its id and the fields we posted (all strings).</summary>
	private sealed class BoardPost
	{
		public string Id = "";
		public Dictionary<string, string> Data = new Dictionary<string, string>();

		public string Get(string key)
		{
			return Data.TryGetValue(key, out string v) ? v : "";
		}
	}

	/// <summary>For the screens (GDScript): the text is a 5-digit lobby number.</summary>
	public bool IsLobbyNumber(string text)
	{
		return LobbyNumber(text) != null;
	}

	/// <summary>"48213" (spaces / dashes allowed) -> the number; anything else (long code, address) -> null.</summary>
	public static string LobbyNumber(string text)
	{
		if (string.IsNullOrWhiteSpace(text))
		{
			return null;
		}
		var sb = new StringBuilder();
		foreach (char c in text.Trim())
		{
			if (c >= '0' && c <= '9')
			{
				sb.Append(c);
			}
			else if (c != ' ' && c != '-')
			{
				return null;
			}
		}
		return sb.Length == 5 ? sb.ToString() : null;
	}

	private static IPEndPoint ParseEndpoint(string text)
	{
		if (string.IsNullOrWhiteSpace(text) || !IPEndPoint.TryParse(text.Trim(), out IPEndPoint ep) || ep.AddressFamily != AddressFamily.InterNetwork || ep.Port == 0)
		{
			return null;
		}
		return ep;
	}

	private static string NewNonce()
	{
		return Convert.ToHexString(System.Security.Cryptography.RandomNumberGenerator.GetBytes(6)).ToLowerInvariant();
	}

	/// <summary>The board's messages on a topic since `since` ("10m", or a message id); null if it can't be reached.</summary>
	private static async Task<List<BoardPost>> BoardPoll(string topic, string since)
	{
		try
		{
			string url = LobbyServer + "/" + topic + "/json?poll=1&since=" + Uri.EscapeDataString(since);
			string text = await BoardHttp.GetStringAsync(url);
			var posts = new List<BoardPost>();
			foreach (string line in text.Split('\n'))
			{
				BoardPost p = ParsePost(line);
				if (p != null)
				{
					posts.Add(p);
				}
			}
			return posts;
		}
		catch (Exception e)
		{
			GD.Print("[online] lobby-code service: " + e.Message);
			return null;
		}
	}

	/// <summary>Posts a message (our JSON) on a topic; its id, or null if it didn't get there.</summary>
	private static async Task<string> BoardPublish(string topic, string body)
	{
		try
		{
			using var request = new System.Net.Http.HttpRequestMessage(System.Net.Http.HttpMethod.Post, LobbyServer + "/" + topic);
			request.Content = new System.Net.Http.StringContent(body, Encoding.UTF8, "text/plain");
			request.Headers.TryAddWithoutValidation("X-Firebase", "no");   // nothing to forward to phones
			using var response = await BoardHttp.SendAsync(request);
			if (!response.IsSuccessStatusCode)
			{
				GD.Print("[online] lobby-code service: HTTP " + (int)response.StatusCode);
				return null;
			}
			string text = await response.Content.ReadAsStringAsync();
			using var doc = System.Text.Json.JsonDocument.Parse(text);
			return doc.RootElement.TryGetProperty("id", out var id) ? id.GetString() ?? "" : "";
		}
		catch (Exception e)
		{
			GD.Print("[online] lobby-code service: " + e.Message);
			return null;
		}
	}

	/// <summary>A free 5-digit number (nobody posted a lobby on it in the last 10 minutes), with our lobby
	/// posted on it: (number, message id), or (null, null) when the board can't be reached.</summary>
	private static async Task<(string, string)> BoardClaim(string payload)
	{
		for (int attempt = 0; attempt < 6; attempt++)
		{
			string number = System.Security.Cryptography.RandomNumberGenerator.GetInt32(10000, 100000).ToString();
			string topic = LobbyTopicPrefix + number;
			List<BoardPost> posts = await BoardPoll(topic, "10m");
			if (posts == null)
			{
				return (null, null);
			}
			if (LatestHost(posts) != null)
			{
				continue;   // in use right now: another number
			}
			string id = await BoardPublish(topic, payload);
			return id == null ? (null, null) : (number, id);
		}
		return (null, null);
	}

	/// <summary>Host: listens to our topic (ntfy's JSON stream) for joiners posting their address, until Leave.</summary>
	private void BoardListen(string topic, string sinceId)
	{
		_listenCts?.Cancel();
		var cts = new System.Threading.CancellationTokenSource();
		_listenCts = cts;
		int gen = _generation;
		System.Threading.CancellationToken stop = cts.Token;
		Task.Run(async () =>
		{
			string since = string.IsNullOrEmpty(sinceId) ? "1m" : sinceId;
			int wait = 2000;
			while (!stop.IsCancellationRequested)
			{
				try
				{
					string url = LobbyServer + "/" + topic + "/json?since=" + Uri.EscapeDataString(since);
					using var request = new System.Net.Http.HttpRequestMessage(System.Net.Http.HttpMethod.Get, url);
					using var response = await BoardStreamHttp.SendAsync(request, System.Net.Http.HttpCompletionOption.ResponseHeadersRead, stop);
					response.EnsureSuccessStatusCode();
					using var stream = await response.Content.ReadAsStreamAsync(stop);
					using var reader = new System.IO.StreamReader(stream);
					wait = 2000;
					while (!stop.IsCancellationRequested)
					{
						// the board sends a keepalive at least every minute: silence = a dead connection
						using var quiet = System.Threading.CancellationTokenSource.CreateLinkedTokenSource(stop);
						quiet.CancelAfter(TimeSpan.FromSeconds(100));
						string line = await reader.ReadLineAsync(quiet.Token);
						if (line == null)
						{
							break;
						}
						BoardPost p = ParsePost(line);
						if (p == null)
						{
							continue;
						}
						since = p.Id;
						if (p.Get("t") == "join")
						{
							Post(gen, () => OnJoinPost(p));
						}
					}
				}
				catch (OperationCanceledException)
				{
					if (stop.IsCancellationRequested)
					{
						return;
					}
				}
				catch (Exception e)
				{
					GD.Print("[online] lobby-code service (listening): " + e.Message);
				}
				try
				{
					await Task.Delay(wait, stop);
				}
				catch (OperationCanceledException)
				{
					return;
				}
				wait = Math.Min(wait * 2, 30000);
			}
		});
	}

	/// <summary>One line of ntfy's JSON output -> a post (only "message" events carrying our JSON).</summary>
	private static BoardPost ParsePost(string line)
	{
		if (string.IsNullOrWhiteSpace(line))
		{
			return null;
		}
		try
		{
			using var doc = System.Text.Json.JsonDocument.Parse(line);
			var root = doc.RootElement;
			if (!root.TryGetProperty("event", out var ev) || ev.GetString() != "message" || !root.TryGetProperty("message", out var msg))
			{
				return null;
			}
			using var inner = System.Text.Json.JsonDocument.Parse(msg.GetString() ?? "");
			if (inner.RootElement.ValueKind != System.Text.Json.JsonValueKind.Object)
			{
				return null;
			}
			var p = new BoardPost { Id = root.TryGetProperty("id", out var id) ? id.GetString() ?? "" : "" };
			foreach (var prop in inner.RootElement.EnumerateObject())
			{
				if (prop.Value.ValueKind == System.Text.Json.JsonValueKind.String)
				{
					p.Data[prop.Name] = prop.Value.GetString() ?? "";
				}
			}
			return p;
		}
		catch (Exception)
		{
			return null;   // somebody else's message on the topic
		}
	}

	/// <summary>The newest lobby posted on a topic that hasn't been closed since (null: none).</summary>
	private static BoardPost LatestHost(List<BoardPost> posts)
	{
		BoardPost open = null;
		foreach (BoardPost p in posts)
		{
			string t = p.Get("t");
			if (t == "host")
			{
				open = p;
			}
			else if (t == "closed" && open != null && p.Get("n") == open.Get("n"))
			{
				open = null;
			}
		}
		return open;
	}

	// --- codes ----------------------------------------------------------------------------------

	private const string Alphabet = "0123456789ABCDEFGHJKMNPQRSTVWXYZ";   // Crockford base 32: no I, L, O, U

	/// <summary>An IPv4 address and port as 12 letters/numbers: "K7Q2-M9X4-PA3D" (6 bytes + 1 check byte).</summary>
	public static string Encode(IPEndPoint ep)
	{
		if (ep == null || ep.AddressFamily != AddressFamily.InterNetwork)
		{
			return "";
		}
		byte[] b = new byte[7];
		Buffer.BlockCopy(ep.Address.GetAddressBytes(), 0, b, 0, 4);
		b[4] = (byte)(ep.Port >> 8);
		b[5] = (byte)(ep.Port & 0xFF);
		b[6] = Check(b);
		ulong v = 0;
		for (int i = 0; i < 7; i++)
		{
			v = (v << 8) | b[i];
		}
		v <<= 4;   // 56 bits -> 60 bits (12 characters of 5 bits)
		var sb = new StringBuilder();
		for (int i = 11; i >= 0; i--)
		{
			sb.Append(Alphabet[(int)((v >> (i * 5)) & 31)]);
			if (i == 8 || i == 4)
			{
				sb.Append('-');
			}
		}
		return sb.ToString();
	}

	/// <summary>A lobby code or "address:port" (port defaults to 7777); null when it can't be read.</summary>
	public static IPEndPoint ParseCode(string text)
	{
		if (string.IsNullOrWhiteSpace(text))
		{
			return null;
		}
		string t = text.Trim();
		if (t.Contains('.'))
		{
			string host = t;
			int port = DefaultPort;
			int colon = t.LastIndexOf(':');
			if (colon > 0 && int.TryParse(t.Substring(colon + 1), out int p))
			{
				host = t.Substring(0, colon);
				port = p;
			}
			if (IPAddress.TryParse(host, out IPAddress ip))
			{
				return new IPEndPoint(ip, port);
			}
			try
			{
				foreach (IPAddress a in Dns.GetHostAddresses(host))
				{
					if (a.AddressFamily == AddressFamily.InterNetwork)
					{
						return new IPEndPoint(a, port);
					}
				}
			}
			catch (Exception)
			{
			}
			return null;
		}
		var clean = new StringBuilder();
		foreach (char ch in t.ToUpperInvariant())
		{
			char c = ch == 'O' ? '0' : (ch == 'I' || ch == 'L') ? '1' : ch;
			if (Alphabet.IndexOf(c) >= 0)
			{
				clean.Append(c);
			}
			else if (c != '-' && c != ' ' && c != '_')
			{
				return null;
			}
		}
		if (clean.Length != 12)
		{
			return null;
		}
		ulong v = 0;
		foreach (char c in clean.ToString())
		{
			v = (v << 5) | (uint)Alphabet.IndexOf(c);
		}
		v >>= 4;
		byte[] b = new byte[7];
		for (int i = 6; i >= 0; i--)
		{
			b[i] = (byte)(v & 0xFF);
			v >>= 8;
		}
		if (Check(b) != b[6])
		{
			return null;
		}
		return new IPEndPoint(new IPAddress(new[] { b[0], b[1], b[2], b[3] }), (b[4] << 8) | b[5]);
	}

	private static byte Check(byte[] b)
	{
		int s = 0x5A;
		for (int i = 0; i < 6; i++)
		{
			s = ((s * 31) + b[i] + 7) & 0xFF;
		}
		return (byte)s;
	}

	private static string Describe(IPEndPoint ep)
	{
		return ep.Address + ":" + ep.Port;
	}

	private static IPEndPoint ParseStun(byte[] p, byte[] tx)
	{
		if (p.Length < 20 || p[0] != 0x01 || p[1] != 0x01)
		{
			return null;
		}
		for (int i = 0; i < 12; i++)
		{
			if (p[8 + i] != tx[i])
			{
				return null;
			}
		}
		int end = Math.Min(p.Length, 20 + ((p[2] << 8) | p[3]));
		int pos = 20;
		IPEndPoint plain = null;
		while (pos + 4 <= end)
		{
			int type = (p[pos] << 8) | p[pos + 1];
			int len = (p[pos + 2] << 8) | p[pos + 3];
			int v = pos + 4;
			if (v + len > end)
			{
				break;
			}
			if (len >= 8 && p[v + 1] == 0x01)
			{
				if (type == 0x0020 || type == 0x8020)   // XOR-MAPPED-ADDRESS
				{
					int port = ((p[v + 2] << 8) | p[v + 3]) ^ 0x2112;
					byte[] ip = { (byte)(p[v + 4] ^ 0x21), (byte)(p[v + 5] ^ 0x12), (byte)(p[v + 6] ^ 0xA4), (byte)(p[v + 7] ^ 0x42) };
					return new IPEndPoint(new IPAddress(ip), port);
				}
				if (type == 0x0001)   // MAPPED-ADDRESS (old servers)
				{
					plain = new IPEndPoint(new IPAddress(new[] { p[v + 4], p[v + 5], p[v + 6], p[v + 7] }), (p[v + 2] << 8) | p[v + 3]);
				}
			}
			pos = v + ((len + 3) & ~3);
		}
		return plain;
	}

	private static bool IsPrivate(IPAddress ip)
	{
		byte[] b = ip.GetAddressBytes();
		return b[0] == 10 || b[0] == 127 || (b[0] == 172 && b[1] >= 16 && b[1] <= 31) || (b[0] == 192 && b[1] == 168)
			|| (b[0] == 169 && b[1] == 254) || (b[0] == 100 && b[1] >= 64 && b[1] <= 127);
	}

	/// <summary>This computer's address on the home network (192.168.x.x and friends).</summary>
	private static IPAddress LanAddress()
	{
		IPAddress best = null;
		try
		{
			foreach (NetworkInterface ni in NetworkInterface.GetAllNetworkInterfaces())
			{
				if (ni.OperationalStatus != OperationalStatus.Up || ni.NetworkInterfaceType == NetworkInterfaceType.Loopback)
				{
					continue;
				}
				string name = (ni.Name + " " + ni.Description).ToLowerInvariant();
				bool virtualCard = name.Contains("virtual") || name.Contains("vmware") || name.Contains("vbox") || name.Contains("hyper-v") || name.Contains("wsl") || name.Contains("docker");
				foreach (UnicastIPAddressInformation ua in ni.GetIPProperties().UnicastAddresses)
				{
					IPAddress a = ua.Address;
					if (a.AddressFamily != AddressFamily.InterNetwork || IPAddress.IsLoopback(a))
					{
						continue;
					}
					if (!virtualCard && IsPrivate(a) && ni.GetIPProperties().GatewayAddresses.Count > 0)
					{
						return a;
					}
					best ??= a;
				}
			}
		}
		catch (Exception)
		{
		}
		return best;
	}
}

/// <summary>PleaseResync adapter for a fight over NetsuOnline's connection (see NetsuOnline.CreateSessionAdapter).</summary>
public class NetsuOnlineAdapter : SessionAdapter
{
	private readonly NetsuOnline _online;

	public NetsuOnlineAdapter(NetsuOnline online)
	{
		_online = online;
	}

	public uint SendTo(uint deviceId, DeviceMessage message)
	{
		return _online.SendGame(deviceId, message);
	}

	public List<(uint size, uint deviceId, DeviceMessage message)> ReceiveFrom()
	{
		return _online.TakeGameMessages();
	}

	public void AddRemote(uint deviceId, object remoteConfiguration)
	{
	}

	public void Close()
	{
		_online.EndSession();   // the connection stays: back to the lobby for a rematch
	}
}
