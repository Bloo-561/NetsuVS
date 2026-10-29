# Online play (Oct 24 2026; 5-digit lobby codes Oct 24 late; group lobbies, king of the hill, spectators Oct 25)

Main menu → **ONLINE**. Up to 8 players on different computers in one lobby, rollback netcode, no server of our own
(the lobby codes use a free public message board, ntfy.sh: below).

## Playing
| Step | Host (makes the lobby) | Everyone else |
| --- | --- | --- |
| 1 | **CREATE LOBBY** → a **lobby code** appears: 5 digits, like `48213`. **C** copies it. Send it to your friends (Discord, text...). **A** goes to the room (the first player to join takes you there too). | **JOIN LOBBY** → type the code (or paste it, Ctrl+V) → Enter. |
| 2 | **NAME** (on the online menu) sets the name the others see; empty = "Player 2" and so on (two of the same name get "(2)"). | |

**The room: king of the hill.**
- Everyone stands in **one line** (the list at the bottom: 1 = the king, 2 = the challenger, then who's next).
- The first two fight: the **KING** (left card, player 1 side) against the **CHALLENGER** (right card, player 2 side).
  They pick in the lobby: Left / Right = fighter, Up / Down = colour, S = assist, **A = ready** (B = not ready).
  They get **60 seconds** once both are in the lobby; then what they have is locked in.
- The **winner stays on** (the card says how many wins in a row), the **loser goes to the back of the line**, and the
  next two pick. With only two players that's a rematch every time.
- **Everyone else watches the fight live**: it opens on their screen by itself (VS screen, then the fight a moment
  behind the players, with **WATCHING** under the timer). **B** while watching = back to the lobby; **A** in the lobby
  = watch again. Someone who joins during a fight watches it from the start, fast-forwarded until it's live.
- **S** (when it isn't your turn) = **sit out**: you stay in the lobby and keep watching, out of the line. S again =
  back in line (at the back).
- The **host** picks the stage with **C** (RANDOM = a new one each match) and its Options rules are used (Options →
  Game Settings: rounds, round time, intros). **Start** (host) = the code screen again (backup / reply codes).
- After a fight everyone goes back to the lobby by themselves (5 seconds on the results screen, or press any button).
- Leaving during your own fight loses it (the other player wins). The host leaving closes the lobby for everyone.
- **B twice** (in the lobby) = leave.

**If someone can't get in:**
- Joining with the 5-digit code, both computers call each other at once by themselves (the joiner's address reaches
  the host through the board), which gets through most home routers. If it still says it can't reach the host, the
  host's router is blocking it: the host forwards **UDP port 7777** on their router to their computer (or turns on
  UPnP in the router's settings: the game opens the port by itself when UPnP is on, and says so under the code), then
  opens a new lobby.
- "**No lobby with the code ...**": check the number. A lobby closes when the host leaves its screen (and a code
  nobody refreshes is forgotten after 10 minutes).
- "**Couldn't reach the lobby-code service**": the board (ntfy.sh) is down or blocked on that network. The host
  presses **S** for the **backup code** (12 letters / numbers, like `K7Q2-M9X4-PA3D`): it holds the host's address
  itself and works without the board. With it, a joiner that can't get through gets a **REPLY CODE**: they send it
  to the host, who presses **S** again, types it and presses Enter (both computers then call each other).
- If the **host** can't reach the board, its screen shows the long code straight away (and says so); everything
  else works as before.
- Same house / same network: the 5-digit code works (the joiner also tries the host's local address). A plain
  address works as a code too: `192.168.1.20` or `192.168.1.20:7777`.
- Windows may ask to let the game through the firewall the first time: allow it (private and public networks).

## How it works
- **Connection:** `engine/netcode/NetsuOnline.cs` (autoload **NetsuOnline**, listed in `project.godot`), on LiteNetLib
  (UDP). The host opens port 7777 (or the next free one up to 7786) and works out its internet address: from the
  router (**UPnP**, Godot's `Upnp`, which also opens the port), else from a **STUN** server (Google's / Cloudflare's:
  "what address do you see me at?", asked from the game's own socket so the answer matches what the opponent will
  see). The connection request carries `NetsuOnline.ProtocolVersion`: different versions of the game are turned away.
- **Lobby codes (Oct 24 late):** the host picks a random number from 10000 to 99999 that nobody has posted a lobby on
  in the last 10 minutes, and posts `{"t":"host", "pub": its internet address, "lan": its local address, "v": the game
  version, "n": a random id}` on the ntfy.sh topic `netsu-vs-lobby-q7k3-<number>` (again every 4 minutes while it
  waits). The joiner reads the topic's last 10 minutes, calls the newest open lobby's two addresses, and posts
  `{"t":"join", its own internet address (STUN) and local address}`; the host listens to the topic (ntfy's JSON
  stream) and calls that address at once: both sides calling each other is UDP hole punching. Leaving posts
  `{"t":"closed"}`. Code: `NetsuOnline` `Board*` methods (`BoardClaim`, `BoardPoll`, `BoardPublish`, `BoardListen`).
  `NETSU_LOBBY_SERVER=https://...` (environment variable) points the game at another ntfy server: your own (ntfy is
  open source and easy to host), or a test one.
- **What's on the board:** anyone who knows (or guesses) a number can read what's posted under it: the host's
  internet address and port (the same thing the long code holds), and the joiner's. No names, no accounts, no game
  data. ntfy.sh keeps messages for some hours (12 by default).
- **The long code (backup):** the host's internet address + port packed into 60 bits (Crockford base 32: no I, L, O
  or U; a check byte catches typos; `NetsuOnline.Encode / ParseCode`). Joining with it: up to ~9 s of connection
  attempts, then the joiner's own STUN address as a **reply code** for the host to type in (the manual version of
  what the board does by itself).
- **Group lobbies (Oct 25):** a star: every player is connected to the host only (`NetsuOnline`: `MyId`, host 0,
  players 1, 2... handed out with the welcome; `MemberJoined` / `MemberLeft`). A joiner says hello (`H` + a random
  id, the same id it posted on the board) and gets its id back (`W`); a second connection from the same player (it
  calls the host's internet and local address at once) is closed. Up to `NetsuOnline.MaxMembers` = 8.
- **The room's rules:** `game/autoloads/online_room.gd` (autoload **OnlineRoom**). The host's copy decides everything
  (the line, the match, picks, the pick clock, results, forfeits) and sends the whole room to everyone after every
  change (`room`, JSON); the others send what they do: `hi` (name), `here` (lobby / fight / watch), `pick`,
  `result` (both players report the winner at the results screen; the first report counts), `queue` (sit out / back
  in line). Lobby messages are reliable JSON (`L` packets). Screen: `scenes/online/online_lobby.gd` (+ `.tscn`).
- **The fight:** `MatchSetup.start_online_room(p, side)` fills `data/match_settings.tres` (mode **Online**,
  `data/game_modes/GM_Online.tres`: rollback, no pause, no CPU) the same everywhere (fighters, colours, assists,
  stage, rules, the two names: the VS screen, HUD and win screen show them). Everyone calls `NetsuOnline.SetMatch(id,
  p1, p2)` first: the two players' `PleaseResyncManager.StartOnlineGame` take their connection from
  `NetsuOnline.CreateSessionAdapter()` (`NetsuOnlineAdapter`). Fight packets (`G`, unreliable) go straight to the
  other player when one of them is the host, else **through the host**, which passes them on as they are (adds the
  host's ping; rollback hides it). Each player reads its **own Player 1 controls** (keyboard 1 / controller 1). Input
  delay 2 frames, rollback up to 8 frames (PleaseResync defaults; `FrameDelay` on the RollbackManager node in
  `scenes/battle/battle.tscn`).
- **Spectators:** player 1's computer streams the match's **settled frames** (both players' inputs, as they were
  played; `Peer2PeerSession.ConfirmedFrame`, a few frames at a time) to the host (`S` packets, reliable); the host keeps
  the whole match and passes it to everyone who isn't fighting (a late joiner gets everything so far:
  `NetsuOnline.SendStreamTo`). A spectator runs no session: `PleaseResyncManager` plays the stream back frame by frame
  (`NetsuSpectateLoop`: 12 frames in hand before it starts, faster when far behind) through the same simulation, so it
  sees exactly the players' fight. Each computer keeps the last 3 matches' streams (a spectator a moment behind still
  gets the end of a match after the next one has started).
- **After the fight** `OnlineRoom` takes everyone back to the lobby (`GameManager.NetsuMatchResult()` says when the
  results screen is up and who won); the connections stay open. If the host leaves or the connection drops,
  `MatchSetup._on_online_disconnected` takes you back to the lobby screen with a message.
- **Desync check:** every 30 frames each side sends the checksum of a settled frame; a mismatch stops the fight
  ("Fatal desync detected"). Fixed Oct 24 to only compare frames both sides have settled (it could misfire with lag).

## Testing it
- Several copies on one computer: run the game 2-4 times (Godot: Debug → Customize Run Instances), CREATE LOBBY in
  one, JOIN with its 5-digit code (or `127.0.0.1`) in the others.
- **Fake lag:** start the game with the environment variable `NETSU_ONLINE_LAG="80,30,5"` (ms delay, ms jitter, % lost):
  the fight packets this copy receives are held back / dropped, to see the rollback work.
- Rollback correctness was checked Oct 24 with a sync test (every frame: save, run 8 frames, load, run them again,
  compare) over 40,000+ frames of random play with all three fighters, EX moves, supers, bursts and assists: no
  difference. And with two copies online (90 ms ± 40 ms and 8% loss): both computers had the same game state.
- The lobby codes (Oct 24 late) were tested with two copies against a stand-in for ntfy.sh (the test machine can't
  reach the real one): code claimed, looked up, joiner's address delivered to the host, fight started with both
  computers in the same state; an unknown number; the board unreachable (host falls back to the long code, a joiner
  typing a number is told to ask for the backup code); an address still works.
- **Group lobbies (Oct 25)** were tested with 3 and 4 copies (same stand-in board): king of the hill over 4-5 matches
  in a row (winner stays, loser to the back, a challenger taking over as king), matches between two non-hosts (packets
  through the host) with the host watching, a player joining in the middle of a fight (watched it from the start,
  caught up), sitting out and back in line, stopping watching and watching again, a player leaving mid-fight (the
  other won, everyone went back to the lobby), and lag + packet loss on the streaming player (120 rollbacks). In every
  match the players and every spectator ended with exactly the same health and gauges.

## Limits / not done
- Up to 8 per lobby, one fight at a time (king of the hill). No kicking yet (the pick clock keeps someone away from the
  controller from holding up the line).
- No matchmaking, no lobby list: the code is the invitation.
- Fights between two players who aren't the host go through the host: its connection matters for everyone.
- The 5-digit codes rely on ntfy.sh, a free service run by someone else: if it's down, use the backup code. A relay
  server of our own would also remove the router problems for good (later).
- Controller-only players can't type the code yet (keyboard or paste). With 5 digits a controller digit picker
  would be easy.
- IPv4 only.
- Both players need the **same build** of the game (same fighters, same data), or the fight goes out of sync.
