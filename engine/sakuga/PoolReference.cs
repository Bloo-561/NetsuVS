using System;

namespace SakugaEngine;

[Serializable]
public struct PoolReference
{
	public string Key;

	public SakugaActor[] Objects;
}
