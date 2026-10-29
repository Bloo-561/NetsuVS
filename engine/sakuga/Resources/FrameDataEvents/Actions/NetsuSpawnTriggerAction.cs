using Godot;

namespace SakugaEngine.Resources;

/// <summary>
/// Netsu (Oct 25 2026, Noah): sets off this fighter's spawned objects that are waiting. Every active object of the
/// spawnables pool <see cref="Index"/> whose current state is FromStates[i] plays ToStates[i] (from its first frame).
/// Noah's finger snap (623 again) turns his black holes' idle state into their suction state this way.
/// Deterministic: only the pool's own objects, in pool order.
/// </summary>
[GlobalClass]
public partial class NetsuSpawnTriggerAction : FrameDataAction
{
	/// <summary>Which spawnables pool (SpawnablesList order).</summary>
	[Export(PropertyHint.None, "")]
	public int Index;

	/// <summary>Waiting states (object state indices)...</summary>
	[Export(PropertyHint.None, "")]
	public int[] FromStates = new int[0];

	/// <summary>... and the state each one goes to (same position in the list).</summary>
	[Export(PropertyHint.None, "")]
	public int[] ToStates = new int[0];

	public override void Execute(ref SakugaActor Actor)
	{
		if (Actor.Pool == null || Index < 0 || Index >= Actor.Pool.SpawnCount || FromStates == null || ToStates == null)
		{
			return;
		}
		PoolReference reference = Actor.Pool.GetSpawnReference(Index);
		if (reference.Objects == null)
		{
			return;
		}
		foreach (SakugaActor spawn in reference.Objects)
		{
			if (spawn == null || !spawn.IsActive || spawn.StateManager == null)
			{
				continue;
			}
			int current = spawn.StateManager.CurrentState;
			for (int i = 0; i < FromStates.Length && i < ToStates.Length; i++)
			{
				if (FromStates[i] == current)
				{
					spawn.StateManager.PlayState(ToStates[i], reset: true);
					spawn.StateManager.CurrentStateFrame = -1;
					break;
				}
			}
		}
	}
}
