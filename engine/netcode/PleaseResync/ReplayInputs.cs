using System;

namespace PleaseResync;

public struct ReplayInputs
{
	public byte[] inputs;

	public ReplayInputs()
	{
		inputs = Array.Empty<byte>();
	}

	public ReplayInputs(byte[] i)
	{
		inputs = i;
	}
}
