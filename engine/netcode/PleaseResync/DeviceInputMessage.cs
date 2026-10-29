using MessagePack;

namespace PleaseResync;

[MessagePackObject(false)]
public class DeviceInputMessage : DeviceMessage
{
	[Key(1)]
	public int Advantage;

	[Key(2)]
	public uint StartFrame;

	[Key(3)]
	public uint EndFrame;

	[Key(4)]
	public byte[] Input;

	public override string ToString()
	{
		return $"{typeof(DeviceInputMessage)}: {new { Advantage, StartFrame, EndFrame, Input }}";
	}
}
