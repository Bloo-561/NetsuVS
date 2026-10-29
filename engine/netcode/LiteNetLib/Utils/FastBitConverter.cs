using System;
using System.Runtime.CompilerServices;

namespace LiteNetLib.Utils;

public static class FastBitConverter
{
	[MethodImpl(MethodImplOptions.AggressiveInlining)]
	public static void GetBytes<T>(byte[] bytes, int startIndex, T value) where T : unmanaged
	{
		if (bytes.Length < startIndex + Unsafe.SizeOf<T>())
		{
			ThrowIndexOutOfRangeException();
		}
		Unsafe.As<byte, T>(ref bytes[startIndex]) = value;
	}

	private static void ThrowIndexOutOfRangeException()
	{
		throw new IndexOutOfRangeException();
	}
}
