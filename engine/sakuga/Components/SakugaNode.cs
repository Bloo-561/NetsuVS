using System;
using Godot;

namespace SakugaEngine;

public partial class SakugaNode : Node
{
	[Export(PropertyHint.None, "")]
	protected bool StartActive;

	public bool IsActive;

	public virtual void Initialize()
	{
		IsActive = StartActive;
	}

	public virtual void PreTick()
	{
	}

	public virtual void Tick()
	{
	}

	public virtual void LateTick()
	{
	}

	public virtual byte[] GetStateData()
	{
		return Array.Empty<byte>();
	}

	public virtual void SetStateData(byte[] stateBuffer)
	{
	}

	public virtual void Render()
	{
	}
}
