using System;
using System.Collections.Generic;
using MessagePack.Formatters;
using MessagePack.Internal;
using PleaseResync;
using SakugaEngine;
using SakugaEngine.GameState;
using SakugaEngine.Global;

namespace MessagePack;

internal class GeneratedMessagePackResolver : IFormatterResolver
{
	private static class FormatterCache<T>
	{
		internal static readonly IMessagePackFormatter<T> Formatter;

		static FormatterCache()
		{
			object f = GeneratedMessagePackResolverGetFormatterHelper.GetFormatter(typeof(T));
			if (f != null)
			{
				Formatter = (IMessagePackFormatter<T>)f;
			}
		}
	}

	private static class GeneratedMessagePackResolverGetFormatterHelper
	{
		private static readonly Dictionary<Type, int> closedTypeLookup = new Dictionary<Type, int>(46)
		{
			{
				typeof(byte[][]),
				0
			},
			{
				typeof(HitNotifications[]),
				1
			},
			{
				typeof(HitNotificationPiece[]),
				2
			},
			{
				typeof(CustomVariableState[]),
				3
			},
			{
				typeof(FrameTimerState[]),
				4
			},
			{
				typeof(InputManagerState[]),
				5
			},
			{
				typeof(PlayerInputs[]),
				6
			},
			{
				typeof(CancelCondition),
				7
			},
			{
				typeof(CustomVariableMode),
				8
			},
			{
				typeof(FadeScreenMode),
				9
			},
			{
				typeof(FrameProperties),
				10
			},
			{
				typeof(HitChecker),
				11
			},
			{
				typeof(HitstunType),
				12
			},
			{
				typeof(MatchState),
				13
			},
			{
				typeof(PlayerInputs),
				14
			},
			{
				typeof(WillState),
				15
			},
			{
				typeof(DeviceMessage),
				16
			},
			{
				typeof(DeviceInputAckMessage),
				17
			},
			{
				typeof(DeviceInputMessage),
				18
			},
			{
				typeof(DeviceSyncConfirmMessage),
				19
			},
			{
				typeof(DeviceSyncMessage),
				20
			},
			{
				typeof(HealthCheckMessage),
				21
			},
			{
				typeof(LobbyChatMessage),
				22
			},
			{
				typeof(LobbyGotKicked),
				23
			},
			{
				typeof(LobbyMatchAccepted),
				24
			},
			{
				typeof(LobbyMatchQuit),
				25
			},
			{
				typeof(LobbyMatchRejected),
				26
			},
			{
				typeof(LobbyMatchRequest),
				27
			},
			{
				typeof(PingMessage),
				28
			},
			{
				typeof(HitNotifications),
				29
			},
			{
				typeof(HitNotificationPiece),
				30
			},
			{
				typeof(CombatTrackerState),
				31
			},
			{
				typeof(CustomVariableState),
				32
			},
			{
				typeof(FrameTimerState),
				33
			},
			{
				typeof(GameManagerState),
				34
			},
			{
				typeof(GameMonitorState),
				35
			},
			{
				typeof(InputManagerState),
				36
			},
			{
				typeof(ParametersState),
				37
			},
			{
				typeof(PhysicsBodyState),
				38
			},
			{
				typeof(ProrationsState),
				39
			},
			{
				typeof(SakugaActorState),
				40
			},
			{
				typeof(SakugaVFXState),
				41
			},
			{
				typeof(StanceManagerState),
				42
			},
			{
				typeof(StateManagerState),
				43
			},
			{
				typeof(Vector2IState),
				44
			},
			{
				typeof(Vector3IState),
				45
			}
		};

		internal static object GetFormatter(Type t)
		{
			if (closedTypeLookup.TryGetValue(t, out var closedKey))
			{
				return closedKey switch
				{
					0 => new ArrayFormatter<byte[]>(), 
					1 => new ArrayFormatter<HitNotifications>(), 
					2 => new ArrayFormatter<HitNotificationPiece>(), 
					3 => new ArrayFormatter<CustomVariableState>(), 
					4 => new ArrayFormatter<FrameTimerState>(), 
					5 => new ArrayFormatter<InputManagerState>(), 
					6 => new ArrayFormatter<PlayerInputs>(), 
					7 => new SakugaEngine.Global.CancelConditionFormatter(), 
					8 => new SakugaEngine.Global.CustomVariableModeFormatter(), 
					9 => new SakugaEngine.Global.FadeScreenModeFormatter(), 
					10 => new SakugaEngine.Global.FramePropertiesFormatter(), 
					11 => new SakugaEngine.Global.HitCheckerFormatter(), 
					12 => new SakugaEngine.Global.HitstunTypeFormatter(), 
					13 => new SakugaEngine.Global.MatchStateFormatter(), 
					14 => new SakugaEngine.Global.PlayerInputsFormatter(), 
					15 => new SakugaEngine.Global.WillStateFormatter(), 
					16 => new PleaseResync.DeviceMessageFormatter(), 
					17 => new PleaseResync.DeviceInputAckMessageFormatter(), 
					18 => new PleaseResync.DeviceInputMessageFormatter(), 
					19 => new PleaseResync.DeviceSyncConfirmMessageFormatter(), 
					20 => new PleaseResync.DeviceSyncMessageFormatter(), 
					21 => new PleaseResync.HealthCheckMessageFormatter(), 
					22 => new PleaseResync.LobbyChatMessageFormatter(), 
					23 => new PleaseResync.LobbyGotKickedFormatter(), 
					24 => new PleaseResync.LobbyMatchAcceptedFormatter(), 
					25 => new PleaseResync.LobbyMatchQuitFormatter(), 
					26 => new PleaseResync.LobbyMatchRejectedFormatter(), 
					27 => new PleaseResync.LobbyMatchRequestFormatter(), 
					28 => new PleaseResync.PingMessageFormatter(), 
					29 => new SakugaEngine.HitNotificationsFormatter(), 
					30 => new SakugaEngine.HitNotificationPieceFormatter(), 
					31 => new SakugaEngine.GameState.CombatTrackerStateFormatter(), 
					32 => new SakugaEngine.GameState.CustomVariableStateFormatter(), 
					33 => new SakugaEngine.GameState.FrameTimerStateFormatter(), 
					34 => new SakugaEngine.GameState.GameManagerStateFormatter(), 
					35 => new SakugaEngine.GameState.GameMonitorStateFormatter(), 
					36 => new SakugaEngine.GameState.InputManagerStateFormatter(), 
					37 => new SakugaEngine.GameState.ParametersStateFormatter(), 
					38 => new SakugaEngine.GameState.PhysicsBodyStateFormatter(), 
					39 => new SakugaEngine.GameState.ProrationsStateFormatter(), 
					40 => new SakugaEngine.GameState.SakugaActorStateFormatter(), 
					41 => new SakugaEngine.GameState.SakugaVFXStateFormatter(), 
					42 => new SakugaEngine.GameState.StanceManagerStateFormatter(), 
					43 => new SakugaEngine.GameState.StateManagerStateFormatter(), 
					44 => new SakugaEngine.GameState.Vector2IStateFormatter(), 
					45 => new SakugaEngine.GameState.Vector3IStateFormatter(), 
					_ => null, 
				};
			}
			return null;
		}
	}

	internal class PleaseResync
	{
		internal sealed class DeviceInputAckMessageFormatter : IMessagePackFormatter<DeviceInputAckMessage>, IMessagePackFormatter
		{
			public void Serialize(ref MessagePackWriter writer, DeviceInputAckMessage value, MessagePackSerializerOptions options)
			{
				if (value == null)
				{
					writer.WriteNil();
					return;
				}
				writer.WriteArrayHeader(2);
				writer.Write(value.SequenceNumber);
				writer.Write(value.Frame);
			}

			public DeviceInputAckMessage Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options)
			{
				if (reader.TryReadNil())
				{
					return null;
				}
				options.Security.DepthStep(ref reader);
				int length = reader.ReadArrayHeader();
				DeviceInputAckMessage ____result = new DeviceInputAckMessage();
				for (int i = 0; i < length; i++)
				{
					switch (i)
					{
					case 0:
						____result.SequenceNumber = reader.ReadUInt32();
						break;
					case 1:
						____result.Frame = reader.ReadUInt32();
						break;
					default:
						reader.Skip();
						break;
					}
				}
				reader.Depth--;
				return ____result;
			}
		}

		internal sealed class DeviceInputMessageFormatter : IMessagePackFormatter<DeviceInputMessage>, IMessagePackFormatter
		{
			public void Serialize(ref MessagePackWriter writer, DeviceInputMessage value, MessagePackSerializerOptions options)
			{
				if (value == null)
				{
					writer.WriteNil();
					return;
				}
				writer.WriteArrayHeader(5);
				writer.Write(value.SequenceNumber);
				writer.Write(value.Advantage);
				writer.Write(value.StartFrame);
				writer.Write(value.EndFrame);
				writer.Write(value.Input);
			}

			public DeviceInputMessage Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options)
			{
				if (reader.TryReadNil())
				{
					return null;
				}
				options.Security.DepthStep(ref reader);
				int length = reader.ReadArrayHeader();
				DeviceInputMessage ____result = new DeviceInputMessage();
				for (int i = 0; i < length; i++)
				{
					switch (i)
					{
					case 0:
						____result.SequenceNumber = reader.ReadUInt32();
						break;
					case 1:
						____result.Advantage = reader.ReadInt32();
						break;
					case 2:
						____result.StartFrame = reader.ReadUInt32();
						break;
					case 3:
						____result.EndFrame = reader.ReadUInt32();
						break;
					case 4:
						____result.Input = CodeGenHelpers.GetArrayFromNullableSequence(reader.ReadBytes());
						break;
					default:
						reader.Skip();
						break;
					}
				}
				reader.Depth--;
				return ____result;
			}
		}

		internal sealed class DeviceSyncConfirmMessageFormatter : IMessagePackFormatter<DeviceSyncConfirmMessage>, IMessagePackFormatter
		{
			public void Serialize(ref MessagePackWriter writer, DeviceSyncConfirmMessage value, MessagePackSerializerOptions options)
			{
				if (value == null)
				{
					writer.WriteNil();
					return;
				}
				writer.WriteArrayHeader(4);
				writer.Write(value.SequenceNumber);
				writer.Write(value.DeviceId);
				writer.Write(value.PlayerCount);
				writer.Write(value.RandomResponse);
			}

			public DeviceSyncConfirmMessage Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options)
			{
				if (reader.TryReadNil())
				{
					return null;
				}
				options.Security.DepthStep(ref reader);
				int length = reader.ReadArrayHeader();
				DeviceSyncConfirmMessage ____result = new DeviceSyncConfirmMessage();
				for (int i = 0; i < length; i++)
				{
					switch (i)
					{
					case 0:
						____result.SequenceNumber = reader.ReadUInt32();
						break;
					case 1:
						____result.DeviceId = reader.ReadUInt32();
						break;
					case 2:
						____result.PlayerCount = reader.ReadUInt32();
						break;
					case 3:
						____result.RandomResponse = reader.ReadUInt32();
						break;
					default:
						reader.Skip();
						break;
					}
				}
				reader.Depth--;
				return ____result;
			}
		}

		internal sealed class DeviceSyncMessageFormatter : IMessagePackFormatter<DeviceSyncMessage>, IMessagePackFormatter
		{
			public void Serialize(ref MessagePackWriter writer, DeviceSyncMessage value, MessagePackSerializerOptions options)
			{
				if (value == null)
				{
					writer.WriteNil();
					return;
				}
				writer.WriteArrayHeader(4);
				writer.Write(value.SequenceNumber);
				writer.Write(value.DeviceId);
				writer.Write(value.PlayerCount);
				writer.Write(value.RandomRequest);
			}

			public DeviceSyncMessage Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options)
			{
				if (reader.TryReadNil())
				{
					return null;
				}
				options.Security.DepthStep(ref reader);
				int length = reader.ReadArrayHeader();
				DeviceSyncMessage ____result = new DeviceSyncMessage();
				for (int i = 0; i < length; i++)
				{
					switch (i)
					{
					case 0:
						____result.SequenceNumber = reader.ReadUInt32();
						break;
					case 1:
						____result.DeviceId = reader.ReadUInt32();
						break;
					case 2:
						____result.PlayerCount = reader.ReadUInt32();
						break;
					case 3:
						____result.RandomRequest = reader.ReadUInt32();
						break;
					default:
						reader.Skip();
						break;
					}
				}
				reader.Depth--;
				return ____result;
			}
		}

		internal sealed class HealthCheckMessageFormatter : IMessagePackFormatter<HealthCheckMessage>, IMessagePackFormatter
		{
			public void Serialize(ref MessagePackWriter writer, HealthCheckMessage value, MessagePackSerializerOptions options)
			{
				if (value == null)
				{
					writer.WriteNil();
					return;
				}
				writer.WriteArrayHeader(3);
				writer.Write(value.SequenceNumber);
				writer.Write(value.Frame);
				writer.Write(value.Checksum);
			}

			public HealthCheckMessage Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options)
			{
				if (reader.TryReadNil())
				{
					return null;
				}
				options.Security.DepthStep(ref reader);
				int length = reader.ReadArrayHeader();
				HealthCheckMessage ____result = new HealthCheckMessage();
				for (int i = 0; i < length; i++)
				{
					switch (i)
					{
					case 0:
						____result.SequenceNumber = reader.ReadUInt32();
						break;
					case 1:
						____result.Frame = reader.ReadInt32();
						break;
					case 2:
						____result.Checksum = reader.ReadUInt32();
						break;
					default:
						reader.Skip();
						break;
					}
				}
				reader.Depth--;
				return ____result;
			}
		}

		internal sealed class LobbyChatMessageFormatter : IMessagePackFormatter<LobbyChatMessage>, IMessagePackFormatter
		{
			public void Serialize(ref MessagePackWriter writer, LobbyChatMessage value, MessagePackSerializerOptions options)
			{
				if (value == null)
				{
					writer.WriteNil();
					return;
				}
				IFormatterResolver resolver = options.Resolver;
				writer.WriteArrayHeader(2);
				writer.Write(value.SequenceNumber);
				resolver.GetFormatterWithVerify<string>().Serialize(ref writer, value.Message, options);
			}

			public LobbyChatMessage Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options)
			{
				if (reader.TryReadNil())
				{
					return null;
				}
				options.Security.DepthStep(ref reader);
				IFormatterResolver formatterResolver = options.Resolver;
				int length = reader.ReadArrayHeader();
				LobbyChatMessage ____result = new LobbyChatMessage();
				for (int i = 0; i < length; i++)
				{
					switch (i)
					{
					case 0:
						____result.SequenceNumber = reader.ReadUInt32();
						break;
					case 1:
						____result.Message = formatterResolver.GetFormatterWithVerify<string>().Deserialize(ref reader, options);
						break;
					default:
						reader.Skip();
						break;
					}
				}
				reader.Depth--;
				return ____result;
			}
		}

		internal sealed class LobbyGotKickedFormatter : IMessagePackFormatter<LobbyGotKicked>, IMessagePackFormatter
		{
			public void Serialize(ref MessagePackWriter writer, LobbyGotKicked value, MessagePackSerializerOptions options)
			{
				if (value == null)
				{
					writer.WriteNil();
					return;
				}
				writer.WriteArrayHeader(1);
				writer.Write(value.SequenceNumber);
			}

			public LobbyGotKicked Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options)
			{
				if (reader.TryReadNil())
				{
					return null;
				}
				options.Security.DepthStep(ref reader);
				int length = reader.ReadArrayHeader();
				LobbyGotKicked ____result = new LobbyGotKicked();
				for (int i = 0; i < length; i++)
				{
					if (i == 0)
					{
						____result.SequenceNumber = reader.ReadUInt32();
					}
					else
					{
						reader.Skip();
					}
				}
				reader.Depth--;
				return ____result;
			}
		}

		internal sealed class LobbyMatchAcceptedFormatter : IMessagePackFormatter<LobbyMatchAccepted>, IMessagePackFormatter
		{
			public void Serialize(ref MessagePackWriter writer, LobbyMatchAccepted value, MessagePackSerializerOptions options)
			{
				if (value == null)
				{
					writer.WriteNil();
					return;
				}
				writer.WriteArrayHeader(4);
				writer.Write(value.SequenceNumber);
				writer.Write(value.MatchID);
				writer.Write(value.AsSpectator);
				writer.Write(value.Index);
			}

			public LobbyMatchAccepted Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options)
			{
				if (reader.TryReadNil())
				{
					return null;
				}
				options.Security.DepthStep(ref reader);
				int length = reader.ReadArrayHeader();
				LobbyMatchAccepted ____result = new LobbyMatchAccepted();
				for (int i = 0; i < length; i++)
				{
					switch (i)
					{
					case 0:
						____result.SequenceNumber = reader.ReadUInt32();
						break;
					case 1:
						____result.MatchID = reader.ReadInt64();
						break;
					case 2:
						____result.AsSpectator = reader.ReadBoolean();
						break;
					case 3:
						____result.Index = reader.ReadByte();
						break;
					default:
						reader.Skip();
						break;
					}
				}
				reader.Depth--;
				return ____result;
			}
		}

		internal sealed class LobbyMatchQuitFormatter : IMessagePackFormatter<LobbyMatchQuit>, IMessagePackFormatter
		{
			public void Serialize(ref MessagePackWriter writer, LobbyMatchQuit value, MessagePackSerializerOptions options)
			{
				if (value == null)
				{
					writer.WriteNil();
					return;
				}
				writer.WriteArrayHeader(2);
				writer.Write(value.SequenceNumber);
				writer.Write(value.IsSpectator);
			}

			public LobbyMatchQuit Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options)
			{
				if (reader.TryReadNil())
				{
					return null;
				}
				options.Security.DepthStep(ref reader);
				int length = reader.ReadArrayHeader();
				LobbyMatchQuit ____result = new LobbyMatchQuit();
				for (int i = 0; i < length; i++)
				{
					switch (i)
					{
					case 0:
						____result.SequenceNumber = reader.ReadUInt32();
						break;
					case 1:
						____result.IsSpectator = reader.ReadBoolean();
						break;
					default:
						reader.Skip();
						break;
					}
				}
				reader.Depth--;
				return ____result;
			}
		}

		internal sealed class LobbyMatchRejectedFormatter : IMessagePackFormatter<LobbyMatchRejected>, IMessagePackFormatter
		{
			public void Serialize(ref MessagePackWriter writer, LobbyMatchRejected value, MessagePackSerializerOptions options)
			{
				if (value == null)
				{
					writer.WriteNil();
					return;
				}
				IFormatterResolver resolver = options.Resolver;
				writer.WriteArrayHeader(2);
				writer.Write(value.SequenceNumber);
				resolver.GetFormatterWithVerify<string>().Serialize(ref writer, value.Message, options);
			}

			public LobbyMatchRejected Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options)
			{
				if (reader.TryReadNil())
				{
					return null;
				}
				options.Security.DepthStep(ref reader);
				IFormatterResolver formatterResolver = options.Resolver;
				int length = reader.ReadArrayHeader();
				LobbyMatchRejected ____result = new LobbyMatchRejected();
				for (int i = 0; i < length; i++)
				{
					switch (i)
					{
					case 0:
						____result.SequenceNumber = reader.ReadUInt32();
						break;
					case 1:
						____result.Message = formatterResolver.GetFormatterWithVerify<string>().Deserialize(ref reader, options);
						break;
					default:
						reader.Skip();
						break;
					}
				}
				reader.Depth--;
				return ____result;
			}
		}

		internal sealed class LobbyMatchRequestFormatter : IMessagePackFormatter<LobbyMatchRequest>, IMessagePackFormatter
		{
			public void Serialize(ref MessagePackWriter writer, LobbyMatchRequest value, MessagePackSerializerOptions options)
			{
				if (value == null)
				{
					writer.WriteNil();
					return;
				}
				writer.WriteArrayHeader(3);
				writer.Write(value.SequenceNumber);
				writer.Write(value.MatchID);
				writer.Write(value.Spectate);
			}

			public LobbyMatchRequest Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options)
			{
				if (reader.TryReadNil())
				{
					return null;
				}
				options.Security.DepthStep(ref reader);
				int length = reader.ReadArrayHeader();
				LobbyMatchRequest ____result = new LobbyMatchRequest();
				for (int i = 0; i < length; i++)
				{
					switch (i)
					{
					case 0:
						____result.SequenceNumber = reader.ReadUInt32();
						break;
					case 1:
						____result.MatchID = reader.ReadInt64();
						break;
					case 2:
						____result.Spectate = reader.ReadBoolean();
						break;
					default:
						reader.Skip();
						break;
					}
				}
				reader.Depth--;
				return ____result;
			}
		}

		internal sealed class PingMessageFormatter : IMessagePackFormatter<PingMessage>, IMessagePackFormatter
		{
			public void Serialize(ref MessagePackWriter writer, PingMessage value, MessagePackSerializerOptions options)
			{
				if (value == null)
				{
					writer.WriteNil();
					return;
				}
				writer.WriteArrayHeader(3);
				writer.Write(value.SequenceNumber);
				writer.Write(value.PingTime);
				writer.Write(value.Returning);
			}

			public PingMessage Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options)
			{
				if (reader.TryReadNil())
				{
					return null;
				}
				options.Security.DepthStep(ref reader);
				int length = reader.ReadArrayHeader();
				PingMessage ____result = new PingMessage();
				for (int i = 0; i < length; i++)
				{
					switch (i)
					{
					case 0:
						____result.SequenceNumber = reader.ReadUInt32();
						break;
					case 1:
						____result.PingTime = reader.ReadUInt32();
						break;
					case 2:
						____result.Returning = reader.ReadBoolean();
						break;
					default:
						reader.Skip();
						break;
					}
				}
				reader.Depth--;
				return ____result;
			}
		}

		internal sealed class DeviceMessageFormatter : IMessagePackFormatter<DeviceMessage>, IMessagePackFormatter
		{
			private readonly Dictionary<RuntimeTypeHandle, KeyValuePair<int, int>> typeToKeyAndJumpMap;

			private readonly Dictionary<int, int> keyToJumpMap;

			public DeviceMessageFormatter()
			{
				typeToKeyAndJumpMap = new Dictionary<RuntimeTypeHandle, KeyValuePair<int, int>>(12, RuntimeTypeHandleEqualityComparer.Default)
				{
					{
						typeof(DeviceSyncMessage).TypeHandle,
						new KeyValuePair<int, int>(0, 0)
					},
					{
						typeof(DeviceSyncConfirmMessage).TypeHandle,
						new KeyValuePair<int, int>(1, 1)
					},
					{
						typeof(DeviceInputMessage).TypeHandle,
						new KeyValuePair<int, int>(2, 2)
					},
					{
						typeof(DeviceInputAckMessage).TypeHandle,
						new KeyValuePair<int, int>(3, 3)
					},
					{
						typeof(HealthCheckMessage).TypeHandle,
						new KeyValuePair<int, int>(4, 4)
					},
					{
						typeof(PingMessage).TypeHandle,
						new KeyValuePair<int, int>(5, 5)
					},
					{
						typeof(LobbyChatMessage).TypeHandle,
						new KeyValuePair<int, int>(6, 6)
					},
					{
						typeof(LobbyMatchRequest).TypeHandle,
						new KeyValuePair<int, int>(7, 7)
					},
					{
						typeof(LobbyMatchAccepted).TypeHandle,
						new KeyValuePair<int, int>(8, 8)
					},
					{
						typeof(LobbyMatchRejected).TypeHandle,
						new KeyValuePair<int, int>(9, 9)
					},
					{
						typeof(LobbyMatchQuit).TypeHandle,
						new KeyValuePair<int, int>(10, 10)
					},
					{
						typeof(LobbyGotKicked).TypeHandle,
						new KeyValuePair<int, int>(11, 11)
					}
				};
				keyToJumpMap = new Dictionary<int, int>(12)
				{
					{ 0, 0 },
					{ 1, 1 },
					{ 2, 2 },
					{ 3, 3 },
					{ 4, 4 },
					{ 5, 5 },
					{ 6, 6 },
					{ 7, 7 },
					{ 8, 8 },
					{ 9, 9 },
					{ 10, 10 },
					{ 11, 11 }
				};
			}

			public void Serialize(ref MessagePackWriter writer, DeviceMessage value, MessagePackSerializerOptions options)
			{
				if (value != null && typeToKeyAndJumpMap.TryGetValue(value.GetType().TypeHandle, out var keyValuePair))
				{
					writer.WriteArrayHeader(2);
					writer.WriteInt32(keyValuePair.Key);
					switch (keyValuePair.Value)
					{
					case 0:
						options.Resolver.GetFormatterWithVerify<DeviceSyncMessage>().Serialize(ref writer, (DeviceSyncMessage)value, options);
						break;
					case 1:
						options.Resolver.GetFormatterWithVerify<DeviceSyncConfirmMessage>().Serialize(ref writer, (DeviceSyncConfirmMessage)value, options);
						break;
					case 2:
						options.Resolver.GetFormatterWithVerify<DeviceInputMessage>().Serialize(ref writer, (DeviceInputMessage)value, options);
						break;
					case 3:
						options.Resolver.GetFormatterWithVerify<DeviceInputAckMessage>().Serialize(ref writer, (DeviceInputAckMessage)value, options);
						break;
					case 4:
						options.Resolver.GetFormatterWithVerify<HealthCheckMessage>().Serialize(ref writer, (HealthCheckMessage)value, options);
						break;
					case 5:
						options.Resolver.GetFormatterWithVerify<PingMessage>().Serialize(ref writer, (PingMessage)value, options);
						break;
					case 6:
						options.Resolver.GetFormatterWithVerify<LobbyChatMessage>().Serialize(ref writer, (LobbyChatMessage)value, options);
						break;
					case 7:
						options.Resolver.GetFormatterWithVerify<LobbyMatchRequest>().Serialize(ref writer, (LobbyMatchRequest)value, options);
						break;
					case 8:
						options.Resolver.GetFormatterWithVerify<LobbyMatchAccepted>().Serialize(ref writer, (LobbyMatchAccepted)value, options);
						break;
					case 9:
						options.Resolver.GetFormatterWithVerify<LobbyMatchRejected>().Serialize(ref writer, (LobbyMatchRejected)value, options);
						break;
					case 10:
						options.Resolver.GetFormatterWithVerify<LobbyMatchQuit>().Serialize(ref writer, (LobbyMatchQuit)value, options);
						break;
					case 11:
						options.Resolver.GetFormatterWithVerify<LobbyGotKicked>().Serialize(ref writer, (LobbyGotKicked)value, options);
						break;
					}
				}
				else
				{
					writer.WriteNil();
				}
			}

			public DeviceMessage Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options)
			{
				if (reader.TryReadNil())
				{
					return null;
				}
				if (reader.ReadArrayHeader() != 2)
				{
					throw new InvalidOperationException("Invalid Union data was detected. Type:global::PleaseResync.DeviceMessage");
				}
				options.Security.DepthStep(ref reader);
				int key = reader.ReadInt32();
				if (!keyToJumpMap.TryGetValue(key, out key))
				{
					key = -1;
				}
				DeviceMessage result = null;
				switch (key)
				{
				case 0:
					result = options.Resolver.GetFormatterWithVerify<DeviceSyncMessage>().Deserialize(ref reader, options);
					break;
				case 1:
					result = options.Resolver.GetFormatterWithVerify<DeviceSyncConfirmMessage>().Deserialize(ref reader, options);
					break;
				case 2:
					result = options.Resolver.GetFormatterWithVerify<DeviceInputMessage>().Deserialize(ref reader, options);
					break;
				case 3:
					result = options.Resolver.GetFormatterWithVerify<DeviceInputAckMessage>().Deserialize(ref reader, options);
					break;
				case 4:
					result = options.Resolver.GetFormatterWithVerify<HealthCheckMessage>().Deserialize(ref reader, options);
					break;
				case 5:
					result = options.Resolver.GetFormatterWithVerify<PingMessage>().Deserialize(ref reader, options);
					break;
				case 6:
					result = options.Resolver.GetFormatterWithVerify<LobbyChatMessage>().Deserialize(ref reader, options);
					break;
				case 7:
					result = options.Resolver.GetFormatterWithVerify<LobbyMatchRequest>().Deserialize(ref reader, options);
					break;
				case 8:
					result = options.Resolver.GetFormatterWithVerify<LobbyMatchAccepted>().Deserialize(ref reader, options);
					break;
				case 9:
					result = options.Resolver.GetFormatterWithVerify<LobbyMatchRejected>().Deserialize(ref reader, options);
					break;
				case 10:
					result = options.Resolver.GetFormatterWithVerify<LobbyMatchQuit>().Deserialize(ref reader, options);
					break;
				case 11:
					result = options.Resolver.GetFormatterWithVerify<LobbyGotKicked>().Deserialize(ref reader, options);
					break;
				default:
					reader.Skip();
					break;
				}
				reader.Depth--;
				return result;
			}
		}
	}

	internal class SakugaEngine
	{
		internal sealed class HitNotificationsFormatter : IMessagePackFormatter<HitNotifications>, IMessagePackFormatter
		{
			public void Serialize(ref MessagePackWriter writer, HitNotifications value, MessagePackSerializerOptions options)
			{
				if (value == null)
				{
					writer.WriteNil();
					return;
				}
				IFormatterResolver resolver = options.Resolver;
				writer.WriteArrayHeader(3);
				writer.Write(value.Notifying);
				writer.Write(value.Timer);
				resolver.GetFormatterWithVerify<HitNotificationPiece[]>().Serialize(ref writer, value.Elements, options);
			}

			public HitNotifications Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options)
			{
				if (reader.TryReadNil())
				{
					return null;
				}
				options.Security.DepthStep(ref reader);
				IFormatterResolver formatterResolver = options.Resolver;
				int length = reader.ReadArrayHeader();
				HitNotifications ____result = new HitNotifications();
				for (int i = 0; i < length; i++)
				{
					switch (i)
					{
					case 0:
						____result.Notifying = reader.ReadBoolean();
						break;
					case 1:
						____result.Timer = reader.ReadInt32();
						break;
					case 2:
						____result.Elements = formatterResolver.GetFormatterWithVerify<HitNotificationPiece[]>().Deserialize(ref reader, options);
						break;
					default:
						reader.Skip();
						break;
					}
				}
				reader.Depth--;
				return ____result;
			}
		}

		internal sealed class HitNotificationPieceFormatter : IMessagePackFormatter<HitNotificationPiece>, IMessagePackFormatter
		{
			public void Serialize(ref MessagePackWriter writer, HitNotificationPiece value, MessagePackSerializerOptions options)
			{
				IFormatterResolver resolver = options.Resolver;
				writer.WriteArrayHeader(2);
				writer.Write(value.Active);
				resolver.GetFormatterWithVerify<string>().Serialize(ref writer, value.NotifName, options);
			}

			public HitNotificationPiece Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options)
			{
				if (reader.TryReadNil())
				{
					throw new InvalidOperationException("typecode is null, struct not supported");
				}
				options.Security.DepthStep(ref reader);
				IFormatterResolver formatterResolver = options.Resolver;
				int length = reader.ReadArrayHeader();
				HitNotificationPiece ____result = default(HitNotificationPiece);
				for (int i = 0; i < length; i++)
				{
					switch (i)
					{
					case 0:
						____result.Active = reader.ReadBoolean();
						break;
					case 1:
						____result.NotifName = formatterResolver.GetFormatterWithVerify<string>().Deserialize(ref reader, options);
						break;
					default:
						reader.Skip();
						break;
					}
				}
				reader.Depth--;
				return ____result;
			}
		}

		internal class GameState
		{
			internal sealed class CombatTrackerStateFormatter : IMessagePackFormatter<CombatTrackerState>, IMessagePackFormatter
			{
				public void Serialize(ref MessagePackWriter writer, CombatTrackerState value, MessagePackSerializerOptions options)
				{
					writer.WriteArrayHeader(11);
					writer.Write(value.HitCombo);
					writer.Write(value.LastDamage);
					writer.Write(value.CurrentCombo);
					writer.Write(value.HighestCombo);
					writer.Write(value.TotalFrames);
					writer.Write(value.FrameData);
					writer.Write(value.FrameAdvantage);
					writer.Write(value.HitFrame);
					writer.Write(value.StunAtHit);
					writer.Write(value.LastHitType);
					writer.Write(value.invalidHit);
				}

				public CombatTrackerState Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options)
				{
					if (reader.TryReadNil())
					{
						throw new InvalidOperationException("typecode is null, struct not supported");
					}
					options.Security.DepthStep(ref reader);
					int length = reader.ReadArrayHeader();
					CombatTrackerState ____result = default(CombatTrackerState);
					for (int i = 0; i < length; i++)
					{
						switch (i)
						{
						case 0:
							____result.HitCombo = reader.ReadInt32();
							break;
						case 1:
							____result.LastDamage = reader.ReadInt32();
							break;
						case 2:
							____result.CurrentCombo = reader.ReadInt32();
							break;
						case 3:
							____result.HighestCombo = reader.ReadInt32();
							break;
						case 4:
							____result.TotalFrames = reader.ReadInt32();
							break;
						case 5:
							____result.FrameData = reader.ReadInt32();
							break;
						case 6:
							____result.FrameAdvantage = reader.ReadInt32();
							break;
						case 7:
							____result.HitFrame = reader.ReadInt32();
							break;
						case 8:
							____result.StunAtHit = reader.ReadInt32();
							break;
						case 9:
							____result.LastHitType = reader.ReadInt32();
							break;
						case 10:
							____result.invalidHit = reader.ReadBoolean();
							break;
						default:
							reader.Skip();
							break;
						}
					}
					reader.Depth--;
					return ____result;
				}
			}

			internal sealed class CustomVariableStateFormatter : IMessagePackFormatter<CustomVariableState>, IMessagePackFormatter
			{
				public void Serialize(ref MessagePackWriter writer, CustomVariableState value, MessagePackSerializerOptions options)
				{
					IFormatterResolver resolver = options.Resolver;
					writer.WriteArrayHeader(3);
					writer.Write(value.Value);
					writer.Write(value.Factor);
					resolver.GetFormatterWithVerify<CustomVariableMode>().Serialize(ref writer, value.Mode, options);
				}

				public CustomVariableState Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options)
				{
					if (reader.TryReadNil())
					{
						throw new InvalidOperationException("typecode is null, struct not supported");
					}
					options.Security.DepthStep(ref reader);
					IFormatterResolver formatterResolver = options.Resolver;
					int length = reader.ReadArrayHeader();
					CustomVariableState ____result = default(CustomVariableState);
					for (int i = 0; i < length; i++)
					{
						switch (i)
						{
						case 0:
							____result.Value = reader.ReadInt32();
							break;
						case 1:
							____result.Factor = reader.ReadInt32();
							break;
						case 2:
							____result.Mode = formatterResolver.GetFormatterWithVerify<CustomVariableMode>().Deserialize(ref reader, options);
							break;
						default:
							reader.Skip();
							break;
						}
					}
					reader.Depth--;
					return ____result;
				}
			}

			internal sealed class FrameTimerStateFormatter : IMessagePackFormatter<FrameTimerState>, IMessagePackFormatter
			{
				public void Serialize(ref MessagePackWriter writer, FrameTimerState value, MessagePackSerializerOptions options)
				{
					writer.WriteArrayHeader(3);
					writer.Write(value.WaitTime);
					writer.Write(value.TimeLeft);
					writer.Write(value.Paused);
				}

				public FrameTimerState Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options)
				{
					if (reader.TryReadNil())
					{
						throw new InvalidOperationException("typecode is null, struct not supported");
					}
					options.Security.DepthStep(ref reader);
					int length = reader.ReadArrayHeader();
					FrameTimerState ____result = default(FrameTimerState);
					for (int i = 0; i < length; i++)
					{
						switch (i)
						{
						case 0:
							____result.WaitTime = reader.ReadUInt32();
							break;
						case 1:
							____result.TimeLeft = reader.ReadUInt32();
							break;
						case 2:
							____result.Paused = reader.ReadBoolean();
							break;
						default:
							reader.Skip();
							break;
						}
					}
					reader.Depth--;
					return ____result;
				}
			}

			internal sealed class GameManagerStateFormatter : IMessagePackFormatter<GameManagerState>, IMessagePackFormatter
			{
				public void Serialize(ref MessagePackWriter writer, GameManagerState value, MessagePackSerializerOptions options)
				{
					IFormatterResolver resolver = options.Resolver;
					writer.WriteArrayHeader(9);   // Netsu: 6-8 = the EX / super pause (Oct 24 late)
					resolver.GetFormatterWithVerify<InputManagerState[]>().Serialize(ref writer, value.Inputs, options);
					writer.Write(value.Frame);
					resolver.GetFormatterWithVerify<GameMonitorState>().Serialize(ref writer, value.GameMonitor, options);
					resolver.GetFormatterWithVerify<byte[][]>().Serialize(ref writer, value.SakugaNodes, options);
					resolver.GetFormatterWithVerify<Vector3IState>().Serialize(ref writer, value.RandomTest, options);
					resolver.GetFormatterWithVerify<HitNotifications[]>().Serialize(ref writer, value.Notifs, options);
					writer.Write(value.NetsuPause);
					writer.Write(value.NetsuPauseSide);
					writer.Write(value.NetsuPauseTotal);
				}

				public GameManagerState Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options)
				{
					if (reader.TryReadNil())
					{
						throw new InvalidOperationException("typecode is null, struct not supported");
					}
					options.Security.DepthStep(ref reader);
					IFormatterResolver formatterResolver = options.Resolver;
					int length = reader.ReadArrayHeader();
					GameManagerState ____result = default(GameManagerState);
					for (int i = 0; i < length; i++)
					{
						switch (i)
						{
						case 0:
							____result.Inputs = formatterResolver.GetFormatterWithVerify<InputManagerState[]>().Deserialize(ref reader, options);
							break;
						case 1:
							____result.Frame = reader.ReadInt32();
							break;
						case 2:
							____result.GameMonitor = formatterResolver.GetFormatterWithVerify<GameMonitorState>().Deserialize(ref reader, options);
							break;
						case 3:
							____result.SakugaNodes = formatterResolver.GetFormatterWithVerify<byte[][]>().Deserialize(ref reader, options);
							break;
						case 4:
							____result.RandomTest = formatterResolver.GetFormatterWithVerify<Vector3IState>().Deserialize(ref reader, options);
							break;
						case 5:
							____result.Notifs = formatterResolver.GetFormatterWithVerify<HitNotifications[]>().Deserialize(ref reader, options);
							break;
						case 6:
							____result.NetsuPause = reader.ReadInt32();
							break;
						case 7:
							____result.NetsuPauseSide = reader.ReadInt32();
							break;
						case 8:
							____result.NetsuPauseTotal = reader.ReadInt32();
							break;
						default:
							reader.Skip();
							break;
						}
					}
					reader.Depth--;
					return ____result;
				}
			}

			internal sealed class GameMonitorStateFormatter : IMessagePackFormatter<GameMonitorState>, IMessagePackFormatter
			{
				public void Serialize(ref MessagePackWriter writer, GameMonitorState value, MessagePackSerializerOptions options)
				{
					IFormatterResolver resolver = options.Resolver;
					writer.WriteArrayHeader(13);
					resolver.GetFormatterWithVerify<FadeScreenMode>().Serialize(ref writer, value.FadeMode, options);
					resolver.GetFormatterWithVerify<FrameTimerState>().Serialize(ref writer, value.DelayTimer, options);
					writer.Write(value.Clock);
					writer.Write(value.CurrentRound);
					writer.Write(value.Winner);
					writer.Write(value.FadeScreenIntensity);
					writer.Write(value.FadeTime);
					writer.Write(value.FadeProgress);
					resolver.GetFormatterWithVerify<MatchState>().Serialize(ref writer, value.MatchState, options);
					writer.Write(value.RoundWinner);
					writer.Write(value.CardsCurrentAnimation);
					writer.Write(value.CardsCurrentFrame);
					resolver.GetFormatterWithVerify<int[]>().Serialize(ref writer, value.VictoryCounter, options);
				}

				public GameMonitorState Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options)
				{
					if (reader.TryReadNil())
					{
						throw new InvalidOperationException("typecode is null, struct not supported");
					}
					options.Security.DepthStep(ref reader);
					IFormatterResolver formatterResolver = options.Resolver;
					int length = reader.ReadArrayHeader();
					GameMonitorState ____result = default(GameMonitorState);
					for (int i = 0; i < length; i++)
					{
						switch (i)
						{
						case 0:
							____result.FadeMode = formatterResolver.GetFormatterWithVerify<FadeScreenMode>().Deserialize(ref reader, options);
							break;
						case 1:
							____result.DelayTimer = formatterResolver.GetFormatterWithVerify<FrameTimerState>().Deserialize(ref reader, options);
							break;
						case 2:
							____result.Clock = reader.ReadInt32();
							break;
						case 3:
							____result.CurrentRound = reader.ReadInt32();
							break;
						case 4:
							____result.Winner = reader.ReadInt32();
							break;
						case 5:
							____result.FadeScreenIntensity = reader.ReadInt32();
							break;
						case 6:
							____result.FadeTime = reader.ReadInt32();
							break;
						case 7:
							____result.FadeProgress = reader.ReadInt32();
							break;
						case 8:
							____result.MatchState = formatterResolver.GetFormatterWithVerify<MatchState>().Deserialize(ref reader, options);
							break;
						case 9:
							____result.RoundWinner = reader.ReadInt32();
							break;
						case 10:
							____result.CardsCurrentAnimation = reader.ReadInt32();
							break;
						case 11:
							____result.CardsCurrentFrame = reader.ReadInt32();
							break;
						case 12:
							____result.VictoryCounter = formatterResolver.GetFormatterWithVerify<int[]>().Deserialize(ref reader, options);
							break;
						default:
							reader.Skip();
							break;
						}
					}
					reader.Depth--;
					return ____result;
				}
			}

			internal sealed class InputManagerStateFormatter : IMessagePackFormatter<InputManagerState>, IMessagePackFormatter
			{
				public void Serialize(ref MessagePackWriter writer, InputManagerState value, MessagePackSerializerOptions options)
				{
					IFormatterResolver resolver = options.Resolver;
					writer.WriteArrayHeader(5);
					resolver.GetFormatterWithVerify<PlayerInputs[]>().Serialize(ref writer, value.RawInputs, options);
					resolver.GetFormatterWithVerify<ushort[]>().Serialize(ref writer, value.Durations, options);
					writer.Write(value.hCharge);
					writer.Write(value.vCharge);
					writer.Write(value.CurrentHistory);
				}

				public InputManagerState Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options)
				{
					if (reader.TryReadNil())
					{
						throw new InvalidOperationException("typecode is null, struct not supported");
					}
					options.Security.DepthStep(ref reader);
					IFormatterResolver formatterResolver = options.Resolver;
					int length = reader.ReadArrayHeader();
					InputManagerState ____result = default(InputManagerState);
					for (int i = 0; i < length; i++)
					{
						switch (i)
						{
						case 0:
							____result.RawInputs = formatterResolver.GetFormatterWithVerify<PlayerInputs[]>().Deserialize(ref reader, options);
							break;
						case 1:
							____result.Durations = formatterResolver.GetFormatterWithVerify<ushort[]>().Deserialize(ref reader, options);
							break;
						case 2:
							____result.hCharge = reader.ReadInt16();
							break;
						case 3:
							____result.vCharge = reader.ReadInt16();
							break;
						case 4:
							____result.CurrentHistory = reader.ReadInt32();
							break;
						default:
							reader.Skip();
							break;
						}
					}
					reader.Depth--;
					return ____result;
				}
			}

			internal sealed class ParametersStateFormatter : IMessagePackFormatter<ParametersState>, IMessagePackFormatter
			{
				public void Serialize(ref MessagePackWriter writer, ParametersState value, MessagePackSerializerOptions options)
				{
					IFormatterResolver resolver = options.Resolver;
					writer.WriteArrayHeader(52);
					writer.Write(value.CurrentHealth);
					writer.Write(value.LostHealth);
					writer.Write(value.RecoveryHealth);
					writer.Write(value.CurrentSuperGauge);
					writer.Write(value.CurrentWill);
					resolver.GetFormatterWithVerify<WillState>().Serialize(ref writer, value.CurrentWillState, options);
					writer.Write(value.CurrentSuperArmor);
					resolver.GetFormatterWithVerify<ProrationsState>().Serialize(ref writer, value.Prorations, options);
					resolver.GetFormatterWithVerify<CombatTrackerState>().Serialize(ref writer, value.CombatTracker, options);
					writer.WriteNil();
					writer.WriteNil();
					writer.WriteNil();
					writer.WriteNil();
					writer.WriteNil();
					writer.WriteNil();
					writer.WriteNil();
					writer.WriteNil();
					writer.WriteNil();
					writer.WriteNil();
					writer.WriteNil();
					writer.WriteNil();
					writer.WriteNil();
					writer.WriteNil();
					writer.WriteNil();
					writer.WriteNil();
					writer.WriteNil();
					writer.WriteNil();
					writer.WriteNil();
					writer.WriteNil();
					writer.WriteNil();
					writer.WriteNil();
					writer.WriteNil();
					writer.WriteNil();
					writer.WriteNil();
					writer.WriteNil();
					writer.WriteNil();
					writer.WriteNil();
					writer.WriteNil();
					writer.WriteNil();
					writer.WriteNil();
					writer.WriteNil();
					writer.WriteNil();
					writer.WriteNil();
					writer.WriteNil();
					writer.WriteNil();
					writer.WriteNil();
					writer.WriteNil();
					writer.WriteNil();
					writer.WriteNil();
					writer.WriteNil();
					resolver.GetFormatterWithVerify<FrameTimerState[]>().Serialize(ref writer, value.Timers, options);
					resolver.GetFormatterWithVerify<CustomVariableState[]>().Serialize(ref writer, value.Variables, options);
				}

				public ParametersState Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options)
				{
					if (reader.TryReadNil())
					{
						throw new InvalidOperationException("typecode is null, struct not supported");
					}
					options.Security.DepthStep(ref reader);
					IFormatterResolver formatterResolver = options.Resolver;
					int length = reader.ReadArrayHeader();
					ParametersState ____result = default(ParametersState);
					for (int i = 0; i < length; i++)
					{
						switch (i)
						{
						case 0:
							____result.CurrentHealth = reader.ReadInt32();
							break;
						case 1:
							____result.LostHealth = reader.ReadInt32();
							break;
						case 2:
							____result.RecoveryHealth = reader.ReadInt32();
							break;
						case 3:
							____result.CurrentSuperGauge = reader.ReadInt32();
							break;
						case 4:
							____result.CurrentWill = reader.ReadInt32();
							break;
						case 5:
							____result.CurrentWillState = formatterResolver.GetFormatterWithVerify<WillState>().Deserialize(ref reader, options);
							break;
						case 6:
							____result.CurrentSuperArmor = reader.ReadInt32();
							break;
						case 7:
							____result.Prorations = formatterResolver.GetFormatterWithVerify<ProrationsState>().Deserialize(ref reader, options);
							break;
						case 8:
							____result.CombatTracker = formatterResolver.GetFormatterWithVerify<CombatTrackerState>().Deserialize(ref reader, options);
							break;
						case 50:
							____result.Timers = formatterResolver.GetFormatterWithVerify<FrameTimerState[]>().Deserialize(ref reader, options);
							break;
						case 51:
							____result.Variables = formatterResolver.GetFormatterWithVerify<CustomVariableState[]>().Deserialize(ref reader, options);
							break;
						default:
							reader.Skip();
							break;
						}
					}
					reader.Depth--;
					return ____result;
				}
			}

			internal sealed class PhysicsBodyStateFormatter : IMessagePackFormatter<PhysicsBodyState>, IMessagePackFormatter
			{
				public void Serialize(ref MessagePackWriter writer, PhysicsBodyState value, MessagePackSerializerOptions options)
				{
					IFormatterResolver resolver = options.Resolver;
					writer.WriteArrayHeader(8);
					resolver.GetFormatterWithVerify<Vector2IState>().Serialize(ref writer, value.FixedPosition, options);
					resolver.GetFormatterWithVerify<Vector2IState>().Serialize(ref writer, value.FixedVelocity, options);
					writer.Write(value.IsLeftSide);
					writer.Write(value.PlayerSide);
					writer.Write(value.IsMovable);
					resolver.GetFormatterWithVerify<List<uint>>().Serialize(ref writer, value.HitBodies, options);
					writer.Write(value.ProximityBlocked);
					writer.Write(value.CurrentGravity);
				}

				public PhysicsBodyState Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options)
				{
					if (reader.TryReadNil())
					{
						throw new InvalidOperationException("typecode is null, struct not supported");
					}
					options.Security.DepthStep(ref reader);
					IFormatterResolver formatterResolver = options.Resolver;
					int length = reader.ReadArrayHeader();
					PhysicsBodyState ____result = default(PhysicsBodyState);
					for (int i = 0; i < length; i++)
					{
						switch (i)
						{
						case 0:
							____result.FixedPosition = formatterResolver.GetFormatterWithVerify<Vector2IState>().Deserialize(ref reader, options);
							break;
						case 1:
							____result.FixedVelocity = formatterResolver.GetFormatterWithVerify<Vector2IState>().Deserialize(ref reader, options);
							break;
						case 2:
							____result.IsLeftSide = reader.ReadBoolean();
							break;
						case 3:
							____result.PlayerSide = reader.ReadInt32();
							break;
						case 4:
							____result.IsMovable = reader.ReadBoolean();
							break;
						case 5:
							____result.HitBodies = formatterResolver.GetFormatterWithVerify<List<uint>>().Deserialize(ref reader, options);
							break;
						case 6:
							____result.ProximityBlocked = reader.ReadBoolean();
							break;
						case 7:
							____result.CurrentGravity = reader.ReadInt32();
							break;
						default:
							reader.Skip();
							break;
						}
					}
					reader.Depth--;
					return ____result;
				}
			}

			internal sealed class ProrationsStateFormatter : IMessagePackFormatter<ProrationsState>, IMessagePackFormatter
			{
				public void Serialize(ref MessagePackWriter writer, ProrationsState value, MessagePackSerializerOptions options)
				{
					writer.WriteArrayHeader(10);
					writer.Write(value.CurrentAttack);
					writer.Write(value.CurrentDefense);
					writer.Write(value.CurrentDamageScaling);
					writer.Write(value.CurrentBaseDamageScaling);
					writer.Write(value.CurrentCornerDamageScaling);
					writer.Write(value.CurrentSameMoveProration);
					writer.Write(value.CurrentGravityProration);
					writer.Write(value.CurrentHitstunProration);
					writer.Write(value.GravityDecayFactor);
					writer.Write(value.HitstunDecayFactor);
				}

				public ProrationsState Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options)
				{
					if (reader.TryReadNil())
					{
						throw new InvalidOperationException("typecode is null, struct not supported");
					}
					options.Security.DepthStep(ref reader);
					int length = reader.ReadArrayHeader();
					ProrationsState ____result = default(ProrationsState);
					for (int i = 0; i < length; i++)
					{
						switch (i)
						{
						case 0:
							____result.CurrentAttack = reader.ReadUInt16();
							break;
						case 1:
							____result.CurrentDefense = reader.ReadUInt16();
							break;
						case 2:
							____result.CurrentDamageScaling = reader.ReadUInt16();
							break;
						case 3:
							____result.CurrentBaseDamageScaling = reader.ReadUInt16();
							break;
						case 4:
							____result.CurrentCornerDamageScaling = reader.ReadUInt16();
							break;
						case 5:
							____result.CurrentSameMoveProration = reader.ReadUInt16();
							break;
						case 6:
							____result.CurrentGravityProration = reader.ReadUInt16();
							break;
						case 7:
							____result.CurrentHitstunProration = reader.ReadUInt16();
							break;
						case 8:
							____result.GravityDecayFactor = reader.ReadByte();
							break;
						case 9:
							____result.HitstunDecayFactor = reader.ReadByte();
							break;
						default:
							reader.Skip();
							break;
						}
					}
					reader.Depth--;
					return ____result;
				}
			}

			internal sealed class SakugaActorStateFormatter : IMessagePackFormatter<SakugaActorState>, IMessagePackFormatter
			{
				public void Serialize(ref MessagePackWriter writer, SakugaActorState value, MessagePackSerializerOptions options)
				{
					IFormatterResolver resolver = options.Resolver;
					writer.WriteArrayHeader(15);
					writer.Write(value.IsActive);
					resolver.GetFormatterWithVerify<PhysicsBodyState>().Serialize(ref writer, value.Body, options);
					resolver.GetFormatterWithVerify<ParametersState>().Serialize(ref writer, value.Parameters, options);
					resolver.GetFormatterWithVerify<StateManagerState>().Serialize(ref writer, value.StateManager, options);
					resolver.GetFormatterWithVerify<StanceManagerState>().Serialize(ref writer, value.StanceManager, options);
					writer.Write(value.LayerSorting);
					writer.Write(value.BounceXIntensity);
					writer.Write(value.BounceYIntensity);
					writer.Write(value.SuperFlashing);
					writer.Write(value.CinematicState);
					writer.Write(value.BlockStun);
					resolver.GetFormatterWithVerify<HitstunType>().Serialize(ref writer, value.HitstunType, options);
					resolver.GetFormatterWithVerify<FrameProperties>().Serialize(ref writer, value.FrameProperties, options);
					resolver.GetFormatterWithVerify<HitChecker>().Serialize(ref writer, value.HitCheck, options);
					resolver.GetFormatterWithVerify<CancelCondition>().Serialize(ref writer, value.CancelConditions, options);
				}

				public SakugaActorState Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options)
				{
					if (reader.TryReadNil())
					{
						throw new InvalidOperationException("typecode is null, struct not supported");
					}
					options.Security.DepthStep(ref reader);
					IFormatterResolver formatterResolver = options.Resolver;
					int length = reader.ReadArrayHeader();
					SakugaActorState ____result = default(SakugaActorState);
					for (int i = 0; i < length; i++)
					{
						switch (i)
						{
						case 0:
							____result.IsActive = reader.ReadBoolean();
							break;
						case 1:
							____result.Body = formatterResolver.GetFormatterWithVerify<PhysicsBodyState>().Deserialize(ref reader, options);
							break;
						case 2:
							____result.Parameters = formatterResolver.GetFormatterWithVerify<ParametersState>().Deserialize(ref reader, options);
							break;
						case 3:
							____result.StateManager = formatterResolver.GetFormatterWithVerify<StateManagerState>().Deserialize(ref reader, options);
							break;
						case 4:
							____result.StanceManager = formatterResolver.GetFormatterWithVerify<StanceManagerState>().Deserialize(ref reader, options);
							break;
						case 5:
							____result.LayerSorting = reader.ReadInt32();
							break;
						case 6:
							____result.BounceXIntensity = reader.ReadInt32();
							break;
						case 7:
							____result.BounceYIntensity = reader.ReadInt32();
							break;
						case 8:
							____result.SuperFlashing = reader.ReadBoolean();
							break;
						case 9:
							____result.CinematicState = reader.ReadBoolean();
							break;
						case 10:
							____result.BlockStun = reader.ReadBoolean();
							break;
						case 11:
							____result.HitstunType = formatterResolver.GetFormatterWithVerify<HitstunType>().Deserialize(ref reader, options);
							break;
						case 12:
							____result.FrameProperties = formatterResolver.GetFormatterWithVerify<FrameProperties>().Deserialize(ref reader, options);
							break;
						case 13:
							____result.HitCheck = formatterResolver.GetFormatterWithVerify<HitChecker>().Deserialize(ref reader, options);
							break;
						case 14:
							____result.CancelConditions = formatterResolver.GetFormatterWithVerify<CancelCondition>().Deserialize(ref reader, options);
							break;
						default:
							reader.Skip();
							break;
						}
					}
					reader.Depth--;
					return ____result;
				}
			}

			internal sealed class SakugaVFXStateFormatter : IMessagePackFormatter<SakugaVFXState>, IMessagePackFormatter
			{
				public void Serialize(ref MessagePackWriter writer, SakugaVFXState value, MessagePackSerializerOptions options)
				{
					IFormatterResolver resolver = options.Resolver;
					writer.WriteArrayHeader(5);
					writer.Write(value.IsActive);
					writer.Write(value.AttachedToOwner);
					resolver.GetFormatterWithVerify<Vector2IState>().Serialize(ref writer, value.FixedPosition, options);
					writer.Write(value.Frame);
					writer.Write(value.Side);
				}

				public SakugaVFXState Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options)
				{
					if (reader.TryReadNil())
					{
						throw new InvalidOperationException("typecode is null, struct not supported");
					}
					options.Security.DepthStep(ref reader);
					IFormatterResolver formatterResolver = options.Resolver;
					int length = reader.ReadArrayHeader();
					SakugaVFXState ____result = default(SakugaVFXState);
					for (int i = 0; i < length; i++)
					{
						switch (i)
						{
						case 0:
							____result.IsActive = reader.ReadBoolean();
							break;
						case 1:
							____result.AttachedToOwner = reader.ReadBoolean();
							break;
						case 2:
							____result.FixedPosition = formatterResolver.GetFormatterWithVerify<Vector2IState>().Deserialize(ref reader, options);
							break;
						case 3:
							____result.Frame = reader.ReadInt32();
							break;
						case 4:
							____result.Side = reader.ReadInt32();
							break;
						default:
							reader.Skip();
							break;
						}
					}
					reader.Depth--;
					return ____result;
				}
			}

			internal sealed class StanceManagerStateFormatter : IMessagePackFormatter<StanceManagerState>, IMessagePackFormatter
			{
				public void Serialize(ref MessagePackWriter writer, StanceManagerState value, MessagePackSerializerOptions options)
				{
					writer.WriteArrayHeader(4);
					writer.Write(value.CurrentStance);
					writer.Write(value.BufferedMove);
					writer.Write(value.CurrentMove);
					writer.Write(value.CancelBuffer);
				}

				public StanceManagerState Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options)
				{
					if (reader.TryReadNil())
					{
						throw new InvalidOperationException("typecode is null, struct not supported");
					}
					options.Security.DepthStep(ref reader);
					int length = reader.ReadArrayHeader();
					StanceManagerState ____result = default(StanceManagerState);
					for (int i = 0; i < length; i++)
					{
						switch (i)
						{
						case 0:
							____result.CurrentStance = reader.ReadInt32();
							break;
						case 1:
							____result.BufferedMove = reader.ReadInt32();
							break;
						case 2:
							____result.CurrentMove = reader.ReadInt32();
							break;
						case 3:
							____result.CancelBuffer = reader.ReadBoolean();
							break;
						default:
							reader.Skip();
							break;
						}
					}
					reader.Depth--;
					return ____result;
				}
			}

			internal sealed class StateManagerStateFormatter : IMessagePackFormatter<StateManagerState>, IMessagePackFormatter
			{
				public void Serialize(ref MessagePackWriter writer, StateManagerState value, MessagePackSerializerOptions options)
				{
					writer.WriteArrayHeader(2);
					writer.Write(value.CurrentState);
					writer.Write(value.CurrentStateFrame);
				}

				public StateManagerState Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options)
				{
					if (reader.TryReadNil())
					{
						throw new InvalidOperationException("typecode is null, struct not supported");
					}
					options.Security.DepthStep(ref reader);
					int length = reader.ReadArrayHeader();
					StateManagerState ____result = default(StateManagerState);
					for (int i = 0; i < length; i++)
					{
						switch (i)
						{
						case 0:
							____result.CurrentState = reader.ReadInt32();
							break;
						case 1:
							____result.CurrentStateFrame = reader.ReadInt32();
							break;
						default:
							reader.Skip();
							break;
						}
					}
					reader.Depth--;
					return ____result;
				}
			}

			internal sealed class Vector2IStateFormatter : IMessagePackFormatter<Vector2IState>, IMessagePackFormatter
			{
				public void Serialize(ref MessagePackWriter writer, Vector2IState value, MessagePackSerializerOptions options)
				{
					writer.WriteArrayHeader(2);
					writer.Write(value.X);
					writer.Write(value.Y);
				}

				public Vector2IState Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options)
				{
					if (reader.TryReadNil())
					{
						throw new InvalidOperationException("typecode is null, struct not supported");
					}
					options.Security.DepthStep(ref reader);
					int length = reader.ReadArrayHeader();
					Vector2IState ____result = default(Vector2IState);
					for (int i = 0; i < length; i++)
					{
						switch (i)
						{
						case 0:
							____result.X = reader.ReadInt32();
							break;
						case 1:
							____result.Y = reader.ReadInt32();
							break;
						default:
							reader.Skip();
							break;
						}
					}
					reader.Depth--;
					return ____result;
				}
			}

			internal sealed class Vector3IStateFormatter : IMessagePackFormatter<Vector3IState>, IMessagePackFormatter
			{
				public void Serialize(ref MessagePackWriter writer, Vector3IState value, MessagePackSerializerOptions options)
				{
					writer.WriteArrayHeader(3);
					writer.Write(value.X);
					writer.Write(value.Y);
					writer.Write(value.Z);
				}

				public Vector3IState Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options)
				{
					if (reader.TryReadNil())
					{
						throw new InvalidOperationException("typecode is null, struct not supported");
					}
					options.Security.DepthStep(ref reader);
					int length = reader.ReadArrayHeader();
					Vector3IState ____result = default(Vector3IState);
					for (int i = 0; i < length; i++)
					{
						switch (i)
						{
						case 0:
							____result.X = reader.ReadInt32();
							break;
						case 1:
							____result.Y = reader.ReadInt32();
							break;
						case 2:
							____result.Z = reader.ReadInt32();
							break;
						default:
							reader.Skip();
							break;
						}
					}
					reader.Depth--;
					return ____result;
				}
			}
		}

		internal class Global
		{
			internal sealed class CancelConditionFormatter : IMessagePackFormatter<CancelCondition>, IMessagePackFormatter
			{
				public void Serialize(ref MessagePackWriter writer, CancelCondition value, MessagePackSerializerOptions options)
				{
					writer.Write((byte)value);
				}

				public CancelCondition Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options)
				{
					return (CancelCondition)reader.ReadByte();
				}
			}

			internal sealed class CustomVariableModeFormatter : IMessagePackFormatter<CustomVariableMode>, IMessagePackFormatter
			{
				public void Serialize(ref MessagePackWriter writer, CustomVariableMode value, MessagePackSerializerOptions options)
				{
					writer.Write((int)value);
				}

				public CustomVariableMode Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options)
				{
					return (CustomVariableMode)reader.ReadInt32();
				}
			}

			internal sealed class FadeScreenModeFormatter : IMessagePackFormatter<FadeScreenMode>, IMessagePackFormatter
			{
				public void Serialize(ref MessagePackWriter writer, FadeScreenMode value, MessagePackSerializerOptions options)
				{
					writer.Write((int)value);
				}

				public FadeScreenMode Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options)
				{
					return (FadeScreenMode)reader.ReadInt32();
				}
			}

			internal sealed class FramePropertiesFormatter : IMessagePackFormatter<FrameProperties>, IMessagePackFormatter
			{
				public void Serialize(ref MessagePackWriter writer, FrameProperties value, MessagePackSerializerOptions options)
				{
					writer.Write((byte)value);
				}

				public FrameProperties Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options)
				{
					return (FrameProperties)reader.ReadByte();
				}
			}

			internal sealed class HitCheckerFormatter : IMessagePackFormatter<HitChecker>, IMessagePackFormatter
			{
				public void Serialize(ref MessagePackWriter writer, HitChecker value, MessagePackSerializerOptions options)
				{
					writer.Write((byte)value);
				}

				public HitChecker Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options)
				{
					return (HitChecker)reader.ReadByte();
				}
			}

			internal sealed class HitstunTypeFormatter : IMessagePackFormatter<HitstunType>, IMessagePackFormatter
			{
				public void Serialize(ref MessagePackWriter writer, HitstunType value, MessagePackSerializerOptions options)
				{
					writer.Write((int)value);
				}

				public HitstunType Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options)
				{
					return (HitstunType)reader.ReadInt32();
				}
			}

			internal sealed class MatchStateFormatter : IMessagePackFormatter<MatchState>, IMessagePackFormatter
			{
				public void Serialize(ref MessagePackWriter writer, MatchState value, MessagePackSerializerOptions options)
				{
					writer.Write((int)value);
				}

				public MatchState Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options)
				{
					return (MatchState)reader.ReadInt32();
				}
			}

			internal sealed class PlayerInputsFormatter : IMessagePackFormatter<PlayerInputs>, IMessagePackFormatter
			{
				public void Serialize(ref MessagePackWriter writer, PlayerInputs value, MessagePackSerializerOptions options)
				{
					writer.Write((ushort)value);
				}

				public PlayerInputs Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options)
				{
					return (PlayerInputs)reader.ReadUInt16();
				}
			}

			internal sealed class WillStateFormatter : IMessagePackFormatter<WillState>, IMessagePackFormatter
			{
				public void Serialize(ref MessagePackWriter writer, WillState value, MessagePackSerializerOptions options)
				{
					writer.Write((int)value);
				}

				public WillState Deserialize(ref MessagePackReader reader, MessagePackSerializerOptions options)
				{
					return (WillState)reader.ReadInt32();
				}
			}
		}
	}

	public static readonly IFormatterResolver Instance = new GeneratedMessagePackResolver();

	private GeneratedMessagePackResolver()
	{
	}

	public IMessagePackFormatter<T> GetFormatter<T>()
	{
		return FormatterCache<T>.Formatter;
	}
}
