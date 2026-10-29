using Godot;
using MessagePack;
using SakugaEngine.GameState;
using SakugaEngine.Global;

namespace SakugaEngine;

[GlobalClass]
public partial class SakugaVFX : SakugaNode
{
	private SakugaActor _master;

	[ExportCategory("Settings")]
	[Export(PropertyHint.None, "")]
	private int Duration;

	[Export(PropertyHint.None, "")]
	private AnimationPlayer Player;

	[Export(PropertyHint.None, "")]
	private Node3D Graphics;

	[Export(PropertyHint.None, "")]
	private string AnimationName;

	[Export(PropertyHint.None, "")]
	private SoundQueue Sound;

	public bool AttachedToOwner;

	public Vector2I FixedPosition;

	public int Frame;

	public int Side;

	private SakugaVFX actor;

	private SakugaVFXState State;

	// Oct 25: Play(AnimationName) made a new StringName for every pooled effect every frame (garbage for the
	// collector, whose pauses were hitches); and effects that aren't showing don't need posing at all.
	private StringName _netsuAnim;

	public void SetMaster(SakugaActor newMaster)
	{
		_master = newMaster;
	}

	public SakugaActor GetMaster()
	{
		return _master;
	}

	public override void Render()
	{
		Graphics.Visible = IsActive;
		if (!IsActive)
		{
			return;
		}
		Vector2I pos = FixedPosition;
		if (AttachedToOwner)
		{
			pos = _master.Body.FixedPosition + new Vector2I(FixedPosition.X, FixedPosition.Y);
		}
		Graphics.GlobalPosition = GlobalFunctions.ToScaledVector3(pos);
		Graphics.GlobalRotation = Vector3.Zero;
		Graphics.Scale = new Vector3(Side, 1f, 1f);
		_netsuAnim ??= new StringName(AnimationName);
		Player.Play(_netsuAnim);
		Player.Seek((float)(Duration - Frame) / 60f, update: true);
	}

	public override void Initialize()
	{
		base.Initialize();
		actor = this;
		FixedPosition = Vector2I.Zero;
		Side = 0;
		Frame = -1;
	}

	public void Reset()
	{
		IsActive = StartActive;
		FixedPosition = Vector2I.Zero;
		Side = 0;
		Frame = -1;
	}

	public void Spawn(Vector2I origin, int side, bool attached)
	{
		AttachedToOwner = attached;
		FixedPosition = origin;
		Side = side;
		Frame = Duration;
		if (AttachedToOwner)
		{
			FixedPosition -= new Vector2I(_master.Body.FixedPosition.X, _master.Body.FixedPosition.Y);
		}
		if (Sound != null)
		{
			Sound.SimpleQueueSound();
		}
		IsActive = true;
	}

	public override void LateTick()
	{
		if (IsActive)
		{
			Frame--;
			if (Frame < 0)
			{
				IsActive = false;
			}
		}
	}

	public override byte[] GetStateData()
	{
		State.GetStateData(ref actor);
		return MessagePackSerializer.Serialize(State);
	}

	public override void SetStateData(byte[] stateBuffer)
	{
		State = MessagePackSerializer.Deserialize<SakugaVFXState>(stateBuffer);
		State.SetStateData(ref actor);
	}
}
