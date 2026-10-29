using Godot;

namespace SakugaEngine.Collision;

public struct Collider
{
	[Export(PropertyHint.None, "")]
	public Vector2I Center;

	[Export(PropertyHint.None, "")]
	public Vector2I Size;

	public bool Active => Size != Vector2I.Zero;

	public bool IsOverlapping(Collider other)
	{
		if (!Active)
		{
			return false;
		}
		if (!other.Active)
		{
			return false;
		}
		bool num = Center.X - Size.X / 2 <= other.Center.X + other.Size.X / 2 && Center.X + Size.X / 2 >= other.Center.X - other.Size.X / 2;
		bool collisionY = Center.Y - Size.Y / 2 <= other.Center.Y + other.Size.Y / 2 && Center.Y + Size.Y / 2 >= other.Center.Y - other.Size.Y / 2;
		return num & collisionY;
	}

	public void UpdateCollider(Vector2I center, Vector2I size)
	{
		Center = center;
		Size = size;
	}
}
