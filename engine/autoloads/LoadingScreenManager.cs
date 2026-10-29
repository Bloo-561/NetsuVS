using Godot;
using SakugaEngine;
using SakugaEngine.Resources;

public partial class LoadingScreenManager : Node
{
	public static LoadingScreenManager Instance;

	private Control LoadingScreenSimple;

	private Control LoadingScreenMatchStart;

	private string SimpleDir = "res://engine/ui/loading_screens/LoadingScreen_Simple.tscn";

	private string MatchDir = "res://engine/ui/loading_screens/LoadingScreen_Match.tscn";

	private string JingleDir = "res://assets/audio/music/mahou/04 Versus Screen [No Loop].wav";

	private AudioStream Jingle;

	private string currentLoadingScene;

	public override void _Ready()
	{
		Instance = this;
		LoadingScreenSimple = GD.Load<PackedScene>(SimpleDir).Instantiate(PackedScene.GenEditState.Disabled) as Control;
		LoadingScreenMatchStart = GD.Load<PackedScene>(MatchDir).Instantiate(PackedScene.GenEditState.Disabled) as Control;
		Jingle = GD.Load<AudioStream>(JingleDir);
		AddChild(LoadingScreenSimple, forceReadableName: false, InternalMode.Disabled);
		AddChild(LoadingScreenMatchStart, forceReadableName: false, InternalMode.Disabled);
		LoadingScreenSimple.Visible = false;
		LoadingScreenMatchStart.Visible = false;
	}

	public override void _Process(double delta)
	{
		if (!LoadingScreenSimple.Visible && !LoadingScreenMatchStart.Visible)
		{
			return;
		}
		base._Process(delta);
		ResourceLoader.ThreadLoadStatus status = ResourceLoader.LoadThreadedGetStatus(currentLoadingScene);
		if ((ulong)status <= 3uL)
		{
			switch ((int)status)
			{
			case 3:
				SceneLoaded();
				break;
			case 0:
			case 1:
			case 2:
				break;
			}
		}
	}

	public void LoadScene(string nextScene)
	{
		// Netsu (Oct 25): every scene change goes through SceneRouter (game/autoloads/scene_router.gd): the screen
		// fades to black and the Netsu emblem lights up while the next scene loads, like the menus
		Node router = GetTree().Root.GetNodeOrNull("SceneRouter");
		if (router != null && router.HasMethod("go_to"))
		{
			router.Call("go_to", nextScene);
			return;
		}
		currentLoadingScene = nextScene;
		ResourceLoader.LoadThreadedRequest(currentLoadingScene, "", useSubThreads: false, ResourceLoader.CacheMode.Reuse);
		LoadingScreenSimple.SetDeferred(CanvasItem.PropertyName.Visible, true);
	}

	public void LoadMatch(string nextScene, FighterProfile player1Profile, FighterProfile player2Profile)
	{
		currentLoadingScene = nextScene;
		ResourceLoader.LoadThreadedRequest(currentLoadingScene, "", useSubThreads: false, ResourceLoader.CacheMode.Reuse);
		CallDeferred("MatchSceneSetup", player1Profile, player2Profile);
		LoadingScreenMatchStart.SetDeferred(CanvasItem.PropertyName.Visible, true);
	}

	public void SceneLoaded()
	{
		if (!LoadingScreenMatchStart.Visible || !AudioManager.Instance.PlayingBGM())
		{
			GetTree().ChangeSceneToFile(currentLoadingScene);
			GD.Print("Scene " + currentLoadingScene + " loaded successfully!");
			LoadingScreenSimple.Visible = false;
			LoadingScreenMatchStart.Visible = false;
		}
	}

	private void MatchSceneSetup(FighterProfile player1Profile, FighterProfile player2Profile)
	{
		LoadingScreenMatchStart.GetNode<TextureRect>("P1SelectedRender").Texture = player1Profile.Render;
		LoadingScreenMatchStart.GetNode<TextureRect>("P2SelectedRender").Texture = player2Profile.Render;
		LoadingScreenMatchStart.GetNode<Label>("P1SelectedName").Text = player1Profile.FighterName;
		LoadingScreenMatchStart.GetNode<Label>("P2SelectedName").Text = player2Profile.FighterName;
		AudioManager.Instance.PlayBGM(Jingle);
	}
}
