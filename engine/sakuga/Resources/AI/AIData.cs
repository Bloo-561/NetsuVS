using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class AIData : Resource
{
	[ExportCategory("Actions")]
	[Export(PropertyHint.None, "")]
	public AIAction[] Actions;

	[Export(PropertyHint.None, "")]
	public int HighBlockAction;

	[Export(PropertyHint.None, "")]
	public int LowBlockAction;

	[Export(PropertyHint.None, "")]
	public int ForwardRecoveryAction;

	[Export(PropertyHint.None, "")]
	public int BackRecoveryAction;

	[Export(PropertyHint.None, "")]
	public int ThrowEscapeAction;

	[ExportCategory("Behaviors")]
	[Export(PropertyHint.None, "")]
	public AIBehavior BehaviorBeginner;

	[Export(PropertyHint.None, "")]
	public AIBehavior BehaviorEasy;

	[Export(PropertyHint.None, "")]
	public AIBehavior BehaviorMedium;

	[Export(PropertyHint.None, "")]
	public AIBehavior BehaviorHard;

	[Export(PropertyHint.None, "")]
	public AIBehavior BehaviorVeryHard;

	[Export(PropertyHint.None, "")]
	public AIBehavior BehaviorPro;
}
