using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class CameraShakeAction : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	public float Amplitude;

	[Export(PropertyHint.None, "")]
	public float WaveLength;

	[Export(PropertyHint.None, "")]
	public int Duration;

	[Export(PropertyHint.None, "")]
	public bool SideRelative;

	[Export(PropertyHint.None, "")]
	public Vector2 Direction;

	public override void Execute(ref SakugaActor Actor)
	{
		// Netsu: Amplitude in world units (0.04 = a heavy hit), Duration in frames.
		FighterCamera.Shake(Amplitude, Duration);
	}
}
