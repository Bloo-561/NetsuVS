using Godot;
using SakugaEngine.Resources;

namespace SakugaEngine;

[GlobalClass]
public partial class SakugaProrations : Node
{
	public ushort BaseAttack;

	public ushort BaseDefense;

	public ushort CurrentAttack;

	public ushort CurrentDefense;

	public ushort CurrentDamageScaling;

	public ushort CurrentBaseDamageScaling;

	public ushort CurrentCornerDamageScaling;

	public ushort CurrentSameMoveProration;

	public ushort CurrentGravityProration;

	public ushort CurrentHitstunProration;

	public byte GravityDecayFactor;

	public byte HitstunDecayFactor;

	public ushort SelectDamageScaling(bool condition)
	{
		if (!condition)
		{
			return CurrentBaseDamageScaling;
		}
		return CurrentCornerDamageScaling;
	}

	public void Initialize(DataContainer data)
	{
		BaseAttack = data.BaseAttack;
		BaseDefense = data.BaseDefense;
		CurrentAttack = BaseAttack;
		CurrentDefense = BaseDefense;
		ResetProrations();
	}

	public void UpdateDamageScaling(bool condition)
	{
		CurrentDamageScaling = SelectDamageScaling(condition);
	}

	public void RemoveDamageScaling(ushort value)
	{
		// Netsu (Oct 29): harsher combo scaling, tuned in GameManager (NetsuComboScaling*). Only the hits AFTER this one
		// are affected, so a single attack still does its full damage.
		int floor = 15;
		SakugaEngine.Game.GameManager gm = SakugaEngine.Game.GameManager.Instance;
		if (gm != null && value > 0)
		{
			int loss = Mathf.Max(gm.NetsuComboScalingMinLoss, value * gm.NetsuComboScalingPercent / 100);
			value = (ushort)Mathf.Clamp(loss, 0, 100);
		}
		if (gm != null)
		{
			floor = Mathf.Clamp(gm.NetsuComboScalingFloor, 1, 100);
		}
		if (CurrentBaseDamageScaling - value < floor)
		{
			CurrentBaseDamageScaling = (ushort)floor;
		}
		else
		{
			CurrentBaseDamageScaling -= value;
		}
		if (CurrentCornerDamageScaling - value < floor + 5)
		{
			CurrentCornerDamageScaling = (ushort)(floor + 5);
		}
		else
		{
			CurrentCornerDamageScaling -= value;
		}
	}

	public void ResetDamageScaling()
	{
		CurrentBaseDamageScaling = 100;
		CurrentCornerDamageScaling = 120;
	}

	public void ResetProrations()
	{
		ResetDamageScaling();
		CurrentSameMoveProration = 100;
		CurrentGravityProration = 100;
		CurrentHitstunProration = 100;
		GravityDecayFactor = 0;
		HitstunDecayFactor = 0;
	}

	/// <summary>kind: 0 = a normal hit, 1 = an EX move's, 2 = a super's (Oct 29: those two scale less, GameManager).</summary>
	public int CalculateCompleteDamage(int damage, int attackValue, int defenseValue, ushort damageScalingLoss, int kind = 0)
	{
		int damageFactor = attackValue + (defenseValue - 100);
		int scaling = CurrentDamageScaling;
		SakugaEngine.Game.GameManager gm = SakugaEngine.Game.GameManager.Instance;
		if (kind > 0 && gm != null && scaling < 100)
		{
			int ignore = kind == 2 ? gm.NetsuSuperScalingIgnorePercent : gm.NetsuExScalingIgnorePercent;
			int minimum = kind == 2 ? gm.NetsuSuperScalingMinimum : gm.NetsuExScalingMinimum;
			scaling += (100 - scaling) * Mathf.Clamp(ignore, 0, 100) / 100;
			scaling = Mathf.Max(scaling, Mathf.Min(minimum, 100));
		}
		int num = damage * scaling / 100 * damageFactor / 100;
		if (num > 0)
		{
			RemoveDamageScaling(damageScalingLoss);
		}
		return num;
	}
}
