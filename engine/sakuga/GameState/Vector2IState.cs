using Godot;
using MessagePack;

namespace SakugaEngine.GameState;

[MessagePackObject(false)]
public struct Vector2IState
{
	[Key(0)]
	public int X;

	[Key(1)]
	public int Y;

	public void GetStateData(ref Vector2I reference)
	{
		X = reference.X;
		Y = reference.Y;
	}

	public void SetStateData(ref Vector2I reference)
	{
		reference.X = X;
		reference.Y = Y;
	}
}
