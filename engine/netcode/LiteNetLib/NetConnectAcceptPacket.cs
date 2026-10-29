using System;
using LiteNetLib.Utils;

namespace LiteNetLib;

internal sealed class NetConnectAcceptPacket
{
	public const int Size = 15;

	public readonly long ConnectionTime;

	public readonly byte ConnectionNumber;

	public readonly int PeerId;

	public readonly bool PeerNetworkChanged;

	private NetConnectAcceptPacket(long connectionTime, byte connectionNumber, int peerId, bool peerNetworkChanged)
	{
		ConnectionTime = connectionTime;
		ConnectionNumber = connectionNumber;
		PeerId = peerId;
		PeerNetworkChanged = peerNetworkChanged;
	}

	public static NetConnectAcceptPacket FromData(NetPacket packet)
	{
		if (packet.Size != 15)
		{
			return null;
		}
		long connectionId = BitConverter.ToInt64(packet.RawData, 1);
		byte connectionNumber = packet.RawData[9];
		if (connectionNumber >= 4)
		{
			return null;
		}
		byte isReused = packet.RawData[10];
		if (isReused > 1)
		{
			return null;
		}
		int peerId = BitConverter.ToInt32(packet.RawData, 11);
		if (peerId < 0)
		{
			return null;
		}
		return new NetConnectAcceptPacket(connectionId, connectionNumber, peerId, isReused == 1);
	}

	public static NetPacket Make(long connectTime, byte connectNum, int localPeerId)
	{
		NetPacket netPacket = new NetPacket(PacketProperty.ConnectAccept, 0);
		FastBitConverter.GetBytes(netPacket.RawData, 1, connectTime);
		netPacket.RawData[9] = connectNum;
		FastBitConverter.GetBytes(netPacket.RawData, 11, localPeerId);
		return netPacket;
	}

	public static NetPacket MakeNetworkChanged(NetPeer peer)
	{
		NetPacket netPacket = new NetPacket(PacketProperty.PeerNotFound, 14);
		FastBitConverter.GetBytes(netPacket.RawData, 1, peer.ConnectTime);
		netPacket.RawData[9] = peer.ConnectionNum;
		netPacket.RawData[10] = 1;
		FastBitConverter.GetBytes(netPacket.RawData, 11, peer.RemoteId);
		return netPacket;
	}
}
