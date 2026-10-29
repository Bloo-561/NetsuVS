using System.Collections.Generic;
using Godot;
using SakugaEngine.Game;
using SakugaEngine.Resources;

namespace SakugaEngine;

[GlobalClass]
public partial class ObjectPool : Node
{
	private List<PoolReference> SpawnReferences = new List<PoolReference>();

	private List<VFXPoolReference> VFXReferences = new List<VFXPoolReference>();

	/// <summary>Netsu: how many hit effects this pool has (assists borrow their fighter's).</summary>
	public int VFXCount => VFXReferences.Count;

	/// <summary>Netsu: how many kinds of spawnable this pool has.</summary>
	public int SpawnCount => SpawnReferences.Count;

	public void Initialize(SakugaActor owner)
	{
		CreateSpawnablePool(owner);
		CreateVFXPool(owner);
	}

	private void CreateSpawnablePool(SakugaActor owner)
	{
		if (owner.SpawnablesList == null)
		{
			return;
		}
		SpawnsList SpawnsPool = owner.SpawnablesList;
		for (int i = 0; i < SpawnsPool.SpawnObjects.Length; i++)
		{
			SpawnReferences.Add(new PoolReference
			{
				Key = SpawnsPool.SpawnObjects[i].Key,
				Objects = new SakugaActor[SpawnsPool.SpawnObjects[i].PoolSize]
			});
			for (int j = 0; j < SpawnReferences[i].Objects.Length; j++)
			{
				Node node = SpawnsPool.SpawnObjects[i].Instance.Instantiate(PackedScene.GenEditState.Disabled);
				node.Name = owner.playerID + "_" + SpawnsPool.SpawnObjects[i].Key + "_" + j;
				SpawnReferences[i].Objects[j] = node as SakugaActor;
				SpawnReferences[i].Objects[j].Inputs = owner.Inputs;
				SpawnReferences[i].Objects[j].playerID = owner.playerID;
				SpawnReferences[i].Objects[j].Initialize();
				SpawnReferences[i].Objects[j].SetMaster(owner);
				SpawnReferences[i].Objects[j].SetAllies(owner.GetAllies());
				SpawnReferences[i].Objects[j].SetOpponents(owner.GetOpponents());
				GameManager.Instance.AddActor(SpawnReferences[i].Objects[j]);
			}
		}
	}

	private void CreateVFXPool(SakugaActor owner)
	{
		if (owner.VFXList == null)
		{
			return;
		}
		SpawnsList vfxPool = owner.VFXList;
		for (int i = 0; i < vfxPool.SpawnObjects.Length; i++)
		{
			VFXReferences.Add(new VFXPoolReference
			{
				Key = vfxPool.SpawnObjects[i].Key,
				Objects = new SakugaVFX[vfxPool.SpawnObjects[i].PoolSize]
			});
			for (int j = 0; j < VFXReferences[i].Objects.Length; j++)
			{
				Node node = vfxPool.SpawnObjects[i].Instance.Instantiate(PackedScene.GenEditState.Disabled);
				node.Name = owner.playerID + "_" + vfxPool.SpawnObjects[i].Key + "_" + j;
				VFXReferences[i].Objects[j] = node as SakugaVFX;
				VFXReferences[i].Objects[j].Initialize();
				VFXReferences[i].Objects[j].SetMaster(owner);
				GameManager.Instance.AddActor(VFXReferences[i].Objects[j], isPhysicsBody: false);
			}
		}
	}

	public void Reset()
	{
		foreach (PoolReference spawnReference in SpawnReferences)
		{
			SakugaActor[] objects = spawnReference.Objects;
			for (int i = 0; i < objects.Length; i++)
			{
				objects[i].Reset();
			}
		}
		foreach (VFXPoolReference vFXReference in VFXReferences)
		{
			SakugaVFX[] objects2 = vFXReference.Objects;
			for (int i = 0; i < objects2.Length; i++)
			{
				objects2[i].Reset();
			}
		}
	}

	public void SpawnObject(string key, int initialState, Vector2I position)
	{
		if (SpawnReferences.Count != 0)
		{
			PoolReference spawnElement = GetSpawnReference(key);
			SpawnObjectCommon(spawnElement, initialState, position);
		}
	}

	public void SpawnObject(int index, int initialState, Vector2I position)
	{
		if (SpawnReferences.Count != 0)
		{
			PoolReference spawnElement = GetSpawnReference(index);
			SpawnObjectCommon(spawnElement, initialState, position);
		}
	}

	private void SpawnObjectCommon(PoolReference reference, int initialState, Vector2I position)
	{
		SakugaActor objectToSpawn = GetNextInactiveElement(reference);
		// Netsu (Oct 27 c35): set the facing BEFORE the state starts. Its OnEnter events (the note's / Shade Wave's
		// forward MoveX) read the facing right away, so with the old order a reused pooled object flew with its
		// PREVIOUS facing, i.e. backwards whenever the spawner had turned since the last use.
		objectToSpawn.Body.UpdateSide(objectToSpawn.GetMaster().Body.PlayerSide > 0);
		objectToSpawn.Body.FlipSide();
		objectToSpawn.StateManager.PlayState(initialState, reset: true);
		objectToSpawn.StateManager.CurrentStateFrame = -1;
		objectToSpawn.Body.MoveTo(position);
		// Netsu (Oct 27 c29): face the way the spawner FACES (PlayerSide), not the side of the opponent it's on
		// (IsLeftSide, updated every frame from positions). They differ after a cross-up / an air hit until the spawner
		// turns, and Noah's Shade Wave or Mary's note then flew backwards.
		objectToSpawn.Body.UpdateSide(objectToSpawn.GetMaster().Body.PlayerSide > 0);
		objectToSpawn.Body.FlipSide();
		objectToSpawn.IsActive = true;
		// Netsu (Oct 27 c27): remember the move that spawned it (repeat proration counts a projectile as that move); a
		// projectile spawned by a projectile keeps the first one's move
		SakugaActor master = objectToSpawn.GetMaster();
		if (master != null && master.GetMaster() != null)
		{
			objectToSpawn.NetsuSpawnMove = master.NetsuSpawnMove;
			objectToSpawn.NetsuSpawnUse = master.NetsuSpawnUse;
		}
		else if (master != null && master.StanceManager != null)
		{
			objectToSpawn.NetsuSpawnMove = master.StanceManager.CurrentMove;
			objectToSpawn.NetsuSpawnUse = master.StanceManager.ExecutedMoves;
		}
	}

	public PoolReference GetSpawnReference(string key)
	{
		foreach (PoolReference reference in SpawnReferences)
		{
			if (!(reference.Key != key))
			{
				return reference;
			}
		}
		return default(PoolReference);
	}

	public PoolReference GetSpawnReference(int index)
	{
		return SpawnReferences[index];
	}

	public SakugaActor GetActiveSpawn(PoolReference reference)
	{
		for (int i = 0; i < reference.Objects.Length; i++)
		{
			if (reference.Objects[i].IsActive)
			{
				return reference.Objects[i];
			}
		}
		return null;
	}

	/// <summary>Oct 27 c35: is a projectile / object that the given move spawned still out? (Roman Cancel on a whiff is only
	/// allowed then: Noah's black hole.)</summary>
	public bool NetsuHasActiveSpawnFrom(int moveIndex)
	{
		for (int r = 0; r < SpawnReferences.Count; r++)
		{
			SakugaActor[] objects = SpawnReferences[r].Objects;
			for (int i = 0; objects != null && i < objects.Length; i++)
			{
				if (objects[i] != null && objects[i].IsActive && objects[i].NetsuSpawnMove == moveIndex)
				{
					return true;
				}
			}
		}
		return false;
	}

	public SakugaActor GetActiveSpawnByIndex(int index)
	{
		PoolReference reference = GetSpawnReference(index);
		return GetActiveSpawn(reference);
	}

	public SakugaActor GetNextInactiveElement(PoolReference reference)
	{
		for (int i = 0; i < reference.Objects.Length; i++)
		{
			if (!reference.Objects[i].IsActive)
			{
				return reference.Objects[i];
			}
		}
		return reference.Objects[0];
	}

	public void SpawnVFX(string key, Vector2I position, int side, bool attached)
	{
		if (VFXReferences.Count != 0)
		{
			VFXPoolReference spawnElement = GetVFXReference(key);
			GetNextInactiveVFXElement(spawnElement).Spawn(position, side, attached);
		}
	}

	public void SpawnVFX(int index, Vector2I position, int side, bool attached)
	{
		if (VFXReferences.Count != 0)
		{
			VFXPoolReference spawnElement = GetVFXReference(index);
			GetNextInactiveVFXElement(spawnElement).Spawn(position, side, attached);
		}
	}

	public VFXPoolReference GetVFXReference(string key)
	{
		foreach (VFXPoolReference reference in VFXReferences)
		{
			if (!(reference.Key != key))
			{
				return reference;
			}
		}
		return default(VFXPoolReference);
	}

	public VFXPoolReference GetVFXReference(int index)
	{
		return VFXReferences[index];
	}

	public SakugaVFX GetNextInactiveVFXElement(VFXPoolReference reference)
	{
		for (int i = 0; i < reference.Objects.Length; i++)
		{
			if (!reference.Objects[i].IsActive)
			{
				return reference.Objects[i];
			}
		}
		return reference.Objects[0];
	}
}
