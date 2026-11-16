using Godot;

namespace SakugaEngine.Resources;

/// <summary>Nov 13 (TamaDeez): the run. Each frame she speeds up by Acceleration toward TopSpeed in the direction she
/// faces (a burst: from the dash's first-frame speed to full speed in about 4 frames, like Million Arthur's dash), and
/// keeps running at TopSpeed while forward is held (the Dash Forward move ends on release, MoveSettings.NetsuMinHoldFrames
/// keeps a tap from being a stub). With Brake > 0 it is the skid instead: she slows toward 0 by Brake each frame
/// (Dash_Stop). Integer only, for rollback.</summary>
[GlobalClass]
public partial class NetsuRunAction : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	public int TopSpeed = 74000;

	[Export(PropertyHint.None, "")]
	public int Acceleration = 13500;

	[Export(PropertyHint.None, "")]
	public int Brake;

	public override void Execute(ref SakugaActor Actor)
	{
		if (Actor.Body == null || Actor.OnKnockback())
		{
			return;
		}
		int vx = Actor.Body.FixedVelocity.X;
		if (Brake > 0)
		{
			Actor.Body.SetLateralVelocity(vx - Mathf.Min(Mathf.Abs(vx), Brake) * Mathf.Sign(vx));
			return;
		}
		int side = Actor.InputSide();
		int v = vx * side;   // speed in the direction she faces
		v = v < 0 ? Acceleration : Mathf.Min(TopSpeed, v + Acceleration);
		Actor.Body.SetLateralVelocity(v * side);
	}
}
