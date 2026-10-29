using MessagePack;

namespace SakugaEngine.GameState;

[MessagePackObject(false)]
public struct SakugaVFXState
{
	[Key(0)]
	public bool IsActive;

	[Key(1)]
	public bool AttachedToOwner;

	[Key(2)]
	public Vector2IState FixedPosition;

	[Key(3)]
	public int Frame;

	[Key(4)]
	public int Side;

	public void GetStateData(ref SakugaVFX reference)
	{
		if (reference != null)
		{
			IsActive = reference.IsActive;
			AttachedToOwner = reference.AttachedToOwner;
			FixedPosition.GetStateData(ref reference.FixedPosition);
			Frame = reference.Frame;
			Side = reference.Side;
		}
	}

	public void SetStateData(ref SakugaVFX reference)
	{
		if (reference != null)
		{
			reference.IsActive = IsActive;
			reference.AttachedToOwner = AttachedToOwner;
			FixedPosition.SetStateData(ref reference.FixedPosition);
			reference.Frame = Frame;
			reference.Side = Side;
		}
	}
}
