using System;

namespace SakugaEngine;

[Serializable]
public struct VFXPoolReference
{
	public string Key;

	public SakugaVFX[] Objects;
}
