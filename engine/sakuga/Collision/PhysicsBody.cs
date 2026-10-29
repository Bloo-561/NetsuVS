using System.Collections.Generic;
using Godot;
using SakugaEngine.Resources;

namespace SakugaEngine.Collision;

[GlobalClass]
public partial class PhysicsBody : Node
{
	private SakugaActor _owner;

	[Export(PropertyHint.None, "")]
	public bool IsStatic;

	[Export(PropertyHint.None, "")]
	public bool StayOnBounds;

	[Export(PropertyHint.None, "")]
	public bool IgnoreWalls;

	[Export(PropertyHint.None, "")]
	public int HitboxesLimit = 16;

	public IDamage Parent;

	public uint ID;

	public Collider Pushbox;

	public Collider[] Hitboxes;

	public Vector2I FixedPosition;

	public Vector2I FixedVelocity;

	public bool IsLeftSide;

	public int PlayerSide;

	public bool IsMovable = true;

	public List<uint> HitBodies = new List<uint>();

	public bool ProximityBlocked;

	public HitboxState CurrentHitbox;

	public int CurrentGravity = 260000;

	public bool IsOnGround => FixedPosition.Y <= 0;

	public bool IsOnLeftWall => FixedPosition.X <= -SakugaEngine.Global.GlobalVariables.WallLimit;   // c26: was -120000

	public bool IsOnRightWall => FixedPosition.X >= SakugaEngine.Global.GlobalVariables.WallLimit;   // c26: was 120000

	public bool IsFalling
	{
		get
		{
			if (!IsOnGround)
			{
				return FixedVelocity.Y <= 0;
			}
			return false;
		}
	}

	public bool JustLanded
	{
		get
		{
			if (IsOnGround)
			{
				return FixedVelocity.Y < 0;
			}
			return false;
		}
	}

	public bool IsOnWall
	{
		get
		{
			if (!IsOnLeftWall)
			{
				return IsOnRightWall;
			}
			return true;
		}
	}

	public void Initialize(SakugaActor newOwner, IDamage newParent)
	{
		_owner = newOwner;
		Parent = newParent;
		FixedPosition = Vector2I.Zero;
		FixedVelocity = Vector2I.Zero;
		Hitboxes = new Collider[HitboxesLimit];
	}

	public void SetID(uint newID)
	{
		ID = newID;
	}

	public void UpdateSide(bool leftSide)
	{
		IsLeftSide = leftSide;
	}

	public void FlipSide()
	{
		PlayerSide = (IsLeftSide ? 1 : (-1));
	}

	public void SetVelocity(Vector2I newVelocity)
	{
		FixedVelocity = newVelocity;
	}

	public void SetLateralVelocity(int newVelocity)
	{
		FixedVelocity.X = newVelocity;
	}

	public void SetVerticalVelocity(int newVelocity)
	{
		FixedVelocity.Y = newVelocity;
	}

	public void AddLateralAcceleration(int newVelocity)
	{
		int absVelocity = Mathf.Abs(newVelocity);
		if (newVelocity != 0 && Mathf.Sign(newVelocity) > 0)
		{
			if (FixedVelocity.X < 0)
			{
				FixedVelocity.X += 6666;
			}
			else if (FixedVelocity.X < absVelocity)
			{
				FixedVelocity.X += 6000;
			}
			else
			{
				FixedVelocity.X = absVelocity;
			}
		}
		else if (newVelocity != 0 && Mathf.Sign(newVelocity) < 0)
		{
			if (FixedVelocity.X > 0)
			{
				FixedVelocity.X -= 6666;
			}
			else if (FixedVelocity.X > -absVelocity)
			{
				FixedVelocity.X -= 6000;
			}
			else
			{
				FixedVelocity.X = -absVelocity;
			}
		}
		else
		{
			FixedVelocity.X -= Mathf.Min(Mathf.Abs(FixedVelocity.X), 4166) * Mathf.Sign(FixedVelocity.X);
		}
	}

	public void AddVerticalAcceleration(int newVelocity)
	{
		int absVelocity = Mathf.Abs(newVelocity);
		if (newVelocity != 0 && Mathf.Sign(newVelocity) > 0)
		{
			if (FixedVelocity.Y < 0)
			{
				FixedVelocity.Y += 6666;
			}
			else if (FixedVelocity.Y < absVelocity)
			{
				FixedVelocity.Y += 6000;
			}
			else
			{
				FixedVelocity.Y = absVelocity;
			}
		}
		else if (newVelocity != 0 && Mathf.Sign(newVelocity) < 0)
		{
			if (FixedVelocity.Y > 0)
			{
				FixedVelocity.Y -= 6666;
			}
			else if (FixedVelocity.Y > -absVelocity)
			{
				FixedVelocity.Y -= 6000;
			}
			else
			{
				FixedVelocity.Y = -absVelocity;
			}
		}
		else
		{
			FixedVelocity.Y -= Mathf.Min(Mathf.Abs(FixedVelocity.Y), 4166) * Mathf.Sign(FixedVelocity.Y);
		}
	}

	public void AddGravity()
	{
		FixedVelocity.Y -= CurrentGravity / 60;
	}

	public void MoveTo(Vector2I destination)
	{
		if (!IsStatic)
		{
			FixedPosition = destination;
			UpdateColliders();
		}
	}

	public void Resolve(Vector2I depth)
	{
		FixedPosition -= depth;
		UpdateColliders();
	}

	public void Move()
	{
		if (!IsStatic && IsMovable)
		{
			FixedPosition += FixedVelocity / 120;
			UpdateColliders();
		}
	}

	public void AddHitBody(PhysicsBody body)
	{
		HitBodies.Add(body.ID);
	}

	public void ResetHits()
	{
		HitBodies.Clear();
	}

	public bool CanHitBody(PhysicsBody body)
	{
		return !HitBodies.Contains(body.ID);
	}

	public void BounceX(int intensity)
	{
		FixedVelocity.X *= -intensity;
		FixedVelocity.X /= 100;
		SakugaEngine.Global.NetsuLog.Debug($"{FixedVelocity.X}, {intensity}");
	}

	public void BounceY(int intensity)
	{
		FixedVelocity.Y *= -intensity;
		FixedVelocity.Y /= 100;
	}

	public void UpdateColliders()
	{
		CurrentHitbox = GetCurrentHitboxSettings();
		if (StayOnBounds)
		{
			if (!IgnoreWalls)
			{
				FixedPosition.X = Mathf.Clamp(FixedPosition.X, -SakugaEngine.Global.GlobalVariables.WallLimit, SakugaEngine.Global.GlobalVariables.WallLimit);   // c26: was +-120000
			}
			FixedPosition.Y = Mathf.Clamp(FixedPosition.Y, 0, 250000);
		}
		if (CurrentHitbox == null || CurrentHitbox.HitboxData == null)
		{
			Pushbox.UpdateCollider(FixedPosition, Vector2I.Zero);
			for (int i = 0; i < Hitboxes.Length; i++)
			{
				Hitboxes[i].UpdateCollider(FixedPosition, Vector2I.Zero);
			}
			return;
		}
		Vector2I Side = new Vector2I(PlayerSide, 1);
		if (CurrentHitbox.HitboxData.Pushbox == null)
		{
			Pushbox.UpdateCollider(FixedPosition + Vector2I.Zero, Vector2I.Zero);
		}
		else
		{
			Pushbox.UpdateCollider(FixedPosition + CurrentHitbox.HitboxData.Pushbox.Center * Side, CurrentHitbox.HitboxData.Pushbox.Size);
		}
		for (int j = 0; j < Hitboxes.Length; j++)
		{
			if (j < CurrentHitbox.HitboxData.Hitboxes.Length)
			{
				HitboxElement el = CurrentHitbox.HitboxData.Hitboxes[j];
				NetsuBox(el, out Vector2I c, out Vector2I s);
				Hitboxes[j].UpdateCollider(FixedPosition + c * Side, s);
			}
			else
			{
				Hitboxes[j].UpdateCollider(FixedPosition, Vector2I.Zero);
			}
		}
	}

	// ---------------------------------------------------------------------------------------------
	// Netsu (Oct 26 2026, TamaDeez): universal boxes, for the fighters themselves (not assists or projectiles).
	//  - Hurtboxes: every fighter's are stretched / squashed up and down so her standing hurtbox is
	//    NetsuUniversalHeight tall (Cecilia, Flan, Leticia and Noah are drawn at different heights; now an attack that
	//    hits one of them standing hits all of them). Crouching / jumping / lying boxes get the same factor.
	//  - Attack boxes reach from their top down to her feet (to the floor when she's standing), keeping their width,
	//    so a move hits short and crouching fighters the same as tall ones. NetsuKeepHeight on a box opts out.
	// Only what the game uses is changed (the colliders, also what F10 shows); the .tres files keep the drawn sizes.
	// Integer maths from the fighter's own data, the same on every computer.

	/// <summary>Standing hurtbox height every fighter gets (units, 10000 = 1 m).</summary>
	public const int NetsuUniversalHeight = 14000;

	private int _netsuHurtScale;   // per mille; 0 = not worked out yet (data only, nothing to save for rollback)

	private bool NetsuIsFighter()
	{
		return _owner != null && _owner.GetMaster() == null && _owner.Data != null && _owner.Data.States != null && _owner.Data.States.Length > 0;
	}

	/// <summary>Hurtbox height factor (per mille): NetsuUniversalHeight / the top of her idle hurtboxes.</summary>
	public int NetsuHurtScale()
	{
		if (_netsuHurtScale != 0)
		{
			return _netsuHurtScale;
		}
		_netsuHurtScale = 1000;
		if (!NetsuIsFighter())
		{
			return _netsuHurtScale;
		}
		AnimationData idle = _owner.Data.States[0]?.AnimationData;
		HitboxSettings boxes = (idle != null && idle.Hitboxes != null && idle.Hitboxes.Length > 0) ? idle.Hitboxes[0]?.HitboxData : null;
		int top = 0;
		for (int i = 0; boxes != null && boxes.Hitboxes != null && i < boxes.Hitboxes.Length; i++)
		{
			HitboxElement e = boxes.Hitboxes[i];
			if (e != null && e.HitboxType == SakugaEngine.Global.HitboxType.HURTBOX)
			{
				top = Mathf.Max(top, e.Center.Y + e.Size.Y / 2);
			}
		}
		if (top > 4000)
		{
			_netsuHurtScale = Mathf.Clamp(NetsuUniversalHeight * 1000 / top, 700, 1400);
		}
		return _netsuHurtScale;
	}

	/// <summary>The box the game uses for this element (see above).</summary>
	public void NetsuBox(HitboxElement el, out Vector2I center, out Vector2I size)
	{
		center = el.Center;
		size = el.Size;
		if (!NetsuIsFighter())
		{
			return;
		}
		int ds = _owner.Data.NetsuScale > 0 ? _owner.Data.NetsuScale : 1000;   // the fighter's drawn size (DataContainer)
		if (el.HitboxType == SakugaEngine.Global.HitboxType.HURTBOX)
		{
			int k = NetsuHurtScale();
			if (k != 1000)
			{
				center.Y = center.Y * k / 1000;
				size.Y = size.Y * k / 1000;
			}
			if (ds != 1000)
			{
				center.X = center.X * ds / 1000;
				size.X = size.X * ds / 1000;
			}
			return;
		}
		if (ds != 1000)
		{
			center = center * ds / 1000;
			size = size * ds / 1000;
		}
		if (el.HitboxType != SakugaEngine.Global.HitboxType.HITBOX)
		{
			return;
		}
		if (!el.NetsuKeepHeight)
		{
			int top = center.Y + size.Y / 2;
			int bottom = center.Y - size.Y / 2;
			if (bottom > 0 && top > 0)
			{
				center.Y = top / 2;
				size.Y = top;
			}
		}
	}

	public HitboxState GetCurrentHitboxSettings()
	{
		FighterState State = _owner.StateManager.GetCurrentState();
		if (State.AnimationData == null)
		{
			return null;
		}
		if (State.AnimationData.Hitboxes == null || State.AnimationData.Hitboxes.Length == 0)
		{
			return null;
		}
		if (State.AnimationData.Hitboxes.Length == 1)
		{
			return State.AnimationData.Hitboxes[0];
		}
		int anim = 0;
		for (int i = 0; i < State.AnimationData.Hitboxes.Length; i++)
		{
			int nextFrame = ((i == State.AnimationData.Hitboxes.Length - 1) ? int.MaxValue : (State.AnimationData.Hitboxes[i + 1].AtFrame - 1));
			if (_owner.StateManager.CurrentStateFrame >= State.AnimationData.Hitboxes[i].AtFrame && _owner.StateManager.CurrentStateFrame <= nextFrame)
			{
				anim = i;
			}
		}
		return State.AnimationData.Hitboxes[anim];
	}
}
