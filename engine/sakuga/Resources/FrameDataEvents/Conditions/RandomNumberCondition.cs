using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class RandomNumberCondition : FrameDataCondition
{
	[Export(PropertyHint.None, "")]
	private Vector2I Range = new Vector2I(0, int.MaxValue);

	[Export(PropertyHint.None, "")]
	private int Value;

	[Export(PropertyHint.None, "")]
	private bool Not;

	public override bool Check(ref SakugaActor Actor)
	{
		int random = RNG.Next(Range.X, Range.Y);
		if (Not)
		{
			return random != Value;
		}
		return random == Value;
	}
}
