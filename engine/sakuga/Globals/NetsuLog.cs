using System.Diagnostics;
using Godot;

namespace SakugaEngine.Global;

/// <summary>
/// Netsu (Oct 24 2026): debug messages the engine used to print every hit / every move
/// ("Fighter: Hit!", "You executed 5A!", "Buffer Cleaned!"...). Printing many lines a second costs
/// frame time (more under rollback, which replays frames), so these calls are left out of the
/// build completely unless the NETSU_VERBOSE symbol is defined: add
///   &lt;DefineConstants&gt;$(DefineConstants);NETSU_VERBOSE&lt;/DefineConstants&gt;
/// to a PropertyGroup in NetsuVS.csproj (then Build) to see them again.
/// </summary>
public static class NetsuLog
{
	[Conditional("NETSU_VERBOSE")]
	public static void Debug(string message)
	{
		GD.Print(message);
	}
}
