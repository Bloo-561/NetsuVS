using Godot;

namespace SakugaEngine.Resources;

[GlobalClass]
public partial class DataContainer : Resource
{
	[Export(PropertyHint.None, "")]
	public FighterProfile Profile;

	[Export(PropertyHint.None, "")]
	public FighterState[] States;

	[Export(PropertyHint.None, "")]
	public FighterStance[] Stances;

	[Export(PropertyHint.None, "")]
	public int MaxHealth = 10000;

	[Export(PropertyHint.None, "")]
	public int MaxSuperGauge = 10000;

	[Export(PropertyHint.None, "")]
	public int SuperGaugeChargeRate = 4;

	[Export(PropertyHint.None, "")]
	public int MaxWill = 10000;

	[Export(PropertyHint.None, "")]
	public ushort BaseAttack = 100;

	[Export(PropertyHint.None, "")]
	public ushort BaseDefense = 100;

	[Export(PropertyHint.None, "")]
	public AIData _aiData;

	[Export(PropertyHint.None, "")]
	public FighterIntro[] Intros;

	[Export(PropertyHint.None, "")]
	public FighterOutro[] Outros;

	[Export(PropertyHint.None, "")]
	public FighterIntro[] VictoryPoses;

	[Export(PropertyHint.None, "")]
	public int DefeatPose;

	/// <summary>Netsu (Oct 26 2026, TamaDeez): how big this fighter is drawn, per mille (1000 = as drawn). Her sprites and
	/// her attack / throw boxes are scaled by it around her feet (SakugaActor.Render, PhysicsBody.NetsuBox); her
	/// hurtboxes keep the universal height. Leticia: 940 (a little taller than Flan).</summary>
	[Export(PropertyHint.None, "")]
	public int NetsuScale = 1000;
}
