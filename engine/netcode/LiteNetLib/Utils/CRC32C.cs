using System;
using System.Runtime.InteropServices;
using System.Runtime.Intrinsics.Arm;
using System.Runtime.Intrinsics.X86;

namespace LiteNetLib.Utils;

public static class CRC32C
{
	public const int ChecksumSize = 4;

	private const uint Poly = 2197175160u;

	private static readonly uint[] Table = NetUtils.AllocatePinnedUninitializedArray<uint>(4096);

	static CRC32C()
	{
		if (Sse42.IsSupported || Crc32.IsSupported)
		{
			return;
		}
		for (uint i = 0u; i < 256; i++)
		{
			uint res = i;
			for (int t = 0; t < 16; t++)
			{
				for (int k = 0; k < 8; k++)
				{
					res = (((res & 1) == 1) ? (0x82F63B78u ^ (res >> 1)) : (res >> 1));
				}
				Table[t * 256 + i] = res;
			}
		}
	}

	public static uint Compute(byte[] input, int offset, int length)
	{
		uint crcLocal = uint.MaxValue;
		if (Sse42.IsSupported)
		{
			ReadOnlySpan<byte> data = new ReadOnlySpan<byte>(input, offset, length);
			int processed = 0;
			if (Sse42.X64.IsSupported && data.Length > 8)
			{
				processed = data.Length / 8 * 8;
				ReadOnlySpan<ulong> ulongs = MemoryMarshal.Cast<byte, ulong>(data.Slice(0, processed));
				ulong crclong = crcLocal;
				for (int i = 0; i < ulongs.Length; i++)
				{
					crclong = Sse42.X64.Crc32(crclong, ulongs[i]);
				}
				crcLocal = (uint)crclong;
			}
			else if (data.Length > 4)
			{
				processed = data.Length / 4 * 4;
				ReadOnlySpan<uint> uints = MemoryMarshal.Cast<byte, uint>(data.Slice(0, processed));
				for (int j = 0; j < uints.Length; j++)
				{
					crcLocal = Sse42.Crc32(crcLocal, uints[j]);
				}
			}
			for (int k = processed; k < data.Length; k++)
			{
				crcLocal = Sse42.Crc32(crcLocal, data[k]);
			}
			return crcLocal ^ 0xFFFFFFFFu;
		}
		if (Crc32.IsSupported)
		{
			ReadOnlySpan<byte> data2 = new ReadOnlySpan<byte>(input, offset, length);
			int processed2 = 0;
			if (Crc32.Arm64.IsSupported && data2.Length > 8)
			{
				processed2 = data2.Length / 8 * 8;
				ReadOnlySpan<ulong> ulongs2 = MemoryMarshal.Cast<byte, ulong>(data2.Slice(0, processed2));
				for (int l = 0; l < ulongs2.Length; l++)
				{
					crcLocal = Crc32.Arm64.ComputeCrc32C(crcLocal, ulongs2[l]);
				}
			}
			else if (data2.Length > 4)
			{
				processed2 = data2.Length / 4 * 4;
				ReadOnlySpan<uint> uints2 = MemoryMarshal.Cast<byte, uint>(data2.Slice(0, processed2));
				for (int m = 0; m < uints2.Length; m++)
				{
					crcLocal = Crc32.ComputeCrc32C(crcLocal, uints2[m]);
				}
			}
			for (int n = processed2; n < data2.Length; n++)
			{
				crcLocal = Crc32.ComputeCrc32C(crcLocal, data2[n]);
			}
			return crcLocal ^ 0xFFFFFFFFu;
		}
		while (length >= 16)
		{
			uint a = Table[768 + input[offset + 12]] ^ Table[512 + input[offset + 13]] ^ Table[256 + input[offset + 14]] ^ Table[input[offset + 15]];
			uint b = Table[1792 + input[offset + 8]] ^ Table[1536 + input[offset + 9]] ^ Table[1280 + input[offset + 10]] ^ Table[1024 + input[offset + 11]];
			uint c = Table[2816 + input[offset + 4]] ^ Table[2560 + input[offset + 5]] ^ Table[2304 + input[offset + 6]] ^ Table[2048 + input[offset + 7]];
			crcLocal = Table[3840 + ((byte)crcLocal ^ input[offset])] ^ Table[3584 + ((byte)(crcLocal >> 8) ^ input[offset + 1])] ^ Table[3328 + ((byte)(crcLocal >> 16) ^ input[offset + 2])] ^ Table[3072 + ((crcLocal >> 24) ^ input[offset + 3])] ^ c ^ b ^ a;
			offset += 16;
			length -= 16;
		}
		while (--length >= 0)
		{
			crcLocal = Table[(byte)(crcLocal ^ input[offset++])] ^ (crcLocal >> 8);
		}
		return crcLocal ^ 0xFFFFFFFFu;
	}
}
