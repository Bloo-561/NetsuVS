using Godot;
using SakugaEngine.Resources;

namespace SakugaEngine.Collision;

public struct HitQuery
{
	public IDamage p1;

	public int p1HitType;

	public HitboxElement p1Hitbox;

	public Vector2I p1ContactPoint;

	public IDamage p2;

	public int p2HitType;

	public HitboxElement p2Hitbox;

	public Vector2I p2ContactPoint;
}
