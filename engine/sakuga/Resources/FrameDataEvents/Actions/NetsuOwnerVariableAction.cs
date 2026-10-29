using Godot;

namespace SakugaEngine.Resources;

/// <summary>
/// Netsu (Oct 25 2026, night): sets a custom variable of the FIGHTER who owns this spawned object (its root), not the
/// object's own. With <see cref="OnlyIfLastOfPool"/> (a spawnables pool index, -1 = always) it only does so when no other
/// object of that owner pool is still active in one of <see cref="WaitingStates"/>.
/// Noah's black holes: a hole that bursts on contact clears his HoleTimer (so 623 summons a new hole instead of a snap
/// with nothing to snap), unless his other hole is still waiting.
/// Deterministic: only the owner's own data.
/// </summary>
[GlobalClass]
public partial class NetsuOwnerVariableAction : FrameDataAction
{
	[Export(PropertyHint.None, "")]
	public int ByIndex;

	[Export(PropertyHint.None, "")]
	public int Value;

	[Export(PropertyHint.None, "")]
	public int OnlyIfLastOfPool = -1;

	[Export(PropertyHint.None, "")]
	public int[] WaitingStates = new int[0];

	public override void Execute(ref SakugaActor Actor)
	{
		SakugaActor owner = Actor.NetsuRoot();
		if (owner == null || owner == Actor || owner.Parameters == null)
		{
			return;
		}
		if (OnlyIfLastOfPool >= 0 && owner.Pool != null && OnlyIfLastOfPool < owner.Pool.SpawnCount)
		{
			PoolReference reference = owner.Pool.GetSpawnReference(OnlyIfLastOfPool);
			if (reference.Objects != null)
			{
				foreach (SakugaActor other in reference.Objects)
				{
					if (other == null || other == Actor || !other.IsActive || other.StateManager == null)
					{
						continue;
					}
					if (WaitingStates == null)
					{
						continue;
					}
					foreach (int s in WaitingStates)
					{
						if (other.StateManager.CurrentState == s)
						{
							return;
						}
					}
				}
			}
		}
		CustomVariable variable = owner.Parameters.GetVariable(ByIndex);
		variable?.Set(Value);
	}
}
