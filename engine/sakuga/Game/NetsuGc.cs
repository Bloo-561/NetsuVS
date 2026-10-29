using System;
using System.Runtime;

namespace SakugaEngine.Game;

/// <summary>
/// Netsu (Oct 25 2026): keeps the .NET garbage collector out of the fight. Its pauses (a few to tens of
/// milliseconds, every ~10 seconds of fighting before this) were the small hitches in the fight. Three parts:
///  - much less garbage per frame: about a tenth of what it was (InputManager, GameManager.ReadInputs, SakugaVFX,
///    NetsuAssist, AnimationViewer, the HUD texts, the training status...);
///  - the collector cleans up when the screen is fully black anyway (the fight's first frame, between rounds:
///    GameManager.Render), where its pause can't be seen;
///  - and then it isn't allowed to run until the next black screen ("no GC region", up to RoundBudget bytes of
///    new objects: at the fight's ~2 KB a frame that is far longer than any round). If a round does make more
///    garbage than that, the collector simply runs as usual. Between those it is in "sustained low latency"
///    mode (no full blocking collections).
/// Presentation only: nothing in the match depends on it.
/// </summary>
public static class NetsuGc
{
	/// <summary>Bytes of new objects a round may make before the collector is allowed to run again (96 MB).</summary>
	public const long RoundBudget = 96L * 1024 * 1024;

	private static GCLatencyMode _before;
	private static bool _fighting;

	public static void FightStarted()
	{
		if (_fighting)
		{
			return;
		}
		_before = GCSettings.LatencyMode == GCLatencyMode.NoGCRegion ? GCLatencyMode.Interactive : GCSettings.LatencyMode;
		EndRegion();
		CollectNow();   // the fight was just built (loading garbage) and the screen is still black
		try
		{
			GCSettings.LatencyMode = GCLatencyMode.SustainedLowLatency;
		}
		catch (Exception)
		{
		}
		_fighting = true;
		StartRegion();
	}

	public static void FightEnded()
	{
		if (!_fighting)
		{
			return;
		}
		_fighting = false;
		EndRegion();
		try
		{
			GCSettings.LatencyMode = _before;
		}
		catch (Exception)
		{
		}
	}

	/// <summary>The screen is fully black (between rounds): clean up now, then no collections until the next one.</summary>
	public static void ScreenBlack()
	{
		if (!_fighting)
		{
			CollectNow();
			return;
		}
		EndRegion();
		CollectNow();
		StartRegion();
	}

	/// <summary>A full collection now (call it only while the screen is black).</summary>
	public static void CollectNow()
	{
		GC.Collect(2, GCCollectionMode.Forced, blocking: true, compacting: false);
	}

	private static void StartRegion()
	{
		try
		{
			if (GCSettings.LatencyMode != GCLatencyMode.NoGCRegion)
			{
				GC.TryStartNoGCRegion(RoundBudget);
			}
		}
		catch (Exception)
		{
			// not allowed here (or already in one): the collector just runs as usual
		}
	}

	private static void EndRegion()
	{
		try
		{
			if (GCSettings.LatencyMode == GCLatencyMode.NoGCRegion)
			{
				GC.EndNoGCRegion();
			}
		}
		catch (Exception)
		{
			// the region had already ended (a round made more garbage than the budget): nothing to do
		}
	}
}
