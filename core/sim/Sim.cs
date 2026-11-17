// Netsu VS new core (Nov 16 2026): the deterministic fight simulation (movement only for now).
// Rules:
//  - whole numbers only (no float anywhere), so every machine computes the same frame;
//  - the whole match is one value-type struct (World): saving a frame for rollback is a plain copy;
//  - nothing here knows about Godot, sprites, sound or the camera's look: the view reads World.
using System;

namespace Netsu.Core;

[Flags]
public enum Btn : ushort
{
	None = 0, Up = 1, Down = 2, Left = 4, Right = 8, A = 0x10, B = 0x20, C = 0x40, D = 0x80,
	Dirs = Up | Down | Left | Right, Buttons = A | B | C | D,
}

public enum St : byte
{
	Idle, Crouch, WalkF, WalkB, Run, Skid, BackDash, PreJump, Air, AirDash, AirBackDash, Land, Attack, AirAttack,
}

public enum Ev : byte { None, Jump, SuperJump, Dash, BackDash, AtkA, AtkB, AtkC }

public unsafe struct Fighter
{
	public const int Hist = 32;

	public int X, Y, Vx, Vy;
	public sbyte Facing;           // +1 = facing right
	public sbyte MoveDir;          // direction locked during a run / skid (+1 / -1)
	public St State;
	public int StateFrame;         // frames spent in the current state (0 on its first frame)
	public int AirFrame;           // frames since leaving the ground
	public int AirActionsLeft, AirJumpsLeft, AirDashesLeft;
	public int BaseVx;             // sideways speed the jump gave her (air control is measured from it)
	public int LandLag;            // frames of the landing she's in
	public byte JumpKind;          // 0 normal, 1 super, 2 dash jump, 3 double
	public sbyte JumpDir;          // -1 back, 0 up, +1 forward (relative to facing at take-off)
	public byte Attack;            // 0..8 = 5A 5B 5C 2A 2B 2C j.A j.B j.C
	public Ev Buffered;
	public int BufferTimer;
	public int HistHead;
	public fixed ushort Inputs[Hist];

	public readonly bool Grounded => State != St.Air && State != St.AirDash && State != St.AirBackDash && State != St.AirAttack && State != St.BackDash;

	public ushort In(int framesAgo)
	{
		fixed (ushort* p = Inputs) return p[(HistHead - framesAgo + Hist * 4) % Hist];
	}
}

public struct World
{
	public int Frame;
	public Fighter P1, P2;
	public int CamX, CamY;   // camera centre x, bottom y (u)
}

public static class Sim
{
	public static World NewWorld(CoreParams p)
	{
		var w = new World();
		w.P1 = NewFighter(-60000, 1);
		w.P2 = NewFighter(60000, -1);
		w.CamX = 0; w.CamY = 0;
		return w;
	}

	static Fighter NewFighter(int x, sbyte facing)
	{
		var f = new Fighter { X = x, Facing = facing, MoveDir = facing, State = St.Idle };
		return f;
	}

	public static void Step(ref World w, ushort in1, ushort in2, CoreParams p)
	{
		Record(ref w.P1, in1);
		Record(ref w.P2, in2);
		Parse(ref w.P1, p);
		Parse(ref w.P2, p);
		Think(ref w.P1, w.P2.X, p);
		Think(ref w.P2, w.P1.X, p);
		Move(ref w.P1, p);
		Move(ref w.P2, p);
		Push(ref w, p);
		Walls(ref w, p);
		Camera(ref w, p);
		AutoFace(ref w.P1, w.P2.X);
		AutoFace(ref w.P2, w.P1.X);
		w.Frame++;
	}

	// ------------------------------------------------------------------ input
	static unsafe void Record(ref Fighter f, ushort raw)
	{
		// SOCD: up+down = up, left+right = neutral
		if ((raw & (ushort)Btn.Up) != 0 && (raw & (ushort)Btn.Down) != 0) raw &= unchecked((ushort)~(ushort)Btn.Down);
		if ((raw & (ushort)Btn.Left) != 0 && (raw & (ushort)Btn.Right) != 0) raw &= unchecked((ushort)~(ushort)(Btn.Left | Btn.Right));
		f.HistHead = (f.HistHead + 1) % Fighter.Hist;
		fixed (ushort* p = f.Inputs) p[f.HistHead] = raw;
	}

	/// <summary>Direction relative to facing: 6 = toward where she faces.</summary>
	public static bool Fwd(ushort i, int facing) => facing > 0 ? (i & (ushort)Btn.Right) != 0 : (i & (ushort)Btn.Left) != 0;
	public static bool Back(ushort i, int facing) => facing > 0 ? (i & (ushort)Btn.Left) != 0 : (i & (ushort)Btn.Right) != 0;
	static bool Has(ushort i, Btn b) => (i & (ushort)b) != 0;

	static void Parse(ref Fighter f, CoreParams p)
	{
		ushort now = f.In(0), prev = f.In(1);
		Ev ev = Ev.None;
		// buttons (strongest first)
		if (Has(now, Btn.C) && !Has(prev, Btn.C)) ev = Ev.AtkC;
		else if (Has(now, Btn.B) && !Has(prev, Btn.B)) ev = Ev.AtkB;
		else if (Has(now, Btn.A) && !Has(prev, Btn.A)) ev = Ev.AtkA;
		else if (Has(now, Btn.Up) && !Has(prev, Btn.Up))
		{
			ev = Ev.Jump;
			for (int k = 1; k <= p.SuperJumpWindow; k++)
				if (Has(f.In(k), Btn.Down)) { ev = Ev.SuperJump; break; }
		}
		else
		{
			int face = f.Facing;
			bool fNow = Fwd(now, face) && !Fwd(prev, face);
			bool bNow = Back(now, face) && !Back(prev, face);
			if (fNow && Tapped(ref f, true, p)) ev = Ev.Dash;
			else if (bNow && Tapped(ref f, false, p)) ev = Ev.BackDash;
		}
		if (ev != Ev.None) { f.Buffered = ev; f.BufferTimer = p.Buffer; }
		else if (f.BufferTimer > 0) f.BufferTimer--;
		else f.Buffered = Ev.None;
	}

	/// <summary>66 / 44: the direction was pressed, let go, and pressed again within the window.</summary>
	static bool Tapped(ref Fighter f, bool forward, CoreParams p)
	{
		int face = f.Facing;
		bool released = false;
		for (int k = 1; k <= p.DashWindow; k++)
		{
			ushort i = f.In(k);
			bool d = forward ? Fwd(i, face) : Back(i, face);
			if (!d) released = true;
			else if (released) return true;
		}
		return false;
	}

	static bool Take(ref Fighter f, Ev e)
	{
		if (f.Buffered != e) return false;
		f.Buffered = Ev.None; f.BufferTimer = 0;
		return true;
	}

	static Ev Peek(ref Fighter f) => f.Buffered;

	// ------------------------------------------------------------------ decisions
	static void Enter(ref Fighter f, St s)
	{
		f.State = s; f.StateFrame = 0;
	}

	static void Think(ref Fighter f, int oppX, CoreParams p)
	{
		ushort now = f.In(0);
		int face = f.Facing;
		switch (f.State)
		{
			case St.Idle: case St.Crouch: case St.WalkF: case St.WalkB: case St.Skid:
				GroundFree(ref f, now, p);
				break;
			case St.Run:
				// anything cancels a run; holding 6 keeps it going
				if (TryGroundAction(ref f, now, p, fromRun: true)) break;
				bool hold = Fwd(now, f.MoveDir);
				if (Back(now, f.MoveDir) || Has(now, Btn.Down)) { Enter(ref f, St.Skid); f.StateFrame = 99; break; } // back / down = stop now (block-ready)
				if (!hold && f.StateFrame >= p.RunMinFrames) Enter(ref f, St.Skid);
				break;
			case St.Land:
				if (f.StateFrame >= f.LandLag) GroundFree(ref f, now, p);
				break;
			case St.PreJump:
				if (f.StateFrame >= p.PreJump) TakeOff(ref f, now, p);
				break;
			case St.Air:
				AirFree(ref f, now, p);
				break;
			case St.AirDash: case St.AirBackDash:
				if (f.StateFrame >= p.AirDashActAfter) AirFree(ref f, now, p, fromDash: true);
				int len = f.State == St.AirDash ? p.AirDashFrames : p.AirBackDashFrames;
				if (f.State != St.Air && f.State != St.AirAttack && f.StateFrame >= len)
				{
					f.Vx = f.Vx * p.AirDashCarry / 100; f.Vy = 0; f.BaseVx = f.Vx;
					Enter(ref f, St.Air);
				}
				break;
			case St.Attack:
				if (f.StateFrame >= p.AttackFrames[f.Attack]) { Enter(ref f, St.Idle); GroundFree(ref f, now, p); }
				break;
			case St.AirAttack:
				if (f.StateFrame >= p.AttackFrames[f.Attack]) Enter(ref f, St.Air);
				break;
			case St.BackDash:
				break;
		}
	}

	static void GroundFree(ref Fighter f, ushort now, CoreParams p)
	{
		if (TryGroundAction(ref f, now, p, fromRun: false)) return;
		int face = f.Facing;
		St want;
		if (Has(now, Btn.Down)) want = St.Crouch;
		else if (Fwd(now, face)) want = St.WalkF;
		else if (Back(now, face)) want = St.WalkB;
		else want = St.Idle;
		if (f.State == St.Skid && want != St.Crouch && want != St.WalkB && Math.Abs(f.Vx) > 0) return; // skid plays out unless cancelled
		if (f.State == St.Land && f.StateFrame < f.LandLag) return;
		if (f.State != want) Enter(ref f, want);
	}

	static bool TryGroundAction(ref Fighter f, ushort now, CoreParams p, bool fromRun)
	{
		Ev e = Peek(ref f);
		switch (e)
		{
			case Ev.AtkA: case Ev.AtkB: case Ev.AtkC:
				Take(ref f, e);
				int k = e - Ev.AtkA;
				f.Attack = (byte)(Has(now, Btn.Down) ? 3 + k : k);
				Enter(ref f, St.Attack);   // keeps f.Vx: the sliding 5B
				return true;
			case Ev.SuperJump: case Ev.Jump:
				Take(ref f, e);
				f.JumpKind = (byte)(e == Ev.SuperJump ? 1 : (fromRun || (f.State == St.Skid && f.StateFrame < 4) ? 2 : 0));
				Enter(ref f, St.PreJump);
				return true;
			case Ev.BackDash:
				Take(ref f, e);
				f.Vx = -f.Facing * p.BackdashSpeed; f.Vy = p.BackdashHop;
				Enter(ref f, St.BackDash);
				return true;
			case Ev.Dash:
				if (fromRun) return false;
				Take(ref f, e);
				f.MoveDir = f.Facing;
				f.Vx = f.Facing * Math.Max(p.RunStart, Math.Abs(f.Vx));
				Enter(ref f, St.Run);
				return true;
		}
		return false;
	}

	static void TakeOff(ref Fighter f, ushort now, CoreParams p)
	{
		int face = f.Facing;
		sbyte dir = (sbyte)(Fwd(now, face) ? 1 : Back(now, face) ? -1 : 0);
		f.JumpDir = dir;
		f.AirActionsLeft = p.AirActions; f.AirJumpsLeft = p.MaxAirJumps; f.AirDashesLeft = p.MaxAirDashes;
		if (f.JumpKind == 1)
		{
			f.Vy = p.SuperJumpVy;
			f.Vx = dir * face * p.SuperJumpVx;
			if (p.SuperJumpCostsAction > 0) f.AirActionsLeft = Math.Max(0, f.AirActionsLeft - 1);
		}
		else
		{
			f.Vy = p.JumpVy;
			if (f.JumpKind == 2 && dir >= 0)
				f.Vx = Math.Max(Math.Abs(f.Vx) * p.DashJumpCarry / 100, p.JumpFwdVx) * f.MoveDir;   // momentum carries
			else
			{
				f.JumpKind = 0;
				f.Vx = dir > 0 ? face * p.JumpFwdVx : dir < 0 ? -face * p.JumpBackVx : 0;
			}
		}
		f.BaseVx = f.Vx;
		f.AirFrame = 0;
		Enter(ref f, St.Air);
	}

	static void AirFree(ref Fighter f, ushort now, CoreParams p, bool fromDash = false)
	{
		Ev e = Peek(ref f);
		int face = f.Facing;
		switch (e)
		{
			case Ev.AtkA: case Ev.AtkB: case Ev.AtkC:
				Take(ref f, e);
				f.Attack = (byte)(6 + (e - Ev.AtkA));
				if (fromDash) { f.Vx = f.Vx * p.AirDashCarry / 100; f.BaseVx = f.Vx; }
				Enter(ref f, St.AirAttack);
				return;
			case Ev.Jump: case Ev.SuperJump:
				if (f.AirFrame < p.DoubleJumpDelay || f.AirActionsLeft <= 0 || f.AirJumpsLeft <= 0) return;
				Take(ref f, e);
				f.AirActionsLeft--; f.AirJumpsLeft--;
				sbyte dir = (sbyte)(Fwd(now, face) ? 1 : Back(now, face) ? -1 : 0);
				f.Vy = p.DoubleJumpVy;
				f.Vx = dir * face * p.DoubleJumpVx;
				f.BaseVx = f.Vx; f.JumpDir = dir; f.JumpKind = 3;
				Enter(ref f, St.Air);
				return;
			case Ev.Dash: case Ev.BackDash:
				if (f.Y < p.AirDashMinY || f.AirActionsLeft <= 0 || f.AirDashesLeft <= 0) return;
				Take(ref f, e);
				f.AirActionsLeft--; f.AirDashesLeft--;
				if (e == Ev.Dash) { f.Vx = face * p.AirDashSpeed; Enter(ref f, St.AirDash); }
				else { f.Vx = -face * p.AirBackDashSpeed; Enter(ref f, St.AirBackDash); }
				f.Vy = 0;
				return;
		}
	}

	// ------------------------------------------------------------------ physics
	static void Move(ref Fighter f, CoreParams p)
	{
		ushort now = f.In(0);
		int face = f.Facing;
		switch (f.State)
		{
			case St.Idle: case St.Crouch: case St.Land:
				f.Vx = Toward0(f.Vx, p.GroundFriction);
				break;
			case St.WalkF:
				// momentum from a run or dash jump slides down to walking speed instead of stopping dead
				if (f.Vx * face > p.WalkFwd) f.Vx = Toward0(f.Vx, p.GroundFriction);
				else f.Vx = face * p.WalkFwd;
				break;
			case St.WalkB: f.Vx = -face * p.WalkBack; break;
			case St.Run:
				int sp = Math.Min(Math.Abs(f.Vx) + p.RunAccel, p.RunMax);
				f.Vx = f.MoveDir * sp;
				break;
			case St.Skid:
				f.Vx = Toward0(f.Vx, f.StateFrame >= 99 ? p.SkidDecel * 3 : p.SkidDecel);
				if (f.Vx == 0 && f.State == St.Skid) Enter(ref f, St.Idle);
				break;
			case St.PreJump:
				break;   // keeps run speed for the dash jump
			case St.Attack:
				f.Vx = Toward0(f.Vx, p.AttackFriction);
				break;
			case St.Air: case St.AirAttack:
				if (f.State == St.Air && p.AirControlAccel > 0)
				{
					int want = Fwd(now, face) ? face : Back(now, face) ? -face : 0;
					if (want != 0)
					{
						int nv = f.Vx + want * p.AirControlAccel;
						if (nv > f.BaseVx + p.AirControlMax) nv = f.BaseVx + p.AirControlMax;
						if (nv < f.BaseVx - p.AirControlMax) nv = f.BaseVx - p.AirControlMax;
						f.Vx = nv;
					}
				}
				f.Vy = Math.Max(f.Vy - p.Gravity, -p.MaxFall);
				break;
			case St.BackDash:
				f.Vy = f.Vy - p.BackdashGravity;
				break;
			case St.AirDash: case St.AirBackDash:
				f.Vy = 0;
				break;
		}
		f.X += f.Vx;
		f.Y += f.Vy;
		if (!f.Grounded || f.State == St.BackDash) f.AirFrame++;
		// landing
		if (f.Y <= 0)
		{
			f.Y = 0;
			if (f.State == St.Air || f.State == St.AirAttack || f.State == St.AirDash || f.State == St.AirBackDash || f.State == St.BackDash)
			{
				if (f.Vy <= 0 || f.State == St.AirDash || f.State == St.AirBackDash)
				{
					int lag = f.State switch
					{
						St.AirAttack => f.Attack == 6 ? p.LandLagA : f.Attack == 7 ? p.LandLagB : p.LandLagC,
						St.BackDash => p.BackdashRecovery,
						_ => p.LandEmpty,
					};
					f.Vy = 0;
					f.LandLag = lag;
					Enter(ref f, St.Land);
				}
			}
		}
		f.StateFrame++;
	}

	static int Toward0(int v, int d) => v > 0 ? Math.Max(0, v - d) : Math.Min(0, v + d);

	// ------------------------------------------------------------------ bodies, walls, camera
	static void Push(ref World w, CoreParams p)
	{
		ref Fighter a = ref w.P1; ref Fighter b = ref w.P2;
		// bodies only collide when they overlap vertically (a high jump passes over)
		if (Math.Abs(a.Y - b.Y) >= CoreParams.H * 6 / 10) return;
		int minDist = p.PushHalfWidth * 2;
		int dx = b.X - a.X;
		int dist = Math.Abs(dx);
		if (dist >= minDist) return;
		int side = dx > 0 ? 1 : dx < 0 ? -1 : (a.Facing > 0 ? 1 : -1);
		int overlap = minDist - dist;
		int pa = overlap / 2, pb = overlap - pa;
		a.X -= side * pa;
		b.X += side * pb;
	}

	static void Walls(ref World w, CoreParams p)
	{
		int stageHalf = p.ViewWidth * p.StageScreens / 2;
		int margin = p.PushHalfWidth;
		// the screen is a wall too: keep both inside one screen width
		int span = p.ViewWidth - margin * 2;
		ref Fighter a = ref w.P1; ref Fighter b = ref w.P2;
		int lo = Math.Min(a.X, b.X), hi = Math.Max(a.X, b.X);
		if (hi - lo > span)
		{
			// whoever moved away is held back; split evenly when both did
			int excess = hi - lo - span;
			bool aIsLow = a.X <= b.X;
			ref Fighter low = ref (aIsLow ? ref a : ref b);
			ref Fighter high = ref (aIsLow ? ref b : ref a);
			bool lowAway = low.Vx < 0, highAway = high.Vx > 0;
			if (lowAway && !highAway) low.X += excess;
			else if (highAway && !lowAway) high.X -= excess;
			else { low.X += excess / 2; high.X -= excess - excess / 2; }
		}
		Clamp(ref a, -stageHalf + margin, stageHalf - margin);
		Clamp(ref b, -stageHalf + margin, stageHalf - margin);
	}

	static void Clamp(ref Fighter f, int lo, int hi)
	{
		if (f.X < lo) { f.X = lo; if (f.Vx < 0 && f.Grounded) f.Vx = 0; }
		if (f.X > hi) { f.X = hi; if (f.Vx > 0 && f.Grounded) f.Vx = 0; }
	}

	static void Camera(ref World w, CoreParams p)
	{
		int stageHalf = p.ViewWidth * p.StageScreens / 2;
		int half = p.ViewWidth / 2;
		int mid = (w.P1.X + w.P2.X) / 2;
		w.CamX = Math.Clamp(mid, -stageHalf + half, stageHalf - half);
		// follow the higher fighter once they're above 60% of the screen height
		int viewH = p.ViewWidth * 9 / 16;
		int top = Math.Max(w.P1.Y, w.P2.Y) + CoreParams.H;
		int want = Math.Max(0, top - viewH * 85 / 100);
		w.CamY += (want - w.CamY) / 4;
	}

	static void AutoFace(ref Fighter f, int oppX)
	{
		// she turns only when she's free on the ground (runs keep their direction until let go)
		if (f.State is St.Idle or St.Crouch or St.WalkF or St.WalkB || (f.State == St.Land && f.StateFrame >= f.LandLag))
		{
			if (oppX > f.X + 100) f.Facing = 1;
			else if (oppX < f.X - 100) f.Facing = -1;
		}
	}

	// ------------------------------------------------------------------ rollback helpers
	public static unsafe ulong Checksum(in World w)
	{
		ulong h = 1469598103934665603UL;
		fixed (World* p = &w)
		{
			byte* b = (byte*)p;
			for (int i = 0; i < sizeof(World); i++) { h ^= b[i]; h *= 1099511628211UL; }
		}
		return h;
	}
}
