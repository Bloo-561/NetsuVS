using Godot;

namespace SakugaEngine.Global;

public static class GlobalFunctions
{
	public static Vector2 ToScaledVector2(Vector2I vector)
	{
		return new Vector2((float)vector.X / 10000f, (float)vector.Y / 10000f);
	}

	public static Vector3 ToScaledVector3(Vector2I vector, float zScale = 0f)
	{
		return new Vector3((float)vector.X / 10000f, (float)vector.Y / 10000f, zScale);
	}

	public static Vector3 ToScaledVector3(Vector3I vector)
	{
		return new Vector3((float)vector.X / 10000f, (float)vector.Y / 10000f, (float)vector.Z / 10000f);
	}

	public static float ToScaledFloat(int value)
	{
		return (float)value / 10000f;
	}

	public static int IntLerp(int from, int to, int numberOfSteps, int currentStep)
	{
		return (to - from) * currentStep / numberOfSteps;
	}

	public static bool IsOnRange(int value, int min, int max)
	{
		if (value >= min)
		{
			return value <= max;
		}
		return false;
	}

	public static Vector2I Distance(Vector2I a, Vector2I b)
	{
		int dx = b.X - a.X;
		int dy = b.Y - a.Y;
		if (b.X < a.X)
		{
			dx = a.X - b.X;
		}
		if (b.Y < a.Y)
		{
			dx = a.Y - b.Y;
		}
		return new Vector2I(dx, dy);
	}

	public static int HorizontalDistance(Vector2I a, Vector2I b)
	{
		int num = a.X - b.X;
		int dy = 0;
		return num * num + dy * dy;
	}

	public static int VerticalDistance(Vector2I a, Vector2I b)
	{
		int dy = a.Y - b.Y;
		return 0 * 0 + dy * dy;
	}

	public static float SineWaveFunction(float amp, float len, int time, float phase)
	{
		return amp * Mathf.Sin(len * ((float)time / 60f) + phase);
	}

	public static string GetPlayerPrefix(int id)
	{
		// NetsuVS: each player has ONE set of actions (p1_..., p2_...) that covers
		// both keyboard and controller (see game/autoloads/controls.gd).
		// Device 0/2 = player 1, device 1/3 = player 2.
		return id switch
		{
			0 => "p1", 
			1 => "p2", 
			2 => "p1", 
			3 => "p2", 
			_ => "general", 
		};
	}
}
