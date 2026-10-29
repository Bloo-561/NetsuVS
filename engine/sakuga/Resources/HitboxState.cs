using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

[GlobalClass]
[Tool]
public partial class HitboxState : Resource
{
	[Export(PropertyHint.None, "")]
	public int AtFrame;

	[Export(PropertyHint.None, "")]
	public AnimationStage animationStage;

	/// <summary>Netsu (Oct 28): when this window starts, the attack may hit the same opponent again (multi-hit moves in ONE state:
	/// Leticia's 623). Without it a body hit once stays 'already hit' until the state changes.</summary>
	[Export(PropertyHint.None, "")]
	public bool NetsuRehit;

	[Export(PropertyHint.None, "")]
	public HitboxSettings HitboxData;
}
