using System;
using Godot;

namespace PleaseResync;

[Serializable]
public class ConnectionAddress
{
	public LineEdit IPField;

	public LineEdit PortField;

	public ConnectionAddress(LineEdit _IP, LineEdit _Port)
	{
		IPField = _IP;
		PortField = _Port;
	}
}
