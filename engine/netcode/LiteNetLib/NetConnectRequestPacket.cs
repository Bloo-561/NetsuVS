using System;
using System.Net;
using LiteNetLib.Utils;

namespace LiteNetLib;

internal sealed class NetConnectRequestPacket
{
	public const int HeaderSize = 18;

	public readonly long ConnectionTime;

	public byte ConnectionNumber;

	public readonly byte[] TargetAddress;

	public readonly NetDataReader Data;

	public readonly int PeerId;

	private NetConnectRequestPacket(long connectionTime, byte connectionNumber, int localId, byte[] targetAddress, NetDataReader data)
	{
		ConnectionTime = connectionTime;
		ConnectionNumber = connectionNumber;
		TargetAddress = targetAddress;
		Data = data;
		PeerId = localId;
	}

	public static int GetProtocolId(NetPacket packet)
	{
		return BitConverter.ToInt32(packet.RawData, 1);
	}

	public static NetConnectRequestPacket FromData(NetPacket packet)
	{
		if (packet.ConnectionNumber >= 4)
		{
			return null;
		}
		long connectionTime = BitConverter.ToInt64(packet.RawData, 5);
		int peerId = BitConverter.ToInt32(packet.RawData, 13);
		int addrSize = packet.RawData[17];
		if (addrSize != 16 && addrSize != 28)
		{
			return null;
		}
		byte[] addressBytes = new byte[addrSize];
		Buffer.BlockCopy(packet.RawData, 18, addressBytes, 0, addrSize);
		NetDataReader reader = new NetDataReader(null, 0, 0);
		if (packet.Size > 18 + addrSize)
		{
			reader.SetSource(packet.RawData, 18 + addrSize, packet.Size);
		}
		return new NetConnectRequestPacket(connectionTime, packet.ConnectionNumber, peerId, addressBytes, reader);
	}

	public static NetPacket Make(NetDataWriter connectData, SocketAddress addressBytes, long connectTime, int localId)
	{
		NetPacket packet = new NetPacket(PacketProperty.ConnectRequest, connectData.Length + addressBytes.Size);
		FastBitConverter.GetBytes(packet.RawData, 1, 13);
		FastBitConverter.GetBytes(packet.RawData, 5, connectTime);
		FastBitConverter.GetBytes(packet.RawData, 13, localId);
		packet.RawData[17] = (byte)addressBytes.Size;
		for (int i = 0; i < addressBytes.Size; i++)
		{
			packet.RawData[18 + i] = addressBytes[i];
		}
		Buffer.BlockCopy(connectData.Data, 0, packet.RawData, 18 + addressBytes.Size, connectData.Length);
		return packet;
	}
}
