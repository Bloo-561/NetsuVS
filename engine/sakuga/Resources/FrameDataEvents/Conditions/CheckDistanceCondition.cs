using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class CheckDistanceCondition : FrameDataCondition
{
	[Export(PropertyHint.None, "")]
	private int MinDistance;

	[Export(PropertyHint.None, "")]
	private int MaxDistance;

	[Export(PropertyHint.None, "")]
	private RelativeTo RelativeTo;

	[Export(PropertyHint.None, "")]
	private int Index;

	[Export(PropertyHint.None, "")]
	private bool Not;

	public override bool Check(ref SakugaActor Actor)
	{
		if (Actor.Body == null)
		{
			return false;
		}
		int dist = GlobalFunctions.HorizontalDistance(Actor.Body.FixedPosition, Actor.GenerateTargetPosition(Vector2I.Zero, Index, RelativeTo, RelativeTo));
		if (Not)
		{
			if (dist >= MinDistance)
			{
				return dist > MaxDistance;
			}
			return true;
		}
		if (dist >= MinDistance)
		{
			return dist <= MaxDistance;
		}
		return false;
	}
}
