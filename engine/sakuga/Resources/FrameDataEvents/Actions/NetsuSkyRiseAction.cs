using Godot;
using SakugaEngine.Game;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

/// <summary>
/// Netsu (Oct 25 2026): a climb into the sky that fits the stage. On the frame it runs with a Velocity it sets the
/// fighter's vertical speed, and every frame it runs with a Gravity it takes that off the speed (like AddGravityAction).
/// Both are scaled down on a stage whose camera can't go as high as the full climb (StageElement.NetsuCameraTop: a
/// hall's ceiling), so the climb takes as long everywhere but tops out where the camera can still show it: up to the
/// ceiling indoors, the full Height outdoors. Integer maths: the same on every copy of the match.
/// Used by Flan's Big Bang Crash (tools/sprite_port/moves_flan.py).
/// </summary>
[GlobalClass]
public partial class NetsuSkyRiseAction : FrameDataAction
{
	/// <summary>Vertical speed set on this frame (engine units per second; 0 = leave it).</summary>
	[Export(PropertyHint.None, "")]
	public int Velocity;

	/// <summary>Taken off the vertical speed every frame this runs (units per second per second; 0 = none).</summary>
	[Export(PropertyHint.None, "")]
	public int Gravity;

	/// <summary>How high the full climb goes (units): the scale is (stage top - Margin) / Height, at most 1.</summary>
	[Export(PropertyHint.None, "")]
	public int Height = 123000;

	/// <summary>Room left between the top of the climb and the stage's camera top (units).</summary>
	[Export(PropertyHint.None, "")]
	public int Margin = 5000;

	/// <summary>The smallest scale (per mille), however low the stage's top.</summary>
	[Export(PropertyHint.None, "")]
	public int MinScale = 400;

	public override void Execute(ref SakugaActor Actor)
	{
		if (Actor.Body == null)
		{
			return;
		}
		int top = GameManager.Instance != null ? GameManager.Instance.NetsuStageTopUnits() : GlobalVariables.CeilingLimit;
		long k = System.Math.Clamp((long)(top - Margin) * 1000L / System.Math.Max(1, Height), MinScale, 1000L);
		if (Velocity != 0)
		{
			Actor.Body.SetVerticalVelocity((int)(Velocity * k / 1000L));
		}
		if (Gravity != 0)
		{
			Actor.Body.FixedVelocity.Y -= (int)(Gravity * k / 1000L) / 60;
		}
	}
}
