using System.Collections.Generic;
using System.Net.NetworkInformation;

namespace LiteNetLib;

internal class NetworkSorter : IComparer<NetworkInterface>
{
	public int Compare(NetworkInterface a, NetworkInterface b)
	{
		bool num = a.NetworkInterfaceType == NetworkInterfaceType.Wman || a.NetworkInterfaceType == NetworkInterfaceType.Wwanpp || a.NetworkInterfaceType == NetworkInterfaceType.Wwanpp2;
		bool isCellularB = b.NetworkInterfaceType == NetworkInterfaceType.Wman || b.NetworkInterfaceType == NetworkInterfaceType.Wwanpp || b.NetworkInterfaceType == NetworkInterfaceType.Wwanpp2;
		bool isWifiA = a.NetworkInterfaceType == NetworkInterfaceType.Wireless80211;
		bool isWifiB = b.NetworkInterfaceType == NetworkInterfaceType.Wireless80211;
		bool isEthernetA = a.NetworkInterfaceType == NetworkInterfaceType.Ethernet || a.NetworkInterfaceType == NetworkInterfaceType.Ethernet3Megabit || a.NetworkInterfaceType == NetworkInterfaceType.GigabitEthernet || a.NetworkInterfaceType == NetworkInterfaceType.FastEthernetFx || a.NetworkInterfaceType == NetworkInterfaceType.FastEthernetT;
		bool isEthernetB = b.NetworkInterfaceType == NetworkInterfaceType.Ethernet || b.NetworkInterfaceType == NetworkInterfaceType.Ethernet3Megabit || b.NetworkInterfaceType == NetworkInterfaceType.GigabitEthernet || b.NetworkInterfaceType == NetworkInterfaceType.FastEthernetFx || b.NetworkInterfaceType == NetworkInterfaceType.FastEthernetT;
		bool isOtherA = !num && !isWifiA && !isEthernetA;
		bool isOtherB = !isCellularB && !isWifiB && !isEthernetB;
		int priorityA = (isEthernetA ? 3 : (isWifiA ? 2 : (isOtherA ? 1 : 0)));
		int priorityB = (isEthernetB ? 3 : (isWifiB ? 2 : (isOtherB ? 1 : 0)));
		if (priorityA <= priorityB)
		{
			return (priorityA < priorityB) ? 1 : 0;
		}
		return -1;
	}
}
