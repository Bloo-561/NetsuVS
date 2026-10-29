using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class ColorPaletteElement : Resource
{
	[Export(PropertyHint.None, "")]
	public string PaletteName;

	/// <summary>The fighter scene for this colour, loaded with the roster. Netsu (Oct 24): leave empty
	/// and set ScenePath instead, so a fight loads only the two fighters in it (each fighter scene pulls
	/// in all of its sprites).</summary>
	[Export(PropertyHint.None, "")]
	public PackedScene Instance;

	/// <summary>Netsu: path of the fighter scene for this colour, loaded when it's needed (GetScene).</summary>
	[Export(PropertyHint.File, "*.tscn,*.scn")]
	public string ScenePath = "";

	/// <summary>Netsu: the fighter scene: Instance if set, otherwise loaded from ScenePath (cached by Godot).</summary>
	public PackedScene GetScene()
	{
		if (Instance != null)
		{
			return Instance;
		}
		if (string.IsNullOrEmpty(ScenePath))
		{
			return null;
		}
		return ResourceLoader.Load<PackedScene>(ScenePath);
	}
}
