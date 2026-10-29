using System.Collections.Generic;
using MessagePack;
using SakugaEngine.Collision;

namespace SakugaEngine.GameState;

[MessagePackObject(false)]
public struct PhysicsBodyState
{
	[Key(0)]
	public Vector2IState FixedPosition;

	[Key(1)]
	public Vector2IState FixedVelocity;

	[Key(2)]
	public bool IsLeftSide;

	[Key(3)]
	public int PlayerSide;

	[Key(4)]
	public bool IsMovable;

	[Key(5)]
	public List<uint> HitBodies;

	[Key(6)]
	public bool ProximityBlocked;

	[Key(7)]
	public int CurrentGravity;

	public void GetStateData(ref PhysicsBody reference)
	{
		if (reference != null)
		{
			FixedPosition.GetStateData(ref reference.FixedPosition);
			FixedVelocity.GetStateData(ref reference.FixedVelocity);
			IsLeftSide = reference.IsLeftSide;
			PlayerSide = reference.PlayerSide;
			IsMovable = reference.IsMovable;
			HitBodies = reference.HitBodies;
			ProximityBlocked = reference.ProximityBlocked;
			CurrentGravity = reference.CurrentGravity;
		}
	}

	public void SetStateData(ref PhysicsBody reference)
	{
		if (reference != null)
		{
			FixedPosition.SetStateData(ref reference.FixedPosition);
			FixedVelocity.SetStateData(ref reference.FixedVelocity);
			reference.IsLeftSide = IsLeftSide;
			reference.PlayerSide = PlayerSide;
			reference.IsMovable = IsMovable;
			reference.HitBodies = HitBodies;
			reference.ProximityBlocked = ProximityBlocked;
			reference.CurrentGravity = CurrentGravity;
		}
	}
}
