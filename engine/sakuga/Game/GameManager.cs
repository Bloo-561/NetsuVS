using System;
using System.Collections.Generic;
using System.Text;
using Godot;
using MessagePack;
using PleaseResync;
using SakugaEngine.Collision;
using SakugaEngine.GameState;
using SakugaEngine.Global;
using SakugaEngine.Resources;
using SakugaEngine.UI;

namespace SakugaEngine.Game;

public partial class GameManager : Node, IGameState
{
	public static GameManager Instance;

	public InputManager[] Inputs = Array.Empty<InputManager>();

	[Export(PropertyHint.None, "")]
	public MatchSettings Match;

	[Export(PropertyHint.None, "")]
	public GameMonitor Monitor;

	[Export(PropertyHint.None, "")]
	public FighterList fightersList;

	[Export(PropertyHint.None, "")]
	public StageList stagesList;

	[Export(PropertyHint.None, "")]
	public BGMList songsList;

	[Export(PropertyHint.None, "")]
	public HitNotificationList notifications;

	[Export(PropertyHint.None, "")]
	private CanvasLayer FighterUI;

	[Export(PropertyHint.None, "")]
	public FighterCamera Camera;

	private Label SeedViewer;

	private FadeScreen Curtain;

	public uint InputSize;

	public List<SakugaNode> Nodes = new List<SakugaNode>();

	private SakugaActor[] Fighters;

	private PhysicsWorld World;

	/// <summary>Netsu: the physics world (the CPU looks at every attack box in it).</summary>
	public PhysicsWorld NetsuWorld => World;

	private HealthHUD healthHUD;

	private MetersHUD metersHUD;

	public int Frame;

	private int generatedSeed;

	private int finalSeed;

	public bool ShowHitboxes;

	public Vector3I randomTest;

	private GameManagerState State;

	private PauseMenu PauseScreen;

	public HitNotifications[] Notifs;

	private bool paused;

	/// <summary>Netsu: Training mode's dummy and gauge settings (NetsuTraining.cs); null in other modes.</summary>
	public NetsuTraining Training;

	private Godot.Collections.Dictionary _netsuTrainingOptions;

	private readonly PlayerInputs[] _netsuInputs = new PlayerInputs[2];

	// --- Netsu: the EX / super pause (Oct 24 late) ------------------------------------------
	// When a fighter starts an EX move (2 bars) or a super (3 bars), the whole fight stops for a moment: nothing in
	// the match moves (fighters, assists, projectiles, effects), the clock stops and inputs wait. Meanwhile the camera
	// closes in on her (FighterCamera) and the screen goes darker (netsu_super_flash.gd), so everyone sees who did
	// it. Then the fight goes on and the opponent stays frozen for the move's own flash, as before: the timing
	// between the two fighters doesn't change. Started by StanceManager (ExecuteMove / NetsuDelayedFlash).
	// Match state (saved for rollback: GameManagerState).

	/// <summary>Netsu (Oct 26, TamaDeez): how far normals push back, on hit and on block, in percent of the value
	/// in the move's hitbox (100 = as built). Only ground normals (move Priority 6 or less, no meter): specials,
	/// EX moves, supers, assists and projectiles keep their own pushback. The frame data sheets still show the
	/// unscaled numbers.</summary>
	[Export(PropertyHint.Range, "0,200,5")]
	public int NetsuNormalPushbackPercent = 60;

	/// <summary>Netsu (Oct 27 c29, TamaDeez): in the corner (the opponent against the wall) the attacker is pushed back
	/// by this percent of the push the opponent would have taken midscreen (SakugaActor.HitPushback). 100 = the same
	/// gap as midscreen; lower keeps corner strings tight (5A > 5B > 5C link). 0 = no corner pushback at all.</summary>
	[Export(PropertyHint.Range, "0,100,5")]
	public int NetsuCornerPushbackPercent = 25;

	/// <summary>Netsu (Oct 26, TamaDeez): OTG. A fighter lying on the ground can be hit (they stay down, no
	/// pick-up) for this many frames after they land, at full damage scaling. The more scaled the combo is, the
	/// shorter it gets (none at the minimum scaling). After it, and while getting up, they can't be hit.</summary>
	[Export(PropertyHint.Range, "0,300,1")]
	public int NetsuOtgWindowFrames = 90;   // Oct 27 c27: 100 -> 90 (c25: 120 -> 100, c24: 90 -> 120, c22: 180 -> 90, c20: 45 -> 180). Scaled by the combo's proration when they land, then fixed (SakugaActor.NetsuOtgWindow)

	/// <summary>Netsu (Oct 27 c27, TamaDeez): what one OTG hit takes off the OTG window (frames), by the button of the move
	/// that hit: A, B, C. A move with no single button (two buttons, held, throws...) costs the B amount. The window is
	/// set when they land and OTG hits only take these off (their damage scaling no longer shrinks it).</summary>
	[Export(PropertyHint.Range, "0,60,1")]
	public int NetsuOtgCostA = 4;

	[Export(PropertyHint.Range, "0,60,1")]
	public int NetsuOtgCostB = 7;

	[Export(PropertyHint.Range, "0,60,1")]
	public int NetsuOtgCostC = 10;

	/// <summary>Netsu (Oct 26 evening, TamaDeez): the longest a knockdown keeps a fighter on the floor (frames from
	/// landing; they get up then: SakugaActor.NetsuGetUpWhenDue). Was 76 for everyone (the knockdown and Hit_Down
	/// animations). Keep it above NetsuOtgWindowFrames.</summary>
	[Export(PropertyHint.None, "")]
	public int NetsuKnockdownImpactFrames = 28;   // Oct 27 c34: hard knockdown, ticks from the first ground impact: impact / bounce 28 + lying 22 + get-up 22 = 72

	[Export(PropertyHint.None, "")]
	public int NetsuKnockdownLyingFrames = 22;

	[Export(PropertyHint.None, "")]
	public int NetsuKnockdownGetUpFrames = 22;

	[Export(PropertyHint.Range, "0,120,1")]
	public int NetsuDownTotalFrames = 20;   // Oct 27 c33: the shortest a knockdown keeps them down (OTG window shorter than this, e.g. a heavily scaled combo); was 50

	/// <summary>Netsu (Oct 26 c15, TamaDeez): BlazBlue / Under Night style juggle decay. Every hit's hitstun (= the time
	/// before the victim can tech) loses 1 frame for every NetsuJuggleDecayEvery frames the combo has lasted past
	/// NetsuJuggleGraceFrames, up to NetsuJuggleMaxDecay. Long combos (assists included: it counts the victim's time)
	/// end on their own: the victim techs out. Shown under the combo counter (the juggle meter).</summary>
	[Export(PropertyHint.Range, "0,600,1")]
	public int NetsuJuggleGraceFrames = 180;   // Oct 27 c27: 150 -> 180

	[Export(PropertyHint.Range, "1,60,1")]
	public int NetsuJuggleDecayEvery = 6;

	[Export(PropertyHint.Range, "0,120,1")]
	public int NetsuJuggleMaxDecay = 55;   // Oct 27 c27: 45 -> 55 (the air bonus below is bigger, so long combos still end)

	/// <summary>Netsu (Oct 27 c27, TamaDeez): every hit on an opponent in the air gets this much more untech time (the
	/// juggle is more forgiving), before the decays.</summary>
	[Export(PropertyHint.Range, "0,30,1")]
	public int NetsuAirUntechBonus = 8;

	/// <summary>Netsu (Oct 28, TamaDeez): air tech. From the tech press she can't act (attack, jump, air dash, special)
	/// for this many frames (the 20-frame tech animation is part of it), and buttons pressed during that time are
	/// thrown away, so mashing doesn't give a normal the first frame she's free. She is invincible from the tech until
	/// she lands; acting before landing ends it.</summary>
	[Export(PropertyHint.Range, "0,60,1")]
	public int NetsuAirTechActDelay = 26;

	// ---- Netsu (Oct 28): UNI-style recovery scaling. Replaces the time decay, repeat decay and bonuses above for AIR hits
	// (ground hitstun keeps them). Each hit sets the victim's untech time to base x the combo's recovery scale, then
	// multiplies that scale by the move's multiplier. Per-hitbox overrides: HitboxElement.NetsuAirUntech etc.
	[Export(PropertyHint.None, "")]
	public bool NetsuRecoveryScaling = true;   // false = the older decay system

	[Export(PropertyHint.Range, "1,30,1")]
	public int NetsuMinUntech = 6;

	[Export(PropertyHint.Range, "0,120,1")]
	public int NetsuUntechLight = 28;   // Oct 29: 24 -> 28 (more combo freedom)

	[Export(PropertyHint.Range, "0,120,1")]
	public int NetsuUntechMedium = 36;   // Oct 29: 32 -> 36

	[Export(PropertyHint.Range, "0,120,1")]
	public int NetsuUntechHeavy = 44;   // Oct 29: 40 -> 44

	[Export(PropertyHint.Range, "0,120,1")]
	public int NetsuUntechSpecial = 48;   // Oct 29: 40 -> 44; Nov 3: 48 (longer combos)

	[Export(PropertyHint.Range, "0,120,1")]
	public int NetsuUntechEx = 56;   // Nov 3: 52 -> 56. EX moves and supers (a dedicated launcher: set 48 on its hitbox)

	[Export(PropertyHint.Range, "500,1000,1")]
	public int NetsuScaleLight = 970;   // Oct 29: the juggle meter drains a bit slower; Nov 3: 955 -> 970 (long, floaty combos)

	[Export(PropertyHint.Range, "500,1000,1")]
	public int NetsuScaleMedium = 955;   // Nov 3: 935 -> 955

	[Export(PropertyHint.Range, "500,1000,1")]
	public int NetsuScaleHeavy = 945;   // Nov 3: 915 -> 945

	[Export(PropertyHint.Range, "500,1000,1")]
	public int NetsuScaleSpecial = 945;   // Nov 3: 915 -> 945

	[Export(PropertyHint.Range, "500,1000,1")]
	public int NetsuScaleEx = 950;   // Nov 3: 915 -> 950

	/// <summary>Netsu (Nov 3, TamaDeez): juggle gravity. A fighter being hit whose hit state asks for the "default" gravity
	/// falls with this instead of 260000 (jumps and other movement keep 260000). Lower = floatier juggles.</summary>
	[Export(PropertyHint.Range, "100000,300000,1000")]
	public int NetsuJuggleGravity = 200000;

	/// <summary>Netsu (Nov 3): every air hit in a combo takes this much off the upward knockback of the hits after it
	/// (was a fixed 2500). Lower = relaunches keep working deeper into a combo.</summary>
	[Export(PropertyHint.Range, "0,5000,100")]
	public int NetsuGravityDecayPerHit = 1200;

	/// <summary>Netsu (Nov 3, TamaDeez): midscreen wall bounces. A wall-bounce hit sends them this far (units) from the
	/// attacker, then they bounce off an invisible wall (a hit can set its own: HitboxElement.NetsuWallBounceDistance;
	/// the real stage walls and the screen edge still count if they're nearer). Was the screen edge (7.5 m).</summary>
	[Export(PropertyHint.Range, "15000,75000,1000")]
	public int NetsuWallBounceDistance = 37000;

	/// <summary>Netsu (Nov 3): after a wall bounce they fly back so they come down this far (units) in front of the
	/// attacker (where she is at the bounce). 0 = the old slow drift back (Bounce_Wall's MaxBackSpeed).</summary>
	[Export(PropertyHint.Range, "0,40000,1000")]
	public int NetsuWallReturnGap = 12000;

	/// <summary>Netsu (Oct 27 c27, TamaDeez): repeat proration. A move already used earlier in this combo gives less untech
	/// time on air hits: this many frames per earlier use (counted up to 3). A normal costs less than a special; EX moves
	/// and supers count as specials; a projectile counts as the move that threw it. Hits of one use of a move
	/// (multi-hits) are one use. Assist hits don't count.</summary>
	[Export(PropertyHint.Range, "0,30,1")]
	public int NetsuRepeatNormalUntech = 4;   // Oct 27 c33: 3 -> 6; Nov 3: 4 (the same move again drains the juggle meter faster)

	[Export(PropertyHint.Range, "0,30,1")]
	public int NetsuRepeatSpecialUntech = 8;   // Oct 27 c33: 7 -> 12; Nov 3: 8 (ground hits now lose half of it too)

	/// <summary>Netsu (Oct 27 c33, TamaDeez): a COUNTER HIT with a special / EX move: this much more hitstun (on top of the
	/// usual counter bonus), the hit ignores the juggle-time decay and the repeat proration, and its knockback (percent) and
	/// wall bounce (percent of the bounce time and strength) are better.</summary>
	[Export(PropertyHint.Range, "0,40,1")]
	public int NetsuSpecialCounterExtraHitstun = 8;

	[Export(PropertyHint.Range, "100,300,5")]
	public int NetsuSpecialCounterKnockbackPercent = 125;

	[Export(PropertyHint.Range, "100,300,5")]
	public int NetsuSpecialCounterBouncePercent = 150;

	/// <summary>Netsu (Oct 26 c15): extra hitstun on hits of specials / EX moves (combo extenders), and how much of the
	/// juggle decay EX moves and supers ignore (percent).</summary>
	[Export(PropertyHint.Range, "0,30,1")]
	public int NetsuSpecialUntechBonus = 3;

	[Export(PropertyHint.Range, "0,30,1")]
	public int NetsuExUntechBonus = 8;

	[Export(PropertyHint.Range, "0,100,1")]
	public int NetsuExDecayIgnorePercent = 50;

	/// <summary>Netsu (Oct 26 evening): Overdrive activation stops the fight this long (frames) while the fighter strikes
	/// her win pose and glows (no inputs). 0 = no pause.</summary>
	[Export(PropertyHint.Range, "0,120,1")]
	public int NetsuOverdrivePauseFrames = 45;

	/// <summary>Netsu (Oct 29): COMBO SCALING. The first hit of a combo always does full damage; each hit then lowers
	/// the damage of the hits after it by its hitbox's DamageScalingSubtract. These three numbers make that harsher
	/// (or softer) for every move at once, without touching a single attack's damage:
	///  - NetsuComboScalingPercent: each hit's scaling loss x this % (100 = as set on the hitbox; 150 = half as much again)
	///  - NetsuComboScalingMinLoss: a hit that scales at all takes off at least this many points (0 = no minimum).
	///    Hitboxes set to 0 still don't scale.
	///  - NetsuComboScalingFloor: the lowest a combo can scale to, in % (was 15). In the corner the floor is 5 higher.
	/// Put all three back to 100 / 0 / 15 for the old scaling.</summary>
	[Export(PropertyHint.Range, "0,400,5")]
	public int NetsuComboScalingPercent = 150;

	[Export(PropertyHint.Range, "0,20,1")]
	public int NetsuComboScalingMinLoss = 3;

	[Export(PropertyHint.Range, "1,100,1")]
	public int NetsuComboScalingFloor = 10;

	/// <summary>Netsu (Oct 29): EX moves and supers scale less in combos. Their hits get back this % of the damage the
	/// combo scaling has taken away (0 = scaled like everything else, 100 = never scaled), and never drop below the
	/// minimum % of their damage. E.g. at 30% combo scaling, ignore 50 / minimum 40 -> 65%. Only these moves' own damage
	/// changes (their projectiles and follow-ups too); how much they scale the hits AFTER them doesn't.</summary>
	[Export(PropertyHint.Range, "0,100,5")]
	public int NetsuExScalingIgnorePercent = 30;

	[Export(PropertyHint.Range, "0,100,5")]
	public int NetsuExScalingMinimum = 30;

	[Export(PropertyHint.Range, "0,100,5")]
	public int NetsuSuperScalingIgnorePercent = 50;

	[Export(PropertyHint.Range, "0,100,5")]
	public int NetsuSuperScalingMinimum = 45;

	/// <summary>Netsu (Oct 29): after an EX move hits an airborne opponent they're held up (can't fall or tech) only
	/// while the EX keeps hitting: if no new EX hit lands within this many frames, they fall and can tech as usual.</summary>
	[Export(PropertyHint.Range, "0,120,1")]
	public int NetsuExHoldGraceFrames = 20;

	/// <summary>Netsu: is an EX / super flash freezing someone right now (inputs are locked: GameLoop)?</summary>
	public bool NetsuFlashFreeze()
	{
		for (int i = 0; Fighters != null && i < Fighters.Length; i++)
		{
			if (Fighters[i] != null && Fighters[i].SuperFlashing)
			{
				return true;
			}
		}
		return false;
	}

	/// <summary>Frames the EX pause lasts (0 = no pause).</summary>
	[Export(PropertyHint.None, "")]
	public int NetsuPauseExFrames = 30;

	/// <summary>Frames the super pause lasts (0 = no pause). Oct 25: a second (was 40 frames), so a super's start
	/// lands harder than an EX move's. A move can set its own: MoveSettings.NetsuPauseFrames.</summary>
	[Export(PropertyHint.None, "")]
	public int NetsuPauseSuperFrames = 60;

	/// <summary>Frames of the pause still to go (0 = the fight is running).</summary>
	public int NetsuPause;

	/// <summary>Who started the pause (0 = player 1, 1 = player 2; -1 = none yet).</summary>
	public int NetsuPauseSide = -1;

	/// <summary>The pause's length when it started.</summary>
	public int NetsuPauseTotal;

	/// <summary>Netsu (Oct 25): the pause going on (or the last one) is a super's (the camera zooms in a little
	/// more: FighterCamera.NetsuZoomFactorSuper). Presentation only: not saved (set again by every pause).</summary>
	public bool NetsuPauseIsSuper;

	/// <summary>Netsu: stops the whole fight for a moment because `side` started a move costing `cost`
	/// (2000 = EX, 6000 = super; Pushblock never gets here, it has no flash). `frames` >= 0: the move's own length (MoveSettings.NetsuPauseFrames).</summary>
	public void NetsuStartPause(int side, int cost, int frames = -1)
	{
		if (frames < 0)
		{
			frames = cost >= StanceManager.NetsuSuperCost ? NetsuPauseSuperFrames : (cost >= StanceManager.NetsuExCost ? NetsuPauseExFrames : 0);
		}
		if (frames <= 0)
		{
			return;
		}
		NetsuPause = frames;
		NetsuPauseTotal = frames;
		NetsuPauseSide = side;
		NetsuPauseIsSuper = cost >= StanceManager.NetsuSuperCost;
	}

	/// <summary>Netsu (Oct 25), for the online lobby (GDScript): [the match is over and its results screen is up,
	/// the winner (0 = player 1, 1 = player 2, -1 = none yet), the engine frame].</summary>
	public Godot.Collections.Array NetsuMatchResult()
	{
		bool over = Monitor != null && Monitor.MatchState == MatchState.RESULTS;
		// Oct 25: one array, updated in place (asked every frame; a new one each time was garbage for the collector)
		_netsuResult ??= new Godot.Collections.Array { false, -1, 0 };
		_netsuResult[0] = over;
		_netsuResult[1] = Monitor != null ? Monitor.Winner : -1;
		_netsuResult[2] = Frame;
		return _netsuResult;
	}

	private Godot.Collections.Array _netsuResult;
	private Godot.Collections.Array _netsuPauseInfo;
	private Godot.Collections.Dictionary _netsuNoTraining;

	/// <summary>Netsu, for the HUD (GDScript): [frames left, who, length]. Presentation only. (One array, updated
	/// in place.)</summary>
	public Godot.Collections.Array NetsuPauseInfo()
	{
		_netsuPauseInfo ??= new Godot.Collections.Array { 0, -1, 0 };
		_netsuPauseInfo[0] = NetsuPause;
		_netsuPauseInfo[1] = NetsuPauseSide;
		_netsuPauseInfo[2] = NetsuPauseTotal;
		return _netsuPauseInfo;
	}

	public override void _Ready()
	{
		Instance = this;
		healthHUD = (HealthHUD)FighterUI.GetNode("GameHUD_Background");
		metersHUD = (MetersHUD)FighterUI.GetNode("GameHUD_Foreground");
		SeedViewer = (Label)FighterUI.GetNode("Seed");
		Control OnlinePlayersInfo = (Control)healthHUD.GetNode("OnlineInfo");
		Control TrainingInfo = (Control)metersHUD.GetNode("TrainingInfo");
		Control InputHistory = (Control)metersHUD.GetNode("InputHistory");
		Control DebugWindow = (Control)FighterUI.GetNode("Debug");
		Control obj = (Control)FighterUI.GetNode("PleaseResync_UI");
		PauseScreen = (PauseMenu)FighterUI.GetNode("PauseMenu");
		if (Monitor != null)
		{
			Monitor.Cards = (MatchCardsController)FighterUI.GetNode("MatchCards");
			Monitor.ResultsScreen = (Control)FighterUI.GetNode("ResultsScreen");
			Monitor.ResultsScreen.Visible = false;
		}
		Curtain = (FadeScreen)FighterUI.GetNode("FadeScreen");
		OnlinePlayersInfo.Visible = Match.SelectedModeSettings.ShowOnlineInfo;
		TrainingInfo.Visible = Match.SelectedModeSettings.ShowTrainingInfo;
		InputHistory.Visible = Match.SelectedModeSettings.AllowShowInputs;
		DebugWindow.Visible = Match.SelectedModeSettings.AllowShowDebugElements;
		obj.Visible = Match.SelectedModeSettings.UseLAN;
		SeedViewer.Visible = Match.SelectedModeSettings.AllowShowDebugElements;
		if (Match.SelectedModeSettings.ShowOnlineInfo && OnlinePlayersInfo != null)
		{
			((OnlineInfo)OnlinePlayersInfo).Set(Match);
		}
	}

	public override void _Process(double delta)
	{
		base._Process(delta);
		if (Fighters == null || Monitor == null)
		{
			return;
		}
		if (SeedViewer.Visible)
		{
			SeedViewer.Text = finalSeed.ToString();
		}
		if (Input.IsActionJustPressed(NetsuPauseAction) && Match.SelectedModeSettings.PauseMode != PauseMode.LOCK && Monitor.MatchState == MatchState.ROUND_RUNNING)
		{
			CallDeferred("PauseControl", !paused);
		}
		// (Oct 25: online, the lobby takes everyone back itself: game/autoloads/online_room.gd)
		if (Monitor.MatchState == MatchState.RESULTS && Match.SelectedModeSettings.ModeName != "Online" && (Input.IsActionJustPressed(NetsuAcceptAction) || Input.IsActionJustPressed(NetsuCancelAction)))
		{
			LoadingScreenManager.Instance.LoadScene(Monitor.sceneToReturn);
		}
	}

	private bool _netsuBlackSeen;

	public void Render()
	{
		// Oct 25: a garbage collection whenever the screen is fully black (the fight's first frame, between rounds),
		// where its pause can't be seen (NetsuGc)
		if (Monitor.FadeScreenIntensity >= 100)
		{
			if (!_netsuBlackSeen)
			{
				_netsuBlackSeen = true;
				NetsuGc.ScreenBlack();
			}
		}
		else
		{
			_netsuBlackSeen = false;
		}
		RenderNodes();
		Camera.UpdateCamera(Fighters[0], Fighters[1]);
		healthHUD.UpdateHealthBars(Fighters, Monitor);
		healthHUD.UpdateHitNotifications(Notifs);
		metersHUD.UpdateMeters(Fighters);
		Curtain.FadeIntensity = Monitor.FadeScreenIntensity;
		Monitor.Render();
	}

	private void RenderNodes()
	{
		foreach (SakugaNode node in Nodes)
		{
			node.Render();
		}
	}

	private void GenerateBaseSeed()
	{
		string seedText = RNG.baseSeed + Fighters[0].Data.Profile.FighterName + Fighters[1].Data.Profile.FighterName;
		byte[] seedArray = Encoding.ASCII.GetBytes(seedText);
		generatedSeed = (int)Platform.GetChecksum(seedArray);
	}

	private int CalculateSeed()
	{
		int posX = Fighters[0].Body.FixedPosition.X + Fighters[1].Body.FixedPosition.X;
		int posY = Fighters[0].Body.FixedPosition.Y + Fighters[1].Body.FixedPosition.Y;
		int stateFrame = Fighters[0].StateManager.CurrentStateFrame + Fighters[0].StateManager.CurrentState;
		stateFrame += Fighters[1].StateManager.CurrentStateFrame + Fighters[1].StateManager.CurrentState;
		return generatedSeed + posX + posY + stateFrame + Frame * 10000 + Monitor.Clock;
	}

	public void Setup()
	{
		if (GetChildren().Count > 0)
		{
			foreach (Node child in GetChildren())
			{
				child.QueueFree();
			}
		}
		Inputs = new InputManager[2];
		Inputs[0] = new InputManager();
		Inputs[1] = new InputManager();
		Frame = 0;
		NetsuPause = 0;
		NetsuPauseSide = -1;
		NetsuPauseTotal = 0;
		if (Training == null && Match.SelectedModeSettings.ModeName == "Training")
		{
			Training = new NetsuTraining();   // Netsu: the Training Menu's dummy / gauge settings
			if (_netsuTrainingOptions != null)
			{
				Training.Apply(_netsuTrainingOptions);
			}
		}
		CreateStage(Match.SelectedStage);
		World = new PhysicsWorld();
		Nodes.Clear();
		Fighters = new SakugaActor[2];
		CreateFighter(Match.P1SelectedCharacter, 0);
		CreateFighter(Match.P2SelectedCharacter, 1);
		Fighters[0].SetAllies(new SakugaActor[1] { Fighters[0] });
		Fighters[1].SetAllies(new SakugaActor[1] { Fighters[1] });
		Fighters[0].SetOpponents(new SakugaActor[1] { Fighters[1] });
		Fighters[1].SetOpponents(new SakugaActor[1] { Fighters[0] });
		GenerateBaseSeed();
		Monitor.Initialize(Fighters, Match);
		Notifs = new HitNotifications[2]
		{
			new HitNotifications(5),
			new HitNotifications(5)
		};
		healthHUD.Setup(Fighters);
		metersHUD.Setup(Fighters);
		AudioManager.Instance.PlayBGM(songsList.elements[Match.SelectedBGM].clip);
	}

	public void CreateFighter(int characterIndex, int playerIndex)
	{
		bool AIcontrolled = false;
		int selectedColor = 0;
		switch (playerIndex)
		{
		case 0:
			AIcontrolled = !Match.SelectedModeSettings.NoAI && Match.P1SelectedDevice == -1;
			selectedColor = Match.P1SelectedColor;
			break;
		case 1:
			AIcontrolled = !Match.SelectedModeSettings.NoAI && Match.P2SelectedDevice == -1;
			selectedColor = Match.P2SelectedColor;
			if (characterIndex == Match.P1SelectedCharacter && Match.P1SelectedColor == Match.P2SelectedColor)
			{
				selectedColor++;
			}
			if (selectedColor >= fightersList.elements[characterIndex].ColorPalettes.Length)
			{
				selectedColor = 0;
			}
			break;
		}
		// Netsu: GetScene() loads only this fighter's scene (the roster no longer loads every fighter)
		Node temp = fightersList.elements[characterIndex].ColorPalettes[selectedColor].GetScene().Instantiate(PackedScene.GenEditState.Disabled);
		Fighters[playerIndex] = temp as SakugaActor;
		// Netsu (Oct 25): this fighter's frame data spreadsheet (data/frame_data), before anything reads the data
		NetsuFrameData.ApplyFighter(Fighters[playerIndex].Data);
		AddActor(Fighters[playerIndex]);
		Fighters[playerIndex].playerID = (uint)playerIndex;
		Fighters[playerIndex].Inputs = Inputs[playerIndex];
		Fighters[playerIndex].Initialize();
		Fighters[playerIndex].InitializeBrain(AIcontrolled, Match.Difficulty);
		// Netsu: the assist this player picked (Mary, Adin, Eren...), called with S
		Fighters[playerIndex].NetsuAssist = NetsuAssist.Create(Fighters[playerIndex], playerIndex == 0 ? Match.P1SelectedAssist : Match.P2SelectedAssist);
	}

	/// <summary>Netsu (Oct 25): Training - a frame data spreadsheet (data/frame_data) was saved again since the fight
	/// started: put it into both fighters and their assists now. Returns what changed ("" = nothing was saved).
	/// netsu_training_hud.gd asks twice a second and shows the answer.</summary>
	public string NetsuReloadFrameData()
	{
		if (Fighters == null || !NetsuFrameData.Changed())
		{
			return "";
		}
		NetsuFrameData.TakeReport();
		foreach (SakugaActor f in Fighters)
		{
			if (f == null)
			{
				continue;
			}
			NetsuFrameData.ApplyFighter(f.Data);
			if (f.NetsuAssist?.Element != null && f.NetsuAssist.Actor != null)
			{
				NetsuFrameData.ApplyAssist(f.NetsuAssist.Element, f.NetsuAssist.Actor.Data);
			}
		}
		string report = NetsuFrameData.TakeReport();
		return report != "" ? report : "Frame data reloaded: no changes from the game's own values.";
	}

	/// <summary>Netsu (Oct 25): how high the camera may go on the stage being played (StageElement.NetsuCameraTop), in
	/// engine units (10000 = 1 m; the engine's 25 m if the stage sets none). Moves that fly into the sky stop under it
	/// (NetsuSkyRiseAction). The same on every copy of the match (the stage is part of the match settings).</summary>
	public int NetsuStageTopUnits()
	{
		int index = Match != null ? Match.SelectedStage : -1;
		if (stagesList?.elements == null || index < 0 || index >= stagesList.elements.Length || stagesList.elements[index] == null)
		{
			return GlobalVariables.CeilingLimit;
		}
		float top = stagesList.elements[index].NetsuCameraTop;
		return top > 0f ? Mathf.Min(GlobalVariables.CeilingLimit, Mathf.RoundToInt(top * GlobalVariables.SimulationScale)) : GlobalVariables.CeilingLimit;
	}

	/// <summary>Netsu (Oct 28): the fighters can't get further apart than GlobalVariables.NetsuMaxSeparation (the screen
	/// edge). The one moving away is stopped; if both (or neither) are, each gives half. Deterministic (state only).</summary>
	private void NetsuLeash()
	{
		int max = GlobalVariables.NetsuMaxSeparation;
		if (max <= 0 || Fighters == null || Fighters[0] == null || Fighters[1] == null)
		{
			return;
		}
		PhysicsBody a = Fighters[0].Body;
		PhysicsBody b = Fighters[1].Body;
		int dx = b.FixedPosition.X - a.FixedPosition.X;
		int sep = Math.Abs(dx);
		if (sep <= max)
		{
			return;
		}
		int excess = sep - max;
		int dir = dx > 0 ? 1 : -1;   // b is on the +dir side of a
		bool aAway = a.FixedVelocity.X * dir < 0;
		bool bAway = b.FixedVelocity.X * dir > 0;
		int moveA;
		int moveB;
		if (aAway && !bAway) { moveA = excess; moveB = 0; }
		else if (bAway && !aAway) { moveA = 0; moveB = excess; }
		else { moveA = excess / 2; moveB = excess - moveA; }
		a.FixedPosition.X += dir * moveA;
		b.FixedPosition.X -= dir * moveB;
		if (moveA > 0 && aAway) { a.FixedVelocity.X = 0; }
		if (moveB > 0 && bAway) { b.FixedVelocity.X = 0; }
		a.UpdateColliders();
		b.UpdateColliders();
	}

	private Node3D _netsuStage;

	private void NetsuApplyStageScale()
	{
		if (_netsuStage != null && IsInstanceValid(_netsuStage))
		{
			float k = GlobalVariables.NetsuStageScaleNow;
			_netsuStage.Scale = new Vector3(k, k, k);
		}
	}

	public void CreateStage(int stageIndex)
	{
		// Netsu: GetScene() loads only the stage being played (the list no longer loads every stage)
		Node temp = stagesList.elements[stageIndex].GetScene().Instantiate(PackedScene.GenEditState.Disabled);
		AddChild(temp, forceReadableName: false, InternalMode.Disabled);
		_netsuStage = temp as Node3D;   // Oct 28: drawn a little smaller in the bigger view (F8 switches)
		NetsuApplyStageScale();
		Camera?.NetsuSetStageTop(stagesList.elements[stageIndex].NetsuCameraTop);   // Netsu: how high the camera may go here
	}

	public void AddActor(SakugaNode newNode, bool isPhysicsBody = true)
	{
		AddChild(newNode, forceReadableName: false, InternalMode.Disabled);
		Nodes.Add(newNode);
		if (isPhysicsBody)
		{
			World.AddBody((newNode as SakugaActor).Body);
		}
	}

	public void GameLoop(byte[] playerInput)
	{
		if (paused)
		{
			return;
		}
		if (NetsuPause > 0)
		{
			// Netsu: the EX / super pause: only the frame counter goes on (no inputs, no clock, nothing moves)
			NetsuPause--;
			for (int f = 0; f < Fighters.Length; f++)
			{
				Fighters[f].Parameters?.NetsuResourceTick();   // Oct 29: meter cooldown and Burst recharge keep going in the flash
			}
			Frame++;
			return;
		}
		finalSeed = CalculateSeed();
		RNG.Set(finalSeed);
		Frame++;
		Monitor.Tick();
		randomTest = new Vector3I(RNG.Next(), RNG.Next(), RNG.Next());
		HitNotifications[] notifs = Notifs;
		for (int i = 0; i < notifs.Length; i++)
		{
			notifs[i].Tick();
		}
		// Netsu: both players' inputs for this frame. In Training the dummy's comes from NetsuTraining
		// (stance, recoveries, wake-up action, playback), and player 1 drives the dummy while recording.
		for (int j = 0; j < Fighters.Length && j < _netsuInputs.Length; j++)
		{
			PlayerInputs combinedInput = PlayerInputs.NEUTRAL;
			combinedInput = (PlayerInputs)((uint)combinedInput | (uint)playerInput[j * InputSize]);
			combinedInput = (PlayerInputs)((uint)combinedInput | (uint)(ushort)(playerInput[j * InputSize + 1] << 8));
			_netsuInputs[j] = combinedInput;
		}
		if (Training != null && Monitor.MatchState == MatchState.ROUND_RUNNING)
		{
			Training.PreFrame(this, Fighters, _netsuInputs, Match.P2SelectedDevice >= 0);
		}
		// taken after PreFrame: a training reset may have just moved both fighters
		int center = (Fighters[0].Body.FixedPosition.X + Fighters[1].Body.FixedPosition.X) / 2;
		bool netsuFrozen = NetsuFlashFreeze();
		for (int j = 0; j < Fighters.Length; j++)
		{
			if (Monitor.MatchState == MatchState.ROUND_START || Monitor.MatchState == MatchState.ROUND_END)
			{
				Inputs[j].InsertToHistory(PlayerInputs.NEUTRAL);
				continue;
			}
			if (netsuFrozen)
			{
				// Netsu (Oct 26, TamaDeez): during an EX / super flash freeze nobody can input anything (pause still
				// works: it's read outside the match loop). Each side's last input is held, so a held direction or
				// button stays held, but nothing new is pressed and no motion can be done during the freeze.
				// (Before this, an EX could be turned into a super before it even came out.)
				Inputs[j].InsertToHistory(Inputs[j].CurrentInput().rawInput);
				continue;
			}
			if (Fighters[j].UseAI)
			{
				Fighters[j].Brain.SelectCommand();
				Fighters[j].Brain.UpdateCommand();
				continue;
			}
			Inputs[j].InsertToHistory(_netsuInputs[j]);
		}
		for (int k = 0; k < Nodes.Count; k++)
		{
			Nodes[k].PreTick();
		}
		for (int l = 0; l < Nodes.Count; l++)
		{
			Nodes[l].Tick();
		}
		World.Simulate();
		NetsuLeash();
		if (Fighters[0].Body.FixedPosition.X < Fighters[1].Body.FixedPosition.X)
		{
			Fighters[0].Body.UpdateSide(leftSide: true);
			Fighters[1].Body.UpdateSide(leftSide: false);
		}
		else if (Fighters[0].Body.FixedPosition.X > Fighters[1].Body.FixedPosition.X)
		{
			Fighters[0].Body.UpdateSide(leftSide: false);
			Fighters[1].Body.UpdateSide(leftSide: true);
		}
		for (int m = 0; m < Fighters.Length; m++)
		{
			Fighters[m].Body.FixedPosition.X = Mathf.Clamp(Fighters[m].Body.FixedPosition.X, center - 50000, center + 50000);
			Fighters[m].Body.UpdateColliders();
			if (!Match.SelectedModeSettings.CanKO && Training == null)   // Training: NetsuTraining.PostFrame
			{
				if (Fighters[m].Parameters.Health.CurrentValue < 0)
				{
					Fighters[m].Parameters.Health.CurrentValue = 0;
				}
				if (!Fighters[m].OnHitstun() && Fighters[m].StateManager.CurrentStateType() != StateType.HIT_REACTION)
				{
					Fighters[m].Parameters.Health.CurrentValue = Fighters[m].Data.MaxHealth;
				}
			}
			if (Match.SelectedModeSettings.AutoFillResources && Training == null && Fighters[m].StateManager.CurrentStateType() <= StateType.MOVEMENT)
			{
				Fighters[m].Parameters.SuperGauge.CurrentValue = Fighters[m].Data.MaxSuperGauge;
				if (Fighters[m].Parameters.Will.State != WillState.LOCKED)   // Netsu: keep a running Overdrive
				{
					Fighters[m].Parameters.Will.CurrentValue = Fighters[m].Data.MaxWill;
					Fighters[m].Parameters.Will.State = WillState.WORKING;
				}
			}
		}
		if (Training != null && Monitor.MatchState == MatchState.ROUND_RUNNING)
		{
			Training.PostFrame(Fighters);   // health and gauges as the Training Menu says
		}
		for (int n = 0; n < Nodes.Count; n++)
		{
			Nodes[n].LateTick();
		}
	}

	// --- Netsu: Training mode (called from GDScript: game/ui/training/) ---------------------

	/// <summary>The Training Menu's settings (GameSettings "training" keys). Kept, so settings sent
	/// before the fight is set up still apply.</summary>
	public void NetsuSetTraining(Godot.Collections.Dictionary options)
	{
		_netsuTrainingOptions = options;
		Training?.Apply(options);
	}

	/// <summary>Training shortcuts and Training Menu actions: "reset" (value = NetsuTraining.Reset* mode),
	/// "record" / "play" (start or stop), "record_start" / "play_start" (always start), "stop", "clear"
	/// (forget the recording). See NetsuTraining.Command.</summary>
	public void NetsuTrainingCommand(string name, int value)
	{
		Training?.Command(name, value);
	}

	/// <summary>{"recording", "playing", "frames", "index", "max", "cpu"} for the training HUD.</summary>
	public Godot.Collections.Dictionary NetsuTrainingStatus()
	{
		return Training != null ? Training.Status() : (_netsuNoTraining ??= new Godot.Collections.Dictionary());
	}

	public bool NetsuIsTraining()
	{
		return Training != null;
	}

	/// <summary>Training Menu: show / hide the hitboxes (F10 still toggles them too).</summary>
	public void NetsuShowHitboxes(bool show)
	{
		if (Match.SelectedModeSettings.AllowShowHitboxes)
		{
			ShowHitboxes = show;
		}
	}

	public override void _UnhandledInput(InputEvent @event)
	{
		if (!(@event is InputEventKey eventKey))
		{
			return;
		}
		if (eventKey.Pressed && eventKey.Keycode == Key.F10 && Match.SelectedModeSettings.AllowShowHitboxes)
		{
			ShowHitboxes = !ShowHitboxes;
		}
		if (eventKey.Pressed && !eventKey.Echo && eventKey.Keycode == Key.F8)
		{
			// Netsu (Oct 28): big fighters / old view (presentation only)
			GlobalVariables.NetsuBigView = !GlobalVariables.NetsuBigView;
			NetsuApplyStageScale();
		}
		if (!Match.SelectedModeSettings.AllowUseDebugCommands)
		{
			return;
		}
		if (eventKey.Pressed && eventKey.Keycode == Key.F1)
		{
			if (eventKey.ShiftPressed)
			{
				Fighters[0].Parameters.Health.SetHealth(0);
			}
			else
			{
				Fighters[0].Parameters.Health.RemoveHealth(100);
			}
		}
		if (eventKey.Pressed && eventKey.Keycode == Key.F2)
		{
			if (eventKey.ShiftPressed)
			{
				Fighters[1].Parameters.Health.SetHealth(0);
			}
			else
			{
				Fighters[1].Parameters.Health.RemoveHealth(100);
			}
		}
		if (eventKey.Pressed && eventKey.Keycode == Key.F3)
		{
			if (eventKey.ShiftPressed)
			{
				Fighters[0].Parameters.Health.SetHealth(Fighters[0].Data.MaxHealth);
			}
			else
			{
				Fighters[0].Parameters.Health.AddHealth(100);
			}
		}
		if (eventKey.Pressed && eventKey.Keycode == Key.F4)
		{
			if (eventKey.ShiftPressed)
			{
				Fighters[1].Parameters.Health.SetHealth(Fighters[1].Data.MaxHealth);
			}
			else
			{
				Fighters[1].Parameters.Health.AddHealth(100);
			}
		}
		if (eventKey.Pressed && eventKey.Keycode == Key.F5)
		{
			Fighters[0].Parameters.SuperGauge.SetSuperGauge(Fighters[0].Data.MaxSuperGauge);
			Fighters[0].Parameters.Will.SetWillGauge(Fighters[0].Data.MaxWill);
		}
		if (eventKey.Pressed && eventKey.Keycode == Key.F6)
		{
			Fighters[1].Parameters.SuperGauge.SetSuperGauge(Fighters[1].Data.MaxSuperGauge);
			Fighters[1].Parameters.Will.SetWillGauge(Fighters[1].Data.MaxWill);
		}
		if (eventKey.Pressed && eventKey.Keycode == Key.F7)
		{
			if (eventKey.ShiftPressed)
			{
				Monitor.ResetTimer();
			}
			else
			{
				Monitor.Clock = 0;
			}
		}
		if (eventKey.Pressed && eventKey.Keycode == Key.F11)
		{
			Fighters[0].Reset();
			Fighters[1].Reset();
		}
	}

	// NetsuVS: buttons still held when the pause menu closes (the A on "Close", the B
	// that backs out, Start) must not reach the fight. Each player's attack buttons are
	// ignored until they let go of all of them once.
	private readonly System.Collections.Generic.HashSet<string> holdAfterPause = new System.Collections.Generic.HashSet<string>();

	public void PauseControl(bool pause)
	{
		if (Match.SelectedModeSettings.PauseMode != PauseMode.LOCK && Monitor.MatchState == MatchState.ROUND_RUNNING)
		{
			if (paused && !pause)
			{
				holdAfterPause.Add(GlobalFunctions.GetPlayerPrefix(0));
				holdAfterPause.Add(GlobalFunctions.GetPlayerPrefix(1));
			}
			paused = pause;
			PauseScreen.CallPauseMenu(paused);
		}
	}

	public void PlayHitNotificationByIndex(int playerIndex, int notifIndex)
	{
		HitNotificationElement hitNotif = notifications.Elements[notifIndex];
		PlayHitNotification(playerIndex, hitNotif.NotificationName, hitNotif.AnnouncerVoiceLine);
	}

	public void PlayHitNotification(int playerIndex, string name, int announcerLine)
	{
		Notifs[playerIndex].Notify(name);
		AudioManager.Instance.PlayAnnouncerClip(announcerLine);
	}

	public bool WaitingForFirstStrike()
	{
		if (Monitor.CurrentRound == 0 && Match.SelectedModeSettings.CanKO && Fighters[0].Parameters.Health.CurrentValue == Fighters[0].Data.MaxHealth)
		{
			return Fighters[1].Parameters.Health.CurrentValue == Fighters[1].Data.MaxHealth;
		}
		return false;
	}

	// Oct 25: the action names as StringNames made once per player ("p1_up"...): building them from strings
	// every frame (13 per player) was garbage for the collector, whose pauses were hitches in the fight.
	private static readonly System.Collections.Generic.Dictionary<string, StringName[]> _netsuActionNames = new();
	private static readonly string[] NetsuActionSuffixes = { "_up", "_down", "_left", "_right", "_a", "_b", "_c", "_s", "_ab", "_bc", "_abc", "_start" };
	private static readonly StringName NetsuPauseAction = new StringName("pause");
	private static readonly StringName NetsuAcceptAction = new StringName("ui_accept");
	private static readonly StringName NetsuCancelAction = new StringName("ui_cancel");

	private static StringName[] NetsuActions(string prefix)
	{
		lock (_netsuActionNames)
		{
			if (!_netsuActionNames.TryGetValue(prefix, out StringName[] names))
			{
				names = new StringName[NetsuActionSuffixes.Length];
				for (int i = 0; i < names.Length; i++)
				{
					names[i] = new StringName(prefix + NetsuActionSuffixes[i]);
				}
				_netsuActionNames[prefix] = names;
			}
			return names;
		}
	}

	public byte[] ReadInputs(int id, int inputSize)
	{
		if (id < 0)
		{
			return new byte[inputSize];
		}
		PlayerInputs input = PlayerInputs.NEUTRAL;
		string prefix = GlobalFunctions.GetPlayerPrefix(id);
		StringName[] act = NetsuActions(prefix);
		bool up = Input.IsActionPressed(act[0]);
		bool down = Input.IsActionPressed(act[1]);
		bool left = Input.IsActionPressed(act[2]);
		bool right = Input.IsActionPressed(act[3]);
		// Netsu (Oct 24 night) SOCD cleaning for leverless / keyboard: up + down = up (jump wins, the usual
		// tournament rule), left + right = neutral. Applied here, before the input is sent online.
		if (up)
		{
			input |= PlayerInputs.UP;
		}
		if (!up && down)
		{
			input |= PlayerInputs.DOWN;
		}
		if (left && !right)
		{
			input |= PlayerInputs.LEFT;
		}
		if (!left && right)
		{
			input |= PlayerInputs.RIGHT;
		}
		// NetsuVS buttons (set up in game/autoloads/controls.gd):
		//   A / B / C -> FACE_A / FACE_B / FACE_C
		//   S (support) -> FACE_D   (Mahou used FACE_D as its dash button)
		//   AB / BC / ABC macros press several buttons at once.
		if (Input.IsActionPressed(act[4]))
		{
			input |= PlayerInputs.FACE_A;
		}
		if (Input.IsActionPressed(act[5]))
		{
			input |= PlayerInputs.FACE_B;
		}
		if (Input.IsActionPressed(act[6]))
		{
			input |= PlayerInputs.FACE_C;
		}
		if (Input.IsActionPressed(act[7]))
		{
			input |= PlayerInputs.FACE_D;
		}
		if (Input.IsActionPressed(act[8]))
		{
			input |= PlayerInputs.FACE_A | PlayerInputs.FACE_B;
		}
		if (Input.IsActionPressed(act[9]))
		{
			input |= PlayerInputs.FACE_B | PlayerInputs.FACE_C;
		}
		if (Input.IsActionPressed(act[10]))
		{
			input |= PlayerInputs.FACE_A | PlayerInputs.FACE_B | PlayerInputs.FACE_C;
		}
		if (holdAfterPause.Contains(prefix))
		{
			PlayerInputs buttons = PlayerInputs.FACE_A | PlayerInputs.FACE_B | PlayerInputs.FACE_C | PlayerInputs.FACE_D;
			if ((input & buttons) == 0 && !Input.IsActionPressed(act[11]))
				holdAfterPause.Remove(prefix);   // everything released: buttons work again
			else
				input &= ~buttons;               // still held from the menu: ignore it
		}
		return BitConverter.GetBytes((ushort)input);
	}

	public byte[] SaveState()
	{
		State.GetStateData(ref Instance);
		return MessagePackSerializer.Serialize(State);
	}

	public void LoadState(byte[] stateBuffer)
	{
		State = MessagePackSerializer.Deserialize<GameManagerState>(stateBuffer);
		State.SetStateData(ref Instance);
	}

	public byte[] GetLocalInput(int PlayerID, int InputSize)
	{
		int playerInputDevice = 0;
		switch (PlayerID)
		{
		case 0:
			playerInputDevice = Match.P1SelectedDevice;
			break;
		case 1:
			playerInputDevice = Match.P2SelectedDevice;
			break;
		}
		return ReadInputs(playerInputDevice, InputSize);
	}
}
