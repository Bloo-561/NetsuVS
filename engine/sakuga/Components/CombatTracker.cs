using Godot;
using SakugaEngine.Global;

namespace SakugaEngine;

[GlobalClass]
public partial class CombatTracker : Node
{
	private SakugaActor _owner;

	public int HitCombo;

	public int LastDamage;

	public int CurrentCombo;

	public int HighestCombo;

	public int TotalFrames;

	public int FrameData;

	public int FrameAdvantage;

	public int HitFrame;

	public int StunAtHit;

	public int LastHitType;

	public bool invalidHit;

	public void Initialize(SakugaActor onwer)
	{
		_owner = onwer;
		HitCombo = 0;
		LastDamage = 0;
		CurrentCombo = 0;
		HighestCombo = 0;
		TotalFrames = 0;
		FrameData = 0;
		FrameAdvantage = 0;
		HitFrame = 0;
		StunAtHit = 0;
		LastHitType = 0;
		invalidHit = false;
	}

	public void UpdateTrackers(int damage, int hitFrame, int hitStun, int hitType, bool isInvalid = false, bool isCombo = true)
	{
		if (isInvalid)
		{
			invalidHit = true;
		}
		if (HitCombo == 0)
		{
			CurrentCombo = 0;
		}
		if (isCombo)
		{
			HitCombo++;
		}
		LastDamage = damage;
		CurrentCombo += damage;
		if (CurrentCombo > HighestCombo)
		{
			HighestCombo = CurrentCombo;
		}
		HitFrame = hitFrame;
		StunAtHit = hitStun;
		LastHitType = hitType;
		FrameAdvantage = HitFrame - StunAtHit;
	}

	public void UpdateFrameData()
	{
		int selectFrameOrigin = ((_owner.StateManager.CurrentStateType() == StateType.HIT_REACTION || _owner.StateManager.CurrentStateType() == StateType.BLOCKING) ? ((int)_owner.Hitstun.TimeLeft) : (_owner.StateManager.GetCurrentState().AnimationData.Duration - _owner.StateManager.CurrentStateFrame));
		FrameData = ((_owner.StateManager.CurrentStateType() > StateType.MOVEMENT) ? selectFrameOrigin : 0);
	}

	public void Reset()
	{
		HitCombo = 0;
		invalidHit = false;
	}
}
