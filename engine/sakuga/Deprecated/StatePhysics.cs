using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class StatePhysics : Resource
{
	[Export(PropertyHint.None, "")]
	public int Frame;

	[Export(PropertyHint.None, "")]
	public bool UseLateralSpeed;

	[Export(PropertyHint.None, "")]
	public int LateralSpeed;

	[Export(PropertyHint.None, "")]
	public bool UseVerticalSpeed;

	[Export(PropertyHint.None, "")]
	public int VerticalSpeed;

	[Export(PropertyHint.None, "")]
	public bool UseGravity;

	[Export(PropertyHint.None, "")]
	public bool ResetGravity;

	[Export(PropertyHint.None, "")]
	public int Gravity;

	[Export(PropertyHint.None, "")]
	public bool UseLateralInertia;

	[Export(PropertyHint.None, "")]
	public bool UseVerticalInertia;

	[Export(PropertyHint.None, "")]
	public bool UseHorizontalInput;

	[Export(PropertyHint.None, "")]
	public bool UseVerticalInput;
}
