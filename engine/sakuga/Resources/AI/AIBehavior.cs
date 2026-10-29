using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class AIBehavior : Resource
{
	[ExportCategory("Blackboard")]
	[Export(PropertyHint.None, "")]
	public Vector2I DecisionRateFree;

	[Export(PropertyHint.None, "")]
	public Vector2I DecisionRateBusy;

	[Export(PropertyHint.None, "")]
	public Vector2I InputRandomness;

	[Export(PropertyHint.None, "")]
	public int BlockingRate;

	[Export(PropertyHint.None, "")]
	public int TechingRate;

	[Export(PropertyHint.None, "")]
	public int PredictionQuality;

	[Export(PropertyHint.None, "")]
	public int LowHealth = 4000;

	/// <summary>0-10: chance to keep a combo going after each hit/block
	/// (low = drops combos like a beginner, 10 = never drops).</summary>
	[Export(PropertyHint.None, "")]
	public int ComboSkill = 10;

	/// <summary>0-10: chance to STOP a combo when it was blocked instead of
	/// throwing out the risky rest of it (hit-confirming).</summary>
	[Export(PropertyHint.None, "")]
	public int BlockConfirm;

	/// <summary>0-10: chance to pick the RIGHT guard (stand vs crouch) when it
	/// decides to block.</summary>
	[Export(PropertyHint.None, "")]
	public int BlockAccuracy = 10;

	// --- Netsu (Oct 24 2026, night): the CPU's reactions (AIBrain) ---------------------------------------
	/// <summary>Frames an opponent's move must have been showing before the CPU reacts to it (guards it on
	/// sight, anti-airs, punishes). A real player is around 12-20; lower = sharper.</summary>
	[Export(PropertyHint.None, "")]
	public int ReactionTime = 14;

	/// <summary>Frames it keeps guarding after the last attack it saw coming / its last blockstun (so a
	/// string doesn't open it up between hits).</summary>
	[Export(PropertyHint.None, "")]
	public int GuardHold = 8;

	/// <summary>0-10: chance, at each decision with the opponent close (1.8 m) and able to attack, that it
	/// crouch-guards until the next decision instead of picking a plan (players hold guard in range: they
	/// don't wait to see the attack).</summary>
	[Export(PropertyHint.None, "")]
	public int GuardHabit;

	/// <summary>0-10: how keen it is on calling its assist (5 = 10% a try in neutral, 50% in a combo).</summary>
	[Export(PropertyHint.None, "")]
	public int AssistRate = 5;

	/// <summary>0-10: chance to do WakeupReversal (an invincible move, an action list) as it gets up
	/// with the opponent close.</summary>
	[Export(PropertyHint.None, "")]
	public int WakeupRate;

	[Export(PropertyHint.None, "")]
	public int[] WakeupReversal;

	/// <summary>Meter (super gauge) WakeupReversal needs (0 = free).</summary>
	[Export(PropertyHint.None, "")]
	public int WakeupGauge;

	[ExportCategory("Behavior Tree")]
	[Export(PropertyHint.None, "")]
	public AIActionPack NearActions;

	[Export(PropertyHint.None, "")]
	public AIActionPack MidActions;

	[Export(PropertyHint.None, "")]
	public AIActionPack FarActions;

	[Export(PropertyHint.None, "")]
	public AIActionPack DistantActions;
}
