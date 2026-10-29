using System;

namespace LiteNetLib;

internal sealed class SequencedChannel : BaseChannel
{
	private int _localSequence;

	private ushort _remoteSequence;

	private readonly bool _reliable;

	private NetPacket _lastPacket;

	private readonly NetPacket _ackPacket;

	private bool _mustSendAck;

	private readonly byte _id;

	private long _lastPacketSendTime;

	public SequencedChannel(NetPeer peer, bool reliable, byte id)
		: base(peer)
	{
		_id = id;
		_reliable = reliable;
		if (_reliable)
		{
			_ackPacket = new NetPacket(PacketProperty.Ack, 0)
			{
				ChannelId = id
			};
		}
	}

	protected override bool SendNextPackets()
	{
		if (_reliable && OutgoingQueue.Count == 0)
		{
			long currentTime = DateTime.UtcNow.Ticks;
			if ((double)(currentTime - _lastPacketSendTime) >= Peer.ResendDelay * 10000.0)
			{
				NetPacket packet = _lastPacket;
				if (packet != null)
				{
					_lastPacketSendTime = currentTime;
					Peer.SendUserData(packet);
				}
			}
		}
		else
		{
			lock (OutgoingQueue)
			{
				while (OutgoingQueue.Count > 0)
				{
					NetPacket packet2 = OutgoingQueue.Dequeue();
					_localSequence = (_localSequence + 1) % 32768;
					packet2.Sequence = (ushort)_localSequence;
					packet2.ChannelId = _id;
					Peer.SendUserData(packet2);
					if (_reliable && OutgoingQueue.Count == 0)
					{
						_lastPacketSendTime = DateTime.UtcNow.Ticks;
						_lastPacket = packet2;
					}
					else
					{
						Peer.NetManager.PoolRecycle(packet2);
					}
				}
			}
		}
		if (_reliable && _mustSendAck)
		{
			_mustSendAck = false;
			_ackPacket.Sequence = _remoteSequence;
			Peer.SendUserData(_ackPacket);
		}
		return _lastPacket != null;
	}

	public override bool ProcessPacket(NetPacket packet)
	{
		if (packet.IsFragmented)
		{
			return false;
		}
		if (packet.Property == PacketProperty.Ack)
		{
			if (_reliable && _lastPacket != null && packet.Sequence == _lastPacket.Sequence)
			{
				_lastPacket = null;
			}
			return false;
		}
		int relative = NetUtils.RelativeSequenceNumber(packet.Sequence, _remoteSequence);
		bool packetProcessed = false;
		if (packet.Sequence < 32768 && relative > 0)
		{
			if (Peer.NetManager.EnableStatistics)
			{
				Peer.Statistics.AddPacketLoss(relative - 1);
				Peer.NetManager.Statistics.AddPacketLoss(relative - 1);
			}
			_remoteSequence = packet.Sequence;
			Peer.NetManager.CreateReceiveEvent(packet, (!_reliable) ? DeliveryMethod.Sequenced : DeliveryMethod.ReliableSequenced, (byte)(packet.ChannelId / 4), 4, Peer);
			packetProcessed = true;
		}
		if (_reliable)
		{
			_mustSendAck = true;
			AddToPeerChannelSendQueue();
		}
		return packetProcessed;
	}
}
