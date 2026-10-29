using System;
using System.Collections.Generic;
using System.Linq;

namespace PleaseResync;

public class SpectatorSession : Session
{
	public class BroadcastStream
	{
		public readonly uint InputSize;

		private readonly int _initialFrameBuffer;

		private int _currentFrame;

		private int _availableFrame;

		private readonly List<byte[]> _frameInputs;

		public BroadcastStream(int initialBuffer = 30, uint inputSize = 1u)
		{
			InputSize = inputSize;
			_initialFrameBuffer = initialBuffer;
			_currentFrame = 0;
			_availableFrame = -1;
			_frameInputs = new List<byte[]>(_initialFrameBuffer);
		}

		public void AddFrameInput(int frame, byte[] input)
		{
			if (frame == _availableFrame + 1)
			{
				_frameInputs.Add(new byte[InputSize]);
				Array.Copy(input, _frameInputs.Last(), InputSize);
				_availableFrame++;
			}
		}

		public bool GetFrameInput(out int frame, out byte[] input)
		{
			frame = 0;
			input = null;
			if (_availableFrame <= _initialFrameBuffer)
			{
				return false;
			}
			if (_currentFrame > _availableFrame)
			{
				return false;
			}
			frame = _currentFrame;
			input = new byte[InputSize];
			Array.Copy(_frameInputs[_currentFrame], input, InputSize);
			_currentFrame++;
			return true;
		}
	}

	private Device _broadcastDevice;

	private BroadcastStream _broadcastStream;

	private readonly SessionAdapter _sessionAdapter;

	protected internal override Device LocalDevice => null;

	protected internal override Device[] AllDevices
	{
		get
		{
			throw new NotImplementedException();
		}
	}

	public SpectatorSession(uint inputSize, uint playerCount, SessionAdapter adapter, uint frameDelay = 30u)
		: base(inputSize, 1u, playerCount, offline: false)
	{
		_sessionAdapter = adapter;
		_broadcastStream = new BroadcastStream((int)frameDelay, inputSize * playerCount);
	}

	public override void AddRemoteDevice(uint deviceId, uint playerCount, object remoteConfiguration)
	{
		_sessionAdapter.AddRemote(deviceId, remoteConfiguration);
		_broadcastDevice = new Device(this, deviceId, playerCount, Device.DeviceType.Remote);
		_broadcastDevice.StartSyncing();
	}

	public override List<SessionAction> AdvanceFrame(byte[] localInput = null)
	{
		Poll();
		List<SessionAction> actions = new List<SessionAction>();
		if (_broadcastStream.GetFrameInput(out var frame, out var input))
		{
			actions.Add(new SessionAdvanceFrameAction(frame, input));
		}
		return actions;
	}

	public override uint AverageRollbackFrames()
	{
		throw new NotImplementedException();
	}

	public override int Frame()
	{
		throw new NotImplementedException();
	}

	public override int FrameAdvantage()
	{
		throw new NotImplementedException();
	}

	public override int FrameAdvantageDifference()
	{
		throw new NotImplementedException();
	}

	public override bool IsRunning()
	{
		return _broadcastDevice.State == Device.DeviceState.Running;
	}

	public override void Poll()
	{
		if (!IsRunning())
		{
			_broadcastDevice.Sync();
		}
		List<(uint, uint, DeviceMessage)> messages = _sessionAdapter.ReceiveFrom();
		if (messages.Count == 0)
		{
			_broadcastDevice.TestConnection();
			return;
		}
		foreach (var item in messages)
		{
			uint deviceId = item.Item2;
			DeviceMessage message = item.Item3;
			if (deviceId == _broadcastDevice.Id)
			{
				_broadcastDevice.HandleMessage(message);
			}
		}
	}

	public override int RemoteFrame()
	{
		throw new NotImplementedException();
	}

	public override int RemoteFrameAdvantage()
	{
		throw new NotImplementedException();
	}

	public override uint RollbackFrames()
	{
		throw new NotImplementedException();
	}

	public override void SetLocalDevice(uint deviceId, uint playerCount, uint frameDelay)
	{
		throw new NotImplementedException();
	}

	public override int State()
	{
		throw new NotImplementedException();
	}

	protected internal override void AddRemoteInput(uint deviceId, DeviceInputMessage message)
	{
		if (deviceId == _broadcastDevice.Id)
		{
			uint count = message.EndFrame - message.StartFrame + 1;
			int inpSize = (int)_broadcastStream.InputSize;
			for (int i = 0; i < count; i++)
			{
				int newFrame = (int)(i + message.StartFrame);
				_broadcastStream.AddFrameInput(newFrame, message.Input.Skip(i * inpSize).ToArray());
				SendMessageTo(_broadcastDevice.Id, new DeviceInputAckMessage
				{
					Frame = (uint)newFrame
				});
			}
		}
	}

	protected internal override uint SendMessageTo(uint deviceId, DeviceMessage message)
	{
		if (deviceId != _broadcastDevice.Id)
		{
			return 0u;
		}
		return _sessionAdapter.SendTo(deviceId, message);
	}

	public override void AddSpectatorDevice(object remoteConfiguration)
	{
		throw new NotImplementedException();
	}
}
