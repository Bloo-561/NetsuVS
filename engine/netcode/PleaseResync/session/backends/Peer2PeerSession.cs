using System;
using System.Collections.Generic;
using System.Linq;

namespace PleaseResync;

public class Peer2PeerSession : Session
{
	private readonly Device[] _allDevices;

	private List<Device> _spectators;

	private readonly SessionAdapter _sessionAdapter;

	private Sync _sync;

	private Device _localDevice;

	private uint _numSpectators;

	protected internal override Device LocalDevice => _localDevice;

	protected internal override Device[] AllDevices => _allDevices;

	public Peer2PeerSession(uint inputSize, uint deviceCount, uint totalPlayerCount, bool offline, SessionAdapter adapter)
		: base(inputSize, deviceCount, totalPlayerCount, offline)
	{
		_allDevices = new Device[deviceCount];
		_spectators = new List<Device>();
		_sessionAdapter = adapter;
		_sync = new Sync(_allDevices, inputSize, offline, _spectators);
	}

	public override void SetLocalDevice(uint deviceId, uint playerCount, uint frameDelay)
	{
		_localDevice = new Device(this, deviceId, playerCount, Device.DeviceType.Local);
		_allDevices[deviceId] = LocalDevice;
		_sync.SetLocalDevice(deviceId, playerCount, frameDelay);
		if (OfflinePlay)
		{
			_localDevice.State = Device.DeviceState.Running;
		}
	}

	public override void AddRemoteDevice(uint deviceId, uint playerCount, object remoteConfiguration)
	{
		_sessionAdapter.AddRemote(deviceId, remoteConfiguration);
		_allDevices[deviceId] = new Device(this, deviceId, playerCount, Device.DeviceType.Remote);
		_allDevices[deviceId].StartSyncing();
		_sync.AddRemoteDevice(deviceId, playerCount);
	}

	public override void AddSpectatorDevice(object remoteConfiguration)
	{
		uint spectatorId = uint.MaxValue - _numSpectators;
		_sessionAdapter.AddRemote(spectatorId, remoteConfiguration);
		_spectators.Add(new Device(this, spectatorId, 0u, Device.DeviceType.Spectator));
		Platform.Log($"New spectator created with Id: {spectatorId}");
		_spectators.Last().StartSyncing();
		_numSpectators++;
	}

	public override void Poll()
	{
		if (OfflinePlay)
		{
			return;
		}
		if (!IsRunning())
		{
			Device[] allDevices = _allDevices;
			for (int i = 0; i < allDevices.Length; i++)
			{
				allDevices[i].Sync();
			}
			foreach (Device spectator in _spectators)
			{
				spectator.Sync();
			}
		}
		_sync.LookForDisconnectedDevices();
		List<(uint, uint, DeviceMessage)> messages = _sessionAdapter.ReceiveFrom();
		if (messages.Count == 0)
		{
			Device[] allDevices = _allDevices;
			foreach (Device device in allDevices)
			{
				if (device.Type == Device.DeviceType.Remote)
				{
					device.TestConnection();
				}
			}
			{
				foreach (Device spectator2 in _spectators)
				{
					spectator2.TestConnection();
				}
				return;
			}
		}
		foreach (var item in messages)
		{
			uint deviceId = item.Item2;
			DeviceMessage message = item.Item3;
			if (deviceId <= DeviceCount)
			{
				_allDevices[deviceId].HandleMessage(message);
				continue;
			}
			int idx = -1 - (int)deviceId;
			_spectators[idx].HandleMessage(message);
		}
	}

	/// <summary>Netsu (Oct 25): the last settled frame (Sync.ConfirmedFrame): the spectator stream goes up to here.</summary>
	public int ConfirmedFrame()
	{
		return _sync.ConfirmedFrame();
	}

	public override bool IsRunning()
	{
		if (_allDevices.All((Device device) => device.State == Device.DeviceState.Running))
		{
			return _spectators.All((Device device) => device.State != Device.DeviceState.Syncing);
		}
		return false;
	}

	public override List<SessionAction> AdvanceFrame(byte[] localInput)
	{
		Poll();
		return _sync.AdvanceSync(_localDevice.Id, localInput);
	}

	protected internal override uint SendMessageTo(uint deviceId, DeviceMessage message)
	{
		return _sessionAdapter.SendTo(deviceId, message);
	}

	protected internal override void AddRemoteInput(uint deviceId, DeviceInputMessage message)
	{
		if (message == null)
		{
			return;
		}
		uint inputCount = message.EndFrame - message.StartFrame + 1;
		if (inputCount != 0)
		{
			uint inputSize = (uint)(message.Input.Length / inputCount);
			int inputIndex = 0;
			for (uint i = message.StartFrame; i <= message.EndFrame; i++)
			{
				byte[] inputsForFrame = new byte[message.Input.Length / inputCount];
				Array.Copy(message.Input, inputIndex * inputSize, inputsForFrame, 0L, inputSize);
				_sync.AddRemoteInput(deviceId, (int)i, message.Advantage, inputsForFrame);
				inputIndex++;
			}
		}
	}

	public override int Frame()
	{
		return _sync.Frame();
	}

	public override int RemoteFrame()
	{
		return _sync.RemoteFrame();
	}

	public override int FrameAdvantage()
	{
		return _sync.FramesAhead();
	}

	public override int RemoteFrameAdvantage()
	{
		return _sync.FramesAhead();
	}

	public override int FrameAdvantageDifference()
	{
		return _sync.FrameDifference();
	}

	public override uint RollbackFrames()
	{
		return _sync.RollbackFrames();
	}

	public override uint AverageRollbackFrames()
	{
		return _sync.AverageRollbackFrames();
	}

	public override int State()
	{
		return (int)_sync.State();
	}
}
