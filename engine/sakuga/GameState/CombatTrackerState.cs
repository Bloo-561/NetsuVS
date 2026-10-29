using MessagePack;

namespace SakugaEngine.GameState;

[MessagePackObject(false)]
public struct CombatTrackerState
{
	[Key(0)]
	public int HitCombo;

	[Key(1)]
	public int LastDamage;

	[Key(2)]
	public int CurrentCombo;

	[Key(3)]
	public int HighestCombo;

	[Key(4)]
	public int TotalFrames;

	[Key(5)]
	public int FrameData;

	[Key(6)]
	public int FrameAdvantage;

	[Key(7)]
	public int HitFrame;

	[Key(8)]
	public int StunAtHit;

	[Key(9)]
	public int LastHitType;

	[Key(10)]
	public bool invalidHit;

	public void GetStateData(ref CombatTracker reference)
	{
		if (reference != null)
		{
			HitCombo = reference.HitCombo;
			LastDamage = reference.LastDamage;
			CurrentCombo = reference.CurrentCombo;
			HighestCombo = reference.HighestCombo;
			TotalFrames = reference.TotalFrames;
			FrameData = reference.FrameData;
			FrameAdvantage = reference.FrameAdvantage;
			HitFrame = reference.HitFrame;
			StunAtHit = reference.StunAtHit;
			LastHitType = reference.LastHitType;
			invalidHit = reference.invalidHit;
		}
	}

	public void SetStateData(ref CombatTracker reference)
	{
		if (reference != null)
		{
			reference.HitCombo = HitCombo;
			reference.LastDamage = LastDamage;
			reference.CurrentCombo = CurrentCombo;
			reference.HighestCombo = HighestCombo;
			reference.TotalFrames = TotalFrames;
			reference.FrameData = FrameData;
			reference.FrameAdvantage = FrameAdvantage;
			reference.HitFrame = HitFrame;
			reference.StunAtHit = StunAtHit;
			reference.LastHitType = LastHitType;
			reference.invalidHit = invalidHit;
		}
	}
}
