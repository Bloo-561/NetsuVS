using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class HitNotificationElement : Resource
{
	[Export(PropertyHint.None, "")]
	public string NotificationName;

	[Export(PropertyHint.MultilineText, "")]
	public string Description;

	[Export(PropertyHint.None, "")]
	public int AnnouncerVoiceLine = -1;
}
