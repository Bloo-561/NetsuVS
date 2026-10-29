using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class AnimationEventsList : Resource
{
	[Export(PropertyHint.None, "")]
	public int Frame;

	[Export(PropertyHint.None, "")]
	public AnimationEvent[] Events;
}
