using System.Threading;

namespace LiteNetLib;

public sealed class NetStatistics
{
	private long _packetsSent;

	private long _packetsReceived;

	private long _bytesSent;

	private long _bytesReceived;

	private long _packetLoss;

	public long PacketsSent => Interlocked.Read(in _packetsSent);

	public long PacketsReceived => Interlocked.Read(in _packetsReceived);

	public long BytesSent => Interlocked.Read(in _bytesSent);

	public long BytesReceived => Interlocked.Read(in _bytesReceived);

	public long PacketLoss => Interlocked.Read(in _packetLoss);

	public long PacketLossPercent
	{
		get
		{
			long sent = PacketsSent;
			long loss = PacketLoss;
			if (sent != 0L)
			{
				return loss * 100 / sent;
			}
			return 0L;
		}
	}

	public void Reset()
	{
		Interlocked.Exchange(ref _packetsSent, 0L);
		Interlocked.Exchange(ref _packetsReceived, 0L);
		Interlocked.Exchange(ref _bytesSent, 0L);
		Interlocked.Exchange(ref _bytesReceived, 0L);
		Interlocked.Exchange(ref _packetLoss, 0L);
	}

	public void IncrementPacketsSent()
	{
		Interlocked.Increment(ref _packetsSent);
	}

	public void IncrementPacketsReceived()
	{
		Interlocked.Increment(ref _packetsReceived);
	}

	public void AddBytesSent(long bytesSent)
	{
		Interlocked.Add(ref _bytesSent, bytesSent);
	}

	public void AddBytesReceived(long bytesReceived)
	{
		Interlocked.Add(ref _bytesReceived, bytesReceived);
	}

	public void IncrementPacketLoss()
	{
		Interlocked.Increment(ref _packetLoss);
	}

	public void AddPacketLoss(long packetLoss)
	{
		Interlocked.Add(ref _packetLoss, packetLoss);
	}

	public override string ToString()
	{
		return $"BytesReceived: {BytesReceived}\nPacketsReceived: {PacketsReceived}\nBytesSent: {BytesSent}\nPacketsSent: {PacketsSent}\nPacketLoss: {PacketLoss}\nPacketLossPercent: {PacketLossPercent}\n";
	}
}
