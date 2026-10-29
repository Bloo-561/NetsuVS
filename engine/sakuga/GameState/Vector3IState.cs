using Godot;
using MessagePack;

namespace SakugaEngine.GameState;

[MessagePackObject(false)]
public struct Vector3IState
{
	[Key(0)]
	public int X;

	[Key(1)]
	public int Y;

	[Key(2)]
	public int Z;

	public void GetStateData(ref Vector3I reference)
	{
		X = reference.X;
		Y = reference.Y;
		Z = reference.Z;
	}

	public void SetStateData(ref Vector3I reference)
	{
		reference.X = X;
		reference.Y = Y;
		reference.Z = Z;
	}
}
