// Netsu VS new core, movement lab (Nov 16 2026): draws a fighter from the old AnimationData files
// (sprites + offsets) without using any Sakuga code: the resources are read as plain properties.
// View only: nothing here touches the simulation.
using System.Collections.Generic;
using Godot;
using Netsu.Core;

namespace Netsu.Lab;

public sealed class LabFrame
{
	public int At;
	public List<(Texture2D tex, Vector2 off, int rot, bool flip)> Layers = new();
}

public sealed class LabAnim
{
	public string Name;
	public int Duration;
	public List<LabFrame> Frames = new();

	public LabFrame At(int f)
	{
		LabFrame cur = Frames.Count > 0 ? Frames[0] : null;
		foreach (var fr in Frames) if (fr.At <= f) cur = fr;
		return cur;
	}

	public static LabAnim Load(string path)
	{
		var res = ResourceLoader.Exists(path) ? GD.Load<Resource>(path) : null;
		if (res == null) return null;
		var a = new LabAnim { Name = path.GetFile().Replace("_AnimData.tres", ""), Duration = (int)res.Get("Duration") };
		var anims = res.Get("Animations").AsGodotArray();
		foreach (var v in anims)
		{
			var s = v.As<Resource>();
			if (s == null) continue;
			var fr = new LabFrame { At = (int)s.Get("AtFrame") };
			foreach (var mv in s.Get("Modifiers").AsGodotArray())
			{
				var m = mv.As<Resource>();
				if (m == null || (bool)m.Get("OnlyOnContact")) continue;
				var tex = m.Get("Sprite").As<Texture2D>();
				if (tex == null) continue;
				fr.Layers.Add((tex, m.Get("Offset").AsVector2(), (int)m.Get("Rotation"), (bool)m.Get("FlipX")));
			}
			a.Frames.Add(fr);
		}
		a.Frames.Sort((x, y) => x.At.CompareTo(y.At));
		return a;
	}
}

/// <summary>Which animation and frame shows for a fighter's state. Keeps a little memory per fighter
/// (view only) so a fall after an air dash doesn't replay the jump.</summary>
public sealed class LabLook
{
	const string Dir = "res://actors/cecilia/AnimationData/";
	readonly Dictionary<string, LabAnim> _anims = new();
	public readonly string[] AttackAnims = { "48_CEC_5A", "49_CEC_5B", "50_CEC_5C", "51_CEC_2A", "52_CEC_2B", "53_CEC_2C", "54_CEC_j5A", "55_CEC_j5B", "56_CEC_j5C" };
	St _last = St.Idle;
	bool _fallOnly;
	int _loopClock;

	public LabAnim Get(string name)
	{
		if (!_anims.TryGetValue(name, out var a)) { a = LabAnim.Load(Dir + name + "_AnimData.tres"); _anims[name] = a; }
		return a;
	}

	public (LabAnim anim, int frame) Pick(in Fighter f)
	{
		_loopClock++;
		if (f.State != St.Air) _fallOnly = false;
		if (f.State == St.Air && (_last == St.AirDash || _last == St.AirBackDash || _last == St.AirAttack)) _fallOnly = true;
		if (f.State == St.Air && f.JumpKind == 3 && f.StateFrame <= 1) _fallOnly = false;   // a double jump plays the jump again
		_last = f.State;
		int sf = f.StateFrame;
		switch (f.State)
		{
			case St.Idle: return Loop("0_CEC_Neutral", _loopClock);
			case St.Crouch: return sf < 12 ? Once("6_CEC_CrouchEnter", sf) : Loop("7_CEC_Crouching", sf);
			case St.WalkF: return Loop("1_CEC_MoveF", sf);
			case St.WalkB: return Loop("2_CEC_MoveB", sf);
			case St.Run:
				var run = Get("9_CEC_DashFw");
				if (run == null) break;
				return (run, sf < 9 ? sf : 9 + (sf - 9) % System.Math.Max(1, run.Duration - 9));
			case St.Skid: return Once("10_CEC_RunStop", System.Math.Min(sf, 8));
			case St.BackDash: return Once("11_CEC_DashBw", sf);
			case St.PreJump: return Once("3_CEC_Jump", 0);
			case St.Air:
				string j = f.JumpDir > 0 ? "3b_CEC_JumpForward" : f.JumpDir < 0 ? "3c_CEC_JumpBackward" : "3_CEC_Jump";
				var ja = Get(j);
				if (!_fallOnly && ja != null && sf + 4 < ja.Duration) return (ja, sf + 4);
				return Loop("4_CEC_Falling", sf);
			case St.AirDash: return Once("12_CEC_AirDashFw", sf);
			case St.AirBackDash: return Once("14_CEC_AirDashBw", sf);
			case St.Land: return Once("5_CEC_Landing", sf);
			case St.Attack: case St.AirAttack: return Once(AttackAnims[f.Attack], sf);
		}
		return Loop("0_CEC_Neutral", _loopClock);
	}

	(LabAnim, int) Loop(string n, int f) { var a = Get(n); return (a, a == null || a.Duration <= 0 ? 0 : f % a.Duration); }
	(LabAnim, int) Once(string n, int f) { var a = Get(n); return (a, a == null ? 0 : System.Math.Min(f, System.Math.Max(0, a.Duration - 1))); }
}
