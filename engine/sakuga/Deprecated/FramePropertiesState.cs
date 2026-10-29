using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class FramePropertiesState : Resource
{
	[Export(PropertyHint.None, "")]
	public int Frame;

	[Export(PropertyHint.None, "")]
	public FrameProperties Properties;
}
