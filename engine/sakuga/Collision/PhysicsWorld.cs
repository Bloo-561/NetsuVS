using System.Collections.Generic;
using Godot;
using SakugaEngine.Global;
using SakugaEngine.Resources;

namespace SakugaEngine.Collision;

public class PhysicsWorld
{
	private List<PhysicsBody> bodies;

	private List<HitQuery> hitQueries;

	private uint CreatedBodies;

	private int MinSteps = 1;

	private int MaxSteps = 64;

	private int Steps;

	public int BodyCount => bodies.Count;

	private static bool NetsuInHitstun(SakugaActor target)
	{
		return target != null && target.StateManager != null && target.StateManager.CurrentStateType() == StateType.HIT_REACTION;
	}

	public PhysicsWorld()
	{
		bodies = new List<PhysicsBody>();
		hitQueries = new List<HitQuery>();
		CreatedBodies = 0u;
		Steps = Mathf.Clamp(2, MinSteps, MaxSteps);
	}

	public void AddBody(PhysicsBody newBody)
	{
		newBody.SetID(CreatedBodies);
		CreatedBodies++;
		bodies.Add(newBody);
	}

	public bool RemoveBody(PhysicsBody body)
	{
		return bodies.Remove(body);
	}

	public bool GetBody(int index, out PhysicsBody body)
	{
		body = null;
		if (index < 0 || index >= bodies.Count)
		{
			return false;
		}
		body = bodies[index];
		return true;
	}

	public void Simulate()
	{
		hitQueries.Clear();
		for (int st = 0; st < Steps; st++)
		{
			for (int i = 0; i < bodies.Count; i++)
			{
				bodies[i].Move();
			}
			for (int j = 0; j < bodies.Count; j++)
			{
				PhysicsBody bodyA = bodies[j];
				for (int k = j + 1; k < bodies.Count; k++)
				{
					PhysicsBody bodyB = bodies[k];
					if ((bodyA.IsStatic && bodyB.IsStatic) || !bodyA.Pushbox.IsOverlapping(bodyB.Pushbox))
					{
						continue;
					}
					Vector2I depth = GetDepth(bodyA.Pushbox, bodyB.Pushbox);
					Vector2I normal = Vector2I.Zero;
					if (bodyA.FixedPosition.X > bodyB.FixedPosition.X)
					{
						normal.X = -1;
					}
					else if (bodyA.FixedPosition.X < bodyB.FixedPosition.X)
					{
						normal.X = 1;
					}
					else
					{
						normal.X = (bodyA.IsLeftSide ? 1 : (-1));
					}
					if (bodyA.IsStatic)
					{
						bodyB.Resolve(-normal * depth);
						continue;
					}
					if (bodyB.IsStatic)
					{
						bodyA.Resolve(normal * depth);
						continue;
					}
					if (Unpushable(bodyA, bodyB))
					{
						bodyA.Resolve(normal * depth);
					}
					else
					{
						bodyA.Resolve(normal * (depth / 2));
					}
					if (Unpushable(bodyB, bodyA))
					{
						bodyB.Resolve(-normal * depth);
					}
					else
					{
						bodyB.Resolve(-normal * (depth / 2));
					}
				}
			}
		}
		for (int l = 0; l < bodies.Count; l++)
		{
			bodies[l].ProximityBlocked = false;
		}
		for (int m = 0; m < bodies.Count; m++)
		{
			PhysicsBody bodyA2 = bodies[m];
			for (int n = m + 1; n < bodies.Count; n++)
			{
				PhysicsBody bodyB2 = bodies[n];
				HitboxesCheck(bodyA2, bodyB2);
			}
		}
		HitQueries();
		for (int num = 0; num < bodies.Count; num++)
		{
			if (!bodies[num].ProximityBlocked)
			{
				bodies[num].Parent.OnHitboxExit();
			}
		}
	}

	// Netsu (Oct 26 c6, TamaDeez): a box pair that can't hit any more (that attack already hit this fighter) now only
	// skips that pair. Before, it ended the check for the whole fighter pair, so a frozen opponent whose used-up
	// attack still overlapped Cecilia made her counter super's slashes (and any other hit landing in that overlap) whiff.
	private void HitboxesCheck(PhysicsBody bodyA, PhysicsBody bodyB)
	{
		HitQuery currentHit = new HitQuery
		{
			p1 = bodyA.Parent,
			p2 = bodyB.Parent,
			p1HitType = -1,
			p2HitType = -1
		};
		for (int i = 0; i < bodyA.Hitboxes.Length; i++)
		{
			Collider hitboxA = bodyA.Hitboxes[i];
			for (int j = 0; j < bodyB.Hitboxes.Length; j++)
			{
				Collider hitboxB = bodyB.Hitboxes[j];
				if (!hitboxA.IsOverlapping(hitboxB))
				{
					continue;
				}
				HitboxElement boxSettingsA = bodyA.CurrentHitbox.HitboxData.Hitboxes[i];
				HitboxElement boxSettingsB = bodyB.CurrentHitbox.HitboxData.Hitboxes[j];
				HitboxType myType = boxSettingsA.HitboxType;
				HitboxType otType = boxSettingsB.HitboxType;
				if (myType == HitboxType.HURTBOX && otType == HitboxType.HURTBOX)
				{
					continue;
				}
				Vector2I ContactPoint = GetContactPoint(hitboxA, hitboxB);
				if (myType == HitboxType.HITBOX && otType == HitboxType.HURTBOX)
				{
					if (!bodyA.CanHitBody(bodyB))
					{
						continue;   // Netsu (Oct 26 c6): this box pair only, not the whole fighter pair
					}
					if (currentHit.p1HitType < 0)
					{
						currentHit.p1HitType = 0;
						currentHit.p1Hitbox = boxSettingsA;
						currentHit.p1ContactPoint = ContactPoint;
					}
				}
				else if (otType == HitboxType.HITBOX && myType == HitboxType.HURTBOX)
				{
					if (!bodyB.CanHitBody(bodyA))
					{
						continue;   // Netsu (Oct 26 c6): this box pair only, not the whole fighter pair
					}
					if (currentHit.p2HitType < 0)
					{
						currentHit.p2HitType = 0;
						currentHit.p2Hitbox = boxSettingsB;
						currentHit.p2ContactPoint = ContactPoint;
					}
				}
				if (myType == HitboxType.HITBOX && otType == HitboxType.HITBOX)
				{
					if (!bodyA.CanHitBody(bodyB) || !bodyB.CanHitBody(bodyA) || boxSettingsA.Priority != boxSettingsB.Priority)
					{
						continue;   // Netsu (Oct 26 c6): this box pair only, not the whole fighter pair
					}
					if (currentHit.p1HitType < 0)
					{
						currentHit.p1HitType = 11;
						currentHit.p1Hitbox = boxSettingsA;
						currentHit.p1ContactPoint = ContactPoint;
					}
					if (currentHit.p2HitType < 0)
					{
						currentHit.p2HitType = 11;
						currentHit.p2Hitbox = boxSettingsB;
						currentHit.p2ContactPoint = ContactPoint;
					}
				}
				if (myType == HitboxType.PROJECTILE && otType == HitboxType.HURTBOX)
				{
					if (!bodyA.CanHitBody(bodyB))
					{
						continue;   // Netsu (Oct 26 c6): this box pair only, not the whole fighter pair
					}
					if (currentHit.p1HitType < 0)
					{
						currentHit.p1HitType = 0;
						currentHit.p1Hitbox = boxSettingsA;
						currentHit.p1ContactPoint = ContactPoint;
					}
				}
				else if (otType == HitboxType.PROJECTILE && myType == HitboxType.HURTBOX)
				{
					if (!bodyB.CanHitBody(bodyA))
					{
						continue;   // Netsu (Oct 26 c6): this box pair only, not the whole fighter pair
					}
					if (currentHit.p2HitType < 0)
					{
						currentHit.p2HitType = 0;
						currentHit.p2Hitbox = boxSettingsB;
						currentHit.p2ContactPoint = ContactPoint;
					}
				}
				if (myType == HitboxType.PROJECTILE && otType == HitboxType.PROJECTILE)
				{
					if (!bodyA.CanHitBody(bodyB) || !bodyB.CanHitBody(bodyA))
					{
						continue;   // Netsu (Oct 26 c6): this box pair only, not the whole fighter pair
					}
					if (currentHit.p1HitType < 0)
					{
						currentHit.p1HitType = 12;
						currentHit.p1Hitbox = boxSettingsA;
						currentHit.p1ContactPoint = ContactPoint;
					}
					if (currentHit.p2HitType < 0)
					{
						currentHit.p2HitType = 12;
						currentHit.p2Hitbox = boxSettingsB;
						currentHit.p2ContactPoint = ContactPoint;
					}
				}
				if (myType == HitboxType.PROJECTILE && otType == HitboxType.DEFLECT)
				{
					if (!bodyA.CanHitBody(bodyB))
					{
						continue;   // Netsu (Oct 26 c6): this box pair only, not the whole fighter pair
					}
					if (currentHit.p1HitType < 0)
					{
						currentHit.p1HitType = 10;
						currentHit.p1Hitbox = boxSettingsA;
						currentHit.p1ContactPoint = ContactPoint;
					}
				}
				else if (otType == HitboxType.PROJECTILE && myType == HitboxType.DEFLECT)
				{
					if (!bodyB.CanHitBody(bodyA))
					{
						continue;   // Netsu (Oct 26 c6): this box pair only, not the whole fighter pair
					}
					if (currentHit.p2HitType < 0)
					{
						currentHit.p2HitType = 10;
						currentHit.p2Hitbox = boxSettingsB;
						currentHit.p2ContactPoint = ContactPoint;
					}
				}
				if (myType == HitboxType.PROXIMITY_BLOCK && otType == HitboxType.HURTBOX)
				{
					if (!bodyA.CanHitBody(bodyB))
					{
						continue;   // Netsu (Oct 26 c6): this box pair only, not the whole fighter pair
					}
					bodyB.Parent.ProximityBlock(boxSettingsA);
				}
				else if (otType == HitboxType.PROXIMITY_BLOCK && myType == HitboxType.HURTBOX)
				{
					if (!bodyB.CanHitBody(bodyA))
					{
						continue;   // Netsu (Oct 26 c6): this box pair only, not the whole fighter pair
					}
					bodyA.Parent.ProximityBlock(boxSettingsB);
				}
				if (myType == HitboxType.THROW && otType == HitboxType.HURTBOX)
				{
					if (!bodyA.CanHitBody(bodyB))
					{
						continue;   // Netsu (Oct 26 c6): this box pair only, not the whole fighter pair
					}
					if (currentHit.p1HitType < 0)
					{
						currentHit.p1HitType = 2;
						currentHit.p1Hitbox = boxSettingsA;
						currentHit.p1ContactPoint = ContactPoint;
					}
				}
				else if (otType == HitboxType.THROW && myType == HitboxType.HURTBOX)
				{
					if (!bodyB.CanHitBody(bodyA))
					{
						continue;   // Netsu (Oct 26 c6): this box pair only, not the whole fighter pair
					}
					if (currentHit.p2HitType < 0)
					{
						currentHit.p2HitType = 2;
						currentHit.p2Hitbox = boxSettingsB;
						currentHit.p2ContactPoint = ContactPoint;
					}
				}
				if (myType == HitboxType.COUNTER && otType == HitboxType.HITBOX)
				{
					if (!bodyA.CanHitBody(bodyB))
					{
						continue;   // Netsu (Oct 26 c6): this box pair only, not the whole fighter pair
					}
					if (currentHit.p1HitType < 0)
					{
						currentHit.p1HitType = 3;
						currentHit.p1Hitbox = boxSettingsA;
						currentHit.p1ContactPoint = ContactPoint;
					}
				}
				else if (otType == HitboxType.COUNTER && myType == HitboxType.HITBOX)
				{
					if (!bodyB.CanHitBody(bodyA))
					{
						continue;   // Netsu (Oct 26 c6): this box pair only, not the whole fighter pair
					}
					if (currentHit.p2HitType < 0)
					{
						currentHit.p2HitType = 3;
						currentHit.p2Hitbox = boxSettingsB;
						currentHit.p2ContactPoint = ContactPoint;
					}
				}
			}
		}
		hitQueries.Add(currentHit);
	}

	private void HitQueries()
	{
		if (hitQueries == null || hitQueries.Count <= 0)
		{
			return;
		}
		// Netsu: counters (an attack touching a COUNTER box, e.g. Adin's shield) are settled first.
		// An attack that was countered this frame hits nothing else: the shield absorbs it, so the
		// fighter standing behind it isn't hit in the same frame.
		HashSet<IDamage> countered = null;
		for (int i = 0; i < hitQueries.Count; i++)
		{
			HitQuery c = hitQueries[i];
			bool p1Counters = c.p1HitType == 3 && c.p2HitType == -1;
			bool p2Counters = c.p1HitType == -1 && c.p2HitType == 3;
			if (!p1Counters && !p2Counters)
			{
				continue;
			}
			SakugaActor c1 = c.p1 as SakugaActor;
			SakugaActor c2 = c.p2 as SakugaActor;
			if (!c1.CanHitTarget(c2) || !c2.CanHitTarget(c1))
			{
				continue;
			}
			// the countered attack also can't hit the fighter behind the counter later on
			// (it stays out while the attacker is frozen); a new move or a ResetHit clears this
			if (p1Counters)
			{
				c.p1.CounterHit(c2, c.p1Hitbox, c.p1ContactPoint);
				(countered ??= new HashSet<IDamage>()).Add(c.p2);
				c2.Body.AddHitBody(c1.NetsuRoot().Body);
			}
			else
			{
				c.p2.CounterHit(c1, c.p2Hitbox, c.p2ContactPoint);
				(countered ??= new HashSet<IDamage>()).Add(c.p1);
				c1.Body.AddHitBody(c2.NetsuRoot().Body);
			}
		}
		for (int i = 0; i < hitQueries.Count; i++)
		{
			HitQuery currentHit = hitQueries[i];
			if ((currentHit.p1HitType == 3 && currentHit.p2HitType == -1) || (currentHit.p1HitType == -1 && currentHit.p2HitType == 3))
			{
				continue;   // Netsu: counters were handled above
			}
			if (countered != null)
			{
				if (countered.Contains(currentHit.p1)) currentHit.p1HitType = -1;
				if (countered.Contains(currentHit.p2)) currentHit.p2HitType = -1;
			}
			// Netsu (Oct 28): attack boxes that need the target to be in hitstun (Leticia's j.236) do nothing otherwise
			if (currentHit.p1HitType == 0 && currentHit.p1Hitbox != null && currentHit.p1Hitbox.NetsuRequireTargetHitstun && !NetsuInHitstun(currentHit.p2 as SakugaActor))
			{
				currentHit.p1HitType = -1;
			}
			if (currentHit.p2HitType == 0 && currentHit.p2Hitbox != null && currentHit.p2Hitbox.NetsuRequireTargetHitstun && !NetsuInHitstun(currentHit.p1 as SakugaActor))
			{
				currentHit.p2HitType = -1;
			}
			if (currentHit.p1HitType < 0 && currentHit.p2HitType < 0)
			{
				continue;
			}
			SakugaActor actor1 = currentHit.p1 as SakugaActor;
			SakugaActor actor2 = currentHit.p2 as SakugaActor;
			if (!actor1.CanHitTarget(actor2) || !actor2.CanHitTarget(actor1))
			{
				continue;
			}
			if (currentHit.p1HitType == 0 && currentHit.p2HitType != 0)
			{
				currentHit.p1.BaseDamage(currentHit.p2 as SakugaActor, currentHit.p1Hitbox, currentHit.p1ContactPoint);
			}
			else if (currentHit.p1HitType != 0 && currentHit.p2HitType == 0)
			{
				currentHit.p2.BaseDamage(currentHit.p1 as SakugaActor, currentHit.p2Hitbox, currentHit.p2ContactPoint);
			}
			else if (currentHit.p1HitType == 0 && currentHit.p2HitType == 0)
			{
				currentHit.p1.HitTrade(currentHit.p2 as SakugaActor, currentHit.p2Hitbox, currentHit.p1ContactPoint);
				currentHit.p2.HitTrade(currentHit.p1 as SakugaActor, currentHit.p1Hitbox, currentHit.p2ContactPoint);
			}
			else if (currentHit.p1HitType == 11 && currentHit.p2HitType == 11)
			{
				if (currentHit.p1Hitbox.Priority != currentHit.p2Hitbox.Priority)
				{
					break;
				}
				currentHit.p1.HitboxClash(currentHit.p2 as SakugaActor, currentHit.p1Hitbox, currentHit.p1ContactPoint);
				currentHit.p2.HitboxClash(currentHit.p1 as SakugaActor, currentHit.p2Hitbox, Vector2I.Zero);
			}
			else if (currentHit.p1HitType == 12 && currentHit.p2HitType == 12)
			{
				if (currentHit.p2Hitbox.Priority >= currentHit.p1Hitbox.Priority)
				{
					currentHit.p1.ProjectileClash(currentHit.p2 as SakugaActor, currentHit.p1Hitbox, currentHit.p1ContactPoint);
				}
				if (currentHit.p1Hitbox.Priority >= currentHit.p2Hitbox.Priority)
				{
					currentHit.p2.ProjectileClash(currentHit.p1 as SakugaActor, currentHit.p2Hitbox, currentHit.p2ContactPoint);
				}
			}
			if (currentHit.p1HitType == 12 && currentHit.p2HitType == -1)
			{
				currentHit.p1.ProjectileDeflect(currentHit.p2 as SakugaActor, currentHit.p1Hitbox, currentHit.p1ContactPoint);
			}
			else if (currentHit.p1HitType == -1 && currentHit.p2HitType == 12)
			{
				currentHit.p2.ProjectileDeflect(currentHit.p1 as SakugaActor, currentHit.p2Hitbox, currentHit.p2ContactPoint);
			}
			if (currentHit.p1HitType == 2 && currentHit.p2HitType == -1)
			{
				currentHit.p1.ThrowDamage(currentHit.p2 as SakugaActor, currentHit.p1Hitbox, currentHit.p1ContactPoint);
			}
			else if (currentHit.p1HitType == -1 && currentHit.p2HitType == 2)
			{
				currentHit.p2.ThrowDamage(currentHit.p1 as SakugaActor, currentHit.p2Hitbox, currentHit.p2ContactPoint);
			}
			else if (currentHit.p1HitType == 2 && currentHit.p2HitType == 2)
			{
				currentHit.p1.ThrowTrade();
				currentHit.p2.ThrowTrade();
			}
			if (currentHit.p1HitType == 3 && currentHit.p2HitType == -1)
			{
				currentHit.p1.CounterHit(currentHit.p2 as SakugaActor, currentHit.p1Hitbox, currentHit.p1ContactPoint);
			}
			else if (currentHit.p1HitType == -1 && currentHit.p2HitType == 3)
			{
				currentHit.p2.CounterHit(currentHit.p1 as SakugaActor, currentHit.p2Hitbox, currentHit.p2ContactPoint);
			}
		}
	}

	public Vector2I GetContactPoint(Collider A, Collider B)
	{
		int num = Mathf.Min(A.Center.X + A.Size.X, B.Center.X + B.Size.X);
		int maxPointX = Mathf.Max(A.Center.X - A.Size.X, B.Center.X - B.Size.X);
		int minPointY = Mathf.Min(A.Center.Y + A.Size.Y, B.Center.Y + B.Size.Y);
		int maxPointY = Mathf.Max(A.Center.Y - A.Size.Y, B.Center.Y - B.Size.Y);
		int x = (num + maxPointX) / 2;
		int MedianY = (minPointY + maxPointY) / 2;
		return new Vector2I(x, MedianY);
	}

	public Vector2I GetDepth(Collider A, Collider B)
	{
		Vector2I length = A.Center - B.Center;
		Vector2I Depth = (A.Size + B.Size) / 2;
		Depth.X -= Mathf.Abs(length.X);
		Depth.Y -= Mathf.Abs(length.Y);
		return Depth;
	}

	private bool Unpushable(PhysicsBody bodyA, PhysicsBody bodyB)
	{
		bool num = bodyB.IsOnLeftWall && bodyA.FixedPosition.X >= bodyB.FixedPosition.X;
		bool RightWall = bodyB.IsOnRightWall && bodyA.FixedPosition.X <= bodyB.FixedPosition.X;
		return num | RightWall;
	}
}
