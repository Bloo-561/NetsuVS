using System;
using Godot;
using SakugaEngine.Global;
using SakugaEngine.Resources;
using SakugaEngine.Utils;

namespace SakugaEngine.UI;

public partial class SelectScreen : Control
{
	[ExportCategory("Settings")]
	[Export(PropertyHint.None, "")]
	private MatchSettings Match;

	[Export(PropertyHint.None, "")]
	private FighterList fightersList;

	[Export(PropertyHint.None, "")]
	private StageList stagesList;

	[Export(PropertyHint.None, "")]
	private BGMList songsList;

	[Export(PropertyHint.None, "")]
	private AudioStream BGM;

	[Export(PropertyHint.None, "")]
	private CharacterSelectStyle PlayerSelection;

	[Export(PropertyHint.None, "")]
	private CharacterSelectMode SelectionMode;

	[Export(PropertyHint.None, "")]
	private Control CharSelectMode;

	[Export(PropertyHint.None, "")]
	private Control StageSelectMode;

	[Export(PropertyHint.None, "")]
	private int P1Selected;

	[Export(PropertyHint.None, "")]
	private int P2Selected = 1;

	[Export(PropertyHint.None, "")]
	private int P1ColorSelected;

	[Export(PropertyHint.None, "")]
	private int P2ColorSelected;

	[Export(PropertyHint.None, "")]
	private int StageSelected = -2;

	[Export(PropertyHint.None, "")]
	private int BGMSelected = -2;

	[Export(PropertyHint.None, "")]
	private bool SinglePlayerSelection;

	[Export(PropertyHint.None, "")]
	private bool AllowSelectStage = true;

	[Export(PropertyHint.None, "")]
	private string destination = "res://scenes/battle/battle.tscn";

	[Export(PropertyHint.None, "")]
	private string returnTo = "res://scenes/main_menu/main_menu.tscn";

	[ExportCategory("Character Select")]
	[Export(PropertyHint.None, "")]
	private TextureRect P1SelectedRender;

	[Export(PropertyHint.None, "")]
	private TextureRect P2SelectedRender;

	[Export(PropertyHint.None, "")]
	private Label P1SelectedName;

	[Export(PropertyHint.None, "")]
	private Label P2SelectedName;

	[Export(PropertyHint.None, "")]
	private TextureRect P1Cursor;

	[Export(PropertyHint.None, "")]
	private TextureRect P2Cursor;

	[Export(PropertyHint.None, "")]
	private PackedScene charactersButtonElement;

	[Export(PropertyHint.None, "")]
	private GridContainer charactersContainer;

	[Export(PropertyHint.None, "")]
	private Texture2D randomCharPortrait;

	[Export(PropertyHint.None, "")]
	private Texture2D randomCharRender;

	[Export(PropertyHint.None, "")]
	private ColorSelectMenu P1ColorSelect;

	[Export(PropertyHint.None, "")]
	private ColorSelectMenu P2ColorSelect;

	[Export(PropertyHint.None, "")]
	private InputRemapper Remapper;

	[ExportCategory("Stage Select")]
	[Export(PropertyHint.None, "")]
	private TextureRect StageSelectedRender;

	[Export(PropertyHint.None, "")]
	private Label StageSelectedName;

	[Export(PropertyHint.None, "")]
	private Label SongSelectedName;

	[Export(PropertyHint.None, "")]
	private Control P1SelectingStage;

	[Export(PropertyHint.None, "")]
	private Control P2SelectingStage;

	[Export(PropertyHint.None, "")]
	private Control StageCursor;

	[Export(PropertyHint.None, "")]
	private PackedScene stagesButtonElement;

	[Export(PropertyHint.None, "")]
	private HBoxContainer stagesContainer;

	[Export(PropertyHint.None, "")]
	private Texture2D randomStageThumbnail;

	[Export(PropertyHint.None, "")]
	private Texture2D autoStageThumbnail;

	private CharacterSelectState P1State;

	private CharacterSelectState P2State;

	private bool isPlayer1SelectingStage = true;

	private bool AllSet;

	private TextureRect[] characterButtons;

	private TextureRect[] stageButtons;

	private Random randomSelection;

	private string p1Prefix;

	private string p2Prefix;

	private bool P1Up;

	private bool P1Down;

	private bool P1Left;

	private bool P1Right;

	private bool P1Confirm;

	private bool P1Return;

	private bool P1Menu;

	private bool P1Options;

	private bool P2Up;

	private bool P2Down;

	private bool P2Left;

	private bool P2Right;

	private bool P2Confirm;

	private bool P2Return;

	private bool P2Menu;

	private bool P2Options;

	private bool P1Finished => P1State == CharacterSelectState.DONE;

	private bool P2Finished => P2State == CharacterSelectState.DONE;

	public override void _Ready()
	{
		base._Ready();
		AudioManager.Instance.PlayBGM(BGM);
		P1Cursor.GetNode<Control>("Frame").Visible = false;
		P2Cursor.GetNode<Control>("Frame").Visible = false;
		randomSelection = new Random();
		if (Match.P1SelectedDevice > -1 && Match.P2SelectedDevice > -1)
		{
			PlayerSelection = CharacterSelectStyle.VERSUS;
		}
		else if (Match.P2SelectedDevice == -1)
		{
			PlayerSelection = CharacterSelectStyle.PLAYER1;
		}
		else if (Match.P1SelectedDevice == -1)
		{
			PlayerSelection = CharacterSelectStyle.PLAYER2;
		}
		p1Prefix = GlobalFunctions.GetPlayerPrefix(Match.P1SelectedDevice);
		p2Prefix = GlobalFunctions.GetPlayerPrefix(Match.P2SelectedDevice);
		characterButtons = new TextureRect[fightersList.elements.Length + 1];
		for (int i = 0; i <= fightersList.elements.Length; i++)
		{
			TextureRect temp = charactersButtonElement.Instantiate(PackedScene.GenEditState.Disabled) as TextureRect;
			if (i == fightersList.elements.Length)
			{
				temp.Name = "Random_Portrait";
				temp.Texture = randomCharPortrait;
			}
			else
			{
				temp.Name = fightersList.elements[i].Profile.ShortName + "_Portrait";
				temp.Texture = fightersList.elements[i].Profile.Portrait;
			}
			characterButtons[i] = temp;
			charactersContainer.AddChild(temp, forceReadableName: false, InternalMode.Disabled);
			AudioManager.Instance.PlayAnnouncerClip(6);
		}
		stageButtons = new TextureRect[stagesList.elements.Length + 2];
		for (int j = -2; j < stagesList.elements.Length; j++)
		{
			TextureRect temp2 = stagesButtonElement.Instantiate(PackedScene.GenEditState.Disabled) as TextureRect;
			if (j == -2)
			{
				temp2.Name = "Auto_Portrait";
				temp2.Texture = autoStageThumbnail;
			}
			else if (j == -1)
			{
				temp2.Name = "Random_Portrait";
				temp2.Texture = randomStageThumbnail;
			}
			else if (j >= 0)
			{
				temp2.Name = stagesList.elements[j].Name + "_Portrait";
				temp2.Texture = stagesList.elements[j].Thumbnail;
			}
			stageButtons[j + 2] = temp2;
			stagesContainer.AddChild(temp2, forceReadableName: false, InternalMode.Disabled);
		}
	}

	public override void _PhysicsProcess(double delta)
	{
		if (!base.Visible || AllSet)
		{
			return;
		}
		base._PhysicsProcess(delta);
		string p1SelectPrefix = ((PlayerSelection != CharacterSelectStyle.PLAYER2) ? p1Prefix : p2Prefix);
		string p2SelectPrefix = ((PlayerSelection != CharacterSelectStyle.PLAYER1) ? p2Prefix : p1Prefix);
		P1Up = Input.IsActionJustPressed(p1SelectPrefix + "_up");
		P1Down = Input.IsActionJustPressed(p1SelectPrefix + "_down");
		P1Left = Input.IsActionJustPressed(p1SelectPrefix + "_left");
		P1Right = Input.IsActionJustPressed(p1SelectPrefix + "_right");
		P1Confirm = Input.IsActionJustPressed(p1SelectPrefix + "_accept");
		P1Return = Input.IsActionJustPressed(p1SelectPrefix + "_return");
		P1Menu = Input.IsActionJustPressed(p1SelectPrefix + "_menu");
		P1Options = Input.IsActionJustPressed(p1SelectPrefix + "_options");
		P2Up = Input.IsActionJustPressed(p2SelectPrefix + "_up");
		P2Down = Input.IsActionJustPressed(p2SelectPrefix + "_down");
		P2Left = Input.IsActionJustPressed(p2SelectPrefix + "_left");
		P2Right = Input.IsActionJustPressed(p2SelectPrefix + "_right");
		P2Confirm = Input.IsActionJustPressed(p2SelectPrefix + "_accept");
		P2Return = Input.IsActionJustPressed(p2SelectPrefix + "_return");
		P2Menu = Input.IsActionJustPressed(p2SelectPrefix + "_menu");
		P2Options = Input.IsActionJustPressed(p2SelectPrefix + "_options");
		switch (SelectionMode)
		{
		case CharacterSelectMode.CHARACTER_SELECT:
			switch (P2State)
			{
			case CharacterSelectState.SELECTING_CHARACTER:
				SelectCharacterP2();
				break;
			case CharacterSelectState.SELECTING_COLOR:
				SelectColorP2();
				break;
			case CharacterSelectState.REMAPPING_INPUTS:
				if (!Remapper.IsP2Remapping)
				{
					HideInputRemapperP2();
				}
				break;
			case CharacterSelectState.DONE:
				if (P2Return)
				{
					P2State = CharacterSelectState.SELECTING_CHARACTER;
				}
				break;
			}
			switch (P1State)
			{
			case CharacterSelectState.SELECTING_CHARACTER:
				SelectCharacterP1();
				break;
			case CharacterSelectState.SELECTING_COLOR:
				SelectColorP1();
				break;
			case CharacterSelectState.REMAPPING_INPUTS:
				if (!Remapper.IsP1Remapping)
				{
					HideInputRemapperP1();
				}
				break;
			case CharacterSelectState.DONE:
				if (P1Return)
				{
					P1State = CharacterSelectState.SELECTING_CHARACTER;
				}
				break;
			}
			break;
		case CharacterSelectMode.STAGE_SELECT:
			SelectStage();
			break;
		}
		SelectionMode = ((P1Finished && P2Finished) ? CharacterSelectMode.STAGE_SELECT : CharacterSelectMode.CHARACTER_SELECT);
		CharSelectMode.Visible = !AllowSelectStage || SelectionMode == CharacterSelectMode.CHARACTER_SELECT;
		StageSelectMode.Visible = AllowSelectStage && SelectionMode == CharacterSelectMode.STAGE_SELECT;
		P1Cursor.GlobalPosition = characterButtons[P1Selected].GlobalPosition;
		P2Cursor.GlobalPosition = characterButtons[P2Selected].GlobalPosition;
		UpdateMenuVisuals();
	}

	private void SelectCharacterP1()
	{
		if (P1Up)
		{
			AudioManager.Instance.PlayMenuClip(0);
			P1Selected -= charactersContainer.Columns;
			if (P1Selected < 0)
			{
				P1Selected += charactersContainer.Columns;
			}
		}
		if (P1Down)
		{
			AudioManager.Instance.PlayMenuClip(0);
			P1Selected += charactersContainer.Columns;
			if (P1Selected > fightersList.elements.Length)
			{
				P1Selected -= charactersContainer.Columns;
			}
		}
		if (P1Left)
		{
			AudioManager.Instance.PlayMenuClip(0);
			if (P1Selected % charactersContainer.Columns > 0)
			{
				P1Selected--;
			}
		}
		if (P1Right)
		{
			AudioManager.Instance.PlayMenuClip(0);
			if (P1Selected % charactersContainer.Columns < charactersContainer.Columns - 1)
			{
				P1Selected++;
			}
			if (P1Selected >= fightersList.elements.Length)
			{
				P1Selected = fightersList.elements.Length;
			}
		}
		if (P1Confirm)
		{
			AudioManager.Instance.PlayMenuClip(1);
			if (P1Selected >= fightersList.elements.Length)
			{
				P1Selected = randomSelection.Next(0, fightersList.elements.Length);
			}
			P1State = CharacterSelectState.SELECTING_COLOR;
			CallColorSelectP1();
			AudioManager.Instance.PlayAnnouncerClip(7 + P1Selected);
		}
		if (P1Return)
		{
			ReturnToPrevious();
		}
		if (P1Options)
		{
			CallInputRemapperP1();
		}
	}

	private void CallColorSelectP1()
	{
		if (P1ColorSelect == null || fightersList.elements[P1Selected].ColorPalettes == null || fightersList.elements[P1Selected].ColorPalettes.Length <= 1)
		{
			P1State = CharacterSelectState.DONE;
			if (SinglePlayerSelection)
			{
				P2State = CharacterSelectState.DONE;
			}
		}
		else
		{
			P1ColorSelect.Activate(fightersList.elements[P1Selected]);
		}
	}

	private void SelectColorP1()
	{
		if (P1Up)
		{
			AudioManager.Instance.PlayMenuClip(0);
			P1ColorSelected--;
			if (P1ColorSelected < 0)
			{
				P1ColorSelected = 0;
			}
			P1ColorSelect.SelectElement(P1ColorSelected);
		}
		if (P1Down)
		{
			AudioManager.Instance.PlayMenuClip(0);
			P1ColorSelected++;
			if (P1ColorSelected >= fightersList.elements[P1Selected].ColorPalettes.Length)
			{
				P1ColorSelected = fightersList.elements[P1Selected].ColorPalettes.Length - 1;
			}
			P1ColorSelect.SelectElement(P1ColorSelected);
		}
		if (P1Confirm)
		{
			AudioManager.Instance.PlayMenuClip(3);
			if (!P2Finished)
			{
				isPlayer1SelectingStage = true;
			}
			P1State = CharacterSelectState.DONE;
			if (SinglePlayerSelection)
			{
				P2State = CharacterSelectState.DONE;
			}
			P1ColorSelect.Deactivate();
		}
		if (P1Return)
		{
			AudioManager.Instance.PlayMenuClip(2);
			P1State = CharacterSelectState.SELECTING_CHARACTER;
			P1ColorSelect.Deactivate();
		}
	}

	private void CallInputRemapperP1()
	{
		Remapper.ToggleInputMapperP1(Match.P1SelectedDevice);
		P1State = CharacterSelectState.REMAPPING_INPUTS;
	}

	private void HideInputRemapperP1()
	{
		P1State = CharacterSelectState.SELECTING_CHARACTER;
	}

	private void SelectCharacterP2()
	{
		if ((int)PlayerSelection > 0 && !P1Finished)
		{
			return;
		}
		if (P2Up)
		{
			AudioManager.Instance.PlayMenuClip(0);
			P2Selected -= charactersContainer.Columns;
			if (P2Selected < 0)
			{
				P2Selected += charactersContainer.Columns;
			}
		}
		if (P2Down)
		{
			AudioManager.Instance.PlayMenuClip(0);
			P2Selected += charactersContainer.Columns;
			if (P2Selected > fightersList.elements.Length)
			{
				P2Selected -= charactersContainer.Columns;
			}
		}
		if (P2Left)
		{
			AudioManager.Instance.PlayMenuClip(0);
			if (P2Selected % charactersContainer.Columns > 0)
			{
				P2Selected--;
			}
		}
		if (P2Right)
		{
			AudioManager.Instance.PlayMenuClip(0);
			if (P2Selected % charactersContainer.Columns < charactersContainer.Columns - 1)
			{
				P2Selected++;
			}
			if (P2Selected >= fightersList.elements.Length)
			{
				P2Selected = fightersList.elements.Length;
			}
		}
		if (P2Confirm)
		{
			AudioManager.Instance.PlayMenuClip(1);
			if (P2Selected >= fightersList.elements.Length)
			{
				P2Selected = randomSelection.Next(0, fightersList.elements.Length);
			}
			P2State = CharacterSelectState.SELECTING_COLOR;
			AudioManager.Instance.PlayAnnouncerClip(7 + P2Selected);
			CallColorSelectP2();
		}
		if (P2Return)
		{
			AudioManager.Instance.PlayMenuClip(2);
			ReturnToPrevious();
		}
		if (P2Options)
		{
			CallInputRemapperP2();
		}
	}

	private void CallColorSelectP2()
	{
		if (P2ColorSelect == null || fightersList.elements[P2Selected].ColorPalettes == null || fightersList.elements[P2Selected].ColorPalettes.Length <= 1)
		{
			P2State = CharacterSelectState.DONE;
		}
		else
		{
			P2ColorSelect.Activate(fightersList.elements[P2Selected]);
		}
	}

	private void SelectColorP2()
	{
		if (P2Up)
		{
			AudioManager.Instance.PlayMenuClip(0);
			P2ColorSelected--;
			if (P2ColorSelected < 0)
			{
				P2ColorSelected = 0;
			}
			P2ColorSelect.SelectElement(P2ColorSelected);
		}
		if (P2Down)
		{
			AudioManager.Instance.PlayMenuClip(0);
			P2ColorSelected++;
			if (P2ColorSelected >= fightersList.elements[P2Selected].ColorPalettes.Length)
			{
				P2ColorSelected = fightersList.elements[P2Selected].ColorPalettes.Length - 1;
			}
			P2ColorSelect.SelectElement(P2ColorSelected);
		}
		if (P2Confirm)
		{
			AudioManager.Instance.PlayMenuClip(3);
			if (!P1Finished)
			{
				isPlayer1SelectingStage = false;
			}
			P2State = CharacterSelectState.DONE;
			P2ColorSelect.Deactivate();
		}
		if (P2Return)
		{
			AudioManager.Instance.PlayMenuClip(2);
			P2State = CharacterSelectState.SELECTING_CHARACTER;
			P2ColorSelect.Deactivate();
		}
	}

	private void CallInputRemapperP2()
	{
		Remapper.ToggleInputMapperP2(Match.P2SelectedDevice);
		P2State = CharacterSelectState.REMAPPING_INPUTS;
	}

	private void HideInputRemapperP2()
	{
		P2State = CharacterSelectState.SELECTING_CHARACTER;
	}

	private void ReturnToPrevious()
	{
		if ((int)PlayerSelection > 0 && P1Finished)
		{
			P1State = CharacterSelectState.SELECTING_CHARACTER;
			P2State = CharacterSelectState.SELECTING_CHARACTER;
		}
		else if (returnTo == "")
		{
			base.Visible = false;
		}
		else
		{
			LoadingScreenManager.Instance.LoadScene(returnTo);
		}
	}

	private void SelectStage()
	{
		if (!AllowSelectStage)
		{
			MatchSetup();
			return;
		}
		bool Up;
		bool Down;
		bool Left;
		bool Right;
		bool Confirm;
		bool Return;
		if (isPlayer1SelectingStage)
		{
			Up = P1Up;
			Down = P1Down;
			Left = P1Left;
			Right = P1Right;
			Confirm = P1Confirm;
			Return = P1Return;
		}
		else
		{
			Up = P2Up;
			Down = P2Down;
			Left = P2Left;
			Right = P2Right;
			Confirm = P2Confirm;
			Return = P2Return;
		}
		if (Left)
		{
			AudioManager.Instance.PlayMenuClip(0);
			StageSelected--;
			if (StageSelected < -2)
			{
				StageSelected = -2;
			}
		}
		if (Right)
		{
			AudioManager.Instance.PlayMenuClip(0);
			StageSelected++;
			if (StageSelected >= stagesList.elements.Length)
			{
				StageSelected = stagesList.elements.Length - 1;
			}
		}
		if (Up)
		{
			AudioManager.Instance.PlayMenuClip(0);
			BGMSelected--;
			if (BGMSelected < -2)
			{
				BGMSelected = -2;
			}
		}
		if (Down)
		{
			AudioManager.Instance.PlayMenuClip(0);
			BGMSelected++;
			if (BGMSelected >= songsList.elements.Length)
			{
				BGMSelected = songsList.elements.Length - 1;
			}
		}
		if (Confirm)
		{
			if (StageSelected == -2)
			{
				StageSelected = fightersList.elements[P2Selected].Profile.AutoStage;
			}
			else if (StageSelected == -1)
			{
				StageSelected = randomSelection.Next(0, stagesList.elements.Length);
			}
			if (BGMSelected == -2)
			{
				BGMSelected = fightersList.elements[P2Selected].Profile.AutoBGM;
			}
			else if (BGMSelected == -1)
			{
				BGMSelected = randomSelection.Next(0, songsList.elements.Length);
			}
			AllSet = true;
			MatchSetup();
		}
		if (Return)
		{
			AudioManager.Instance.PlayMenuClip(2);
			P1State = CharacterSelectState.SELECTING_CHARACTER;
			P2State = CharacterSelectState.SELECTING_CHARACTER;
		}
	}

	private void UpdateMenuVisuals()
	{
		bool canShowP2 = SinglePlayerSelection || ((int)PlayerSelection > 0 && !P1Finished);
		P2SelectedRender.Visible = !canShowP2;
		P2SelectedName.Visible = !canShowP2;
		P2Cursor.Visible = !canShowP2;
		if (P1Selected < fightersList.elements.Length)
		{
			P1SelectedRender.Texture = fightersList.elements[P1Selected].Profile.Render;
			P1SelectedName.Text = fightersList.elements[P1Selected].Profile.FighterName;
		}
		else
		{
			P1SelectedRender.Texture = randomCharRender;
			P1SelectedName.Text = "Random";
		}
		if (P2Selected < fightersList.elements.Length)
		{
			P2SelectedRender.Texture = fightersList.elements[P2Selected].Profile.Render;
			P2SelectedName.Text = fightersList.elements[P2Selected].Profile.FighterName;
		}
		else
		{
			P2SelectedRender.Texture = randomCharRender;
			P2SelectedName.Text = "Random";
		}
		P1SelectingStage.Visible = isPlayer1SelectingStage;
		P2SelectingStage.Visible = !isPlayer1SelectingStage;
		StageCursor.GlobalPosition = stageButtons[StageSelected + 2].GlobalPosition;
		if (SelectionMode == CharacterSelectMode.STAGE_SELECT)
		{
			if (StageSelected == -2)
			{
				StageSelectedRender.Texture = autoStageThumbnail;
				StageSelectedName.Text = "Auto";
			}
			else if (StageSelected == -1)
			{
				StageSelectedRender.Texture = randomStageThumbnail;
				StageSelectedName.Text = "Random";
			}
			else if (StageSelected >= 0)
			{
				StageSelectedRender.Texture = stagesList.elements[StageSelected].Thumbnail;
				StageSelectedName.Text = stagesList.elements[StageSelected].Name;
			}
		}
		else
		{
			StageSelectedRender.Texture = null;
		}
		if (BGMSelected == -2)
		{
			SongSelectedName.Text = "Auto";
		}
		else if (BGMSelected == -1)
		{
			SongSelectedName.Text = "Random";
		}
		else if (BGMSelected >= 0)
		{
			SongSelectedName.Text = songsList.elements[BGMSelected].SongName;
		}
	}

	private void MatchSetup()
	{
		Match.P1SelectedCharacter = P1Selected;
		Match.P1SelectedColor = P1ColorSelected;
		Match.P2SelectedCharacter = P2Selected;
		Match.P2SelectedColor = P2ColorSelected;
		Match.SelectedStage = StageSelected;
		Match.SelectedBGM = BGMSelected;
		if (destination == null)
		{
			base.Visible = false;
		}
		else
		{
			LoadingScreenManager.Instance.LoadMatch(destination, fightersList.elements[P1Selected].Profile, fightersList.elements[P2Selected].Profile);
		}
	}
}
