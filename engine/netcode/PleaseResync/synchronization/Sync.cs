using System;
using System.Collections.Generic;

namespace PleaseResync;

internal class Sync
{
	public enum SyncState
	{
		SYNCING,
		RUNNING,
		DEVICE_LOST,
		DESYNCED
	}

	private readonly uint _inputSize;

	private readonly Device[] _devices;

	private readonly List<Device> _spectators;

	private TimeSync _timeSync;

	private InputQueue[] _deviceInputs;

	private StateStorage _stateStorage;

	private const int HealthCheckFramesBehind = 10;

	private const byte HealthCheckTime = 30;

	private const byte PingWaitTime = 30;

	private bool _offlinePlay;

	private SyncState _syncState;

	private uint _lastSentChecksum;

	private uint[] rollbackFrames;

	public Sync(Device[] devices, uint inputSize, bool offline, List<Device> spectators = null)
	{
		_devices = devices;
		_inputSize = inputSize;
		_offlinePlay = offline;
		_timeSync = new TimeSync();
		_stateStorage = new StateStorage(8);
		_deviceInputs = new InputQueue[_devices.Length];
		_syncState = SyncState.SYNCING;
		_spectators = spectators ?? new List<Device>();
		rollbackFrames = new uint[16];
	}

	public void AddRemoteInput(uint deviceId, int frame, int advantage, byte[] deviceInput)
	{
		if (_devices[deviceId].RemoteFrame < frame)
		{
			_devices[deviceId].RemoteFrame = frame;
			_devices[deviceId].RemoteFrameAdvantage = advantage;
			_devices[deviceId].SendMessage(new DeviceInputAckMessage
			{
				Frame = (uint)frame
			});
		}
		AddDeviceInput(frame, deviceId, deviceInput);
	}

	public void SetLocalDevice(uint deviceId, uint playerCount, uint frameDelay)
	{
		_deviceInputs[deviceId] = new InputQueue(_inputSize, playerCount, frameDelay);
	}

	public void AddRemoteDevice(uint deviceId, uint playerCount)
	{
		_deviceInputs[deviceId] = new InputQueue(_inputSize, playerCount);
	}

	public void AddSpectatorDevice(uint deviceId)
	{
		_deviceInputs[deviceId] = new InputQueue(_inputSize, 1u);
	}

	public List<SessionAction> AdvanceSync(uint localDeviceId, byte[] deviceInput)
	{
		bool isTimeSynced = _offlinePlay || _timeSync.IsTimeSynced(_devices);
		_syncState = (isTimeSynced ? SyncState.RUNNING : SyncState.SYNCING);
		UpdateSyncFrame();
		List<SessionAction> actions = new List<SessionAction>();
		if (!_offlinePlay)
		{
			if (_timeSync.LocalFrame == 0)
			{
				actions.Add(new SessionSaveGameAction(_timeSync.LocalFrame, _stateStorage));
			}
			if (_timeSync.ShouldRollback())
			{
				actions.Add(new SessionLoadGameAction(_timeSync.SyncFrame, _stateStorage));
				for (int i = _timeSync.SyncFrame + 1; i <= _timeSync.LocalFrame; i++)
				{
					actions.Add(new SessionAdvanceFrameAction(i, GetFrameInput(i).Inputs));
					actions.Add(new SessionSaveGameAction(i, _stateStorage));
				}
				Platform.Log($"Rollback detected from frame {_timeSync.SyncFrame + 1} to frame {_timeSync.LocalFrame} ({RollbackFrames() + 1} frames)");
			}
			PingDevices();
			HealthCheck();
			SendSpectatorInputs();
			if (isTimeSynced)
			{
				_timeSync.LocalFrame++;
				AddLocalInput(localDeviceId, deviceInput);
				SendLocalInputs(localDeviceId);
				actions.Add(new SessionAdvanceFrameAction(_timeSync.LocalFrame, GetFrameInput(_timeSync.LocalFrame).Inputs));
				actions.Add(new SessionSaveGameAction(_timeSync.LocalFrame, _stateStorage));
			}
		}
		else
		{
			_timeSync.LocalFrame++;
			AddLocalInput(localDeviceId, deviceInput);
			actions.Add(new SessionAdvanceFrameAction(_timeSync.LocalFrame, GetFrameInput(_timeSync.LocalFrame).Inputs));
		}
		rollbackFrames[_timeSync.LocalFrame % rollbackFrames.Length] = RollbackFrames();
		return actions;
	}

	private void SendSpectatorInputs()
	{
		if (_spectators.Count == 0)
		{
			return;
		}
		int maxFrame = _timeSync.SyncFrame;
		int minFrame = Math.Max(0, maxFrame - 7);
		int minAck = int.MaxValue;
		foreach (Device spectator in _spectators)
		{
			if (spectator.State == Device.DeviceState.Running)
			{
				minAck = (int)Math.Min(spectator.LastAckedInputFrame, minAck);
			}
		}
		if (minAck != int.MaxValue)
		{
			minFrame = Math.Max(minFrame, minAck);
		}
		List<byte> sendInput = new List<byte>();
		for (int i = minFrame; i <= maxFrame; i++)
		{
			sendInput.AddRange(GetFrameInput(i).Inputs);
		}
		foreach (Device spectator2 in _spectators)
		{
			spectator2.SendMessage(new DeviceInputMessage
			{
				Advantage = 0,
				StartFrame = (uint)minFrame,
				EndFrame = (uint)maxFrame,
				Input = sendInput.ToArray()
			});
		}
	}

	private uint GetAverageRollbackFrames()
	{
		float sumFrames = 0f;
		for (int i = 0; i < rollbackFrames.Length; i++)
		{
			sumFrames += (float)rollbackFrames[i];
		}
		sumFrames /= (float)rollbackFrames.Length;
		return (uint)Math.Round(sumFrames);
	}

	private void HealthCheck()
	{
		SendHealthCheck();
		CheckHealth();
	}

	private void PingDevices()
	{
		if (Frame() % 30 != 1)
		{
			return;
		}
		Device[] devices = _devices;
		foreach (Device device in devices)
		{
			if (device.Type == Device.DeviceType.Remote)
			{
				device.SendMessage(new PingMessage
				{
					PingTime = Platform.GetCurrentTimeMS(),
					Returning = false
				});
			}
		}
	}

	public void LookForDisconnectedDevices()
	{
		if (_syncState == SyncState.DESYNCED)
		{
			return;
		}
		Device[] devices = _devices;
		for (int i = 0; i < devices.Length; i++)
		{
			if (devices[i].State == Device.DeviceState.Disconnected)
			{
				_syncState = SyncState.DEVICE_LOST;
			}
		}
	}

	private void SendLocalInputs(uint localDeviceId)
	{
		if (_devices[localDeviceId].Type == Device.DeviceType.Spectator)
		{
			return;
		}
		Device[] devices = _devices;
		foreach (Device device in devices)
		{
			if (device.Type == Device.DeviceType.Remote)
			{
				uint startingFrame = (uint)_timeSync.SyncFrame;
				uint finalFrame = (uint)(_timeSync.LocalFrame + _deviceInputs[localDeviceId].GetFrameDelay());
				List<byte> combinedInput = new List<byte>();
				for (uint i2 = startingFrame; i2 <= finalFrame; i2++)
				{
					combinedInput.AddRange(GetDeviceInput((int)i2, localDeviceId).Inputs);
				}
				device.SendMessage(new DeviceInputMessage
				{
					StartFrame = startingFrame,
					EndFrame = finalFrame,
					Advantage = _timeSync.LocalFrameAdvantage,
					Input = combinedInput.ToArray()
				});
			}
		}
	}

	private void SendHealthCheck()
	{
		// Netsu (Oct 24): only a frame this side has settled (<= SyncFrame: no rollback can change it any more);
		// with lag over ~10 frames the old LocalFrame - 10 could still be a guess and read as a desync
		int frame = Math.Min(_timeSync.LocalFrame - 10, _timeSync.SyncFrame);
		if (frame <= 0)
		{
			return;
		}
		uint checksum = _stateStorage.GetChecksum(frame);
		if (_lastSentChecksum == checksum || _timeSync.LocalFrame <= 0 || _timeSync.LocalFrame % 30 != 0)
		{
			return;
		}
		Device[] devices = _devices;
		foreach (Device device in devices)
		{
			if (device.Type == Device.DeviceType.Remote)
			{
				device.SendMessage(new HealthCheckMessage
				{
					Frame = frame,
					Checksum = checksum
				});
			}
		}
		_lastSentChecksum = checksum;
	}

	private void CheckHealth()
	{
		Device[] devices = _devices;
		foreach (Device device in devices)
		{
			if (device.Type != Device.DeviceType.Remote)
			{
				continue;
			}
			// Netsu (Oct 24): compare only frames this side has settled too (<= SyncFrame); later ones wait for the
			// next frames, and ones older than the state storage keeps (its slots are reused) are dropped
			var later = new List<(int, uint)>();
			foreach (var health in device.Health)
			{
				if (health.Item1 > _timeSync.SyncFrame)
				{
					if (_timeSync.LocalFrame - health.Item1 < 20)
					{
						later.Add(health);
					}
					continue;
				}
				if (_timeSync.LocalFrame - health.Item1 >= 28)
				{
					continue;
				}
				if (!_stateStorage.CompareChecksums(health.Item1, health.Item2))
				{
					device.State = Device.DeviceState.Disconnected;
					_syncState = SyncState.DESYNCED;
					Platform.Log($"State mismatch found at frame {health.Item1}.({health.Item2} : {_stateStorage.GetChecksum(health.Item1)})", Platform.DebugType.Error);
					break;
				}
			}
			device.Health.Clear();
			device.Health.AddRange(later);
		}
	}

	private void UpdateSyncFrame()
	{
		if (_offlinePlay)
		{
			return;
		}
		int finalFrame = _timeSync.RemoteFrame;
		if (_timeSync.RemoteFrame > _timeSync.LocalFrame)
		{
			finalFrame = _timeSync.LocalFrame;
		}
		bool foundMistake = false;
		int foundFrame = finalFrame;
		for (int i = _timeSync.SyncFrame + 1; i <= finalFrame; i++)
		{
			InputQueue[] deviceInputs = _deviceInputs;
			foreach (InputQueue input in deviceInputs)
			{
				GameInput predInput = input.GetPredictedInput(i);
				if (predInput.Frame == i && input.GetInput(i, predict: false).Frame == i)
				{
					if (!predInput.Equal(input.GetInput(i, predict: false), inputsOnly: true))
					{
						foundFrame = i - 1;
						foundMistake = true;
					}
					input.ResetPrediction(i);
				}
			}
			if (foundMistake)
			{
				break;
			}
		}
		_timeSync.SyncFrame = foundFrame;
	}

	private void AddLocalInput(uint deviceId, byte[] deviceInput)
	{
		AddDeviceInput(_timeSync.LocalFrame, deviceId, deviceInput);
	}

	private void AddDeviceInput(int frame, uint deviceId, byte[] deviceInput)
	{
		GameInput input = new GameInput(frame, _inputSize, _devices[deviceId].PlayerCount);
		input.SetInputs(0u, _devices[deviceId].PlayerCount, deviceInput);
		_deviceInputs[deviceId].AddInput(frame, input);
	}

	private GameInput GetDeviceInput(int frame, uint deviceId)
	{
		return _deviceInputs[deviceId].GetInput(frame);
	}

	public GameInput GetFrameInput(int frame)
	{
		uint playerCount = 0u;
		Device[] devices = _devices;
		foreach (Device device in devices)
		{
			playerCount += device.PlayerCount;
		}
		GameInput input = new GameInput(frame, _inputSize, playerCount);
		uint playerOffset = 0u;
		for (uint i2 = 0u; i2 < _devices.Length; i2++)
		{
			GameInput tmpInput = GetDeviceInput(frame, i2);
			input.SetInputs(playerOffset, _devices[i2].PlayerCount, tmpInput.Inputs);
			playerOffset += _devices[i2].PlayerCount;
		}
		return input;
	}

	public int Frame()
	{
		return _timeSync.LocalFrame;
	}

	/// <summary>Netsu (Oct 25): the last frame that is settled: every player's input for it is in and checked, and
	/// it won't be played again. Player 1's computer streams the frames up to here to the lobby's spectators.</summary>
	public int ConfirmedFrame()
	{
		return _offlinePlay ? _timeSync.LocalFrame : _timeSync.SyncFrame;
	}

	public int RemoteFrame()
	{
		return _timeSync.RemoteFrame;
	}

	public int FramesAhead()
	{
		return _timeSync.LocalFrameAdvantage;
	}

	public int RemoteFramesAhead()
	{
		return _timeSync.RemoteFrameAdvantage;
	}

	public int FrameDifference()
	{
		return _timeSync.FrameAdvantageDifference;
	}

	public uint RollbackFrames()
	{
		return (uint)Math.Max(0, _timeSync.LocalFrame - (_timeSync.SyncFrame + 1));
	}

	public uint AverageRollbackFrames()
	{
		return GetAverageRollbackFrames();
	}

	public SyncState State()
	{
		return _syncState;
	}
}
