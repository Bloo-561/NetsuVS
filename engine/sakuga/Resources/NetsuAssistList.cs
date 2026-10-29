using Godot;

namespace SakugaEngine.Resources;

/// <summary>Netsu: every assist the players can pick (data/assist_list.tres). The order is the
/// order on the character select; MatchSettings.P1SelectedAssist / P2SelectedAssist index it.</summary>
[GlobalClass]
public partial class NetsuAssistList : Resource
{
	[Export(PropertyHint.None, "")]
	public NetsuAssistElement[] Assists;
}
