using MessagePack;

namespace SakugaEngine.GameState;

[MessagePackObject(false)]
public struct ProrationsState
{
	[Key(0)]
	public ushort CurrentAttack;

	[Key(1)]
	public ushort CurrentDefense;

	[Key(2)]
	public ushort CurrentDamageScaling;

	[Key(3)]
	public ushort CurrentBaseDamageScaling;

	[Key(4)]
	public ushort CurrentCornerDamageScaling;

	[Key(5)]
	public ushort CurrentSameMoveProration;

	[Key(6)]
	public ushort CurrentGravityProration;

	[Key(7)]
	public ushort CurrentHitstunProration;

	[Key(8)]
	public byte GravityDecayFactor;

	[Key(9)]
	public byte HitstunDecayFactor;

	public void GetStateData(ref SakugaProrations reference)
	{
		if (reference != null)
		{
			CurrentAttack = reference.CurrentAttack;
			CurrentDefense = reference.CurrentDefense;
			CurrentDamageScaling = reference.CurrentDamageScaling;
			CurrentBaseDamageScaling = reference.CurrentBaseDamageScaling;
			CurrentCornerDamageScaling = reference.CurrentCornerDamageScaling;
			CurrentSameMoveProration = reference.CurrentSameMoveProration;
			CurrentGravityProration = reference.CurrentGravityProration;
			CurrentHitstunProration = reference.CurrentHitstunProration;
			GravityDecayFactor = reference.GravityDecayFactor;
			HitstunDecayFactor = reference.HitstunDecayFactor;
		}
	}

	public void SetStateData(ref SakugaProrations reference)
	{
		if (reference != null)
		{
			reference.CurrentAttack = CurrentAttack;
			reference.CurrentDefense = CurrentDefense;
			reference.CurrentDamageScaling = CurrentDamageScaling;
			reference.CurrentBaseDamageScaling = CurrentBaseDamageScaling;
			reference.CurrentCornerDamageScaling = CurrentCornerDamageScaling;
			reference.CurrentSameMoveProration = CurrentSameMoveProration;
			reference.CurrentGravityProration = CurrentGravityProration;
			reference.CurrentHitstunProration = CurrentHitstunProration;
			reference.GravityDecayFactor = GravityDecayFactor;
			reference.HitstunDecayFactor = HitstunDecayFactor;
		}
	}
}
