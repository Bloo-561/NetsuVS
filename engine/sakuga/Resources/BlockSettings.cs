using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class BlockSettings : Resource
{
	[Export(PropertyHint.None, "")]
	public StanceSelect ReferenceStance;

	[Export(PropertyHint.None, "")]
	public BlockType BlockType;

	[Export(PropertyHint.None, "")]
	public MotionInputs InputToCheck;

	[Export(PropertyHint.None, "")]
	public int EnterState;

	[Export(PropertyHint.None, "")]
	public int StunState;

	[Export(PropertyHint.None, "")]
	public int ExitState;

	[Export(PropertyHint.None, "")]
	public int GuardCrushState;
}
