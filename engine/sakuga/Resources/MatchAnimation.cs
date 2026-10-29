using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class MatchAnimation : Resource
{
	[Export(PropertyHint.None, "")]
	public string Name;

	[Export(PropertyHint.None, "")]
	public int Duration;

	[Export(PropertyHint.None, "")]
	public int DelaySubtract;

	[Export(PropertyHint.None, "")]
	public int AnnouncerLineIndex = -1;
}
