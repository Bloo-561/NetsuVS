using System.Collections.Generic;

namespace PleaseResync;

public interface SessionAdapter
{
	uint SendTo(uint deviceId, DeviceMessage message);

	List<(uint size, uint deviceId, DeviceMessage message)> ReceiveFrom();

	void AddRemote(uint deviceId, object remoteConfiguration);

	void Close();
}
