using System;
using System.Collections.Generic;
using System.Net;
using System.Net.NetworkInformation;
using System.Net.Sockets;

namespace LiteNetLib;

public static class NetUtils
{
	private static readonly NetworkSorter NetworkSorter = new NetworkSorter();

	private static readonly List<string> IpList = new List<string>();

	public static IPEndPoint MakeEndPoint(string hostStr, int port)
	{
		return new IPEndPoint(ResolveAddress(hostStr), port);
	}

	public static IPAddress ResolveAddress(string hostStr)
	{
		if (hostStr == "localhost")
		{
			return IPAddress.Loopback;
		}
		if (!IPAddress.TryParse(hostStr, out IPAddress ipAddress))
		{
			if (NetManager.IPv6Support)
			{
				ipAddress = ResolveAddress(hostStr, AddressFamily.InterNetworkV6);
			}
			if (ipAddress == null)
			{
				ipAddress = ResolveAddress(hostStr, AddressFamily.InterNetwork);
			}
		}
		if (ipAddress == null)
		{
			throw new ArgumentException("Invalid address: " + hostStr);
		}
		return ipAddress;
	}

	public static IPAddress ResolveAddress(string hostStr, AddressFamily addressFamily)
	{
		IPAddress[] addressList = Dns.GetHostEntry(hostStr).AddressList;
		foreach (IPAddress ip in addressList)
		{
			if (ip.AddressFamily == addressFamily)
			{
				return ip;
			}
		}
		return null;
	}

	public static List<string> GetLocalIpList(LocalAddrType addrType)
	{
		List<string> list = new List<string>();
		GetLocalIpList(list, addrType);
		return list;
	}

	public static void GetLocalIpList(IList<string> targetList, LocalAddrType addrType)
	{
		bool ipv4 = (addrType & LocalAddrType.IPv4) == LocalAddrType.IPv4;
		bool ipv6 = (addrType & LocalAddrType.IPv6) == LocalAddrType.IPv6;
		try
		{
			NetworkInterface[] allNetworkInterfaces = NetworkInterface.GetAllNetworkInterfaces();
			Array.Sort(allNetworkInterfaces, NetworkSorter);
			NetworkInterface[] array = allNetworkInterfaces;
			foreach (NetworkInterface ni in array)
			{
				if (ni.NetworkInterfaceType == NetworkInterfaceType.Loopback || ni.OperationalStatus != OperationalStatus.Up)
				{
					continue;
				}
				IPInterfaceProperties ipProps = ni.GetIPProperties();
				if (ipProps.GatewayAddresses.Count == 0)
				{
					continue;
				}
				foreach (UnicastIPAddressInformation unicastAddress in ipProps.UnicastAddresses)
				{
					IPAddress address = unicastAddress.Address;
					if ((ipv4 && address.AddressFamily == AddressFamily.InterNetwork) || (ipv6 && address.AddressFamily == AddressFamily.InterNetworkV6))
					{
						targetList.Add(address.ToString());
					}
				}
			}
			if (targetList.Count == 0)
			{
				IPAddress[] addressList = Dns.GetHostEntry(Dns.GetHostName()).AddressList;
				foreach (IPAddress ip in addressList)
				{
					if ((ipv4 && ip.AddressFamily == AddressFamily.InterNetwork) || (ipv6 && ip.AddressFamily == AddressFamily.InterNetworkV6))
					{
						targetList.Add(ip.ToString());
					}
				}
			}
		}
		catch
		{
		}
		if (targetList.Count == 0)
		{
			if (ipv4)
			{
				targetList.Add("127.0.0.1");
			}
			if (ipv6)
			{
				targetList.Add("::1");
			}
		}
	}

	public static string GetLocalIp(LocalAddrType addrType)
	{
		lock (IpList)
		{
			IpList.Clear();
			GetLocalIpList(IpList, addrType);
			return (IpList.Count == 0) ? string.Empty : IpList[0];
		}
	}

	internal static void PrintInterfaceInfos()
	{
		try
		{
			NetworkInterface[] allNetworkInterfaces = NetworkInterface.GetAllNetworkInterfaces();
			for (int i = 0; i < allNetworkInterfaces.Length; i++)
			{
				foreach (UnicastIPAddressInformation ip in allNetworkInterfaces[i].GetIPProperties().UnicastAddresses)
				{
					if (ip.Address.AddressFamily != AddressFamily.InterNetwork)
					{
						_ = ip.Address.AddressFamily;
						_ = 23;
					}
				}
			}
		}
		catch (Exception)
		{
		}
	}

	internal static int RelativeSequenceNumber(int number, int expected)
	{
		return (number - expected + 32768 + 16384) % 32768 - 16384;
	}

	internal static T[] AllocatePinnedUninitializedArray<T>(int count) where T : unmanaged
	{
		return GC.AllocateUninitializedArray<T>(count, pinned: true);
	}
}
