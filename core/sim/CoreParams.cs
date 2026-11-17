// Netsu VS new core (Nov 16 2026): every tunable movement number, in one place.
// Units: positions in 1/100 px ("u"), speeds in u per frame, gravity in u per frame per frame, times in frames.
// 1 H = Cecilia's standing height on screen = 500 px = 50000 u. 60 frames = 1 second.
// Pure C#: no Godot types, so the sim compiles and runs headless.
using System;
using System.Collections.Generic;
using System.Reflection;

namespace Netsu.Core;

[AttributeUsage(AttributeTargets.Field)]
public sealed class TuneAttribute : Attribute
{
	public string Group, Label, Unit, Definition;
	public int Min, Max;
	public TuneAttribute(string group, string label, string unit, int min, int max, string definition)
	{
		Group = group; Label = label; Unit = unit; Min = min; Max = max; Definition = definition;
	}
}

public sealed class CoreParams
{
	public const int PX = 100;          // u per pixel
	public const int H = 500 * PX;      // Cecilia's height

	// ---------------------------------------------------------------- ground
	[Tune("Ground", "Walk forward", "px/f", 0, 4000, "Walking speed toward the opponent.")]
	public int WalkFwd = 1100;
	[Tune("Ground", "Walk back", "px/f", 0, 4000, "Walking speed away from the opponent (holding back also blocks).")]
	public int WalkBack = 800;
	[Tune("Ground", "Run start speed", "px/f", 0, 8000, "Speed on the first frame of a run (66).")]
	public int RunStart = 2200;
	[Tune("Ground", "Run acceleration", "px/f²", 0, 1000, "Speed added every frame while the run builds up.")]
	public int RunAccel = 300;
	[Tune("Ground", "Run top speed", "px/f", 0, 8000, "Fastest the run gets while 6 is held.")]
	public int RunMax = 3700;
	[Tune("Ground", "Run minimum", "f", 0, 30, "A tapped 66 still runs at least this many frames.")]
	public int RunMinFrames = 8;
	[Tune("Ground", "Skid brake", "px/f²", 1, 1500, "Speed lost every frame in the skid after letting go of a run. Anything cancels the skid.")]
	public int SkidDecel = 300;
	[Tune("Ground", "Ground friction", "px/f²", 1, 1500, "Speed lost every frame when sliding on the ground with momentum (after landing or out of a run into an attack).")]
	public int GroundFriction = 200;
	[Tune("Ground", "Attack slide friction", "px/f²", 1, 1500, "Speed lost every frame by a ground attack that kept the run's momentum (the sliding 5B).")]
	public int AttackFriction = 150;
	[Tune("Ground", "Back dash speed", "px/f", 0, 6000, "Backward speed of the back dash hop.")]
	public int BackdashSpeed = 2400;
	[Tune("Ground", "Back dash hop", "px/f", 0, 4000, "Upward speed of the back dash hop.")]
	public int BackdashHop = 1200;
	[Tune("Ground", "Back dash gravity", "px/f²", 1, 1000, "Gravity during the back dash hop (lower = longer hop).")]
	public int BackdashGravity = 150;
	[Tune("Ground", "Back dash invincible", "f", 0, 20, "Frames at the start of the back dash that can't be hit (shown, not used until attacks exist).")]
	public int BackdashInvuln = 6;
	[Tune("Ground", "Back dash recovery", "f", 0, 20, "Frames on landing before she can act.")]
	public int BackdashRecovery = 4;
	[Tune("Ground", "Push box half-width", "px", 10, 200, "Half the width of the body box that stops fighters overlapping.")]
	public int PushHalfWidth = 6000;

	// ---------------------------------------------------------------- jumps
	[Tune("Jump", "Prejump", "f", 1, 10, "Frames on the ground between pressing up and leaving the floor (she can still be thrown).")]
	public int PreJump = 4;
	[Tune("Jump", "Jump speed", "px/f", 500, 12000, "Upward speed at take-off. Height = speed² / (2 × gravity).")]
	public int JumpVy = 5800;
	[Tune("Jump", "Gravity", "px/f²", 10, 1000, "Speed lost upward (gained downward) every frame in the air. Same going up and down: a symmetric arc.")]
	public int Gravity = 264;
	[Tune("Jump", "Max fall speed", "px/f", 500, 15000, "Falling never gets faster than this.")]
	public int MaxFall = 7000;
	[Tune("Jump", "Jump forward", "px/f", 0, 4000, "Sideways speed of a forward jump (9).")]
	public int JumpFwdVx = 1000;
	[Tune("Jump", "Jump back", "px/f", 0, 4000, "Sideways speed of a back jump (7).")]
	public int JumpBackVx = 900;
	[Tune("Jump", "Dash jump carry", "%", 0, 150, "Share of the run's speed a jump out of a run keeps (momentum).")]
	public int DashJumpCarry = 90;
	[Tune("Jump", "Air control", "px/f²", 0, 200, "How much holding left/right nudges her sideways speed each frame in the air. 0 = arc locked.")]
	public int AirControlAccel = 30;
	[Tune("Jump", "Air control limit", "px/f", 0, 2000, "The most air control can change her sideways speed from what the jump gave her.")]
	public int AirControlMax = 300;
	[Tune("Jump", "Double jump speed", "px/f", 0, 12000, "Upward speed of the second jump.")]
	public int DoubleJumpVy = 5200;
	[Tune("Jump", "Double jump sideways", "px/f", 0, 4000, "Sideways speed of a forward or back double jump.")]
	public int DoubleJumpVx = 900;
	[Tune("Jump", "Double jump delay", "f", 0, 20, "Frames after take-off before a double jump is allowed.")]
	public int DoubleJumpDelay = 5;
	[Tune("Jump", "Super jump speed", "px/f", 500, 15000, "Upward speed of a super jump (2 then 8).")]
	public int SuperJumpVy = 7100;
	[Tune("Jump", "Super jump sideways", "px/f", 0, 4000, "Sideways speed of a forward or back super jump.")]
	public int SuperJumpVx = 1100;
	[Tune("Jump", "Empty landing", "f", 0, 15, "Frames she can't act after landing from a jump with no attack.")]
	public int LandEmpty = 2;

	// ---------------------------------------------------------------- air actions
	[Tune("Air", "Air actions", "", 0, 4, "Air moves per jump (double jumps and air dashes share these).")]
	public int AirActions = 2;
	[Tune("Air", "Max double jumps", "", 0, 3, "How many of the air actions can be double jumps.")]
	public int MaxAirJumps = 1;
	[Tune("Air", "Max air dashes", "", 0, 3, "How many of the air actions can be air dashes.")]
	public int MaxAirDashes = 1;
	[Tune("Air", "Super jump uses an action", "", 0, 1, "1 = a super jump spends one air action.")]
	public int SuperJumpCostsAction = 1;
	[Tune("Air", "Air dash speed", "px/f", 0, 8000, "Speed of the forward air dash. Gravity is off while it lasts.")]
	public int AirDashSpeed = 4000;
	[Tune("Air", "Air dash length", "f", 1, 40, "Frames the forward air dash lasts.")]
	public int AirDashFrames = 16;
	[Tune("Air", "Air dash carry", "%", 0, 100, "Share of the air dash speed kept after it ends (drift into the fall).")]
	public int AirDashCarry = 50;
	[Tune("Air", "Air dash attack after", "f", 0, 20, "Frames into an air dash before she can attack or act out of it.")]
	public int AirDashActAfter = 5;
	[Tune("Air", "Air back dash speed", "px/f", 0, 8000, "Speed of the backward air dash.")]
	public int AirBackDashSpeed = 3200;
	[Tune("Air", "Air back dash length", "f", 1, 40, "Frames the backward air dash lasts.")]
	public int AirBackDashFrames = 12;
	[Tune("Air", "Air dash min height", "px", 0, 300, "She must be at least this high to air dash (stops dashes along the floor).")]
	public int AirDashMinY = 3000;

	// ---------------------------------------------------------------- attacks (placeholders: no hitboxes yet)
	[Tune("Attacks", "Landing lag A", "f", 0, 20, "Frames she can't act after landing during a j.A.")]
	public int LandLagA = 3;
	[Tune("Attacks", "Landing lag B", "f", 0, 20, "Frames she can't act after landing during a j.B.")]
	public int LandLagB = 4;
	[Tune("Attacks", "Landing lag C", "f", 0, 20, "Frames she can't act after landing during a j.C.")]
	public int LandLagC = 6;

	// ---------------------------------------------------------------- input
	[Tune("Input", "Buffer", "f", 0, 15, "A button or motion pressed this many frames too early still comes out when she can act.")]
	public int Buffer = 6;
	[Tune("Input", "66 window", "f", 4, 25, "Frames allowed between the two taps of 66 / 44.")]
	public int DashWindow = 12;
	[Tune("Input", "Super jump window", "f", 2, 20, "Frames allowed between down and up for a super jump.")]
	public int SuperJumpWindow = 10;

	// ---------------------------------------------------------------- stage
	[Tune("Stage", "Screen width", "px", 1000, 6000, "Width of the area the camera shows. The screen edges are walls for both fighters.")]
	public int ViewWidth = 265000;   // BlazBlue: the screen is about 3 H tall, so about 5.3 H wide
	[Tune("Stage", "Stage width", "screens", 1, 4, "How many screens wide the stage is.")]
	public int StageScreens = 2;

	// attack durations (frames): filled from the animation data by the lab, defaults = her current ones
	public int[] AttackFrames = { 23, 28, 33, 17, 22, 42, 15, 19, 29 };

	public CoreParams Clone()
	{
		var c = (CoreParams)MemberwiseClone();
		c.AttackFrames = (int[])AttackFrames.Clone();
		return c;
	}

	public static IEnumerable<(FieldInfo field, TuneAttribute tune)> Tunables()
	{
		foreach (var f in typeof(CoreParams).GetFields(BindingFlags.Public | BindingFlags.Instance))
		{
			var t = f.GetCustomAttribute<TuneAttribute>();
			if (t != null) yield return (f, t);
		}
	}

	/// <summary>Starting point: estimates inspired by BlazBlue's feel, to be replaced by measured numbers.</summary>
	public static CoreParams Baseline() => new CoreParams();

	/// <summary>The old Netsu movement (Sakuga, after the Nov 13 changes), converted: px/f = units/s ÷ 1650.</summary>
	public static CoreParams OldNetsu()
	{
		var p = new CoreParams();
		p.WalkFwd = 848; p.WalkBack = 667;
		p.RunStart = 1100; p.RunAccel = 850; p.RunMax = 4485; p.RunMinFrames = 9; p.SkidDecel = 727;
		p.JumpVy = 5150; p.Gravity = 263; p.JumpFwdVx = 848; p.JumpBackVx = 788; p.DashJumpCarry = 41;
		p.AirControlAccel = 0; p.AirControlMax = 0;
		p.SuperJumpVy = 5700; p.SuperJumpVx = 970;
		p.AirBackDashSpeed = 2121; p.AirBackDashFrames = 17;
		p.AirActions = 1; p.MaxAirJumps = 0; p.MaxAirDashes = 1;
		p.Buffer = 3;
		return p;
	}
}
