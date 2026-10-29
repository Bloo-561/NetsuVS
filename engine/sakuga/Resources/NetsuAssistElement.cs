using Godot;

namespace SakugaEngine.Resources;

/// <summary>
/// Netsu: one assist character (Mary, Adin, Eren...). Listed in data/assist_list.tres.
/// </summary>
[GlobalClass]
public partial class NetsuAssistElement : Resource
{
	[Export(PropertyHint.None, "")]
	public string AssistName = "Assist";

	/// <summary>The assist character: actors/assists/&lt;name&gt;/Instances/&lt;TAG&gt;_Assist.tscn (a SakugaActor).</summary>
	[Export(PropertyHint.None, "")]
	public PackedScene Instance;

	/// <summary>Small square picture (character select, battle HUD).</summary>
	[Export(PropertyHint.None, "")]
	public Texture2D Icon;

	/// <summary>Bigger picture for the character select (optional).</summary>
	[Export(PropertyHint.None, "")]
	public Texture2D Portrait;

	[Export(PropertyHint.None, "")]
	public NetsuAssistMove[] Moves;

	/// <summary>Size of the gauge at the start of a round (it starts full).</summary>
	[Export(PropertyHint.None, "")]
	public int StartingCooldown = 600;

	/// <summary>Safety net: the assist is sent away after this many frames on screen.</summary>
	[Export(PropertyHint.None, "")]
	public int MaxOnScreen = 600;

	[Export(PropertyHint.MultilineText)]
	public string Description = "";

	// Buff look (shown on the fighter while an assist's buff lasts): the aura drawn around the buffed fighter
	[ExportGroup("Buff look")]
	[Export(PropertyHint.None, "")]
	public Texture2D[] BuffAura;

	/// <summary>Flash when the buff starts (same canvas size as the aura).</summary>
	[Export(PropertyHint.None, "")]
	public Texture2D BuffPulse;

	/// <summary>Bottom-left corner of the aura picture, in sprite pixels from the fighter's feet (y up).</summary>
	[Export(PropertyHint.None, "")]
	public Vector2 BuffAuraOffset = new Vector2(-200f, -40f);

	[Export(PropertyHint.None, "")]
	public float BuffAuraPixelSize = 0.00275f;

	[Export(PropertyHint.None, "")]
	public Color BuffAuraTint = new Color(1f, 1f, 1f, 0.75f);

	/// <summary>Frames each aura picture shows.</summary>
	[Export(PropertyHint.None, "")]
	public int BuffAuraFrameTime = 5;
}
