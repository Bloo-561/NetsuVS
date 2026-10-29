using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class SoundsList : Resource
{
	[Export(PropertyHint.None, "")]
	public AudioStream[] Sounds;
}
