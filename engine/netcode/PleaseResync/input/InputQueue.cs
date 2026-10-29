namespace PleaseResync;

internal class InputQueue
{
	public const int QueueSize = 128;

	private uint _frameDelay;

	private GameInput[] _inputs;

	private GameInput[] _lastPredictedInputs;

	public InputQueue(uint inputSize, uint playerCount, uint frameDelay = 0u)
	{
		_frameDelay = frameDelay;
		_inputs = new GameInput[128];
		_lastPredictedInputs = new GameInput[128];
		for (int i = 0; i < _inputs.Length; i++)
		{
			_inputs[i] = new GameInput(-1, inputSize, playerCount);
			_lastPredictedInputs[i] = new GameInput(-1, inputSize, playerCount);
		}
	}

	public GameInput GetPredictedInput(int frame)
	{
		return _lastPredictedInputs[frame % 128];
	}

	public uint GetFrameDelay()
	{
		return _frameDelay;
	}

	public void AddInput(int frame, GameInput input)
	{
		frame += (int)_frameDelay;
		_inputs[frame % 128] = new GameInput(input);
		_inputs[frame % 128].Frame = frame;
	}

	public GameInput GetInput(int frame, bool predict = true)
	{
		int frameOffset = frame % 128;
		if (predict && (_inputs[frameOffset].Frame == -1 || _inputs[frameOffset].Frame != frame))
		{
			GameInput prevFrame = _inputs[PreviousFrame(frameOffset)];
			_inputs[frameOffset] = new GameInput(prevFrame);
			_inputs[frameOffset].Frame = -1;
			_lastPredictedInputs[frameOffset] = new GameInput(_inputs[frameOffset]);
			_lastPredictedInputs[frameOffset].Frame = frame;
		}
		return new GameInput(_inputs[frameOffset]);
	}

	public void ResetPrediction(int frame)
	{
		int frameOffset = frame % 128;
		_lastPredictedInputs[frameOffset].Frame = -1;
	}

	private int PreviousFrame(int offset)
	{
		if (offset != 0)
		{
			return offset - 1;
		}
		return 127;
	}
}
