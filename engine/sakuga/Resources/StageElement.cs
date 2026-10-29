using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class StageElement : Resource
{
	/// <summary>The stage scene, loaded with the list. Netsu (Oct 24): leave empty and set ScenePath
	/// instead, so only the stage being played is loaded (a list holding every stage loaded all of them,
	/// hundreds of MB of textures, each time a fight or the stage select started).</summary>
	[Export(PropertyHint.None, "")]
	public PackedScene Instance;

	/// <summary>Netsu: path of the stage scene, loaded only when this stage is played (GetScene).</summary>
	[Export(PropertyHint.File, "*.tscn,*.scn")]
	public string ScenePath = "";

	[Export(PropertyHint.None, "")]
	public string Name;

	[Export(PropertyHint.None, "")]
	public Texture2D Thumbnail;

	/// <summary>Netsu (Oct 25): the highest the fight camera may go on this stage (metres: its eye height), so it never
	/// looks over a ceiling or past where the scenery ends; fighters flying higher (Flan's Big Bang Crash) leave the top
	/// of the screen instead. 0 = no limit but the engine's 25 m. Measured for each stage with renders from the fight
	/// camera (docs/game_systems.md, Camera).</summary>
	[Export(PropertyHint.None, "")]
	public float NetsuCameraTop;

	/// <summary>Netsu: the stage scene: Instance if set, otherwise loaded from ScenePath (cached by Godot).</summary>
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
