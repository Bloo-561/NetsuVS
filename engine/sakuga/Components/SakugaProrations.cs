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
		if (CurrentBaseDamageScaling - value < 15)
		{
			CurrentBaseDamageScaling = 15;
		}
		else
		{
			CurrentBaseDamageScaling -= value;
		}
		if (CurrentCornerDamageScaling - value < 20)
		{
			CurrentCornerDamageScaling = 20;
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

	public int CalculateCompleteDamage(int damage, int attackValue, int defenseValue, ushort damageScalingLoss)
	{
		int damageFactor = attackValue + (defenseValue - 100);
		int num = damage * CurrentDamageScaling / 100 * damageFactor / 100;
		if (num > 0)
		{
			RemoveDamageScaling(damageScalingLoss);
		}
		return num;
	}
}
