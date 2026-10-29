using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class FighterStance : Resource
{
	[ExportCategory("Settings")]
	[Export(PropertyHint.None, "")]
	public bool IsDamagePersistent;

	[Export(PropertyHint.None, "")]
	public bool IsRoundPersistent;

	[Export(PropertyHint.None, "")]
	public int DefaultState;

	[Export(PropertyHint.None, "")]
	public MoveSettings[] Moves;

	[Export(PropertyHint.None, "")]
	public int[] HitReactions;

	[Export(PropertyHint.None, "")]
	public BlockSettings[] BlockReactions;

	[ExportCategory("Throw Escape")]
	[Export(PropertyHint.None, "")]
	public MotionInputs ThrowEscapeInput;

	[Export(PropertyHint.None, "")]
	public int GroundThrowEscapeState = -1;

	[Export(PropertyHint.None, "")]
	public int AirThrowEscapeState = -1;
}
