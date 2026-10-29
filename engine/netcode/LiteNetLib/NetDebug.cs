using System;
using System.Diagnostics;

namespace LiteNetLib;

public static class NetDebug
{
	public static INetLogger Logger = null;

	private static readonly object DebugLogLock = new object();

	private static void WriteLogic(NetLogLevel logLevel, string str, params object[] args)
	{
		lock (DebugLogLock)
		{
			if (Logger == null)
			{
				Console.WriteLine(str, args);
			}
			else
			{
				Logger.WriteNet(logLevel, str, args);
			}
		}
	}

	[Conditional("DEBUG_MESSAGES")]
	internal static void Write(string str)
	{
		WriteLogic(NetLogLevel.Trace, str);
	}

	[Conditional("DEBUG_MESSAGES")]
	internal static void Write(NetLogLevel level, string str)
	{
		WriteLogic(level, str);
	}

	[Conditional("DEBUG_MESSAGES")]
	[Conditional("DEBUG")]
	internal static void WriteForce(string str)
	{
		WriteLogic(NetLogLevel.Trace, str);
	}

	[Conditional("DEBUG_MESSAGES")]
	[Conditional("DEBUG")]
	internal static void WriteForce(NetLogLevel level, string str)
	{
		WriteLogic(level, str);
	}

	internal static void WriteError(string str)
	{
		WriteLogic(NetLogLevel.Error, str);
	}
}
