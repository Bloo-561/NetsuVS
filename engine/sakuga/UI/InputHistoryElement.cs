using Godot;
using SakugaEngine.Global;

namespace SakugaEngine.UI;

public partial class InputHistoryElement : Control
{
	public Sprite2D directional;

	public Sprite2D button_A;

	public Sprite2D button_B;

	public Sprite2D button_C;

	public Sprite2D button_D;

	public Label frames;

	public bool set;

	private int A_Standard;

	private int B_Standard;

	private int C_Standard;

	private int D_Standard;

	public override void _Ready()
	{
		directional = GetNode<Sprite2D>("Dir");
		button_A = GetNode<Sprite2D>("A");
		button_B = GetNode<Sprite2D>("B");
		button_C = GetNode<Sprite2D>("C");
		button_D = GetNode<Sprite2D>("D");
		frames = GetNode<Label>("Frames");
		A_Standard = button_A.Frame;
		B_Standard = button_B.Frame;
		C_Standard = button_C.Frame;
		D_Standard = button_D.Frame;
	}

	public void SetHistory(InputRegistry reg)
	{
		int dir = 0;
		int h = (((reg.rawInput & PlayerInputs.RIGHT) != PlayerInputs.NEUTRAL) ? 1 : (((reg.rawInput & PlayerInputs.LEFT) != PlayerInputs.NEUTRAL) ? (-1) : 0));
		int v = (((reg.rawInput & PlayerInputs.DOWN) != PlayerInputs.NEUTRAL) ? (-1) : (((reg.rawInput & PlayerInputs.UP) != PlayerInputs.NEUTRAL) ? 1 : 0));
		if (h < 0 && v < 0)
		{
			dir = 0;
		}
		else if (h == 0 && v < 0)
		{
			dir = 1;
		}
		else if (h > 0 && v < 0)
		{
			dir = 2;
		}
		else if (h < 0 && v == 0)
		{
			dir = 3;
		}
		else if (h == 0 && v == 0)
		{
			dir = 4;
		}
		else if (h > 0 && v == 0)
		{
			dir = 5;
		}
		else if (h < 0 && v > 0)
		{
			dir = 6;
		}
		else if (h == 0 && v > 0)
		{
			dir = 7;
		}
		else if (h > 0 && v > 0)
		{
			dir = 8;
		}
		bool b_a = (reg.rawInput & PlayerInputs.FACE_A) != 0;
		bool b_b = (reg.rawInput & PlayerInputs.FACE_B) != 0;
		bool b_c = (reg.rawInput & PlayerInputs.FACE_C) != 0;
		bool b_d = (reg.rawInput & PlayerInputs.FACE_D) != 0;
		directional.Frame = dir;
		button_A.Frame = (b_a ? (A_Standard + 2) : A_Standard);
		button_B.Frame = (b_b ? (B_Standard + 2) : B_Standard);
		button_C.Frame = (b_c ? (C_Standard + 2) : C_Standard);
		button_D.Frame = (b_d ? (D_Standard + 2) : D_Standard);
		if (reg.duration != _shownDuration)   // Oct 25: a new string only when the number changes
		{
			_shownDuration = reg.duration;
			frames.Text = _shownDuration.ToString();
		}
	}

	private int _shownDuration = int.MinValue;

	public void TransferFrom(InputHistoryElement other)
	{
		directional.Frame = other.directional.Frame;
		button_A.Frame = other.button_A.Frame;
		button_B.Frame = other.button_B.Frame;
		button_C.Frame = other.button_C.Frame;
		button_D.Frame = other.button_D.Frame;
		frames.Text = other.frames.Text;
		_shownDuration = other._shownDuration;
	}
}
