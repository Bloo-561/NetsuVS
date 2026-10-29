using System;
using System.Runtime.CompilerServices;
using Godot;

namespace PleaseResync;

internal static class Platform
{
	public enum DebugType
	{
		Log,
		Warning,
		Error
	}

	private static readonly Random RandomNumberGenerator = new Random();

	public static uint GetCurrentTimeMS()
	{
		return (uint)DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
	}

	public static ushort GetRandomUnsignedShort()
	{
		return (ushort)RandomNumberGenerator.Next();
	}

	[MethodImpl(MethodImplOptions.AggressiveInlining)]
	public static byte[] CloneByteArray(byte[] array)
	{
		byte[] newArray = new byte[array.Length];
		Array.Copy(array, 0, newArray, 0, array.Length);
		return newArray;
	}

	public static uint GetChecksum(byte[] byteArray)
	{
		ushort[] newArray = new ushort[(int)Math.Ceiling((double)byteArray.Length / 2.0)];
		Buffer.BlockCopy(byteArray, 0, newArray, 0, byteArray.Length);
		return FletcherChecksum(newArray, newArray.Length);
	}

	public static uint FletcherChecksum(ushort[] data, int len)
	{
		uint sum1 = 65535u;
		uint sum2 = 65535u;
		int index = 0;
		while (len > 0)
		{
			int tlen = ((len > 360) ? 360 : len);
			len -= tlen;
			do
			{
				sum1 += data[index++];
				sum2 += sum1;
			}
			while (--tlen > 0);
			sum1 = (sum1 & 0xFFFF) + (sum1 >> 16);
			sum2 = (sum2 & 0xFFFF) + (sum2 >> 16);
		}
		sum1 = (sum1 & 0xFFFF) + (sum1 >> 16);
		sum2 = (sum2 & 0xFFFF) + (sum2 >> 16);
		return (sum2 << 16) | sum1;
	}

	public static void Log(string message = "", DebugType type = DebugType.Log)
	{
		switch (type)
		{
		case DebugType.Log:
			GD.Print(message);
			break;
		case DebugType.Warning:
			GD.PrintRich("[color=YELLOW]" + message);
			break;
		case DebugType.Error:
			GD.PrintErr(message);
			break;
		}
	}
}
