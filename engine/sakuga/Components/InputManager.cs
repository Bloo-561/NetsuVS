using Godot;
using SakugaEngine.Global;
using SakugaEngine.Resources;

namespace SakugaEngine;

public class InputManager
{
	public InputRegistry[] InputHistory;

	public short hCharge;

	public short vCharge;

	public int CurrentHistory;

	public InputManager()
	{
		InputHistory = new InputRegistry[16];
		hCharge = 0;
		vCharge = 0;
		CurrentHistory = 0;
	}

	// ---------------------------------------------------------------------------------------------
	// Netsu (Oct 24 2026, night): input leniency. Mahou's matcher wants a motion's steps to be the last N
	// changes of the input, each held at most InputBuffer (8) frames, and two buttons pressed on the very same
	// frame. On top of that exact check (kept as it was), a motion also counts when:
	//  - its directions come in order with a little other input in between (2 1 3 6, 2 3 6 9, 41236...),
	//    the first one held as long as you like (crouch, then 236), the button up to NetsuLatePress frames
	//    after the last direction;
	//  - but 6 2 3 6 + button is only a 623 when the first 6 was a short tap (NetsuFreshFirst frames): walking
	//    forward into 236 stays a 236. Pressing the button on the 3 (6 2 3 + P) is a 623 either way.
	// And a press of two or more buttons together may be spread over NetsuButtonWindow frames (B, then C a
	// frame later = B+C). StanceManager lets such a press replace a normal that started from its first button.
	public const int NetsuButtonWindow = 3;   // B and C pressed up to 2 frames apart still count as B+C
	public const int NetsuMotionGap = 6;      // frames of other input allowed between two directions of a motion
	public const int NetsuMotionHold = 12;    // the longest a middle direction (or the last one, before the button) may be held
	public const int NetsuLatePress = 6;      // the button may come this many frames after leaving the last direction
	public const int NetsuFreshFirst = 8;     // ...and then the first direction must have been this short
	public const int NetsuMotionWindow = 10;  // + 8 per direction: the whole motion, from leaving the first direction

	public bool CheckMotionInputs(MotionInputs motion, int side)
	{
		if (motion == null)
		{
			return false;
		}
		if (motion.ValidInputs == null)
		{
			return false;
		}
		if (NetsuExactMotion(motion, side))
		{
			return true;
		}
		if (NetsuSuperJumpMotion(motion, side))
		{
			return true;   // Netsu (Oct 26 c16): super jump = any down, then up (no neutral step, no 6-frame limit)
		}
		for (int i = 0; i < motion.ValidInputs.Length; i++)
		{
			if (motion.ValidInputs[i] != null && NetsuLenientMotion(motion.ValidInputs[i], side, motion.AbsoluteDirection))
			{
				return true;
			}
		}
		return false;
	}

	/// <summary>Netsu (Oct 26 c16, TamaDeez): how long ago (frames) a down may have been held for down-then-up to be a
	/// super jump.</summary>
	public const int NetsuSuperJumpWindow = 14;

	/// <summary>Netsu (Oct 26 c16): a "2 then 8" motion with no button (the super jumps: 28 / 29 / 27) counts when an up
	/// direction was just reached (this input change is at most 3 frames old and up wasn't held before it) and any down
	/// (1, 2 or 3) was held within NetsuSuperJumpWindow frames before it. Mahou's matcher wanted down, NEUTRAL, up as
	/// the last three input changes, each at most 6 frames long, so holding down a little, going straight from 2 to 8, or
	/// rolling through 1 / 3 failed. The up direction still decides neutral / forward / back. Rollback-safe (history).</summary>
	private bool NetsuSuperJumpMotion(MotionInputs motion, int side)
	{
		for (int i = 0; i < motion.ValidInputs.Length; i++)
		{
			InputSequence[] steps = motion.ValidInputs[i]?.Inputs;
			if (steps == null || steps.Length < 2 || steps[0] == null || steps[steps.Length - 1] == null)
			{
				continue;
			}
			InputSequence first = steps[0];
			InputSequence last = steps[steps.Length - 1];
			if (first.Buttons != 0 || last.Buttons != 0)
			{
				continue;
			}
			DirectionalInputs ld = last.Directional;
			DirectionalInputs fd = first.Directional;
			bool lastUp = ld == DirectionalInputs.UP || ld == DirectionalInputs.UP_LEFT || ld == DirectionalInputs.UP_RIGHT;
			bool firstDown = fd == DirectionalInputs.DOWN || fd == DirectionalInputs.DOWN_LEFT || fd == DirectionalInputs.DOWN_RIGHT;
			if (!lastUp || !firstDown)
			{
				continue;
			}
			if (InputHistory[CurrentHistory].duration > 3 || !CheckDirectionalInputs(CurrentHistory, side, ld, ButtonMode.HOLD, motion.AbsoluteDirection))
			{
				continue;
			}
			if ((InputHistory[NetsuPrev(CurrentHistory, 1)].rawInput & PlayerInputs.UP) != 0)
			{
				continue;   // up was already held: not a fresh jump
			}
			int age = InputHistory[CurrentHistory].duration;
			for (int b = 1; b < 16 && age <= NetsuSuperJumpWindow; b++)
			{
				int idx = NetsuPrev(CurrentHistory, b);
				if ((InputHistory[idx].rawInput & PlayerInputs.DOWN) != 0)
				{
					return true;
				}
				age += System.Math.Max(1, (int)InputHistory[idx].duration);
			}
		}
		return false;
	}

	/// <summary>Netsu: the ring buffer index `back` entries before `index`.</summary>
	private static int NetsuPrev(int index, int back)
	{
		int i = (index - back) % 16;
		return i < 0 ? i + 16 : i;
	}

	/// <summary>Netsu: a motion (two or more directions, then a button press) done with some slack; see the
	/// constants above. Pure function of the input history (rollback-safe).</summary>
	private bool NetsuLenientMotion(InputOption option, int side, bool absDirection)
	{
		InputSequence[] steps = option.Inputs;
		if (steps == null || steps.Length < 2)
		{
			return false;
		}
		InputSequence last = steps[steps.Length - 1];
		if (last == null || last.Buttons == 0 || last.ButtonMode != ButtonMode.PRESS)
		{
			return false;
		}
		// Oct 25: the button first (cheap, and most frames nothing is pressed), and the directions on the stack:
		// this runs for every motion move every frame, and a new array each time kept the garbage collector busy
		// (its pauses were small hitches in the fight).
		if (!CheckButtonInputs(CurrentHistory, last.Buttons, ButtonMode.PRESS))
		{
			return false;
		}
		System.Span<DirectionalInputs> req = stackalloc DirectionalInputs[16];
		int n = 0;
		for (int s = 0; s < steps.Length - 1; s++)
		{
			InputSequence st = steps[s];
			if (st == null || st.Buttons != 0)
			{
				return false;   // a button in the middle: not a plain motion
			}
			if (st.Directional == 0)
			{
				continue;       // a neutral gap: optional here
			}
			if (st.DirectionalMode != ButtonMode.HOLD && st.DirectionalMode != ButtonMode.PRESS)
			{
				return false;
			}
			if (n > 0 && req[n - 1] == st.Directional)
			{
				continue;       // "6, then 6 newly pressed" is one direction
			}
			if (n >= 15)
			{
				return false;
			}
			req[n++] = st.Directional;
		}
		if (last.Directional != 0 && (n == 0 || req[n - 1] != last.Directional))
		{
			req[n++] = last.Directional;
		}
		if (n < 2)
		{
			return false;
		}
		int k = n - 1;            // the direction being looked for (from the last one back)
		int idx = CurrentHistory;
		int endAge = 0;           // frames from now back to the last frame of entry idx
		bool inSpan = false;      // inside the run of entries that hold req[k]
		int spanStart = 0, spanEnd = 0;
		int newerStart = 0;       // where the run of req[k + 1] began (age)
		bool latePress = false;
		for (int e = 0; e < 16; e++)
		{
			int dur = InputHistory[idx].duration;
			if (dur < 1)
			{
				dur = 1;
			}
			int startAge = endAge + dur - 1;
			bool match = k >= 0 && CheckDirectionalInputs(idx, side, req[k], ButtonMode.HOLD, absDirection);
			if (inSpan && !match)
			{
				// the run of req[k] ends here: check it, then look for the direction before it in this same entry
				if (!NetsuSpanOk(k, n, spanStart, spanEnd, latePress))
				{
					return false;
				}
				if (k == 0)
				{
					return true;
				}
				newerStart = spanStart;
				k--;
				inSpan = false;
				match = CheckDirectionalInputs(idx, side, req[k], ButtonMode.HOLD, absDirection);
			}
			if (inSpan)
			{
				spanStart = startAge;   // the same direction held on (a button pressed meanwhile splits entries)
				if (k == 0 && spanStart - spanEnd + 1 > NetsuFreshFirst && latePress)
				{
					return false;
				}
			}
			else if (match)
			{
				int gap = k == n - 1 ? endAge : newerStart - endAge - 1;
				if (gap > (k == n - 1 ? NetsuLatePress : NetsuMotionGap))
				{
					return false;
				}
				if (k == n - 1)
				{
					latePress = endAge > 0;
				}
				inSpan = true;
				spanStart = startAge;
				spanEnd = endAge;
			}
			else if (k < n - 1 && newerStart - startAge - 1 > NetsuMotionGap)
			{
				return false;   // too long since the next direction began
			}
			else if (k == n - 1 && endAge > NetsuLatePress)
			{
				return false;
			}
			endAge = startAge + 1;
			idx = NetsuPrev(idx, 1);
		}
		// ran out of history while inside the first direction's run: fine (held since long ago)
		return inSpan && k == 0 && NetsuSpanOk(0, n, spanStart, spanEnd, latePress);
	}

	/// <summary>Netsu: timing rules for one direction's run of a lenient motion (ages in frames before now).</summary>
	private static bool NetsuSpanOk(int k, int n, int spanStart, int spanEnd, bool latePress)
	{
		int held = spanStart - spanEnd + 1;
		if (k == n - 1)
		{
			// the last direction: reached at most NetsuMotionHold frames before the button
			return spanStart <= NetsuMotionHold;
		}
		if (k == 0)
		{
			// the first: any length (crouch, then the motion), unless the button came after the motion ended
			if (latePress && held > NetsuFreshFirst)
			{
				return false;
			}
			return spanEnd <= NetsuMotionWindow + 8 * (n - 1);
		}
		return held <= NetsuMotionHold;
	}

	/// <summary>Mahou's matcher: the last N input changes are exactly the steps of one of the options.</summary>
	private bool NetsuExactMotion(MotionInputs motion, int side)
	{
		bool inputFound = false;
		for (int i = 0; i < motion.ValidInputs.Length; i++)
		{
			int startingInput = CurrentHistory - motion.ValidInputs[i].Inputs.Length + 1;
			if (startingInput < 0)
			{
				startingInput += 16;
			}
			for (int j = 0; j < motion.ValidInputs[i].Inputs.Length; j++)
			{
				int HistoryIndex = (startingInput + j) % 16;
				DirectionalInputs directionals = motion.ValidInputs[i].Inputs[j].Directional;
				ButtonInputs buttons = motion.ValidInputs[i].Inputs[j].Buttons;
				ButtonMode dirMode = motion.ValidInputs[i].Inputs[j].DirectionalMode;
				ButtonMode butMode = motion.ValidInputs[i].Inputs[j].ButtonMode;
				bool num = motion.InputBuffer == 0 || InputHistory[HistoryIndex].duration <= motion.InputBuffer;
				bool validInput = (((int)directionals > 0 && buttons == (ButtonInputs)0) ? CheckDirectionalInputs(HistoryIndex, side, directionals, dirMode, motion.AbsoluteDirection) : ((directionals != 0 || (int)buttons <= 0) ? (CheckDirectionalInputs(HistoryIndex, side, directionals, dirMode, motion.AbsoluteDirection) && CheckButtonInputs(HistoryIndex, buttons, butMode)) : CheckButtonInputs(HistoryIndex, buttons, butMode)));
				bool chargedInput = CheckChargeInputs(HistoryIndex, side, directionals, motion.DirectionalChargeLimit);
				inputFound = (num & validInput) | chargedInput;
				if (!inputFound)
				{
					break;
				}
			}
			if (inputFound)
			{
				break;
			}
		}
		return inputFound;
	}

	public bool CheckInputEnd(MotionInputs motion, int side)
	{
		DirectionalInputs directionals = motion.ValidInputs[0].Inputs[motion.ValidInputs[0].Inputs.Length - 1].Directional;
		ButtonInputs buttons = motion.ValidInputs[0].Inputs[motion.ValidInputs[0].Inputs.Length - 1].Buttons;
		if (!(((int)directionals > 0 && buttons == (ButtonInputs)0) ? (!CheckDirectionalInputs(CurrentHistory, side, directionals, ButtonMode.HOLD, motion.AbsoluteDirection)) : ((directionals != 0 || (int)buttons <= 0) ? (!CheckDirectionalInputs(CurrentHistory, side, directionals, ButtonMode.HOLD, motion.AbsoluteDirection) && !CheckButtonInputs(CurrentHistory, buttons, ButtonMode.HOLD)) : (!CheckButtonInputs(CurrentHistory, buttons, ButtonMode.HOLD)))))
		{
			return false;
		}
		return true;
	}

	public bool CheckDirectionalInputs(int index, int side, DirectionalInputs buttonNumber, ButtonMode buttonMode, bool absDirection)
	{
		PlayerInputs _left = PlayerInputs.LEFT;
		if (side < 0)
		{
			_left = PlayerInputs.RIGHT;
		}
		PlayerInputs _right = PlayerInputs.RIGHT;
		if (side < 0)
		{
			_right = PlayerInputs.LEFT;
		}
		bool left = GetButtonState(_left, index, buttonMode);
		bool right = GetButtonState(_right, index, buttonMode);
		bool up = GetButtonState(PlayerInputs.UP, index, buttonMode);
		bool down = GetButtonState(PlayerInputs.DOWN, index, buttonMode);
		bool absV = !absDirection || (!up && !down);
		bool absH = !absDirection || (!left && !right);
		bool num = buttonMode == ButtonMode.NOT_PRESSED;
		bool canAbsH = num | absH;
		bool canAbsV = num | absV;
		bool neutralDirection = (num ? (down & up & left & right) : (!down && !up && !left && !right));
		if (!((buttonNumber == DirectionalInputs.DOWN) & down & canAbsH) && !((buttonNumber == DirectionalInputs.LEFT) & left & canAbsV) && !((buttonNumber == DirectionalInputs.RIGHT) & right & canAbsV) && !((buttonNumber == DirectionalInputs.UP) & up & canAbsH) && !((buttonNumber == DirectionalInputs.DOWN_LEFT) & down & left) && !((buttonNumber == DirectionalInputs.DOWN_RIGHT) & down & right) && !((buttonNumber == DirectionalInputs.UP_LEFT) & up & left) && !((buttonNumber == DirectionalInputs.UP_RIGHT) & up & right))
		{
			return (buttonNumber == (DirectionalInputs)0) & neutralDirection;
		}
		return true;
	}

	public bool CheckButtonInputs(int index, ButtonInputs buttonNumber, ButtonMode buttonMode)
	{
		if (buttonMode == ButtonMode.PRESS && NetsuButtonCount(buttonNumber) >= 2)
		{
			return NetsuMultiPress(index, buttonNumber);
		}
		bool action_ba = GetButtonState(PlayerInputs.FACE_A, index, buttonMode);
		bool action_bb = GetButtonState(PlayerInputs.FACE_B, index, buttonMode);
		bool action_bc = GetButtonState(PlayerInputs.FACE_C, index, buttonMode);
		bool action_bd = GetButtonState(PlayerInputs.FACE_D, index, buttonMode);
		bool action_be = GetButtonState(PlayerInputs.FACE_E, index, buttonMode);
		bool action_bf = GetButtonState(PlayerInputs.FACE_F, index, buttonMode);
		bool action_bg = GetButtonState(PlayerInputs.FACE_G, index, buttonMode);
		bool action_bh = GetButtonState(PlayerInputs.FACE_H, index, buttonMode);
		bool canA = (int)(buttonNumber & ButtonInputs.FACE_A) > 0;
		bool canB = (int)(buttonNumber & ButtonInputs.FACE_B) > 0;
		bool canC = (int)(buttonNumber & ButtonInputs.FACE_C) > 0;
		bool canD = (int)(buttonNumber & ButtonInputs.FACE_D) > 0;
		bool canE = (int)(buttonNumber & ButtonInputs.FACE_E) > 0;
		bool canF = (int)(buttonNumber & ButtonInputs.FACE_F) > 0;
		bool canG = (int)(buttonNumber & ButtonInputs.FACE_G) > 0;
		bool canH = (int)(buttonNumber & ButtonInputs.FACE_H) > 0;
		if (buttonNumber != 0 || action_ba || action_bb || action_bc || action_bd || action_be || action_bf || action_bg || action_bh)
		{
			if ((!canA || canA == action_ba) && (!canB || canB == action_bb) && (!canC || canC == action_bc) && (!canD || canD == action_bd) && (!canE || canE == action_be) && (!canF || canF == action_bf) && (!canG || canG == action_bg))
			{
				if (canH)
				{
					return canH == action_bh;
				}
				return true;
			}
			return false;
		}
		return true;
	}

	/// <summary>Netsu (Oct 25): how many of A, B, C, S are held right now.</summary>
	public int NetsuHeldButtonCount()
	{
		PlayerInputs raw = InputHistory[CurrentHistory].rawInput;
		int n = 0;
		if ((raw & PlayerInputs.FACE_A) != 0) n++;
		if ((raw & PlayerInputs.FACE_B) != 0) n++;
		if ((raw & PlayerInputs.FACE_C) != 0) n++;
		if ((raw & PlayerInputs.FACE_D) != 0) n++;
		return n;
	}

	/// <summary>Netsu (Oct 28): frames since A, B, C or S was last pressed (1 = this frame; 999 = not in the history).</summary>
	public int NetsuLastButtonPressAge()
	{
		const PlayerInputs buttons = PlayerInputs.FACE_A | PlayerInputs.FACE_B | PlayerInputs.FACE_C | PlayerInputs.FACE_D;
		int age = 0;
		int idx = CurrentHistory;
		for (int e = 0; e < 15; e++)
		{
			age += System.Math.Max(1, (int)InputHistory[idx].duration);
			int prev = NetsuPrev(idx, 1);
			PlayerInputs pressed = InputHistory[idx].rawInput & buttons & ~InputHistory[prev].rawInput;
			if (pressed != 0)
			{
				return age;
			}
			idx = prev;
		}
		return 999;
	}

	public static int NetsuButtonCount(ButtonInputs buttons)
	{
		int n = 0;
		for (int b = (int)buttons; b != 0; b &= b - 1)
		{
			n++;
		}
		return n;
	}

	/// <summary>Netsu: a press of several buttons together, spread over up to NetsuButtonWindow frames: all of
	/// them held at `index`, each pressed at most NetsuButtonWindow - 1 frames before it, and the last of them
	/// pressed exactly at `index` (so it fires once, the moment the combination is complete).</summary>
	private bool NetsuMultiPress(int index, ButtonInputs buttons)
	{
		bool newPress = false;
		for (int bit = 0; bit < 8; bit++)
		{
			ButtonInputs b = (ButtonInputs)(1 << bit);
			if ((buttons & b) == 0)
			{
				continue;
			}
			PlayerInputs p = (PlayerInputs)(0x10 << bit);
			if (!IsBeingPressed(index, p))
			{
				return false;
			}
			if (WasPressed(index, p))
			{
				newPress = true;
				continue;
			}
			// held from before: how long ago was it pressed? (age of the first frame of the run that holds it)
			int age = InputHistory[index].duration - 1;
			int i = index;
			for (int e = 0; e < 15; e++)
			{
				int prev = NetsuPrev(i, 1);
				if ((InputHistory[prev].rawInput & p) == 0)
				{
					break;
				}
				i = prev;
				age += System.Math.Max(1, (int)InputHistory[i].duration);
			}
			if (age >= NetsuButtonWindow)
			{
				return false;
			}
		}
		return newPress && InputHistory[index].duration == 1;
	}

	public bool CheckChargeInputs(int index, int side, DirectionalInputs buttonNumber, int dirCharge)
	{
		if (dirCharge == 0)
		{
			return false;
		}
		bool _left = IsBeingPressed(index, PlayerInputs.LEFT);
		bool _right = IsBeingPressed(index, PlayerInputs.RIGHT);
		bool left = _left;
		if (side < 0)
		{
			left = _right;
		}
		_ = 0;
		bool up = IsBeingPressed(index, PlayerInputs.UP);
		bool down = IsBeingPressed(index, PlayerInputs.DOWN);
		if ((!((buttonNumber == DirectionalInputs.LEFT) & left) || Mathf.Abs(hCharge) < dirCharge) && (!((buttonNumber == DirectionalInputs.DOWN) & down) || Mathf.Abs(vCharge) < dirCharge) && (!((((buttonNumber == DirectionalInputs.DOWN_LEFT) & left) && Mathf.Abs(hCharge) >= dirCharge) & down) || vCharge > -dirCharge))
		{
			if ((((buttonNumber == DirectionalInputs.UP_LEFT) & left) && Mathf.Abs(hCharge) >= dirCharge) & up)
			{
				return vCharge >= dirCharge;
			}
			return false;
		}
		return true;
	}

	public void InsertToHistory(PlayerInputs input)
	{
		if (InputHistory[CurrentHistory].rawInput != input)
		{
			CurrentHistory++;
			if (CurrentHistory >= 16)
			{
				CurrentHistory = 0;
			}
			InputHistory[CurrentHistory].rawInput = input;
			InputHistory[CurrentHistory].duration = 0;
		}
		InputHistory[CurrentHistory].duration++;
		ChargeBuffer();
	}

	public bool IsBeingPressed(int index, PlayerInputs input)
	{
		return (InputHistory[index].rawInput & input) != 0;
	}

	public bool WasBeingPressed(int index, PlayerInputs input)
	{
		int previousInput = index - 1;
		if (previousInput < 0)
		{
			previousInput += 16;
		}
		if ((InputHistory[index].rawInput & input) == 0)
		{
			return (InputHistory[previousInput % 16].rawInput & input) != 0;
		}
		return false;
	}

	public bool WasPressed(int index, PlayerInputs input)
	{
		int previousInput = index - 1;
		if (previousInput < 0)
		{
			previousInput += 16;
		}
		if ((InputHistory[index].rawInput & input) != PlayerInputs.NEUTRAL && (InputHistory[previousInput % 16].rawInput & input) == 0)
		{
			return InputHistory[index].duration == 1;
		}
		return false;
	}

	public bool WasReleased(int index, PlayerInputs input)
	{
		int previousInput = index - 1;
		if (previousInput < 0)
		{
			previousInput += 16;
		}
		if ((InputHistory[index].rawInput & input) == 0 && (InputHistory[previousInput % 16].rawInput & input) != PlayerInputs.NEUTRAL)
		{
			return InputHistory[index].duration == 1;
		}
		return false;
	}

	public bool IsDifferentInputs(int index)
	{
		int previousInput = index - 1;
		if (previousInput < 0)
		{
			previousInput += 16;
		}
		return InputHistory[index].rawInput != InputHistory[previousInput % 16].rawInput;
	}

	public bool InputChanged(int index, PlayerInputs input, bool changedThisFrame = true)
	{
		int previousInput = index - 1;
		if (previousInput < 0)
		{
			previousInput += 16;
		}
		bool num = (InputHistory[index].rawInput & input) != 0;
		bool previousInputCkech = (InputHistory[previousInput % 16].rawInput & input) != 0;
		bool isRecent = changedThisFrame && InputHistory[index].duration <= 1;
		return (num == previousInputCkech) & isRecent;
	}

	public bool FaceButtonsChanged(int index)
	{
		int previousInput = index - 1;
		if (previousInput < 0)
		{
			previousInput += 16;
		}
		bool num = (InputHistory[index].rawInput & PlayerInputs.FACE_A) != 0;
		bool CurB = (InputHistory[index].rawInput & PlayerInputs.FACE_B) != 0;
		bool CurC = (InputHistory[index].rawInput & PlayerInputs.FACE_C) != 0;
		bool CurD = (InputHistory[index].rawInput & PlayerInputs.FACE_D) != 0;
		bool CurE = (InputHistory[index].rawInput & PlayerInputs.FACE_E) != 0;
		bool CurF = (InputHistory[index].rawInput & PlayerInputs.FACE_F) != 0;
		bool CurG = (InputHistory[index].rawInput & PlayerInputs.FACE_G) != 0;
		bool CurH = (InputHistory[index].rawInput & PlayerInputs.FACE_H) != 0;
		bool PrevA = (InputHistory[previousInput % 16].rawInput & PlayerInputs.FACE_A) != 0;
		bool PrevB = (InputHistory[previousInput % 16].rawInput & PlayerInputs.FACE_B) != 0;
		bool PrevC = (InputHistory[previousInput % 16].rawInput & PlayerInputs.FACE_C) != 0;
		bool PrevD = (InputHistory[previousInput % 16].rawInput & PlayerInputs.FACE_D) != 0;
		bool PrevE = (InputHistory[previousInput % 16].rawInput & PlayerInputs.FACE_E) != 0;
		bool PrevF = (InputHistory[previousInput % 16].rawInput & PlayerInputs.FACE_F) != 0;
		bool PrevG = (InputHistory[previousInput % 16].rawInput & PlayerInputs.FACE_G) != 0;
		bool PrevH = (InputHistory[previousInput % 16].rawInput & PlayerInputs.FACE_H) != 0;
		bool isThisFrame = InputHistory[index].duration <= 1;
		return (num != PrevA || CurB != PrevB || CurC != PrevC || CurD != PrevD || CurE != PrevE || CurF != PrevF || CurG != PrevG || CurH != PrevH) & isThisFrame;
	}

	private void ChargeBuffer()
	{
		if (IsBeingPressed(CurrentHistory, PlayerInputs.LEFT))
		{
			if (hCharge > 0)
			{
				hCharge = 0;
			}
			hCharge--;
		}
		else if (IsBeingPressed(CurrentHistory, PlayerInputs.RIGHT))
		{
			if (hCharge < 0)
			{
				hCharge = 0;
			}
			hCharge++;
		}
		else if (hCharge != 0)
		{
			hCharge = 0;
		}
		if (IsBeingPressed(CurrentHistory, PlayerInputs.UP))
		{
			if (vCharge < 0)
			{
				vCharge = 0;
			}
			vCharge++;
		}
		else if (IsBeingPressed(CurrentHistory, PlayerInputs.DOWN))
		{
			if (vCharge > 0)
			{
				vCharge = 0;
			}
			vCharge--;
		}
		else if (vCharge != 0)
		{
			vCharge = 0;
		}
	}

	private bool GetButtonState(PlayerInputs buttonFlag, int index, ButtonMode mode)
	{
		return mode switch
		{
			ButtonMode.PRESS => WasPressed(index, buttonFlag), 
			ButtonMode.HOLD => IsBeingPressed(index, buttonFlag), 
			ButtonMode.RELEASE => WasReleased(index, buttonFlag), 
			ButtonMode.WAS_PRESSED => WasBeingPressed(index, buttonFlag), 
			ButtonMode.NOT_PRESSED => !IsBeingPressed(index, buttonFlag), 
			_ => false, 
		};
	}

	public InputRegistry CurrentInput()
	{
		return InputHistory[CurrentHistory];
	}

	public bool IsNeutral()
	{
		return CurrentInput().IsNull;
	}
}
