using Godot;

namespace SakugaEngine.Resources;

/// <summary>
/// Netsu (Oct 26 2026, TamaDeez): true while this fighter (or the fighter that owns this assist / projectile) is in
/// Overdrive. Not = true while it isn't. Used by Flan's Overdrive extras (236 always wall bounces, 214 always ground
/// bounces).
/// </summary>
[GlobalClass]
public partial class NetsuOverdriveCondition : FrameDataCondition
{
	[Export(PropertyHint.None, "")]
	private bool Not;

	public override bool Check(ref SakugaActor Actor)
	{
		SakugaActor root = Actor.NetsuRoot();
		// Oct 28: character Overdrive extras are off with the new Overdrive (SakugaParameters.OverdriveCharacterExtras)
		bool on = SakugaParameters.OverdriveCharacterExtras && root != null && root.Parameters != null && root.Parameters.InOverdrive();
		return Not ? !on : on;
	}
}
