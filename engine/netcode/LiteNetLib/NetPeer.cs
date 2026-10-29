using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Diagnostics;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using LiteNetLib.Utils;

namespace LiteNetLib;

public class NetPeer : IPEndPoint
{
	private class IncomingFragments
	{
		public NetPacket[] Fragments;

		public int ReceivedCount;

		public int TotalSize;

		public byte ChannelId;
	}

	private int _rtt;

	private int _avgRtt;

	private int _rttCount;

	private double _resendDelay = 27.0;

	private int _pingSendTimer;

	private int _rttResetTimer;

	private readonly Stopwatch _pingTimer = new Stopwatch();

	private int _timeSinceLastPacket;

	private long _remoteDelta;

	private readonly object _shutdownLock = new object();

	internal volatile NetPeer NextPeer;

	internal NetPeer PrevPeer;

	private readonly Queue<NetPacket> _unreliableChannel;

	private readonly ConcurrentQueue<BaseChannel> _channelSendQueue;

	private readonly BaseChannel[] _channels;

	private int _mtu;

	private int _mtuIdx;

	private bool _finishMtu;

	private int _mtuCheckTimer;

	private int _mtuCheckAttempts;

	private const int MtuCheckDelay = 1000;

	private const int MaxMtuCheckAttempts = 4;

	private readonly object _mtuMutex = new object();

	private int _fragmentId;

	private readonly Dictionary<ushort, IncomingFragments> _holdedFragments;

	private readonly Dictionary<ushort, ushort> _deliveredFragments;

	private readonly NetPacket _mergeData;

	private int _mergePos;

	private int _mergeCount;

	private int _connectAttempts;

	private int _connectTimer;

	private long _connectTime;

	private byte _connectNum;

	private ConnectionState _connectionState;

	private NetPacket _shutdownPacket;

	private const int ShutdownDelay = 300;

	private int _shutdownTimer;

	private readonly NetPacket _pingPacket;

	private readonly NetPacket _pongPacket;

	private readonly NetPacket _connectRequestPacket;

	private readonly NetPacket _connectAcceptPacket;

	public readonly NetManager NetManager;

	public readonly int Id;

	public object Tag;

	public readonly NetStatistics Statistics;

	private SocketAddress _cachedSocketAddr;

	private int _cachedHashCode;

	internal byte[] NativeAddress;

	internal byte ConnectionNum
	{
		get
		{
			return _connectNum;
		}
		private set
		{
			_connectNum = value;
			_mergeData.ConnectionNumber = value;
			_pingPacket.ConnectionNumber = value;
			_pongPacket.ConnectionNumber = value;
		}
	}

	public ConnectionState ConnectionState => _connectionState;

	internal long ConnectTime => _connectTime;

	public int RemoteId { get; private set; }

	public int Ping => _avgRtt / 2;

	public int RoundTripTime => _avgRtt;

	public int Mtu => _mtu;

	public long RemoteTimeDelta => _remoteDelta;

	public DateTime RemoteUtcTime => new DateTime(DateTime.UtcNow.Ticks + _remoteDelta);

	public int TimeSinceLastPacket => _timeSinceLastPacket;

	internal double ResendDelay => _resendDelay;

	public override SocketAddress Serialize()
	{
		return _cachedSocketAddr;
	}

	public override int GetHashCode()
	{
		return _cachedHashCode;
	}

	internal NetPeer(NetManager netManager, IPEndPoint remoteEndPoint, int id)
		: base(remoteEndPoint.Address, remoteEndPoint.Port)
	{
		Id = id;
		Statistics = new NetStatistics();
		NetManager = netManager;
		_cachedSocketAddr = base.Serialize();
		if (NetManager.UseNativeSockets)
		{
			NativeAddress = new byte[_cachedSocketAddr.Size];
			for (int i = 0; i < _cachedSocketAddr.Size; i++)
			{
				NativeAddress[i] = _cachedSocketAddr[i];
			}
		}
		_cachedHashCode = (NetManager.UseNativeSockets ? base.GetHashCode() : _cachedSocketAddr.GetHashCode());
		ResetMtu();
		_connectionState = ConnectionState.Connected;
		_mergeData = new NetPacket(PacketProperty.Merged, NetConstants.MaxPacketSize);
		_pongPacket = new NetPacket(PacketProperty.Pong, 0);
		_pingPacket = new NetPacket(PacketProperty.Ping, 0)
		{
			Sequence = 1
		};
		_unreliableChannel = new Queue<NetPacket>();
		_holdedFragments = new Dictionary<ushort, IncomingFragments>();
		_deliveredFragments = new Dictionary<ushort, ushort>();
		_channels = new BaseChannel[netManager.ChannelsCount * 4];
		_channelSendQueue = new ConcurrentQueue<BaseChannel>();
	}

	internal void InitiateEndPointChange()
	{
		ResetMtu();
		_connectionState = ConnectionState.EndPointChange;
	}

	internal void FinishEndPointChange(IPEndPoint newEndPoint)
	{
		if (_connectionState != ConnectionState.EndPointChange)
		{
			return;
		}
		_connectionState = ConnectionState.Connected;
		base.Address = newEndPoint.Address;
		base.Port = newEndPoint.Port;
		if (NetManager.UseNativeSockets)
		{
			NativeAddress = new byte[_cachedSocketAddr.Size];
			for (int i = 0; i < _cachedSocketAddr.Size; i++)
			{
				NativeAddress[i] = _cachedSocketAddr[i];
			}
		}
		_cachedSocketAddr = base.Serialize();
		_cachedHashCode = (NetManager.UseNativeSockets ? base.GetHashCode() : _cachedSocketAddr.GetHashCode());
	}

	internal void ResetMtu()
	{
		_finishMtu = false;
		if (NetManager.MtuOverride > 0)
		{
			OverrideMtu(NetManager.MtuOverride);
		}
		else if (NetManager.UseSafeMtu)
		{
			SetMtu(0);
		}
		else
		{
			SetMtu(1);
		}
	}

	private void SetMtu(int mtuIdx)
	{
		_mtuIdx = mtuIdx;
		_mtu = NetConstants.PossibleMtu[mtuIdx] - NetManager.ExtraPacketSizeForLayer;
	}

	private void OverrideMtu(int mtuValue)
	{
		_mtu = mtuValue;
		_finishMtu = true;
	}

	public int GetPacketsCountInReliableQueue(byte channelNumber, bool ordered)
	{
		int idx = channelNumber * 4 + (ordered ? 2 : 0);
		BaseChannel channel = _channels[idx];
		if (channel == null)
		{
			return 0;
		}
		return ((ReliableChannel)channel).PacketsInQueue;
	}

	public PooledPacket CreatePacketFromPool(DeliveryMethod deliveryMethod, byte channelNumber)
	{
		int mtu = _mtu;
		NetPacket packet = NetManager.PoolGetPacket(mtu);
		if (deliveryMethod == DeliveryMethod.Unreliable)
		{
			packet.Property = PacketProperty.Unreliable;
			return new PooledPacket(packet, mtu, 0);
		}
		packet.Property = PacketProperty.Channeled;
		return new PooledPacket(packet, mtu, (byte)((uint)(channelNumber * 4) + (uint)deliveryMethod));
	}

	public void SendPooledPacket(PooledPacket packet, int userDataSize)
	{
		if (_connectionState != ConnectionState.Connected)
		{
			return;
		}
		packet._packet.Size = packet.UserDataOffset + userDataSize;
		if (packet._packet.Property == PacketProperty.Channeled)
		{
			CreateChannel(packet._channelNumber).AddToQueue(packet._packet);
			return;
		}
		lock (_unreliableChannel)
		{
			_unreliableChannel.Enqueue(packet._packet);
		}
	}

	private BaseChannel CreateChannel(byte idx)
	{
		BaseChannel newChannel = _channels[idx];
		if (newChannel != null)
		{
			return newChannel;
		}
		switch ((DeliveryMethod)(byte)(idx % 4))
		{
		case DeliveryMethod.ReliableUnordered:
			newChannel = new ReliableChannel(this, ordered: false, idx);
			break;
		case DeliveryMethod.Sequenced:
			newChannel = new SequencedChannel(this, reliable: false, idx);
			break;
		case DeliveryMethod.ReliableOrdered:
			newChannel = new ReliableChannel(this, ordered: true, idx);
			break;
		case DeliveryMethod.ReliableSequenced:
			newChannel = new SequencedChannel(this, reliable: true, idx);
			break;
		}
		BaseChannel prevChannel = Interlocked.CompareExchange(ref _channels[idx], newChannel, null);
		if (prevChannel != null)
		{
			return prevChannel;
		}
		return newChannel;
	}

	internal NetPeer(NetManager netManager, IPEndPoint remoteEndPoint, int id, byte connectNum, NetDataWriter connectData)
		: this(netManager, remoteEndPoint, id)
	{
		_connectTime = DateTime.UtcNow.Ticks;
		_connectionState = ConnectionState.Outgoing;
		ConnectionNum = connectNum;
		_connectRequestPacket = NetConnectRequestPacket.Make(connectData, remoteEndPoint.Serialize(), _connectTime, id);
		_connectRequestPacket.ConnectionNumber = connectNum;
		NetManager.SendRaw(_connectRequestPacket, this);
	}

	internal NetPeer(NetManager netManager, ConnectionRequest request, int id)
		: this(netManager, request.RemoteEndPoint, id)
	{
		_connectTime = request.InternalPacket.ConnectionTime;
		ConnectionNum = request.InternalPacket.ConnectionNumber;
		RemoteId = request.InternalPacket.PeerId;
		_connectAcceptPacket = NetConnectAcceptPacket.Make(_connectTime, ConnectionNum, id);
		_connectionState = ConnectionState.Connected;
		NetManager.SendRaw(_connectAcceptPacket, this);
	}

	internal void Reject(NetConnectRequestPacket requestData, byte[] data, int start, int length)
	{
		_connectTime = requestData.ConnectionTime;
		_connectNum = requestData.ConnectionNumber;
		Shutdown(data, start, length, force: false);
	}

	internal bool ProcessConnectAccept(NetConnectAcceptPacket packet)
	{
		if (_connectionState != ConnectionState.Outgoing)
		{
			return false;
		}
		if (packet.ConnectionTime != _connectTime)
		{
			return false;
		}
		ConnectionNum = packet.ConnectionNumber;
		RemoteId = packet.PeerId;
		Interlocked.Exchange(ref _timeSinceLastPacket, 0);
		_connectionState = ConnectionState.Connected;
		return true;
	}

	public int GetMaxSinglePacketSize(DeliveryMethod options)
	{
		return _mtu - NetPacket.GetHeaderSize((options != DeliveryMethod.Unreliable) ? PacketProperty.Channeled : PacketProperty.Unreliable);
	}

	public void SendWithDeliveryEvent(byte[] data, byte channelNumber, DeliveryMethod deliveryMethod, object userData)
	{
		if (deliveryMethod != DeliveryMethod.ReliableOrdered && deliveryMethod != DeliveryMethod.ReliableUnordered)
		{
			throw new ArgumentException("Delivery event will work only for ReliableOrdered/Unordered packets");
		}
		SendInternal(data, 0, data.Length, channelNumber, deliveryMethod, userData);
	}

	public void SendWithDeliveryEvent(byte[] data, int start, int length, byte channelNumber, DeliveryMethod deliveryMethod, object userData)
	{
		if (deliveryMethod != DeliveryMethod.ReliableOrdered && deliveryMethod != DeliveryMethod.ReliableUnordered)
		{
			throw new ArgumentException("Delivery event will work only for ReliableOrdered/Unordered packets");
		}
		SendInternal(data, start, length, channelNumber, deliveryMethod, userData);
	}

	public void SendWithDeliveryEvent(NetDataWriter dataWriter, byte channelNumber, DeliveryMethod deliveryMethod, object userData)
	{
		if (deliveryMethod != DeliveryMethod.ReliableOrdered && deliveryMethod != DeliveryMethod.ReliableUnordered)
		{
			throw new ArgumentException("Delivery event will work only for ReliableOrdered/Unordered packets");
		}
		SendInternal(dataWriter.Data, 0, dataWriter.Length, channelNumber, deliveryMethod, userData);
	}

	public void Send(byte[] data, DeliveryMethod deliveryMethod)
	{
		SendInternal(data, 0, data.Length, 0, deliveryMethod, null);
	}

	public void Send(NetDataWriter dataWriter, DeliveryMethod deliveryMethod)
	{
		SendInternal(dataWriter.Data, 0, dataWriter.Length, 0, deliveryMethod, null);
	}

	public void Send(byte[] data, int start, int length, DeliveryMethod options)
	{
		SendInternal(data, start, length, 0, options, null);
	}

	public void Send(byte[] data, byte channelNumber, DeliveryMethod deliveryMethod)
	{
		SendInternal(data, 0, data.Length, channelNumber, deliveryMethod, null);
	}

	public void Send(NetDataWriter dataWriter, byte channelNumber, DeliveryMethod deliveryMethod)
	{
		SendInternal(dataWriter.Data, 0, dataWriter.Length, channelNumber, deliveryMethod, null);
	}

	public void Send(byte[] data, int start, int length, byte channelNumber, DeliveryMethod deliveryMethod)
	{
		SendInternal(data, start, length, channelNumber, deliveryMethod, null);
	}

	private void SendInternal(byte[] data, int start, int length, byte channelNumber, DeliveryMethod deliveryMethod, object userData)
	{
		if (_connectionState != ConnectionState.Connected || channelNumber >= _channels.Length)
		{
			return;
		}
		BaseChannel channel = null;
		PacketProperty property;
		if (deliveryMethod == DeliveryMethod.Unreliable)
		{
			property = PacketProperty.Unreliable;
		}
		else
		{
			property = PacketProperty.Channeled;
			channel = CreateChannel((byte)((uint)(channelNumber * 4) + (uint)deliveryMethod));
		}
		int headerSize = NetPacket.GetHeaderSize(property);
		int mtu = _mtu;
		if (length + headerSize > mtu)
		{
			if (deliveryMethod != DeliveryMethod.ReliableOrdered && deliveryMethod != DeliveryMethod.ReliableUnordered)
			{
				throw new TooBigPacketException("Unreliable or ReliableSequenced packet size exceeded maximum of " + (mtu - headerSize) + " bytes, Check allowed size by GetMaxSinglePacketSize()");
			}
			int packetDataSize = mtu - headerSize - 6;
			int totalPackets = length / packetDataSize + ((length % packetDataSize != 0) ? 1 : 0);
			if (totalPackets > 65535)
			{
				throw new TooBigPacketException("Data was split in " + totalPackets + " fragments, which exceeds " + ushort.MaxValue);
			}
			ushort currentFragmentId = (ushort)Interlocked.Increment(ref _fragmentId);
			for (ushort partIdx = 0; partIdx < totalPackets; partIdx++)
			{
				int sendLength = ((length > packetDataSize) ? packetDataSize : length);
				NetPacket p = NetManager.PoolGetPacket(headerSize + sendLength + 6);
				p.Property = property;
				p.UserData = userData;
				p.FragmentId = currentFragmentId;
				p.FragmentPart = partIdx;
				p.FragmentsTotal = (ushort)totalPackets;
				p.MarkFragmented();
				Buffer.BlockCopy(data, start + partIdx * packetDataSize, p.RawData, 10, sendLength);
				channel.AddToQueue(p);
				length -= sendLength;
			}
			return;
		}
		NetPacket packet = NetManager.PoolGetPacket(headerSize + length);
		packet.Property = property;
		Buffer.BlockCopy(data, start, packet.RawData, headerSize, length);
		packet.UserData = userData;
		if (channel == null)
		{
			lock (_unreliableChannel)
			{
				_unreliableChannel.Enqueue(packet);
				return;
			}
		}
		channel.AddToQueue(packet);
	}

	public void SendWithDeliveryEvent(ReadOnlySpan<byte> data, byte channelNumber, DeliveryMethod deliveryMethod, object userData)
	{
		if (deliveryMethod != DeliveryMethod.ReliableOrdered && deliveryMethod != DeliveryMethod.ReliableUnordered)
		{
			throw new ArgumentException("Delivery event will work only for ReliableOrdered/Unordered packets");
		}
		SendInternal(data, channelNumber, deliveryMethod, userData);
	}

	public void Send(ReadOnlySpan<byte> data, DeliveryMethod deliveryMethod)
	{
		SendInternal(data, 0, deliveryMethod, null);
	}

	public void Send(ReadOnlySpan<byte> data, byte channelNumber, DeliveryMethod deliveryMethod)
	{
		SendInternal(data, channelNumber, deliveryMethod, null);
	}

	private void SendInternal(ReadOnlySpan<byte> data, byte channelNumber, DeliveryMethod deliveryMethod, object userData)
	{
		if (_connectionState != ConnectionState.Connected || channelNumber >= _channels.Length)
		{
			return;
		}
		BaseChannel channel = null;
		PacketProperty property;
		if (deliveryMethod == DeliveryMethod.Unreliable)
		{
			property = PacketProperty.Unreliable;
		}
		else
		{
			property = PacketProperty.Channeled;
			channel = CreateChannel((byte)((uint)(channelNumber * 4) + (uint)deliveryMethod));
		}
		int headerSize = NetPacket.GetHeaderSize(property);
		int mtu = _mtu;
		int length = data.Length;
		if (length + headerSize > mtu)
		{
			if (deliveryMethod != DeliveryMethod.ReliableOrdered && deliveryMethod != DeliveryMethod.ReliableUnordered)
			{
				throw new TooBigPacketException("Unreliable or ReliableSequenced packet size exceeded maximum of " + (mtu - headerSize) + " bytes, Check allowed size by GetMaxSinglePacketSize()");
			}
			int packetDataSize = mtu - headerSize - 6;
			int totalPackets = length / packetDataSize + ((length % packetDataSize != 0) ? 1 : 0);
			if (totalPackets > 65535)
			{
				throw new TooBigPacketException("Data was split in " + totalPackets + " fragments, which exceeds " + ushort.MaxValue);
			}
			ushort currentFragmentId = (ushort)Interlocked.Increment(ref _fragmentId);
			for (ushort partIdx = 0; partIdx < totalPackets; partIdx++)
			{
				int sendLength = ((length > packetDataSize) ? packetDataSize : length);
				NetPacket p = NetManager.PoolGetPacket(headerSize + sendLength + 6);
				p.Property = property;
				p.UserData = userData;
				p.FragmentId = currentFragmentId;
				p.FragmentPart = partIdx;
				p.FragmentsTotal = (ushort)totalPackets;
				p.MarkFragmented();
				data.Slice(partIdx * packetDataSize, sendLength).CopyTo(new Span<byte>(p.RawData, 10, sendLength));
				channel.AddToQueue(p);
				length -= sendLength;
			}
			return;
		}
		NetPacket packet = NetManager.PoolGetPacket(headerSize + length);
		packet.Property = property;
		data.CopyTo(new Span<byte>(packet.RawData, headerSize, length));
		packet.UserData = userData;
		if (channel == null)
		{
			lock (_unreliableChannel)
			{
				_unreliableChannel.Enqueue(packet);
				return;
			}
		}
		channel.AddToQueue(packet);
	}

	public void Disconnect(byte[] data)
	{
		NetManager.DisconnectPeer(this, data);
	}

	public void Disconnect(NetDataWriter writer)
	{
		NetManager.DisconnectPeer(this, writer);
	}

	public void Disconnect(byte[] data, int start, int count)
	{
		NetManager.DisconnectPeer(this, data, start, count);
	}

	public void Disconnect()
	{
		NetManager.DisconnectPeer(this);
	}

	internal DisconnectResult ProcessDisconnect(NetPacket packet)
	{
		if ((_connectionState == ConnectionState.Connected || _connectionState == ConnectionState.Outgoing) && packet.Size >= 9 && BitConverter.ToInt64(packet.RawData, 1) == _connectTime && packet.ConnectionNumber == _connectNum)
		{
			if (_connectionState != ConnectionState.Connected)
			{
				return DisconnectResult.Reject;
			}
			return DisconnectResult.Disconnect;
		}
		return DisconnectResult.None;
	}

	internal void AddToReliableChannelSendQueue(BaseChannel channel)
	{
		_channelSendQueue.Enqueue(channel);
	}

	internal ShutdownResult Shutdown(byte[] data, int start, int length, bool force)
	{
		lock (_shutdownLock)
		{
			if (_connectionState == ConnectionState.Disconnected || _connectionState == ConnectionState.ShutdownRequested)
			{
				return ShutdownResult.None;
			}
			ShutdownResult result = ((_connectionState != ConnectionState.Connected) ? ShutdownResult.Success : ShutdownResult.WasConnected);
			if (force)
			{
				_connectionState = ConnectionState.Disconnected;
				return result;
			}
			Interlocked.Exchange(ref _timeSinceLastPacket, 0);
			_shutdownPacket = new NetPacket(PacketProperty.Disconnect, length)
			{
				ConnectionNumber = _connectNum
			};
			FastBitConverter.GetBytes(_shutdownPacket.RawData, 1, _connectTime);
			if (_shutdownPacket.Size >= _mtu)
			{
				NetDebug.WriteError("[Peer] Disconnect additional data size more than MTU - 8!");
			}
			else if (data != null && length > 0)
			{
				Buffer.BlockCopy(data, start, _shutdownPacket.RawData, 9, length);
			}
			_connectionState = ConnectionState.ShutdownRequested;
			NetManager.SendRaw(_shutdownPacket, this);
			return result;
		}
	}

	private void UpdateRoundTripTime(int roundTripTime)
	{
		_rtt += roundTripTime;
		_rttCount++;
		_avgRtt = _rtt / _rttCount;
		_resendDelay = 25.0 + (double)_avgRtt * 2.1;
	}

	internal void AddReliablePacket(DeliveryMethod method, NetPacket p)
	{
		if (p.IsFragmented)
		{
			ushort packetFragId = p.FragmentId;
			byte packetChannelId = p.ChannelId;
			if (!_holdedFragments.TryGetValue(packetFragId, out var incomingFragments))
			{
				incomingFragments = new IncomingFragments
				{
					Fragments = new NetPacket[p.FragmentsTotal],
					ChannelId = p.ChannelId
				};
				_holdedFragments.Add(packetFragId, incomingFragments);
			}
			NetPacket[] fragments = incomingFragments.Fragments;
			if (p.FragmentPart >= fragments.Length || fragments[p.FragmentPart] != null || p.ChannelId != incomingFragments.ChannelId)
			{
				NetManager.PoolRecycle(p);
				NetDebug.WriteError("Invalid fragment packet");
				return;
			}
			fragments[p.FragmentPart] = p;
			incomingFragments.ReceivedCount++;
			incomingFragments.TotalSize += p.Size - 10;
			if (incomingFragments.ReceivedCount != fragments.Length)
			{
				return;
			}
			NetPacket resultingPacket = NetManager.PoolGetPacket(incomingFragments.TotalSize);
			int pos = 0;
			for (int i = 0; i < incomingFragments.ReceivedCount; i++)
			{
				NetPacket fragment = fragments[i];
				int writtenSize = fragment.Size - 10;
				if (pos + writtenSize > resultingPacket.RawData.Length)
				{
					_holdedFragments.Remove(packetFragId);
					NetDebug.WriteError($"Fragment error pos: {pos + writtenSize} >= resultPacketSize: {resultingPacket.RawData.Length} , totalSize: {incomingFragments.TotalSize}");
					return;
				}
				if (fragment.Size > fragment.RawData.Length)
				{
					_holdedFragments.Remove(packetFragId);
					NetDebug.WriteError($"Fragment error size: {fragment.Size} > fragment.RawData.Length: {fragment.RawData.Length}");
					return;
				}
				Buffer.BlockCopy(fragment.RawData, 10, resultingPacket.RawData, pos, writtenSize);
				pos += writtenSize;
				NetManager.PoolRecycle(fragment);
				fragments[i] = null;
			}
			_holdedFragments.Remove(packetFragId);
			NetManager.CreateReceiveEvent(resultingPacket, method, (byte)(packetChannelId / 4), 0, this);
		}
		else
		{
			NetManager.CreateReceiveEvent(p, method, (byte)(p.ChannelId / 4), 4, this);
		}
	}

	private void ProcessMtuPacket(NetPacket packet)
	{
		if (packet.Size < NetConstants.PossibleMtu[0])
		{
			return;
		}
		int receivedMtu = BitConverter.ToInt32(packet.RawData, 1);
		int endMtuCheck = BitConverter.ToInt32(packet.RawData, packet.Size - 4);
		if (receivedMtu != packet.Size || receivedMtu != endMtuCheck || receivedMtu > NetConstants.MaxPacketSize)
		{
			NetDebug.WriteError($"[MTU] Broken packet. RMTU {receivedMtu}, EMTU {endMtuCheck}, PSIZE {packet.Size}");
		}
		else if (packet.Property == PacketProperty.MtuCheck)
		{
			_mtuCheckAttempts = 0;
			packet.Property = PacketProperty.MtuOk;
			NetManager.SendRawAndRecycle(packet, this);
		}
		else if (receivedMtu > _mtu && !_finishMtu && receivedMtu == NetConstants.PossibleMtu[_mtuIdx + 1] - NetManager.ExtraPacketSizeForLayer)
		{
			lock (_mtuMutex)
			{
				SetMtu(_mtuIdx + 1);
			}
			if (_mtuIdx == NetConstants.PossibleMtu.Length - 1)
			{
				_finishMtu = true;
			}
			NetManager.PoolRecycle(packet);
		}
	}

	private void UpdateMtuLogic(int deltaTime)
	{
		if (_finishMtu)
		{
			return;
		}
		_mtuCheckTimer += deltaTime;
		if (_mtuCheckTimer < 1000)
		{
			return;
		}
		_mtuCheckTimer = 0;
		_mtuCheckAttempts++;
		if (_mtuCheckAttempts >= 4)
		{
			_finishMtu = true;
			return;
		}
		lock (_mtuMutex)
		{
			if (_mtuIdx < NetConstants.PossibleMtu.Length - 1)
			{
				int newMtu = NetConstants.PossibleMtu[_mtuIdx + 1] - NetManager.ExtraPacketSizeForLayer;
				NetPacket p = NetManager.PoolGetPacket(newMtu);
				p.Property = PacketProperty.MtuCheck;
				FastBitConverter.GetBytes(p.RawData, 1, newMtu);
				FastBitConverter.GetBytes(p.RawData, p.Size - 4, newMtu);
				if (NetManager.SendRawAndRecycle(p, this) <= 0)
				{
					_finishMtu = true;
				}
			}
		}
	}

	internal ConnectRequestResult ProcessConnectRequest(NetConnectRequestPacket connRequest)
	{
		switch (_connectionState)
		{
		case ConnectionState.Outgoing:
		{
			if (connRequest.ConnectionTime < _connectTime)
			{
				return ConnectRequestResult.P2PLose;
			}
			if (connRequest.ConnectionTime != _connectTime)
			{
				break;
			}
			byte[] localBytes = connRequest.TargetAddress;
			for (int i = _cachedSocketAddr.Size - 1; i >= 0; i--)
			{
				byte rb = _cachedSocketAddr[i];
				if (rb != localBytes[i] && rb < localBytes[i])
				{
					return ConnectRequestResult.P2PLose;
				}
			}
			break;
		}
		case ConnectionState.Connected:
			if (connRequest.ConnectionTime == _connectTime)
			{
				NetManager.SendRaw(_connectAcceptPacket, this);
			}
			else if (connRequest.ConnectionTime > _connectTime)
			{
				return ConnectRequestResult.Reconnection;
			}
			break;
		case ConnectionState.ShutdownRequested:
		case ConnectionState.Disconnected:
			if (connRequest.ConnectionTime >= _connectTime)
			{
				return ConnectRequestResult.NewConnection;
			}
			break;
		}
		return ConnectRequestResult.None;
	}

	internal void ProcessPacket(NetPacket packet)
	{
		if (_connectionState == ConnectionState.Outgoing || _connectionState == ConnectionState.Disconnected)
		{
			NetManager.PoolRecycle(packet);
			return;
		}
		if (packet.Property == PacketProperty.ShutdownOk)
		{
			if (_connectionState == ConnectionState.ShutdownRequested)
			{
				_connectionState = ConnectionState.Disconnected;
			}
			NetManager.PoolRecycle(packet);
			return;
		}
		if (packet.ConnectionNumber != _connectNum)
		{
			NetManager.PoolRecycle(packet);
			return;
		}
		Interlocked.Exchange(ref _timeSinceLastPacket, 0);
		switch (packet.Property)
		{
		case PacketProperty.Merged:
		{
			int pos = 1;
			while (pos < packet.Size)
			{
				ushort size = BitConverter.ToUInt16(packet.RawData, pos);
				pos += 2;
				if (packet.RawData.Length - pos < size)
				{
					break;
				}
				NetPacket mergedPacket = NetManager.PoolGetPacket(size);
				Buffer.BlockCopy(packet.RawData, pos, mergedPacket.RawData, 0, size);
				mergedPacket.Size = size;
				if (!mergedPacket.Verify())
				{
					break;
				}
				pos += size;
				ProcessPacket(mergedPacket);
			}
			NetManager.PoolRecycle(packet);
			break;
		}
		case PacketProperty.Ping:
			if (NetUtils.RelativeSequenceNumber(packet.Sequence, _pongPacket.Sequence) > 0)
			{
				FastBitConverter.GetBytes(_pongPacket.RawData, 3, DateTime.UtcNow.Ticks);
				_pongPacket.Sequence = packet.Sequence;
				NetManager.SendRaw(_pongPacket, this);
			}
			NetManager.PoolRecycle(packet);
			break;
		case PacketProperty.Pong:
			if (packet.Sequence == _pingPacket.Sequence)
			{
				_pingTimer.Stop();
				int elapsedMs = (int)_pingTimer.ElapsedMilliseconds;
				_remoteDelta = BitConverter.ToInt64(packet.RawData, 3) + (long)elapsedMs * 10000L / 2 - DateTime.UtcNow.Ticks;
				UpdateRoundTripTime(elapsedMs);
				NetManager.ConnectionLatencyUpdated(this, elapsedMs / 2);
			}
			NetManager.PoolRecycle(packet);
			break;
		case PacketProperty.Channeled:
		case PacketProperty.Ack:
		{
			if (packet.ChannelId >= _channels.Length)
			{
				NetManager.PoolRecycle(packet);
				break;
			}
			BaseChannel channel = _channels[packet.ChannelId] ?? ((packet.Property == PacketProperty.Ack) ? null : CreateChannel(packet.ChannelId));
			if (channel != null && !channel.ProcessPacket(packet))
			{
				NetManager.PoolRecycle(packet);
			}
			break;
		}
		case PacketProperty.Unreliable:
			NetManager.CreateReceiveEvent(packet, DeliveryMethod.Unreliable, 0, 1, this);
			break;
		case PacketProperty.MtuCheck:
		case PacketProperty.MtuOk:
			ProcessMtuPacket(packet);
			break;
		default:
			NetDebug.WriteError("Error! Unexpected packet type: " + packet.Property);
			break;
		}
	}

	private void SendMerged()
	{
		if (_mergeCount != 0)
		{
			int bytesSent = ((_mergeCount <= 1) ? NetManager.SendRaw(_mergeData.RawData, 3, _mergePos - 2, this) : NetManager.SendRaw(_mergeData.RawData, 0, 1 + _mergePos, this));
			if (NetManager.EnableStatistics)
			{
				Statistics.IncrementPacketsSent();
				Statistics.AddBytesSent(bytesSent);
			}
			_mergePos = 0;
			_mergeCount = 0;
		}
	}

	internal void SendUserData(NetPacket packet)
	{
		packet.ConnectionNumber = _connectNum;
		int mergedPacketSize = 1 + packet.Size + 2;
		if (mergedPacketSize + 20 >= _mtu)
		{
			int bytesSent = NetManager.SendRaw(packet, this);
			if (NetManager.EnableStatistics)
			{
				Statistics.IncrementPacketsSent();
				Statistics.AddBytesSent(bytesSent);
			}
			return;
		}
		if (_mergePos + mergedPacketSize > _mtu)
		{
			SendMerged();
		}
		FastBitConverter.GetBytes(_mergeData.RawData, _mergePos + 1, (ushort)packet.Size);
		Buffer.BlockCopy(packet.RawData, 0, _mergeData.RawData, _mergePos + 1 + 2, packet.Size);
		_mergePos += packet.Size + 2;
		_mergeCount++;
	}

	internal void Update(int deltaTime)
	{
		Interlocked.Add(ref _timeSinceLastPacket, deltaTime);
		switch (_connectionState)
		{
		case ConnectionState.Connected:
			if (_timeSinceLastPacket > NetManager.DisconnectTimeout)
			{
				NetManager.DisconnectPeerForce(this, DisconnectReason.Timeout, SocketError.Success, null);
				return;
			}
			break;
		case ConnectionState.ShutdownRequested:
			if (_timeSinceLastPacket > NetManager.DisconnectTimeout)
			{
				_connectionState = ConnectionState.Disconnected;
				return;
			}
			_shutdownTimer += deltaTime;
			if (_shutdownTimer >= 300)
			{
				_shutdownTimer = 0;
				NetManager.SendRaw(_shutdownPacket, this);
			}
			return;
		case ConnectionState.Outgoing:
			_connectTimer += deltaTime;
			if (_connectTimer > NetManager.ReconnectDelay)
			{
				_connectTimer = 0;
				_connectAttempts++;
				if (_connectAttempts > NetManager.MaxConnectAttempts)
				{
					NetManager.DisconnectPeerForce(this, DisconnectReason.ConnectionFailed, SocketError.Success, null);
				}
				else
				{
					NetManager.SendRaw(_connectRequestPacket, this);
				}
			}
			return;
		case ConnectionState.Disconnected:
			return;
		}
		_pingSendTimer += deltaTime;
		if (_pingSendTimer >= NetManager.PingInterval)
		{
			_pingSendTimer = 0;
			_pingPacket.Sequence++;
			if (_pingTimer.IsRunning)
			{
				UpdateRoundTripTime((int)_pingTimer.ElapsedMilliseconds);
			}
			_pingTimer.Restart();
			NetManager.SendRaw(_pingPacket, this);
		}
		_rttResetTimer += deltaTime;
		if (_rttResetTimer >= NetManager.PingInterval * 3)
		{
			_rttResetTimer = 0;
			_rtt = _avgRtt;
			_rttCount = 1;
		}
		UpdateMtuLogic(deltaTime);
		int count = _channelSendQueue.Count;
		BaseChannel channel;
		while (count-- > 0 && _channelSendQueue.TryDequeue(out channel))
		{
			if (channel.SendAndCheckQueue())
			{
				_channelSendQueue.Enqueue(channel);
			}
		}
		lock (_unreliableChannel)
		{
			int unreliableCount = _unreliableChannel.Count;
			for (int i = 0; i < unreliableCount; i++)
			{
				NetPacket packet = _unreliableChannel.Dequeue();
				SendUserData(packet);
				NetManager.PoolRecycle(packet);
			}
		}
		SendMerged();
	}

	internal void RecycleAndDeliver(NetPacket packet)
	{
		if (packet.UserData != null)
		{
			if (packet.IsFragmented)
			{
				_deliveredFragments.TryGetValue(packet.FragmentId, out var fragCount);
				fragCount++;
				if (fragCount == packet.FragmentsTotal)
				{
					NetManager.MessageDelivered(this, packet.UserData);
					_deliveredFragments.Remove(packet.FragmentId);
				}
				else
				{
					_deliveredFragments[packet.FragmentId] = fragCount;
				}
			}
			else
			{
				NetManager.MessageDelivered(this, packet.UserData);
			}
			packet.UserData = null;
		}
		NetManager.PoolRecycle(packet);
	}
}
