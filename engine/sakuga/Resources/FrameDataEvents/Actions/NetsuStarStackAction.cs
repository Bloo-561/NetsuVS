using Godot;

namespace SakugaEngine.Resources;

/// <summary>
/// Netsu (Oct 29 2026, TamaDeez): Flan's star stacks. Adds Amount stacks (negative takes them away), or with Set sets
/// the count to Amount; always kept between 0 and the fighter's DataContainer.NetsuStarStackMax. A stack can be spent
/// to cancel a special into a different special (StanceManager.NetsuStarCancel). 22A gives 1, 22B 2, 22C fills all 3.
/// </summary>
[GlobalClass]
public partial class NetsuStarStackAction : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	public int Amount = 1;

	[Export(PropertyHint.None, "")]
	public bool Set;

	public override void Execute(ref SakugaActor Actor)
	{
		SakugaActor root = Actor.NetsuRoot() ?? Actor;
		int max = root.Data != null ? root.Data.NetsuStarStackMax : 0;
		if (max <= 0)
		{
			return;
		}
		int v = Set ? Amount : root.NetsuStarStacks + Amount;
		root.NetsuStarStacks = Mathf.Clamp(v, 0, max);
	}
}
