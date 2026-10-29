using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
[Tool]
public partial class AnimationSettings : Resource
{
	[Export(PropertyHint.None, "")]
	public int AtFrame;

	[Export(PropertyHint.None, "")]
	public SpriteModifier[] Modifiers;
}
