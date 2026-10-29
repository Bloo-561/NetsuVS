using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class SpawnVFXAction : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	private Vector2I TargetPosition = Vector2I.Zero;

	[Export(PropertyHint.None, "")]
	private RelativeTo xRelativeTo;

	[Export(PropertyHint.None, "")]
	private RelativeTo yRelativeTo;

	[Export(PropertyHint.None, "")]
	private int Index;

	[Export(PropertyHint.None, "")]
	private bool IsRandom;

	[Export(PropertyHint.None, "")]
	private int Range;

	[Export(PropertyHint.None, "")]
	private string Key;

	[Export(PropertyHint.None, "")]
	private int FromExtraVariable = -1;

	[Export(PropertyHint.None, "")]
	private bool AttachToParent;

	public override void Execute(ref SakugaActor Actor)
	{
		if (Actor.Pool != null)
		{
			Vector2I dst = Actor.GenerateTargetPosition(TargetPosition, Index, xRelativeTo, yRelativeTo);
			int ind = (IsRandom ? RNG.Next(Index, Range) : Index);
			if (FromExtraVariable >= 0)
			{
				ind = Actor.Parameters.Variables[FromExtraVariable].CurrentValue;
				Actor.Parameters.Variables[FromExtraVariable].ChangeBehavior(CustomVariableBehaviorTarget.ON_USE);
			}
			if (ind >= 0)
			{
				Actor.Pool.SpawnVFX(ind, dst, Actor.InputSide(), AttachToParent);
			}
			else if (Key != "")
			{
				Actor.Pool.SpawnVFX(ind, dst, Actor.InputSide(), AttachToParent);
			}
		}
	}
}
