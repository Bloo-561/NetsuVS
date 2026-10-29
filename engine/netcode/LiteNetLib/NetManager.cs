using System;
using System.Collections;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Diagnostics;
using System.Net;
using System.Net.Sockets;
using System.Runtime.InteropServices;
using System.Threading;
using LiteNetLib.Layers;
using LiteNetLib.Utils;

namespace LiteNetLib;

public class NetManager : IEnumerable<NetPeer>, IEnumerable
{
	public struct NetPeerEnumerator(NetPeer p) : IEnumerator<NetPeer>, IEnumerator, IDisposable
	{
		private readonly NetPeer _initialPeer = p;

		private NetPeer _p = null;

		public NetPeer Current => _p;

		object IEnumerator.Current => _p;

		public void Dispose()
		{
		}

		public bool MoveNext()
		{
			_p = ((_p == null) ? _initialPeer : _p.NextPeer);
			return _p != null;
		}

		public void Reset()
		{
			throw new NotSupportedException();
		}
	}

	private struct Slot
	{
		internal int HashCode;

		internal int Next;

		internal NetPeer Value;
	}

	private Thread _logicThread;

	private bool _manualMode;

	private readonly AutoResetEvent _updateTriggerEvent = new AutoResetEvent(initialState: true);

	private NetEvent _pendingEventHead;

	private NetEvent _pendingEventTail;

	private NetEvent _netEventPoolHead;

	private readonly INetEventListener _netEventListener;

	private readonly IDeliveryEventListener _deliveryEventListener;

	private readonly INtpEventListener _ntpEventListener;

	private readonly IPeerAddressChangedListener _peerAddressChangedListener;

	private readonly Dictionary<IPEndPoint, ConnectionRequest> _requestsDict = new Dictionary<IPEndPoint, ConnectionRequest>();

	private readonly ConcurrentDictionary<IPEndPoint, NtpRequest> _ntpRequests = new ConcurrentDictionary<IPEndPoint, NtpRequest>();

	private int _connectedPeersCount;

	private readonly List<NetPeer> _connectedPeerListCache = new List<NetPeer>();

	private readonly PacketLayerBase _extraPacketLayer;

	private int _lastPeerId;

	private ConcurrentQueue<int> _peerIds = new ConcurrentQueue<int>();

	private byte _channelsCount = 1;

	private readonly object _eventLock = new object();

	public bool UnconnectedMessagesEnabled;

	public bool NatPunchEnabled;

	/// <summary>Netsu: raw (non-LiteNetLib) packets from these addresses are handed to NetsuRawReceive
	/// (on the receive thread) instead of being processed: the online lobby's STUN queries.</summary>
	public readonly System.Collections.Concurrent.ConcurrentDictionary<IPEndPoint, bool> NetsuRawEndpoints = new System.Collections.Concurrent.ConcurrentDictionary<IPEndPoint, bool>();

	public Action<IPEndPoint, byte[]> NetsuRawReceive;

	/// <summary>Netsu: sends bytes exactly as given (no LiteNetLib header) from this manager's socket.</summary>
	public int NetsuSendRaw(byte[] data, IPEndPoint remoteEndPoint)
	{
		return SendRaw(data, 0, data.Length, remoteEndPoint);
	}

	public int UpdateTime = 15;

	public int PingInterval = 1000;

	public int DisconnectTimeout = 5000;

	public bool SimulatePacketLoss;

	public bool SimulateLatency;

	public int SimulationPacketLossChance = 10;

	public int SimulationMinLatency = 30;

	public int SimulationMaxLatency = 100;

	public bool UnsyncedEvents;

	public bool UnsyncedReceiveEvent;

	public bool UnsyncedDeliveryEvent;

	public bool BroadcastReceiveEnabled;

	public int ReconnectDelay = 500;

	public int MaxConnectAttempts = 10;

	public bool ReuseAddress;

	public bool DontRoute;

	public readonly NetStatistics Statistics = new NetStatistics();

	public bool EnableStatistics;

	public readonly NatPunchModule NatPunchModule;

	public bool AutoRecycle;

	public bool IPv6Enabled = true;

	public int MtuOverride;

	public bool UseSafeMtu;

	public bool UseNativeSockets;

	public bool DisconnectOnUnreachable;

	public bool AllowPeerAddressChange;

	private const int MaxPrimeArrayLength = 2147483587;

	private const int HashPrime = 101;

	private const int Lower31BitMask = int.MaxValue;

	private static readonly int[] Primes = new int[72]
	{
		3, 7, 11, 17, 23, 29, 37, 47, 59, 71,
		89, 107, 131, 163, 197, 239, 293, 353, 431, 521,
		631, 761, 919, 1103, 1327, 1597, 1931, 2333, 2801, 3371,
		4049, 4861, 5839, 7013, 8419, 10103, 12143, 14591, 17519, 21023,
		25229, 30293, 36353, 43627, 52361, 62851, 75431, 90523, 108631, 130363,
		156437, 187751, 225307, 270371, 324449, 389357, 467237, 560689, 672827, 807403,
		968897, 1162687, 1395263, 1674319, 2009191, 2411033, 2893249, 3471899, 4166287, 4999559,
		5999471, 7199369
	};

	private int[] _buckets;

	private Slot[] _slots;

	private int _count;

	private int _lastIndex;

	private int _freeList = -1;

	private NetPeer[] _peersArray = new NetPeer[32];

	private readonly ReaderWriterLockSlim _peersLock = new ReaderWriterLockSlim(LockRecursionPolicy.NoRecursion);

	private volatile NetPeer _headPeer;

	private NetPacket _poolHead;

	private int _poolCount;

	private readonly object _poolLock = new object();

	public int PacketPoolSize = 1000;

	private const int ReceivePollingTime = 500000;

	private Socket _udpSocketv4;

	private Socket _udpSocketv6;

	private Thread _receiveThread;

	private IPEndPoint _bufferEndPointv4;

	private IPEndPoint _bufferEndPointv6;

	private readonly SocketAddress _sockAddrCacheV4 = new SocketAddress(AddressFamily.InterNetwork);

	private readonly SocketAddress _sockAddrCacheV6 = new SocketAddress(AddressFamily.InterNetworkV6);

	private const int SioUdpConnreset = -1744830452;

	private static readonly IPAddress MulticastAddressV6 = IPAddress.Parse("ff02::1");

	public static readonly bool IPv6Support = false;

	public int MaxPacketsReceivePerUpdate;

	internal bool NotConnected;

	public bool IsRunning { get; private set; }

	public int LocalPort { get; private set; }

	public NetPeer FirstPeer => _headPeer;

	public byte ChannelsCount
	{
		get
		{
			return _channelsCount;
		}
		set
		{
			if (value < 1 || value > 64)
			{
				throw new ArgumentException("Channels count must be between 1 and 64");
			}
			_channelsCount = value;
		}
	}

	public List<NetPeer> ConnectedPeerList
	{
		get
		{
			GetPeersNonAlloc(_connectedPeerListCache, ConnectionState.Connected);
			return _connectedPeerListCache;
		}
	}

	public int ConnectedPeersCount => Interlocked.CompareExchange(ref _connectedPeersCount, 0, 0);

	public int ExtraPacketSizeForLayer => _extraPacketLayer?.ExtraPacketSizeForLayer ?? 0;

	public int PoolCount => _poolCount;

	public short Ttl
	{
		get
		{
			return _udpSocketv4.Ttl;
		}
		internal set
		{
			_udpSocketv4.Ttl = value;
		}
	}

	public NetManager(INetEventListener listener, PacketLayerBase extraPacketLayer = null)
	{
		_netEventListener = listener;
		_deliveryEventListener = listener as IDeliveryEventListener;
		_ntpEventListener = listener as INtpEventListener;
		_peerAddressChangedListener = listener as IPeerAddressChangedListener;
		NatPunchModule = new NatPunchModule(this);
		_extraPacketLayer = extraPacketLayer;
	}

	internal void ConnectionLatencyUpdated(NetPeer fromPeer, int latency)
	{
		CreateEvent(NetEvent.EType.ConnectionLatencyUpdated, fromPeer, null, SocketError.Success, latency, DisconnectReason.ConnectionFailed, null, DeliveryMethod.Unreliable, 0);
	}

	internal void MessageDelivered(NetPeer fromPeer, object userData)
	{
		if (_deliveryEventListener != null)
		{
			CreateEvent(NetEvent.EType.MessageDelivered, fromPeer, null, SocketError.Success, 0, DisconnectReason.ConnectionFailed, null, DeliveryMethod.Unreliable, 0, null, userData);
		}
	}

	internal void DisconnectPeerForce(NetPeer peer, DisconnectReason reason, SocketError socketErrorCode, NetPacket eventData)
	{
		DisconnectPeer(peer, reason, socketErrorCode, force: true, null, 0, 0, eventData);
	}

	private void DisconnectPeer(NetPeer peer, DisconnectReason reason, SocketError socketErrorCode, bool force, byte[] data, int start, int count, NetPacket eventData)
	{
		switch (peer.Shutdown(data, start, count, force))
		{
		case ShutdownResult.None:
			return;
		case ShutdownResult.WasConnected:
			Interlocked.Decrement(ref _connectedPeersCount);
			break;
		}
		CreateEvent(NetEvent.EType.Disconnect, peer, null, socketErrorCode, 0, reason, null, DeliveryMethod.Unreliable, 0, eventData);
	}

	private void CreateEvent(NetEvent.EType type, NetPeer peer = null, IPEndPoint remoteEndPoint = null, SocketError errorCode = SocketError.Success, int latency = 0, DisconnectReason disconnectReason = DisconnectReason.ConnectionFailed, ConnectionRequest connectionRequest = null, DeliveryMethod deliveryMethod = DeliveryMethod.Unreliable, byte channelNumber = 0, NetPacket readerSource = null, object userData = null)
	{
		bool unsyncEvent = UnsyncedEvents;
		switch (type)
		{
		case NetEvent.EType.Connect:
			Interlocked.Increment(ref _connectedPeersCount);
			break;
		case NetEvent.EType.MessageDelivered:
			unsyncEvent = UnsyncedDeliveryEvent;
			break;
		}
		NetEvent evt;
		lock (_eventLock)
		{
			evt = _netEventPoolHead;
			if (evt == null)
			{
				evt = new NetEvent(this);
			}
			else
			{
				_netEventPoolHead = evt.Next;
			}
		}
		evt.Next = null;
		evt.Type = type;
		evt.DataReader.SetSource(readerSource, readerSource?.GetHeaderSize() ?? 0);
		evt.Peer = peer;
		evt.RemoteEndPoint = remoteEndPoint;
		evt.Latency = latency;
		evt.ErrorCode = errorCode;
		evt.DisconnectReason = disconnectReason;
		evt.ConnectionRequest = connectionRequest;
		evt.DeliveryMethod = deliveryMethod;
		evt.ChannelNumber = channelNumber;
		evt.UserData = userData;
		if (unsyncEvent || _manualMode)
		{
			ProcessEvent(evt);
			return;
		}
		lock (_eventLock)
		{
			if (_pendingEventTail == null)
			{
				_pendingEventHead = evt;
			}
			else
			{
				_pendingEventTail.Next = evt;
			}
			_pendingEventTail = evt;
		}
	}

	private void ProcessEvent(NetEvent evt)
	{
		bool emptyData = evt.DataReader.IsNull;
		switch (evt.Type)
		{
		case NetEvent.EType.Connect:
			_netEventListener.OnPeerConnected(evt.Peer);
			break;
		case NetEvent.EType.Disconnect:
		{
			DisconnectInfo info = new DisconnectInfo
			{
				Reason = evt.DisconnectReason,
				AdditionalData = evt.DataReader,
				SocketErrorCode = evt.ErrorCode
			};
			_netEventListener.OnPeerDisconnected(evt.Peer, info);
			break;
		}
		case NetEvent.EType.Receive:
			_netEventListener.OnNetworkReceive(evt.Peer, evt.DataReader, evt.ChannelNumber, evt.DeliveryMethod);
			break;
		case NetEvent.EType.ReceiveUnconnected:
			_netEventListener.OnNetworkReceiveUnconnected(evt.RemoteEndPoint, evt.DataReader, UnconnectedMessageType.BasicMessage);
			break;
		case NetEvent.EType.Broadcast:
			_netEventListener.OnNetworkReceiveUnconnected(evt.RemoteEndPoint, evt.DataReader, UnconnectedMessageType.Broadcast);
			break;
		case NetEvent.EType.Error:
			_netEventListener.OnNetworkError(evt.RemoteEndPoint, evt.ErrorCode);
			break;
		case NetEvent.EType.ConnectionLatencyUpdated:
			_netEventListener.OnNetworkLatencyUpdate(evt.Peer, evt.Latency);
			break;
		case NetEvent.EType.ConnectionRequest:
			_netEventListener.OnConnectionRequest(evt.ConnectionRequest);
			break;
		case NetEvent.EType.MessageDelivered:
			_deliveryEventListener.OnMessageDelivered(evt.Peer, evt.UserData);
			break;
		case NetEvent.EType.PeerAddressChanged:
		{
			_peersLock.EnterUpgradeableReadLock();
			IPEndPoint previousAddress = null;
			if (ContainsPeer(evt.Peer))
			{
				_peersLock.EnterWriteLock();
				RemovePeerFromSet(evt.Peer);
				previousAddress = new IPEndPoint(evt.Peer.Address, evt.Peer.Port);
				evt.Peer.FinishEndPointChange(evt.RemoteEndPoint);
				AddPeerToSet(evt.Peer);
				_peersLock.ExitWriteLock();
			}
			_peersLock.ExitUpgradeableReadLock();
			if (previousAddress != null && _peerAddressChangedListener != null)
			{
				_peerAddressChangedListener.OnPeerAddressChanged(evt.Peer, previousAddress);
			}
			break;
		}
		}
		if (emptyData)
		{
			RecycleEvent(evt);
		}
		else if (AutoRecycle)
		{
			evt.DataReader.RecycleInternal();
		}
	}

	internal void RecycleEvent(NetEvent evt)
	{
		evt.Peer = null;
		evt.ErrorCode = SocketError.Success;
		evt.RemoteEndPoint = null;
		evt.ConnectionRequest = null;
		lock (_eventLock)
		{
			evt.Next = _netEventPoolHead;
			_netEventPoolHead = evt;
		}
	}

	private void UpdateLogic()
	{
		List<NetPeer> peersToRemove = new List<NetPeer>();
		Stopwatch stopwatch = new Stopwatch();
		stopwatch.Start();
		while (IsRunning)
		{
			try
			{
				int elapsed = (int)stopwatch.ElapsedMilliseconds;
				elapsed = ((elapsed <= 0) ? 1 : elapsed);
				stopwatch.Restart();
				for (NetPeer netPeer = _headPeer; netPeer != null; netPeer = netPeer.NextPeer)
				{
					if (netPeer.ConnectionState == ConnectionState.Disconnected && netPeer.TimeSinceLastPacket > DisconnectTimeout)
					{
						peersToRemove.Add(netPeer);
					}
					else
					{
						netPeer.Update(elapsed);
					}
				}
				if (peersToRemove.Count > 0)
				{
					_peersLock.EnterWriteLock();
					for (int i = 0; i < peersToRemove.Count; i++)
					{
						RemovePeerInternal(peersToRemove[i]);
					}
					_peersLock.ExitWriteLock();
					peersToRemove.Clear();
				}
				ProcessNtpRequests(elapsed);
				int sleepTime = UpdateTime - (int)stopwatch.ElapsedMilliseconds;
				if (sleepTime > 0)
				{
					_updateTriggerEvent.WaitOne(sleepTime);
				}
			}
			catch (ThreadAbortException)
			{
				return;
			}
			catch (Exception ex2)
			{
				NetDebug.WriteError("[NM] LogicThread error: " + ex2);
			}
		}
		stopwatch.Stop();
	}

	[Conditional("DEBUG")]
	private void ProcessDelayedPackets()
	{
	}

	private void ProcessNtpRequests(int elapsedMilliseconds)
	{
		List<IPEndPoint> requestsToRemove = null;
		foreach (KeyValuePair<IPEndPoint, NtpRequest> ntpRequest in _ntpRequests)
		{
			ntpRequest.Value.Send(_udpSocketv4, elapsedMilliseconds);
			if (ntpRequest.Value.NeedToKill)
			{
				if (requestsToRemove == null)
				{
					requestsToRemove = new List<IPEndPoint>();
				}
				requestsToRemove.Add(ntpRequest.Key);
			}
		}
		if (requestsToRemove == null)
		{
			return;
		}
		foreach (IPEndPoint ipEndPoint in requestsToRemove)
		{
			_ntpRequests.TryRemove(ipEndPoint, out var _);
		}
	}

	public void ManualUpdate(int elapsedMilliseconds)
	{
		if (!_manualMode)
		{
			return;
		}
		for (NetPeer netPeer = _headPeer; netPeer != null; netPeer = netPeer.NextPeer)
		{
			if (netPeer.ConnectionState == ConnectionState.Disconnected && netPeer.TimeSinceLastPacket > DisconnectTimeout)
			{
				RemovePeerInternal(netPeer);
			}
			else
			{
				netPeer.Update(elapsedMilliseconds);
			}
		}
		ProcessNtpRequests(elapsedMilliseconds);
	}

	internal NetPeer OnConnectionSolved(ConnectionRequest request, byte[] rejectData, int start, int length)
	{
		NetPeer netPeer = null;
		if (request.Result == ConnectionRequestResult.RejectForce)
		{
			if (rejectData != null && length > 0)
			{
				NetPacket shutdownPacket = PoolGetWithProperty(PacketProperty.Disconnect, length);
				shutdownPacket.ConnectionNumber = request.InternalPacket.ConnectionNumber;
				FastBitConverter.GetBytes(shutdownPacket.RawData, 1, request.InternalPacket.ConnectionTime);
				if (shutdownPacket.Size >= NetConstants.PossibleMtu[0])
				{
					NetDebug.WriteError("[Peer] Disconnect additional data size more than MTU!");
				}
				else
				{
					Buffer.BlockCopy(rejectData, start, shutdownPacket.RawData, 9, length);
				}
				SendRawAndRecycle(shutdownPacket, request.RemoteEndPoint);
			}
			lock (_requestsDict)
			{
				_requestsDict.Remove(request.RemoteEndPoint);
			}
		}
		else
		{
			lock (_requestsDict)
			{
				if (!TryGetPeer(request.RemoteEndPoint, out netPeer))
				{
					if (request.Result == ConnectionRequestResult.Reject)
					{
						netPeer = new NetPeer(this, request.RemoteEndPoint, GetNextPeerId());
						netPeer.Reject(request.InternalPacket, rejectData, start, length);
						AddPeer(netPeer);
					}
					else
					{
						netPeer = new NetPeer(this, request, GetNextPeerId());
						AddPeer(netPeer);
						CreateEvent(NetEvent.EType.Connect, netPeer, null, SocketError.Success, 0, DisconnectReason.ConnectionFailed, null, DeliveryMethod.Unreliable, 0);
					}
				}
				_requestsDict.Remove(request.RemoteEndPoint);
			}
		}
		return netPeer;
	}

	private int GetNextPeerId()
	{
		if (!_peerIds.TryDequeue(out var id))
		{
			return _lastPeerId++;
		}
		return id;
	}

	private void ProcessConnectRequest(IPEndPoint remoteEndPoint, NetPeer netPeer, NetConnectRequestPacket connRequest)
	{
		if (netPeer != null)
		{
			ConnectRequestResult processResult = netPeer.ProcessConnectRequest(connRequest);
			switch (processResult)
			{
			default:
				return;
			case ConnectRequestResult.Reconnection:
				DisconnectPeerForce(netPeer, DisconnectReason.Reconnect, SocketError.Success, null);
				RemovePeer(netPeer);
				break;
			case ConnectRequestResult.NewConnection:
				RemovePeer(netPeer);
				break;
			case ConnectRequestResult.P2PLose:
				DisconnectPeerForce(netPeer, DisconnectReason.PeerToPeerConnection, SocketError.Success, null);
				RemovePeer(netPeer);
				break;
			}
			if (processResult != ConnectRequestResult.P2PLose)
			{
				connRequest.ConnectionNumber = (byte)((netPeer.ConnectionNum + 1) % 4);
			}
		}
		ConnectionRequest req;
		lock (_requestsDict)
		{
			if (_requestsDict.TryGetValue(remoteEndPoint, out req))
			{
				req.UpdateRequest(connRequest);
				return;
			}
			req = new ConnectionRequest(remoteEndPoint, connRequest, this);
			_requestsDict.Add(remoteEndPoint, req);
		}
		CreateEvent(NetEvent.EType.ConnectionRequest, null, null, SocketError.Success, 0, DisconnectReason.ConnectionFailed, req, DeliveryMethod.Unreliable, 0);
	}

	private void OnMessageReceived(NetPacket packet, IPEndPoint remoteEndPoint)
	{
		if (packet.Size == 0)
		{
			PoolRecycle(packet);
			return;
		}
		int originalPacketSize = packet.Size;
		if (EnableStatistics)
		{
			Statistics.IncrementPacketsReceived();
			Statistics.AddBytesReceived(originalPacketSize);
		}
		if (_ntpRequests.Count > 0 && _ntpRequests.TryGetValue(remoteEndPoint, out var _))
		{
			if (packet.Size >= 48)
			{
				byte[] copiedData = new byte[packet.Size];
				Buffer.BlockCopy(packet.RawData, 0, copiedData, 0, packet.Size);
				NtpPacket ntpPacket = NtpPacket.FromServerResponse(copiedData, DateTime.UtcNow);
				try
				{
					ntpPacket.ValidateReply();
				}
				catch (InvalidOperationException)
				{
					ntpPacket = null;
				}
				if (ntpPacket != null)
				{
					_ntpRequests.TryRemove(remoteEndPoint, out var _);
					_ntpEventListener?.OnNtpResponse(ntpPacket);
				}
			}
			return;
		}
		// Netsu (Oct 24): raw packets from addresses the online lobby asked for (STUN answers) go to it
		// instead of LiteNetLib (NetsuOnline.cs). Called on the receive thread.
		if (NetsuRawReceive != null && !NetsuRawEndpoints.IsEmpty && NetsuRawEndpoints.ContainsKey(remoteEndPoint))
		{
			byte[] raw = new byte[packet.Size];
			Buffer.BlockCopy(packet.RawData, 0, raw, 0, packet.Size);
			NetsuRawReceive(new IPEndPoint(remoteEndPoint.Address, remoteEndPoint.Port), raw);
			PoolRecycle(packet);
			return;
		}
		if (_extraPacketLayer != null)
		{
			_extraPacketLayer.ProcessInboundPacket(ref remoteEndPoint, ref packet.RawData, ref packet.Size);
			if (packet.Size == 0)
			{
				return;
			}
		}
		if (!packet.Verify())
		{
			NetDebug.WriteError("[NM] DataReceived: bad!");
			PoolRecycle(packet);
			return;
		}
		switch (packet.Property)
		{
		case PacketProperty.ConnectRequest:
			if (NetConnectRequestPacket.GetProtocolId(packet) != 13)
			{
				SendRawAndRecycle(PoolGetWithProperty(PacketProperty.InvalidProtocol), remoteEndPoint);
				return;
			}
			break;
		case PacketProperty.Broadcast:
			if (BroadcastReceiveEnabled)
			{
				CreateEvent(NetEvent.EType.Broadcast, null, remoteEndPoint, SocketError.Success, 0, DisconnectReason.ConnectionFailed, null, DeliveryMethod.Unreliable, 0, packet);
			}
			return;
		case PacketProperty.UnconnectedMessage:
			if (UnconnectedMessagesEnabled)
			{
				CreateEvent(NetEvent.EType.ReceiveUnconnected, null, remoteEndPoint, SocketError.Success, 0, DisconnectReason.ConnectionFailed, null, DeliveryMethod.Unreliable, 0, packet);
			}
			return;
		case PacketProperty.NatMessage:
			if (NatPunchEnabled)
			{
				NatPunchModule.ProcessMessage(remoteEndPoint, packet);
			}
			return;
		}
		NetPeer netPeer = remoteEndPoint as NetPeer;
		bool peerFound = netPeer != null || TryGetPeer(remoteEndPoint, out netPeer);
		if (peerFound && EnableStatistics)
		{
			netPeer.Statistics.IncrementPacketsReceived();
			netPeer.Statistics.AddBytesReceived(originalPacketSize);
		}
		switch (packet.Property)
		{
		case PacketProperty.ConnectRequest:
		{
			NetConnectRequestPacket connRequest = NetConnectRequestPacket.FromData(packet);
			if (connRequest != null)
			{
				ProcessConnectRequest(remoteEndPoint, netPeer, connRequest);
			}
			break;
		}
		case PacketProperty.PeerNotFound:
			if (peerFound)
			{
				if (netPeer.ConnectionState == ConnectionState.Connected)
				{
					if (packet.Size == 1)
					{
						netPeer.ResetMtu();
						SendRaw(NetConnectAcceptPacket.MakeNetworkChanged(netPeer), remoteEndPoint);
					}
					else if (packet.Size == 2 && packet.RawData[1] == 1)
					{
						DisconnectPeerForce(netPeer, DisconnectReason.PeerNotFound, SocketError.Success, null);
					}
				}
			}
			else
			{
				if (packet.Size <= 1)
				{
					break;
				}
				bool isOldPeer = false;
				if (AllowPeerAddressChange)
				{
					NetConnectAcceptPacket remoteData = NetConnectAcceptPacket.FromData(packet);
					if (remoteData != null && remoteData.PeerNetworkChanged && remoteData.PeerId < _peersArray.Length)
					{
						_peersLock.EnterUpgradeableReadLock();
						NetPeer peer = _peersArray[remoteData.PeerId];
						_peersLock.ExitUpgradeableReadLock();
						if (peer != null && peer.ConnectTime == remoteData.ConnectionTime && peer.ConnectionNum == remoteData.ConnectionNumber)
						{
							if (peer.ConnectionState == ConnectionState.Connected)
							{
								peer.InitiateEndPointChange();
								CreateEvent(NetEvent.EType.PeerAddressChanged, peer, remoteEndPoint, SocketError.Success, 0, DisconnectReason.ConnectionFailed, null, DeliveryMethod.Unreliable, 0);
							}
							isOldPeer = true;
						}
					}
				}
				PoolRecycle(packet);
				if (!isOldPeer)
				{
					NetPacket secondResponse = PoolGetWithProperty(PacketProperty.PeerNotFound, 1);
					secondResponse.RawData[1] = 1;
					SendRawAndRecycle(secondResponse, remoteEndPoint);
				}
			}
			break;
		case PacketProperty.InvalidProtocol:
			if (peerFound && netPeer.ConnectionState == ConnectionState.Outgoing)
			{
				DisconnectPeerForce(netPeer, DisconnectReason.InvalidProtocol, SocketError.Success, null);
			}
			break;
		case PacketProperty.Disconnect:
			if (peerFound)
			{
				DisconnectResult disconnectResult = netPeer.ProcessDisconnect(packet);
				if (disconnectResult == DisconnectResult.None)
				{
					PoolRecycle(packet);
					break;
				}
				DisconnectPeerForce(netPeer, (disconnectResult == DisconnectResult.Disconnect) ? DisconnectReason.RemoteConnectionClose : DisconnectReason.ConnectionRejected, SocketError.Success, packet);
			}
			else
			{
				PoolRecycle(packet);
			}
			SendRawAndRecycle(PoolGetWithProperty(PacketProperty.ShutdownOk), remoteEndPoint);
			break;
		case PacketProperty.ConnectAccept:
			if (peerFound)
			{
				NetConnectAcceptPacket connAccept = NetConnectAcceptPacket.FromData(packet);
				if (connAccept != null && netPeer.ProcessConnectAccept(connAccept))
				{
					CreateEvent(NetEvent.EType.Connect, netPeer, null, SocketError.Success, 0, DisconnectReason.ConnectionFailed, null, DeliveryMethod.Unreliable, 0);
				}
			}
			break;
		default:
			if (peerFound)
			{
				netPeer.ProcessPacket(packet);
			}
			else
			{
				SendRawAndRecycle(PoolGetWithProperty(PacketProperty.PeerNotFound), remoteEndPoint);
			}
			break;
		}
	}

	internal void CreateReceiveEvent(NetPacket packet, DeliveryMethod method, byte channelNumber, int headerSize, NetPeer fromPeer)
	{
		if (UnsyncedEvents || UnsyncedReceiveEvent || _manualMode)
		{
			NetEvent evt;
			lock (_eventLock)
			{
				evt = _netEventPoolHead;
				if (evt == null)
				{
					evt = new NetEvent(this);
				}
				else
				{
					_netEventPoolHead = evt.Next;
				}
			}
			evt.Next = null;
			evt.Type = NetEvent.EType.Receive;
			evt.DataReader.SetSource(packet, headerSize);
			evt.Peer = fromPeer;
			evt.DeliveryMethod = method;
			evt.ChannelNumber = channelNumber;
			ProcessEvent(evt);
			return;
		}
		lock (_eventLock)
		{
			NetEvent evt = _netEventPoolHead;
			if (evt == null)
			{
				evt = new NetEvent(this);
			}
			else
			{
				_netEventPoolHead = evt.Next;
			}
			evt.Next = null;
			evt.Type = NetEvent.EType.Receive;
			evt.DataReader.SetSource(packet, headerSize);
			evt.Peer = fromPeer;
			evt.DeliveryMethod = method;
			evt.ChannelNumber = channelNumber;
			if (_pendingEventTail == null)
			{
				_pendingEventHead = evt;
			}
			else
			{
				_pendingEventTail.Next = evt;
			}
			_pendingEventTail = evt;
		}
	}

	public void SendToAll(NetDataWriter writer, DeliveryMethod options)
	{
		SendToAll(writer.Data, 0, writer.Length, options);
	}

	public void SendToAll(byte[] data, DeliveryMethod options)
	{
		SendToAll(data, 0, data.Length, options);
	}

	public void SendToAll(byte[] data, int start, int length, DeliveryMethod options)
	{
		SendToAll(data, start, length, 0, options);
	}

	public void SendToAll(NetDataWriter writer, byte channelNumber, DeliveryMethod options)
	{
		SendToAll(writer.Data, 0, writer.Length, channelNumber, options);
	}

	public void SendToAll(byte[] data, byte channelNumber, DeliveryMethod options)
	{
		SendToAll(data, 0, data.Length, channelNumber, options);
	}

	public void SendToAll(byte[] data, int start, int length, byte channelNumber, DeliveryMethod options)
	{
		try
		{
			_peersLock.EnterReadLock();
			for (NetPeer netPeer = _headPeer; netPeer != null; netPeer = netPeer.NextPeer)
			{
				netPeer.Send(data, start, length, channelNumber, options);
			}
		}
		finally
		{
			_peersLock.ExitReadLock();
		}
	}

	public void SendToAll(NetDataWriter writer, DeliveryMethod options, NetPeer excludePeer)
	{
		SendToAll(writer.Data, 0, writer.Length, 0, options, excludePeer);
	}

	public void SendToAll(byte[] data, DeliveryMethod options, NetPeer excludePeer)
	{
		SendToAll(data, 0, data.Length, 0, options, excludePeer);
	}

	public void SendToAll(byte[] data, int start, int length, DeliveryMethod options, NetPeer excludePeer)
	{
		SendToAll(data, start, length, 0, options, excludePeer);
	}

	public void SendToAll(NetDataWriter writer, byte channelNumber, DeliveryMethod options, NetPeer excludePeer)
	{
		SendToAll(writer.Data, 0, writer.Length, channelNumber, options, excludePeer);
	}

	public void SendToAll(byte[] data, byte channelNumber, DeliveryMethod options, NetPeer excludePeer)
	{
		SendToAll(data, 0, data.Length, channelNumber, options, excludePeer);
	}

	public void SendToAll(byte[] data, int start, int length, byte channelNumber, DeliveryMethod options, NetPeer excludePeer)
	{
		try
		{
			_peersLock.EnterReadLock();
			for (NetPeer netPeer = _headPeer; netPeer != null; netPeer = netPeer.NextPeer)
			{
				if (netPeer != excludePeer)
				{
					netPeer.Send(data, start, length, channelNumber, options);
				}
			}
		}
		finally
		{
			_peersLock.ExitReadLock();
		}
	}

	public void SendToAll(ReadOnlySpan<byte> data, DeliveryMethod options)
	{
		SendToAll(data, 0, options, null);
	}

	public void SendToAll(ReadOnlySpan<byte> data, DeliveryMethod options, NetPeer excludePeer)
	{
		SendToAll(data, 0, options, excludePeer);
	}

	public void SendToAll(ReadOnlySpan<byte> data, byte channelNumber, DeliveryMethod options, NetPeer excludePeer)
	{
		try
		{
			_peersLock.EnterReadLock();
			for (NetPeer netPeer = _headPeer; netPeer != null; netPeer = netPeer.NextPeer)
			{
				if (netPeer != excludePeer)
				{
					netPeer.Send(data, channelNumber, options);
				}
			}
		}
		finally
		{
			_peersLock.ExitReadLock();
		}
	}

	public bool Start()
	{
		return Start(0);
	}

	public bool Start(IPAddress addressIPv4, IPAddress addressIPv6, int port)
	{
		return Start(addressIPv4, addressIPv6, port, manualMode: false);
	}

	public bool Start(string addressIPv4, string addressIPv6, int port)
	{
		IPAddress ipv4 = NetUtils.ResolveAddress(addressIPv4);
		IPAddress ipv6 = NetUtils.ResolveAddress(addressIPv6);
		return Start(ipv4, ipv6, port);
	}

	public bool Start(int port)
	{
		return Start(IPAddress.Any, IPAddress.IPv6Any, port);
	}

	public bool StartInManualMode(IPAddress addressIPv4, IPAddress addressIPv6, int port)
	{
		return Start(addressIPv4, addressIPv6, port, manualMode: true);
	}

	public bool StartInManualMode(string addressIPv4, string addressIPv6, int port)
	{
		IPAddress ipv4 = NetUtils.ResolveAddress(addressIPv4);
		IPAddress ipv6 = NetUtils.ResolveAddress(addressIPv6);
		return StartInManualMode(ipv4, ipv6, port);
	}

	public bool StartInManualMode(int port)
	{
		return StartInManualMode(IPAddress.Any, IPAddress.IPv6Any, port);
	}

	public bool SendUnconnectedMessage(byte[] message, IPEndPoint remoteEndPoint)
	{
		return SendUnconnectedMessage(message, 0, message.Length, remoteEndPoint);
	}

	public bool SendUnconnectedMessage(NetDataWriter writer, string address, int port)
	{
		IPEndPoint remoteEndPoint = NetUtils.MakeEndPoint(address, port);
		return SendUnconnectedMessage(writer.Data, 0, writer.Length, remoteEndPoint);
	}

	public bool SendUnconnectedMessage(NetDataWriter writer, IPEndPoint remoteEndPoint)
	{
		return SendUnconnectedMessage(writer.Data, 0, writer.Length, remoteEndPoint);
	}

	public bool SendUnconnectedMessage(byte[] message, int start, int length, IPEndPoint remoteEndPoint)
	{
		NetPacket packet = PoolGetWithData(PacketProperty.UnconnectedMessage, message, start, length);
		return SendRawAndRecycle(packet, remoteEndPoint) > 0;
	}

	public void TriggerUpdate()
	{
		_updateTriggerEvent.Set();
	}

	public void PollEvents()
	{
		if (_manualMode)
		{
			if (_udpSocketv4 != null)
			{
				ManualReceive(_udpSocketv4, _bufferEndPointv4);
			}
			if (_udpSocketv6 != null && _udpSocketv6 != _udpSocketv4)
			{
				ManualReceive(_udpSocketv6, _bufferEndPointv6);
			}
		}
		else if (!UnsyncedEvents)
		{
			NetEvent pendingEvent;
			lock (_eventLock)
			{
				pendingEvent = _pendingEventHead;
				_pendingEventHead = null;
				_pendingEventTail = null;
			}
			while (pendingEvent != null)
			{
				NetEvent next = pendingEvent.Next;
				ProcessEvent(pendingEvent);
				pendingEvent = next;
			}
		}
	}

	public NetPeer Connect(string address, int port, string key)
	{
		return Connect(address, port, NetDataWriter.FromString(key));
	}

	public NetPeer Connect(string address, int port, NetDataWriter connectionData)
	{
		IPEndPoint ep;
		try
		{
			ep = NetUtils.MakeEndPoint(address, port);
		}
		catch
		{
			CreateEvent(NetEvent.EType.Disconnect, null, null, SocketError.Success, 0, DisconnectReason.UnknownHost, null, DeliveryMethod.Unreliable, 0);
			return null;
		}
		return Connect(ep, connectionData);
	}

	public NetPeer Connect(IPEndPoint target, string key)
	{
		return Connect(target, NetDataWriter.FromString(key));
	}

	public NetPeer Connect(IPEndPoint target, NetDataWriter connectionData)
	{
		if (!IsRunning)
		{
			throw new InvalidOperationException("Client is not running");
		}
		lock (_requestsDict)
		{
			if (_requestsDict.ContainsKey(target))
			{
				return null;
			}
			byte connectionNumber = 0;
			if (TryGetPeer(target, out var peer))
			{
				ConnectionState connectionState = peer.ConnectionState;
				if (connectionState == ConnectionState.Outgoing || connectionState == ConnectionState.Connected)
				{
					return peer;
				}
				connectionNumber = (byte)((peer.ConnectionNum + 1) % 4);
				RemovePeer(peer);
			}
			peer = new NetPeer(this, target, GetNextPeerId(), connectionNumber, connectionData);
			AddPeer(peer);
			return peer;
		}
	}

	public void Stop()
	{
		Stop(sendDisconnectMessages: true);
	}

	public void Stop(bool sendDisconnectMessages)
	{
		if (IsRunning)
		{
			for (NetPeer netPeer = _headPeer; netPeer != null; netPeer = netPeer.NextPeer)
			{
				netPeer.Shutdown(null, 0, 0, !sendDisconnectMessages);
			}
			CloseSocket();
			_updateTriggerEvent.Set();
			if (!_manualMode)
			{
				_logicThread.Join();
				_logicThread = null;
			}
			ClearPeerSet();
			_peerIds = new ConcurrentQueue<int>();
			_lastPeerId = 0;
			_connectedPeersCount = 0;
			_pendingEventHead = null;
			_pendingEventTail = null;
		}
	}

	public int GetPeersCount(ConnectionState peerState)
	{
		int count = 0;
		_peersLock.EnterReadLock();
		for (NetPeer netPeer = _headPeer; netPeer != null; netPeer = netPeer.NextPeer)
		{
			if ((netPeer.ConnectionState & peerState) != 0)
			{
				count++;
			}
		}
		_peersLock.ExitReadLock();
		return count;
	}

	public void GetPeersNonAlloc(List<NetPeer> peers, ConnectionState peerState)
	{
		peers.Clear();
		_peersLock.EnterReadLock();
		for (NetPeer netPeer = _headPeer; netPeer != null; netPeer = netPeer.NextPeer)
		{
			if ((netPeer.ConnectionState & peerState) != 0)
			{
				peers.Add(netPeer);
			}
		}
		_peersLock.ExitReadLock();
	}

	public void DisconnectAll()
	{
		DisconnectAll(null, 0, 0);
	}

	public void DisconnectAll(byte[] data, int start, int count)
	{
		_peersLock.EnterReadLock();
		for (NetPeer netPeer = _headPeer; netPeer != null; netPeer = netPeer.NextPeer)
		{
			DisconnectPeer(netPeer, DisconnectReason.DisconnectPeerCalled, SocketError.Success, force: false, data, start, count, null);
		}
		_peersLock.ExitReadLock();
	}

	public void DisconnectPeerForce(NetPeer peer)
	{
		DisconnectPeerForce(peer, DisconnectReason.DisconnectPeerCalled, SocketError.Success, null);
	}

	public void DisconnectPeer(NetPeer peer)
	{
		DisconnectPeer(peer, null, 0, 0);
	}

	public void DisconnectPeer(NetPeer peer, byte[] data)
	{
		DisconnectPeer(peer, data, 0, data.Length);
	}

	public void DisconnectPeer(NetPeer peer, NetDataWriter writer)
	{
		DisconnectPeer(peer, writer.Data, 0, writer.Length);
	}

	public void DisconnectPeer(NetPeer peer, byte[] data, int start, int count)
	{
		DisconnectPeer(peer, DisconnectReason.DisconnectPeerCalled, SocketError.Success, force: false, data, start, count, null);
	}

	public void CreateNtpRequest(IPEndPoint endPoint)
	{
		_ntpRequests.TryAdd(endPoint, new NtpRequest(endPoint));
	}

	public void CreateNtpRequest(string ntpServerAddress, int port)
	{
		IPEndPoint endPoint = NetUtils.MakeEndPoint(ntpServerAddress, port);
		_ntpRequests.TryAdd(endPoint, new NtpRequest(endPoint));
	}

	public void CreateNtpRequest(string ntpServerAddress)
	{
		IPEndPoint endPoint = NetUtils.MakeEndPoint(ntpServerAddress, 123);
		_ntpRequests.TryAdd(endPoint, new NtpRequest(endPoint));
	}

	public NetPeerEnumerator GetEnumerator()
	{
		return new NetPeerEnumerator(_headPeer);
	}

	IEnumerator<NetPeer> IEnumerable<NetPeer>.GetEnumerator()
	{
		return new NetPeerEnumerator(_headPeer);
	}

	IEnumerator IEnumerable.GetEnumerator()
	{
		return new NetPeerEnumerator(_headPeer);
	}

	private static int HashSetGetPrime(int min)
	{
		int[] primes = Primes;
		foreach (int prime in primes)
		{
			if (prime >= min)
			{
				return prime;
			}
		}
		for (int j = min | 1; j < int.MaxValue; j += 2)
		{
			if (IsPrime(j) && (j - 1) % 101 != 0)
			{
				return j;
			}
		}
		return min;
		static bool IsPrime(int candidate)
		{
			if ((candidate & 1) != 0)
			{
				int limit = (int)Math.Sqrt(candidate);
				for (int divisor = 3; divisor <= limit; divisor += 2)
				{
					if (candidate % divisor == 0)
					{
						return false;
					}
				}
				return true;
			}
			return candidate == 2;
		}
	}

	private void ClearPeerSet()
	{
		_peersLock.EnterWriteLock();
		_headPeer = null;
		if (_lastIndex > 0)
		{
			Array.Clear(_slots, 0, _lastIndex);
			Array.Clear(_buckets, 0, _buckets.Length);
			_lastIndex = 0;
			_count = 0;
			_freeList = -1;
		}
		_peersArray = new NetPeer[32];
		_peersLock.ExitWriteLock();
	}

	private bool ContainsPeer(NetPeer item)
	{
		if (_buckets != null)
		{
			int hashCode = item.GetHashCode() & 0x7FFFFFFF;
			for (int i = _buckets[hashCode % _buckets.Length] - 1; i >= 0; i = _slots[i].Next)
			{
				if (_slots[i].HashCode == hashCode && _slots[i].Value.Equals(item))
				{
					return true;
				}
			}
		}
		return false;
	}

	public NetPeer GetPeerById(int id)
	{
		if (id < 0 || id >= _peersArray.Length)
		{
			return null;
		}
		return _peersArray[id];
	}

	public bool TryGetPeerById(int id, out NetPeer peer)
	{
		peer = GetPeerById(id);
		return peer != null;
	}

	private void AddPeer(NetPeer peer)
	{
		_peersLock.EnterWriteLock();
		if (_headPeer != null)
		{
			peer.NextPeer = _headPeer;
			_headPeer.PrevPeer = peer;
		}
		_headPeer = peer;
		AddPeerToSet(peer);
		if (peer.Id >= _peersArray.Length)
		{
			int newSize = _peersArray.Length * 2;
			while (peer.Id >= newSize)
			{
				newSize *= 2;
			}
			Array.Resize(ref _peersArray, newSize);
		}
		_peersArray[peer.Id] = peer;
		_peersLock.ExitWriteLock();
	}

	private void RemovePeer(NetPeer peer)
	{
		_peersLock.EnterWriteLock();
		RemovePeerInternal(peer);
		_peersLock.ExitWriteLock();
	}

	private void RemovePeerInternal(NetPeer peer)
	{
		if (RemovePeerFromSet(peer))
		{
			if (peer == _headPeer)
			{
				_headPeer = peer.NextPeer;
			}
			if (peer.PrevPeer != null)
			{
				peer.PrevPeer.NextPeer = peer.NextPeer;
			}
			if (peer.NextPeer != null)
			{
				peer.NextPeer.PrevPeer = peer.PrevPeer;
			}
			peer.PrevPeer = null;
			_peersArray[peer.Id] = null;
			_peerIds.Enqueue(peer.Id);
		}
	}

	private bool RemovePeerFromSet(NetPeer peer)
	{
		if (_buckets == null)
		{
			return false;
		}
		int hashCode = peer.GetHashCode() & 0x7FFFFFFF;
		int bucket = hashCode % _buckets.Length;
		int last = -1;
		for (int i = _buckets[bucket] - 1; i >= 0; i = _slots[i].Next)
		{
			if (_slots[i].HashCode == hashCode && _slots[i].Value.Equals(peer))
			{
				if (last < 0)
				{
					_buckets[bucket] = _slots[i].Next + 1;
				}
				else
				{
					_slots[last].Next = _slots[i].Next;
				}
				_slots[i].HashCode = -1;
				_slots[i].Value = null;
				_slots[i].Next = _freeList;
				_count--;
				if (_count == 0)
				{
					_lastIndex = 0;
					_freeList = -1;
				}
				else
				{
					_freeList = i;
				}
				return true;
			}
			last = i;
		}
		return false;
	}

	private bool TryGetPeer(IPEndPoint endPoint, out NetPeer actualValue)
	{
		if (_buckets != null)
		{
			int hashCode = (UseNativeSockets ? endPoint.GetHashCode() : endPoint.Serialize().GetHashCode()) & 0x7FFFFFFF;
			_peersLock.EnterReadLock();
			for (int i = _buckets[hashCode % _buckets.Length] - 1; i >= 0; i = _slots[i].Next)
			{
				if (_slots[i].HashCode == hashCode && _slots[i].Value.Equals(endPoint))
				{
					actualValue = _slots[i].Value;
					_peersLock.ExitReadLock();
					return true;
				}
			}
			_peersLock.ExitReadLock();
		}
		actualValue = null;
		return false;
	}

	private bool TryGetPeer(SocketAddress saddr, out NetPeer actualValue)
	{
		if (_buckets != null)
		{
			int hashCode = saddr.GetHashCode() & 0x7FFFFFFF;
			_peersLock.EnterReadLock();
			for (int i = _buckets[hashCode % _buckets.Length] - 1; i >= 0; i = _slots[i].Next)
			{
				if (_slots[i].HashCode == hashCode && _slots[i].Value.Serialize().Equals(saddr))
				{
					actualValue = _slots[i].Value;
					_peersLock.ExitReadLock();
					return true;
				}
			}
			_peersLock.ExitReadLock();
		}
		actualValue = null;
		return false;
	}

	private bool AddPeerToSet(NetPeer value)
	{
		if (_buckets == null)
		{
			int size = HashSetGetPrime(0);
			_buckets = new int[size];
			_slots = new Slot[size];
		}
		int hashCode = value.GetHashCode() & 0x7FFFFFFF;
		int bucket = hashCode % _buckets.Length;
		for (int i = _buckets[hashCode % _buckets.Length] - 1; i >= 0; i = _slots[i].Next)
		{
			if (_slots[i].HashCode == hashCode && _slots[i].Value.Equals(value))
			{
				return false;
			}
		}
		int index;
		if (_freeList >= 0)
		{
			index = _freeList;
			_freeList = _slots[index].Next;
		}
		else
		{
			if (_lastIndex == _slots.Length)
			{
				int newSize = 2 * _count;
				newSize = (((uint)newSize > 2147483587u && 2147483587 > _count) ? 2147483587 : HashSetGetPrime(newSize));
				Slot[] newSlots = new Slot[newSize];
				Array.Copy(_slots, 0, newSlots, 0, _lastIndex);
				_buckets = new int[newSize];
				for (int j = 0; j < _lastIndex; j++)
				{
					int b = newSlots[j].HashCode % newSize;
					newSlots[j].Next = _buckets[b] - 1;
					_buckets[b] = j + 1;
				}
				_slots = newSlots;
				bucket = hashCode % _buckets.Length;
			}
			index = _lastIndex;
			_lastIndex++;
		}
		_slots[index].HashCode = hashCode;
		_slots[index].Value = value;
		_slots[index].Next = _buckets[bucket] - 1;
		_buckets[bucket] = index + 1;
		_count++;
		return true;
	}

	private NetPacket PoolGetWithData(PacketProperty property, byte[] data, int start, int length)
	{
		int headerSize = NetPacket.GetHeaderSize(property);
		NetPacket packet = PoolGetPacket(length + headerSize);
		packet.Property = property;
		Buffer.BlockCopy(data, start, packet.RawData, headerSize, length);
		return packet;
	}

	private NetPacket PoolGetWithProperty(PacketProperty property, int size)
	{
		NetPacket netPacket = PoolGetPacket(size + NetPacket.GetHeaderSize(property));
		netPacket.Property = property;
		return netPacket;
	}

	private NetPacket PoolGetWithProperty(PacketProperty property)
	{
		NetPacket netPacket = PoolGetPacket(NetPacket.GetHeaderSize(property));
		netPacket.Property = property;
		return netPacket;
	}

	internal NetPacket PoolGetPacket(int size)
	{
		if (size > NetConstants.MaxPacketSize)
		{
			return new NetPacket(size);
		}
		NetPacket packet;
		lock (_poolLock)
		{
			packet = _poolHead;
			if (packet == null)
			{
				return new NetPacket(size);
			}
			_poolHead = _poolHead.Next;
			_poolCount--;
		}
		packet.Size = size;
		if (packet.RawData.Length < size)
		{
			packet.RawData = new byte[size];
		}
		return packet;
	}

	internal void PoolRecycle(NetPacket packet)
	{
		if (packet.RawData.Length > NetConstants.MaxPacketSize || _poolCount >= PacketPoolSize)
		{
			return;
		}
		packet.RawData[0] = 0;
		lock (_poolLock)
		{
			packet.Next = _poolHead;
			_poolHead = packet;
			_poolCount++;
		}
	}

	static NetManager()
	{
	}

	private bool ProcessError(SocketException ex)
	{
		switch (ex.SocketErrorCode)
		{
		case SocketError.NotConnected:
			NotConnected = true;
			return true;
		case SocketError.OperationAborted:
		case SocketError.Interrupted:
		case SocketError.NotSocket:
			return true;
		default:
			NetDebug.WriteError($"[R]Error code: {(int)ex.SocketErrorCode} - {ex}");
			CreateEvent(NetEvent.EType.Error, null, null, ex.SocketErrorCode, 0, DisconnectReason.ConnectionFailed, null, DeliveryMethod.Unreliable, 0);
			break;
		case SocketError.WouldBlock:
		case SocketError.MessageSize:
		case SocketError.NetworkReset:
		case SocketError.ConnectionReset:
		case SocketError.TimedOut:
			break;
		}
		return false;
	}

	private void ManualReceive(Socket socket, EndPoint bufferEndPoint)
	{
		try
		{
			int packetsReceived = 0;
			while (socket.Available > 0)
			{
				ReceiveFrom(socket, ref bufferEndPoint);
				packetsReceived++;
				if (packetsReceived == MaxPacketsReceivePerUpdate)
				{
					break;
				}
			}
		}
		catch (SocketException ex)
		{
			ProcessError(ex);
		}
		catch (ObjectDisposedException)
		{
		}
		catch (Exception ex3)
		{
			NetDebug.WriteError("[NM] SocketReceiveThread error: " + ex3);
		}
	}

	private void NativeReceiveLogic()
	{
		nint socketHandle4 = _udpSocketv4.Handle;
		nint socketHandle6 = _udpSocketv6?.Handle ?? IntPtr.Zero;
		byte[] addrBuffer4 = new byte[16];
		byte[] addrBuffer6 = new byte[28];
		IPEndPoint tempEndPoint = new IPEndPoint(IPAddress.Any, 0);
		List<Socket> selectReadList = new List<Socket>(2);
		Socket socketv4 = _udpSocketv4;
		Socket socketV6 = _udpSocketv6;
		NetPacket packet = PoolGetPacket(NetConstants.MaxPacketSize);
		while (IsRunning)
		{
			if (socketV6 == null)
			{
				if (!NativeReceiveFrom(socketHandle4, addrBuffer4))
				{
					break;
				}
				continue;
			}
			bool messageReceived = false;
			if (socketv4.Available != 0 || selectReadList.Contains(socketv4))
			{
				if (!NativeReceiveFrom(socketHandle4, addrBuffer4))
				{
					break;
				}
				messageReceived = true;
			}
			if (socketV6.Available != 0 || selectReadList.Contains(socketV6))
			{
				if (!NativeReceiveFrom(socketHandle6, addrBuffer6))
				{
					break;
				}
				messageReceived = true;
			}
			selectReadList.Clear();
			if (messageReceived)
			{
				continue;
			}
			selectReadList.Add(socketv4);
			selectReadList.Add(socketV6);
			try
			{
				Socket.Select(selectReadList, null, null, 500000);
			}
			catch (SocketException ex)
			{
				if (ProcessError(ex))
				{
					break;
				}
			}
			catch (ObjectDisposedException)
			{
				break;
			}
			catch (ThreadAbortException)
			{
				break;
			}
			catch (Exception ex4)
			{
				NetDebug.WriteError("[NM] SocketReceiveThread error: " + ex4);
			}
		}
		bool NativeReceiveFrom(nint s, byte[] address)
		{
			int addrSize = address.Length;
			packet.Size = NativeSocket.RecvFrom(s, packet.RawData, NetConstants.MaxPacketSize, address, ref addrSize);
			if (packet.Size == 0)
			{
				return true;
			}
			if (packet.Size == -1)
			{
				return !ProcessError(new SocketException((int)NativeSocket.GetSocketError()));
			}
			short family = (short)((address[1] << 8) | address[0]);
			tempEndPoint.Port = (ushort)((address[2] << 8) | address[3]);
			if ((NativeSocket.UnixMode && family == 10) || (!NativeSocket.UnixMode && family == 23))
			{
				uint scope = (uint)((address[27] << 24) + (address[26] << 16) + (address[25] << 8) + address[24]);
				tempEndPoint.Address = new IPAddress(new ReadOnlySpan<byte>(address, 8, 16), scope);
			}
			else
			{
				long ipv4Addr = (uint)((address[4] & 0xFF) | ((address[5] << 8) & 0xFF00) | ((address[6] << 16) & 0xFF0000) | (address[7] << 24));
				tempEndPoint.Address = new IPAddress(ipv4Addr);
			}
			if (TryGetPeer(tempEndPoint, out var peer))
			{
				OnMessageReceived(packet, peer);
			}
			else
			{
				OnMessageReceived(packet, tempEndPoint);
				tempEndPoint = new IPEndPoint(IPAddress.Any, 0);
			}
			packet = PoolGetPacket(NetConstants.MaxPacketSize);
			return true;
		}
	}

	private void ReceiveFrom(Socket s, ref EndPoint bufferEndPoint)
	{
		NetPacket packet = PoolGetPacket(NetConstants.MaxPacketSize);
		SocketAddress sockAddr = ((s.AddressFamily == AddressFamily.InterNetwork) ? _sockAddrCacheV4 : _sockAddrCacheV6);
		packet.Size = s.ReceiveFrom(packet, SocketFlags.None, sockAddr);
		OnMessageReceived(packet, TryGetPeer(sockAddr, out var peer) ? peer : ((IPEndPoint)bufferEndPoint.Create(sockAddr)));
	}

	private void ReceiveLogic()
	{
		EndPoint bufferEndPoint4 = new IPEndPoint(IPAddress.Any, 0);
		EndPoint bufferEndPoint6 = new IPEndPoint(IPAddress.IPv6Any, 0);
		List<Socket> selectReadList = new List<Socket>(2);
		Socket socketv4 = _udpSocketv4;
		Socket socketV6 = _udpSocketv6;
		while (IsRunning)
		{
			try
			{
				if (socketV6 == null)
				{
					if (socketv4.Available != 0 || socketv4.Poll(500000, SelectMode.SelectRead))
					{
						ReceiveFrom(socketv4, ref bufferEndPoint4);
					}
					continue;
				}
				bool messageReceived = false;
				if (socketv4.Available != 0 || selectReadList.Contains(socketv4))
				{
					ReceiveFrom(socketv4, ref bufferEndPoint4);
					messageReceived = true;
				}
				if (socketV6.Available != 0 || selectReadList.Contains(socketV6))
				{
					ReceiveFrom(socketV6, ref bufferEndPoint6);
					messageReceived = true;
				}
				selectReadList.Clear();
				if (!messageReceived)
				{
					selectReadList.Add(socketv4);
					selectReadList.Add(socketV6);
					Socket.Select(selectReadList, null, null, 500000);
				}
			}
			catch (SocketException ex)
			{
				if (ProcessError(ex))
				{
					break;
				}
			}
			catch (ObjectDisposedException)
			{
				break;
			}
			catch (ThreadAbortException)
			{
				break;
			}
			catch (Exception ex4)
			{
				NetDebug.WriteError("[NM] SocketReceiveThread error: " + ex4);
			}
		}
	}

	public bool Start(IPAddress addressIPv4, IPAddress addressIPv6, int port, bool manualMode)
	{
		if (IsRunning && !NotConnected)
		{
			return false;
		}
		NotConnected = false;
		_manualMode = manualMode;
		UseNativeSockets = UseNativeSockets && NativeSocket.IsSupported;
		_udpSocketv4 = new Socket(AddressFamily.InterNetwork, SocketType.Dgram, ProtocolType.Udp);
		if (!BindSocket(_udpSocketv4, new IPEndPoint(addressIPv4, port)))
		{
			return false;
		}
		LocalPort = ((IPEndPoint)_udpSocketv4.LocalEndPoint).Port;
		IsRunning = true;
		if (_manualMode)
		{
			_bufferEndPointv4 = new IPEndPoint(IPAddress.Any, 0);
		}
		if (IPv6Support && IPv6Enabled)
		{
			_udpSocketv6 = new Socket(AddressFamily.InterNetworkV6, SocketType.Dgram, ProtocolType.Udp);
			if (BindSocket(_udpSocketv6, new IPEndPoint(addressIPv6, LocalPort)))
			{
				if (_manualMode)
				{
					_bufferEndPointv6 = new IPEndPoint(IPAddress.IPv6Any, 0);
				}
			}
			else
			{
				_udpSocketv6 = null;
			}
		}
		if (!manualMode)
		{
			ThreadStart ts = ReceiveLogic;
			if (UseNativeSockets)
			{
				ts = NativeReceiveLogic;
			}
			_receiveThread = new Thread(ts)
			{
				Name = $"ReceiveThread({LocalPort})",
				IsBackground = true
			};
			_receiveThread.Start();
			if (_logicThread == null)
			{
				_logicThread = new Thread(UpdateLogic)
				{
					Name = "LogicThread",
					IsBackground = true
				};
				_logicThread.Start();
			}
		}
		return true;
	}

	private bool BindSocket(Socket socket, IPEndPoint ep)
	{
		socket.ReceiveTimeout = 500;
		socket.SendTimeout = 500;
		socket.ReceiveBufferSize = 1048576;
		socket.SendBufferSize = 1048576;
		socket.Blocking = true;
		if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
		{
			try
			{
				socket.IOControl(-1744830452, new byte[1], null);
			}
			catch
			{
			}
		}
		try
		{
			socket.ExclusiveAddressUse = !ReuseAddress;
			socket.SetSocketOption(SocketOptionLevel.Socket, SocketOptionName.ReuseAddress, ReuseAddress);
			socket.SetSocketOption(SocketOptionLevel.Socket, SocketOptionName.DontRoute, DontRoute);
		}
		catch
		{
		}
		if (ep.AddressFamily == AddressFamily.InterNetwork)
		{
			Ttl = 255;
			try
			{
				socket.EnableBroadcast = true;
			}
			catch (SocketException ex)
			{
				NetDebug.WriteError($"[B]Broadcast error: {ex.SocketErrorCode}");
			}
			if (!RuntimeInformation.IsOSPlatform(OSPlatform.OSX))
			{
				try
				{
					socket.DontFragment = true;
				}
				catch (SocketException ex2)
				{
					NetDebug.WriteError($"[B]DontFragment error: {ex2.SocketErrorCode}");
				}
			}
		}
		try
		{
			socket.Bind(ep);
			if (ep.AddressFamily == AddressFamily.InterNetworkV6)
			{
				try
				{
					socket.SetSocketOption(SocketOptionLevel.IPv6, SocketOptionName.AddMembership, new IPv6MulticastOption(MulticastAddressV6));
				}
				catch (Exception)
				{
				}
			}
		}
		catch (SocketException ex4)
		{
			switch (ex4.SocketErrorCode)
			{
			case SocketError.AddressAlreadyInUse:
				if (socket.AddressFamily == AddressFamily.InterNetworkV6)
				{
					try
					{
						socket.DualMode = false;
						socket.Bind(ep);
					}
					catch (SocketException ex5)
					{
						NetDebug.WriteError($"[B]Bind exception: {ex5}, errorCode: {ex5.SocketErrorCode}");
						return false;
					}
					return true;
				}
				break;
			case SocketError.AddressFamilyNotSupported:
				return true;
			}
			NetDebug.WriteError($"[B]Bind exception: {ex4}, errorCode: {ex4.SocketErrorCode}");
			return false;
		}
		return true;
	}

	internal int SendRawAndRecycle(NetPacket packet, IPEndPoint remoteEndPoint)
	{
		int result = SendRaw(packet.RawData, 0, packet.Size, remoteEndPoint);
		PoolRecycle(packet);
		return result;
	}

	internal int SendRaw(NetPacket packet, IPEndPoint remoteEndPoint)
	{
		return SendRaw(packet.RawData, 0, packet.Size, remoteEndPoint);
	}

	internal unsafe int SendRaw(byte[] message, int start, int length, IPEndPoint remoteEndPoint)
	{
		if (!IsRunning)
		{
			return 0;
		}
		NetPacket expandedPacket = null;
		if (_extraPacketLayer != null)
		{
			expandedPacket = PoolGetPacket(length + _extraPacketLayer.ExtraPacketSizeForLayer);
			Buffer.BlockCopy(message, start, expandedPacket.RawData, 0, length);
			start = 0;
			_extraPacketLayer.ProcessOutBoundPacket(ref remoteEndPoint, ref expandedPacket.RawData, ref start, ref length);
			message = expandedPacket.RawData;
		}
		Socket socket = _udpSocketv4;
		if (remoteEndPoint.AddressFamily == AddressFamily.InterNetworkV6 && IPv6Support)
		{
			socket = _udpSocketv6;
			if (socket == null)
			{
				return 0;
			}
		}
		int result;
		try
		{
			if (UseNativeSockets && remoteEndPoint is NetPeer peer)
			{
				fixed (byte* dataWithOffset = &message[start])
				{
					result = NativeSocket.SendTo(socket.Handle, dataWithOffset, length, peer.NativeAddress, peer.NativeAddress.Length);
				}
				if (result == -1)
				{
					throw NativeSocket.GetSocketException();
				}
			}
			else
			{
				result = socket.SendTo(new ReadOnlySpan<byte>(message, start, length), SocketFlags.None, remoteEndPoint.Serialize());
			}
		}
		catch (SocketException ex)
		{
			switch (ex.SocketErrorCode)
			{
			case SocketError.Interrupted:
			case SocketError.NoBufferSpaceAvailable:
				return 0;
			case SocketError.MessageSize:
				return 0;
			case SocketError.NetworkUnreachable:
			case SocketError.HostUnreachable:
				if (DisconnectOnUnreachable && remoteEndPoint is NetPeer peer2)
				{
					DisconnectPeerForce(peer2, (ex.SocketErrorCode == SocketError.HostUnreachable) ? DisconnectReason.HostUnreachable : DisconnectReason.NetworkUnreachable, ex.SocketErrorCode, null);
				}
				CreateEvent(NetEvent.EType.Error, null, remoteEndPoint, ex.SocketErrorCode, 0, DisconnectReason.ConnectionFailed, null, DeliveryMethod.Unreliable, 0);
				return -1;
			case SocketError.Shutdown:
				CreateEvent(NetEvent.EType.Error, null, remoteEndPoint, ex.SocketErrorCode, 0, DisconnectReason.ConnectionFailed, null, DeliveryMethod.Unreliable, 0);
				return -1;
			default:
				NetDebug.WriteError($"[S] {ex}");
				return -1;
			}
		}
		catch (Exception value)
		{
			NetDebug.WriteError($"[S] {value}");
			return 0;
		}
		finally
		{
			if (expandedPacket != null)
			{
				PoolRecycle(expandedPacket);
			}
		}
		if (result <= 0)
		{
			return 0;
		}
		if (EnableStatistics)
		{
			Statistics.IncrementPacketsSent();
			Statistics.AddBytesSent(length);
		}
		return result;
	}

	public bool SendBroadcast(NetDataWriter writer, int port)
	{
		return SendBroadcast(writer.Data, 0, writer.Length, port);
	}

	public bool SendBroadcast(byte[] data, int port)
	{
		return SendBroadcast(data, 0, data.Length, port);
	}

	public bool SendBroadcast(byte[] data, int start, int length, int port)
	{
		if (!IsRunning)
		{
			return false;
		}
		NetPacket packet;
		if (_extraPacketLayer != null)
		{
			int headerSize = NetPacket.GetHeaderSize(PacketProperty.Broadcast);
			packet = PoolGetPacket(headerSize + length + _extraPacketLayer.ExtraPacketSizeForLayer);
			packet.Property = PacketProperty.Broadcast;
			Buffer.BlockCopy(data, start, packet.RawData, headerSize, length);
			int checksumComputeStart = 0;
			int preCrcLength = length + headerSize;
			IPEndPoint emptyEp = null;
			_extraPacketLayer.ProcessOutBoundPacket(ref emptyEp, ref packet.RawData, ref checksumComputeStart, ref preCrcLength);
		}
		else
		{
			packet = PoolGetWithData(PacketProperty.Broadcast, data, start, length);
		}
		bool broadcastSuccess = false;
		bool multicastSuccess = false;
		try
		{
			broadcastSuccess = _udpSocketv4.SendTo(packet.RawData, 0, packet.Size, SocketFlags.None, new IPEndPoint(IPAddress.Broadcast, port)) > 0;
			if (_udpSocketv6 != null)
			{
				multicastSuccess = _udpSocketv6.SendTo(packet.RawData, 0, packet.Size, SocketFlags.None, new IPEndPoint(MulticastAddressV6, port)) > 0;
			}
		}
		catch (SocketException ex)
		{
			if (ex.SocketErrorCode == SocketError.HostUnreachable)
			{
				return broadcastSuccess;
			}
			NetDebug.WriteError($"[S][MCAST] {ex}");
			return broadcastSuccess;
		}
		catch (Exception value)
		{
			NetDebug.WriteError($"[S][MCAST] {value}");
			return broadcastSuccess;
		}
		finally
		{
			PoolRecycle(packet);
		}
		return broadcastSuccess | multicastSuccess;
	}

	private void CloseSocket()
	{
		IsRunning = false;
		_udpSocketv4?.Close();
		_udpSocketv6?.Close();
		_udpSocketv4 = null;
		_udpSocketv6 = null;
		if (_receiveThread != null && _receiveThread != Thread.CurrentThread)
		{
			_receiveThread.Join();
		}
		_receiveThread = null;
	}
}
