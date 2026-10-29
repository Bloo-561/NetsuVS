using MessagePack;

namespace SakugaEngine;

[MessagePackObject(false)]
public class HitNotifications
{
	[Key(0)]
	public bool Notifying;

	[Key(1)]
	public int Timer;

	[Key(2)]
	public HitNotificationPiece[] Elements;

	public HitNotifications()
	{
	}

	public HitNotifications(int amount)
	{
		Elements = new HitNotificationPiece[amount];
		Timer = 0;
	}

	public void Tick()
	{
		Timer--;
		if (Timer == 0 && Notifying)
		{
			for (int i = 0; i < Elements.Length; i++)
			{
				Clear(i);
			}
			Notifying = false;
		}
	}

	public void Notify(string notifName)
	{
		for (int i = 0; i < Elements.Length; i++)
		{
			if (!Elements[i].Active)
			{
				Add(i, notifName);
				Timer = 60;
				Notifying = true;
				break;
			}
		}
	}

	public void Add(int Index, string newText)
	{
		Elements[Index].Active = true;
		Elements[Index].NotifName = newText;
	}

	public void Clear(int Index)
	{
		Elements[Index].Active = false;
		Elements[Index].NotifName = "";
	}
}
