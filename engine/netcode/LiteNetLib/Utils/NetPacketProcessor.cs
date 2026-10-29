using System;
using System.Collections.Generic;
using System.Diagnostics.CodeAnalysis;

namespace LiteNetLib.Utils;

public class NetPacketProcessor
{
	private static class HashCache<T>
	{
		public static readonly ulong Id;

		static HashCache()
		{
			ulong hash = 14695981039346656037uL;
			string typeName = typeof(T).ToString();
			for (int i = 0; i < typeName.Length; i++)
			{
				hash ^= typeName[i];
				hash *= 1099511628211L;
			}
			Id = hash;
		}
	}

	protected delegate void SubscribeDelegate(NetDataReader reader, object userData);

	private readonly NetSerializer _netSerializer;

	private readonly Dictionary<ulong, SubscribeDelegate> _callbacks = new Dictionary<ulong, SubscribeDelegate>();

	public NetPacketProcessor()
	{
		_netSerializer = new NetSerializer();
	}

	public NetPacketProcessor(int maxStringLength)
	{
		_netSerializer = new NetSerializer(maxStringLength);
	}

	protected virtual ulong GetHash<T>()
	{
		return HashCache<T>.Id;
	}

	protected virtual SubscribeDelegate GetCallbackFromData(NetDataReader reader)
	{
		ulong hash = reader.GetULong();
		if (!_callbacks.TryGetValue(hash, out var action))
		{
			throw new ParseException("Undefined packet in NetDataReader");
		}
		return action;
	}

	protected virtual void WriteHash<T>(NetDataWriter writer)
	{
		writer.Put(GetHash<T>());
	}

	public void RegisterNestedType<T>() where T : struct, INetSerializable
	{
		_netSerializer.RegisterNestedType<T>();
	}

	public void RegisterNestedType<T>(Action<NetDataWriter, T> writeDelegate, Func<NetDataReader, T> readDelegate)
	{
		_netSerializer.RegisterNestedType(writeDelegate, readDelegate);
	}

	public void RegisterNestedType<T>(Func<T> constructor) where T : class, INetSerializable
	{
		_netSerializer.RegisterNestedType(constructor);
	}

	public void ReadAllPackets(NetDataReader reader)
	{
		while (reader.AvailableBytes > 0)
		{
			ReadPacket(reader);
		}
	}

	public void ReadAllPackets(NetDataReader reader, object userData)
	{
		while (reader.AvailableBytes > 0)
		{
			ReadPacket(reader, userData);
		}
	}

	public void ReadPacket(NetDataReader reader)
	{
		ReadPacket(reader, null);
	}

	public void Write<[DynamicallyAccessedMembers(DynamicallyAccessedMemberTypes.PublicProperties | DynamicallyAccessedMemberTypes.NonPublicProperties)] T>(NetDataWriter writer, T packet) where T : class, new()
	{
		WriteHash<T>(writer);
		_netSerializer.Serialize(writer, packet);
	}

	public void WriteNetSerializable<T>(NetDataWriter writer, ref T packet) where T : INetSerializable
	{
		WriteHash<T>(writer);
		packet.Serialize(writer);
	}

	public void ReadPacket(NetDataReader reader, object userData)
	{
		GetCallbackFromData(reader)(reader, userData);
	}

	public void Subscribe<[DynamicallyAccessedMembers(DynamicallyAccessedMemberTypes.PublicProperties | DynamicallyAccessedMemberTypes.NonPublicProperties)] T>(Action<T> onReceive, Func<T> packetConstructor) where T : class, new()
	{
		_netSerializer.Register<T>();
		_callbacks[GetHash<T>()] = delegate(NetDataReader reader, object userData)
		{
			T val = packetConstructor();
			_netSerializer.Deserialize(reader, val);
			onReceive(val);
		};
	}

	public void Subscribe<[DynamicallyAccessedMembers(DynamicallyAccessedMemberTypes.PublicProperties | DynamicallyAccessedMemberTypes.NonPublicProperties)] T, TUserData>(Action<T, TUserData> onReceive, Func<T> packetConstructor) where T : class, new()
	{
		_netSerializer.Register<T>();
		_callbacks[GetHash<T>()] = delegate(NetDataReader reader, object userData)
		{
			T val = packetConstructor();
			_netSerializer.Deserialize(reader, val);
			onReceive(val, (TUserData)userData);
		};
	}

	public void SubscribeReusable<[DynamicallyAccessedMembers(DynamicallyAccessedMemberTypes.PublicProperties | DynamicallyAccessedMemberTypes.NonPublicProperties)] T>(Action<T> onReceive) where T : class, new()
	{
		_netSerializer.Register<T>();
		T reference = new T();
		_callbacks[GetHash<T>()] = delegate(NetDataReader reader, object userData)
		{
			_netSerializer.Deserialize(reader, reference);
			onReceive(reference);
		};
	}

	public void SubscribeReusable<[DynamicallyAccessedMembers(DynamicallyAccessedMemberTypes.PublicProperties | DynamicallyAccessedMemberTypes.NonPublicProperties)] T, TUserData>(Action<T, TUserData> onReceive) where T : class, new()
	{
		_netSerializer.Register<T>();
		T reference = new T();
		_callbacks[GetHash<T>()] = delegate(NetDataReader reader, object userData)
		{
			_netSerializer.Deserialize(reader, reference);
			onReceive(reference, (TUserData)userData);
		};
	}

	public void SubscribeNetSerializable<T, TUserData>(Action<T, TUserData> onReceive, Func<T> packetConstructor) where T : INetSerializable
	{
		_callbacks[GetHash<T>()] = delegate(NetDataReader reader, object userData)
		{
			T arg = packetConstructor();
			arg.Deserialize(reader);
			onReceive(arg, (TUserData)userData);
		};
	}

	public void SubscribeNetSerializable<T>(Action<T> onReceive, Func<T> packetConstructor) where T : INetSerializable
	{
		_callbacks[GetHash<T>()] = delegate(NetDataReader reader, object userData)
		{
			T obj = packetConstructor();
			obj.Deserialize(reader);
			onReceive(obj);
		};
	}

	public void SubscribeNetSerializable<T, TUserData>(Action<T, TUserData> onReceive) where T : INetSerializable, new()
	{
		T reference = new T();
		_callbacks[GetHash<T>()] = delegate(NetDataReader reader, object userData)
		{
			reference.Deserialize(reader);
			onReceive(reference, (TUserData)userData);
		};
	}

	public void SubscribeNetSerializable<T>(Action<T> onReceive) where T : INetSerializable, new()
	{
		T reference = new T();
		_callbacks[GetHash<T>()] = delegate(NetDataReader reader, object userData)
		{
			reference.Deserialize(reader);
			onReceive(reference);
		};
	}

	public bool RemoveSubscription<T>()
	{
		return _callbacks.Remove(GetHash<T>());
	}
}
