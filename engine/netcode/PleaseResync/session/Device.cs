using System;
using System.Collections.Generic;

namespace PleaseResync;

public class Device
{
	public enum DeviceType
	{
		Local,
		Remote,
		Spectator
	}

	public enum DeviceState
	{
		Syncing,
		Running,
		Disconnected
	}

	public readonly uint Id;

	public readonly uint PlayerCount;

	public readonly DeviceType Type;

	public int RemoteFrame;

	public int RemoteFrameAdvantage;

	public uint LastAckedInputFrame;

	public DeviceState State;

	private const uint NUM_SYNC_ROUNDTRIPS = 5u;

	private const uint SYNC_NEXT_RETRY_INTERVAL = 2000u;

	private const uint SYNC_FIRST_RETRY_INTERVAL = 500u;

	private const ushort CONNECTION_TEST_LIMIT = 300;

	private const int PING_ERRROR_MARGIN = 33;

	private ushort connectionTest;

	private readonly Session _session;

	private uint _lastSendTime;

	private uint _syncRoundtripsRemaining;

	private ushort _syncRoundtripsRandomRequest;

	private Queue<DeviceMessageQueueEntry> _sendQueue;

	public List<(int, uint)> Health = new List<(int, uint)>();

	private uint RTT;

	public Device(Session session, uint deviceId, uint playerCount, DeviceType deviceType)
	{
		_session = session;
		_sendQueue = new Queue<DeviceMessageQueueEntry>();
		Id = deviceId;
		Type = deviceType;
		PlayerCount = playerCount;
		State = ((deviceType == DeviceType.Local) ? DeviceState.Running : DeviceState.Syncing);
		RemoteFrame = 0;
		RemoteFrameAdvantage = 0;
	}

	public override string ToString()
	{
		return $"Device {new { Id, PlayerCount }}";
	}

	public void Sync()
	{
		uint now = Platform.GetCurrentTimeMS();
		if (Type != DeviceType.Local)
		{
			uint interval = ((_syncRoundtripsRemaining == 5) ? 500u : 2000u);
			if (_lastSendTime + interval < now)
			{
				_syncRoundtripsRandomRequest = Platform.GetRandomUnsignedShort();
				SendMessage(new DeviceSyncMessage
				{
					DeviceId = Id,
					PlayerCount = PlayerCount,
					RandomRequest = _syncRoundtripsRandomRequest
				});
			}
		}
	}

	public void StartSyncing()
	{
		_syncRoundtripsRemaining = 5u;
		_syncRoundtripsRandomRequest = Platform.GetRandomUnsignedShort();
		SendMessage(new DeviceSyncMessage
		{
			DeviceId = Id,
			PlayerCount = PlayerCount,
			RandomRequest = _syncRoundtripsRandomRequest
		});
	}

	public void FinishedSyncing()
	{
		State = DeviceState.Running;
	}

	public void EndConnection()
	{
		Platform.Log($"Connection lost with Device {Id}: T({Type})");
		State = DeviceState.Disconnected;
	}

	public void SendMessage(DeviceMessage message)
	{
		_lastSendTime = Platform.GetCurrentTimeMS();
		_sendQueue.Enqueue(new DeviceMessageQueueEntry
		{
			Time = _lastSendTime,
			Message = message
		});
		PumpSendQueue();
	}

	public void HandleMessage(DeviceMessage message)
	{
		if (!(message is DeviceSyncMessage syncMessage))
		{
			if (!(message is DeviceSyncConfirmMessage syncConfirmMessage))
			{
				if (!(message is DeviceInputMessage inputMessage))
				{
					if (!(message is DeviceInputAckMessage inputAckMessage))
					{
						if (!(message is HealthCheckMessage healthCheckMessage))
						{
							if (message is PingMessage pingMessage)
							{
								if (!pingMessage.Returning)
								{
									SendMessage(new PingMessage
									{
										PingTime = pingMessage.PingTime,
										Returning = true
									});
								}
								else
								{
									RTT = Platform.GetCurrentTimeMS() - pingMessage.PingTime;
								}
							}
						}
						else
						{
							Health.Add((healthCheckMessage.Frame, healthCheckMessage.Checksum));
						}
					}
					else
					{
						UpdateAckedInputFrame(inputAckMessage);
					}
				}
				else
				{
					_session.AddRemoteInput(Id, inputMessage);
				}
			}
			else if (syncConfirmMessage.RandomResponse == _syncRoundtripsRandomRequest)
			{
				_syncRoundtripsRemaining--;
				if (_syncRoundtripsRemaining != 0)
				{
					_syncRoundtripsRandomRequest = Platform.GetRandomUnsignedShort();
					SendMessage(new DeviceSyncMessage
					{
						DeviceId = Id,
						PlayerCount = PlayerCount,
						RandomRequest = _syncRoundtripsRandomRequest
					});
				}
				else
				{
					FinishedSyncing();
				}
			}
		}
		else
		{
			SendMessage(new DeviceSyncConfirmMessage
			{
				DeviceId = Id,
				PlayerCount = PlayerCount,
				RandomResponse = syncMessage.RandomRequest
			});
		}
		connectionTest = 0;
	}

	public void TestConnection()
	{
		if (State != DeviceState.Disconnected)
		{
			connectionTest++;
			if (connectionTest >= 300)
			{
				EndConnection();
			}
		}
	}

	private void UpdateAckedInputFrame(DeviceInputAckMessage inputAckMessage)
	{
		if (LastAckedInputFrame + 1 == inputAckMessage.Frame)
		{
			LastAckedInputFrame = inputAckMessage.Frame;
		}
	}

	private void PumpSendQueue()
	{
		while (_sendQueue.Count > 0)
		{
			_session.SendMessageTo(Id, _sendQueue.Dequeue().Message);
		}
	}

	public int GetRTT()
	{
		return Math.Max(0, (int)(RTT - 33));
	}
}
