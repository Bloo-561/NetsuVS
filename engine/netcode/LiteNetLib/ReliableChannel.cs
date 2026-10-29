using System;

namespace LiteNetLib;

internal sealed class ReliableChannel : BaseChannel
{
	private struct PendingPacket
	{
		private NetPacket _packet;

		private long _timeStamp;

		private bool _isSent;

		public override string ToString()
		{
			if (_packet != null)
			{
				return _packet.Sequence.ToString();
			}
			return "Empty";
		}

		public void Init(NetPacket packet)
		{
			_packet = packet;
			_isSent = false;
		}

		public bool TrySend(long currentTime, NetPeer peer)
		{
			if (_packet == null)
			{
				return false;
			}
			if (_isSent)
			{
				double resendDelay = peer.ResendDelay * 10000.0;
				if ((double)(currentTime - _timeStamp) < resendDelay)
				{
					return true;
				}
			}
			_timeStamp = currentTime;
			_isSent = true;
			peer.SendUserData(_packet);
			return true;
		}

		public bool Clear(NetPeer peer)
		{
			if (_packet != null)
			{
				peer.RecycleAndDeliver(_packet);
				_packet = null;
				return true;
			}
			return false;
		}
	}

	private readonly NetPacket _outgoingAcks;

	private readonly PendingPacket[] _pendingPackets;

	private readonly NetPacket[] _receivedPackets;

	private readonly bool[] _earlyReceived;

	private int _localSeqence;

	private int _remoteSequence;

	private int _localWindowStart;

	private int _remoteWindowStart;

	private bool _mustSendAcks;

	private readonly DeliveryMethod _deliveryMethod;

	private readonly bool _ordered;

	private readonly int _windowSize;

	private const int BitsInByte = 8;

	private readonly byte _id;

	public ReliableChannel(NetPeer peer, bool ordered, byte id)
		: base(peer)
	{
		_id = id;
		_windowSize = 64;
		_ordered = ordered;
		_pendingPackets = new PendingPacket[_windowSize];
		for (int i = 0; i < _pendingPackets.Length; i++)
		{
			_pendingPackets[i] = default(PendingPacket);
		}
		if (_ordered)
		{
			_deliveryMethod = DeliveryMethod.ReliableOrdered;
			_receivedPackets = new NetPacket[_windowSize];
		}
		else
		{
			_deliveryMethod = DeliveryMethod.ReliableUnordered;
			_earlyReceived = new bool[_windowSize];
		}
		_localWindowStart = 0;
		_localSeqence = 0;
		_remoteSequence = 0;
		_remoteWindowStart = 0;
		_outgoingAcks = new NetPacket(PacketProperty.Ack, (_windowSize - 1) / 8 + 2)
		{
			ChannelId = id
		};
	}

	private void ProcessAck(NetPacket packet)
	{
		if (packet.Size != _outgoingAcks.Size)
		{
			return;
		}
		ushort ackWindowStart = packet.Sequence;
		int windowRel = NetUtils.RelativeSequenceNumber(_localWindowStart, ackWindowStart);
		if (ackWindowStart >= 32768 || windowRel < 0 || windowRel >= _windowSize)
		{
			return;
		}
		byte[] acksData = packet.RawData;
		lock (_pendingPackets)
		{
			int pendingSeq = _localWindowStart;
			while (pendingSeq != _localSeqence && NetUtils.RelativeSequenceNumber(pendingSeq, ackWindowStart) < _windowSize)
			{
				int pendingIdx = pendingSeq % _windowSize;
				int currentByte = 4 + pendingIdx / 8;
				int currentBit = pendingIdx % 8;
				if ((acksData[currentByte] & (1 << currentBit)) == 0)
				{
					if (Peer.NetManager.EnableStatistics)
					{
						Peer.Statistics.IncrementPacketLoss();
						Peer.NetManager.Statistics.IncrementPacketLoss();
					}
				}
				else
				{
					if (pendingSeq == _localWindowStart)
					{
						_localWindowStart = (_localWindowStart + 1) % 32768;
					}
					_pendingPackets[pendingIdx].Clear(Peer);
				}
				pendingSeq = (pendingSeq + 1) % 32768;
			}
		}
	}

	protected override bool SendNextPackets()
	{
		if (_mustSendAcks)
		{
			_mustSendAcks = false;
			lock (_outgoingAcks)
			{
				Peer.SendUserData(_outgoingAcks);
			}
		}
		long currentTime = DateTime.UtcNow.Ticks;
		bool hasPendingPackets = false;
		lock (_pendingPackets)
		{
			lock (OutgoingQueue)
			{
				while (OutgoingQueue.Count > 0 && NetUtils.RelativeSequenceNumber(_localSeqence, _localWindowStart) < _windowSize)
				{
					NetPacket netPacket = OutgoingQueue.Dequeue();
					netPacket.Sequence = (ushort)_localSeqence;
					netPacket.ChannelId = _id;
					_pendingPackets[_localSeqence % _windowSize].Init(netPacket);
					_localSeqence = (_localSeqence + 1) % 32768;
				}
			}
			for (int pendingSeq = _localWindowStart; pendingSeq != _localSeqence; pendingSeq = (pendingSeq + 1) % 32768)
			{
				if (_pendingPackets[pendingSeq % _windowSize].TrySend(currentTime, Peer))
				{
					hasPendingPackets = true;
				}
			}
		}
		if (!hasPendingPackets && !_mustSendAcks)
		{
			return OutgoingQueue.Count > 0;
		}
		return true;
	}

	public override bool ProcessPacket(NetPacket packet)
	{
		if (packet.Property == PacketProperty.Ack)
		{
			ProcessAck(packet);
			return false;
		}
		int seq = packet.Sequence;
		if (seq >= 32768)
		{
			return false;
		}
		int relate = NetUtils.RelativeSequenceNumber(seq, _remoteWindowStart);
		if (NetUtils.RelativeSequenceNumber(seq, _remoteSequence) > _windowSize)
		{
			return false;
		}
		if (relate < 0)
		{
			return false;
		}
		if (relate >= _windowSize * 2)
		{
			return false;
		}
		int ackIdx;
		lock (_outgoingAcks)
		{
			int ackByte;
			int ackBit;
			if (relate >= _windowSize)
			{
				int newWindowStart = (_remoteWindowStart + relate - _windowSize + 1) % 32768;
				_outgoingAcks.Sequence = (ushort)newWindowStart;
				while (_remoteWindowStart != newWindowStart)
				{
					ackIdx = _remoteWindowStart % _windowSize;
					ackByte = 4 + ackIdx / 8;
					ackBit = ackIdx % 8;
					_outgoingAcks.RawData[ackByte] &= (byte)(~(1 << ackBit));
					_remoteWindowStart = (_remoteWindowStart + 1) % 32768;
				}
			}
			_mustSendAcks = true;
			ackIdx = seq % _windowSize;
			ackByte = 4 + ackIdx / 8;
			ackBit = ackIdx % 8;
			if ((_outgoingAcks.RawData[ackByte] & (1 << ackBit)) != 0)
			{
				AddToPeerChannelSendQueue();
				return false;
			}
			_outgoingAcks.RawData[ackByte] |= (byte)(1 << ackBit);
		}
		AddToPeerChannelSendQueue();
		if (seq == _remoteSequence)
		{
			Peer.AddReliablePacket(_deliveryMethod, packet);
			_remoteSequence = (_remoteSequence + 1) % 32768;
			if (_ordered)
			{
				NetPacket p;
				while ((p = _receivedPackets[_remoteSequence % _windowSize]) != null)
				{
					_receivedPackets[_remoteSequence % _windowSize] = null;
					Peer.AddReliablePacket(_deliveryMethod, p);
					_remoteSequence = (_remoteSequence + 1) % 32768;
				}
			}
			else
			{
				while (_earlyReceived[_remoteSequence % _windowSize])
				{
					_earlyReceived[_remoteSequence % _windowSize] = false;
					_remoteSequence = (_remoteSequence + 1) % 32768;
				}
			}
			return true;
		}
		if (_ordered)
		{
			_receivedPackets[ackIdx] = packet;
		}
		else
		{
			_earlyReceived[ackIdx] = true;
			Peer.AddReliablePacket(_deliveryMethod, packet);
		}
		return true;
	}
}
