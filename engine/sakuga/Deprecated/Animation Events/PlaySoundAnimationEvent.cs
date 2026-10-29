using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class PlaySoundAnimationEvent : AnimationEvent
{
	[Export(PropertyHint.None, "")]
	public SoundType SoundType;

	[Export(PropertyHint.None, "")]
	public int Source;

	[Export(PropertyHint.None, "")]
	public int Index;

	[Export(PropertyHint.None, "")]
	public bool IsRandom;

	[Export(PropertyHint.None, "")]
	public int Range;

	[Export(PropertyHint.None, "")]
	public int FromExtraVariable = -1;
}
