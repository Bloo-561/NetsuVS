using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class GameModeSettings : Resource
{
	[Export(PropertyHint.None, "")]
	public string ModeName;

	[Export(PropertyHint.None, "")]
	public bool AutoStart;

	[Export(PropertyHint.None, "")]
	public NetcodeMode NetcodeMode;

	[Export(PropertyHint.None, "")]
	public PauseMode PauseMode;

	[Export(PropertyHint.None, "")]
	public bool UseLAN;

	[Export(PropertyHint.None, "")]
	public bool CanKO;

	[Export(PropertyHint.None, "")]
	public bool AutoFillResources;

	[Export(PropertyHint.None, "")]
	public bool ShowMatchIntro;

	[Export(PropertyHint.None, "")]
	public bool ShowMatchCards;

	[Export(PropertyHint.None, "")]
	public bool ShowTrainingInfo;

	[Export(PropertyHint.None, "")]
	public bool ShowOnlineInfo;

	[Export(PropertyHint.None, "")]
	public bool AllowShowHitboxes;

	[Export(PropertyHint.None, "")]
	public bool AllowShowInputs;

	[Export(PropertyHint.None, "")]
	public bool AllowShowDebugElements;

	[Export(PropertyHint.None, "")]
	public bool AllowUseDebugCommands;

	[Export(PropertyHint.None, "")]
	public bool NoAI;

	[Export(PropertyHint.None, "")]
	public string ReturnToScene;
}
