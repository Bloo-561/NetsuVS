"""Shared parts of the CPU builders (tools/ai/build_<fighter>_ai.py, Oct 24 2026 night): the six difficulty levels,
the actions every fighter has (throws, waits), the condition helper and the .tres writers.

A fighter's script lists its own ACTIONS (its inputs), its game plans (lists of action numbers) and, per
difficulty, what it does at each distance (near / mid / far / distant). Everything that makes a level harder
or easier for every fighter alike (how fast it thinks and reacts, how well it guards...) is in LEVELS below.

How the engine reads it (engine/sakuga/Components/AIBrain.cs):
  * Every DecisionRate frames it measures the distance to the opponent and picks the near / mid / far /
    distant list. In a list, the FIRST condition whose distance fits is the default; every later condition
    with the same distance rolls its Probability (0-10) and replaces it on success (so the last ones win
    most often). ActionMode makes a condition likelier when healthy (AGG) or low on health (DEF).
  * "counter" conditions (Probability 0 + CounterFlags) are REACTIONS: checked every frame, once per opponent
    move, after `reaction` frames, with a `predict`-in-10 chance: AIR = anti-air (judged from the jump),
    RECOVERY = punish (the opponent's attack has nothing more to come out), BLOCKSTUN = they're blocking
    (pressure: frame trap, throw), KNOCKDOWN = they're down (meaty), ATTACK = they're attacking.
  * It guards attacks it sees coming (any attack box of the opponent's side, NetsuLookAhead frames ahead,
    plus jump-ins and rushing attacks) after `reaction` frames with a `block`-in-10 chance and picks the
    right height with `accuracy`-in-10, and keeps guarding `guard_hold` frames after.
  * A list of actions is a combo: attacks wait to connect, then `combo` / `confirm` decide whether to go on.
Distances: 10000 = 1 metre.
"""
import os
import re
import random
import string

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

F, B, U, D, N = 4, 2, 8, 1, 0            # directions (forward / back / up / down / neutral)
BA, BB, BC = 1, 2, 4                     # buttons A, B, C

# Opponent state flags (engine/sakuga/Globals/AIFlags.cs)
IDLE, GROUND, AIR, MOVE, ATTACK, HITSTUN, BLOCKSTUN, KNOCKDOWN = 1, 2, 4, 8, 16, 32, 64, 128
RECOVERY = 0x2000                        # AIFlags.NETSU_RECOVERY: worked out by the CPU (punish window)

AGG, DEF, ANY = 0, 1, -1

NEAR, MID1, MID2, FAR, DIST = 16000, 30000, 45000, 85000, 999999
AA = 26000                               # anti-airs: considered for a jumper within 2.6 m; WHEN it fires is worked out
AA_DP = 26000                            # by the CPU from the jump (AIBrain.NetsuAntiAirTime), not from this distance

# ------------------------------------------------------------------------------------------------- levels ----
# free / busy: frames between decisions (idle / in the middle of something); inputs: frames per input step;
# reaction: frames before it reacts to something it sees (guard, anti-air, punish); block / accuracy: chance in
# 10 to guard an attack it sees / to pick the right height; guard_hold: frames it keeps guarding after;
# guard_habit: chance in 10, at each decision with the opponent within 1.8 m, to hold crouch guard until the next one;
# tech: throw breaks and air recoveries (in 10); predict: chance in 10 for each reaction; combo / confirm:
# keep a combo going / stop it when blocked; assist: assist calls (5 = 10% a try in neutral, 50% in a combo);
# wakeup: chance in 10 of the wake-up reversal when the opponent is close.
LEVELS = {
    "Beginner": dict(free=(45, 80), busy=(70, 100), inputs=(6, 10), reaction=24, block=2, accuracy=4, guard_hold=4, guard_habit=1,
                     tech=0, predict=1, combo=2, confirm=0, assist=1, wakeup=0, low_health=4000),
    "Easy":     dict(free=(30, 56), busy=(50, 80), inputs=(4, 7), reaction=19, block=4, accuracy=6, guard_hold=6, guard_habit=2,
                     tech=2, predict=3, combo=4, confirm=1, assist=3, wakeup=1, low_health=4000),
    "Normal":   dict(free=(16, 32), busy=(36, 56), inputs=(3, 5), reaction=15, block=6, accuracy=7, guard_hold=9, guard_habit=3,
                     tech=4, predict=5, combo=7, confirm=4, assist=5, wakeup=2, low_health=4000),
    "Hard":     dict(free=(10, 22), busy=(24, 38), inputs=(2, 4), reaction=11, block=7, accuracy=8, guard_hold=11, guard_habit=4,
                     tech=6, predict=7, combo=9, confirm=6, assist=6, wakeup=3, low_health=4000),
    "VeryHard": dict(free=(6, 14), busy=(15, 28), inputs=(1, 3), reaction=8, block=8, accuracy=9, guard_hold=12, guard_habit=4,
                     tech=7, predict=8, combo=10, confirm=8, assist=7, wakeup=4, low_health=3500),
    "Pro":      dict(free=(3, 8), busy=(8, 16), inputs=(1, 2), reaction=5, block=9, accuracy=10, guard_hold=14, guard_habit=5,
                     tech=8, predict=10, combo=10, confirm=10, assist=8, wakeup=5, low_health=3000),
}
ORDER = ["Beginner", "Easy", "Normal", "Hard", "VeryHard", "Pro"]


def c(dist, actions, prob=10, mode=ANY, ground=True, air=False, counter=0, gauge=0, chance=10, startup=-1):
    """one condition of a distance list: up to `dist` away, do `actions` (a list of action numbers)"""
    return dict(dist=dist, actions=list(actions), prob=prob, mode=mode, ground=ground, air=air,
                counter=counter, gauge=gauge, chance=chance, startup=startup)


def react(dist, actions, flags, gauge=0, air=False, chance=10, startup=-1):
    """a reaction (see the module doc): Probability 0 + CounterFlags. `chance` (0-10) on top of the level's
    predict: lower for a costly or risky read (a counter super). `startup` (anti-airs): frames from the button
    press to the first hit as the opponent sees them (0 for an EX: its flash freezes them first; -1 = 7); the CPU
    fires it that long, plus the time to input it, before the jumper is in reach"""
    return c(dist, actions, 0, ANY, ground=not air, air=air, counter=flags, gauge=gauge, chance=chance, startup=startup)


def add_common_actions(actions):
    """appends the actions every fighter has to its ACTIONS list; returns {name: action number}"""
    extra = [
        ("throw", ("Throw (B+C) / throw break", [(N, BB | BC), (N, 0)], False, 0)),
        ("back_throw", ("Back throw (4 + B+C)", [(B, BB | BC), (N, 0)], False, 0)),
        ("dash_throw", ("Throw after a dash", [(N, BB | BC), (N, 0)], False, 7)),
        ("wait_long", ("Wait (blockstun + throw protection)", [(N, 0)], True, 16)),
        ("wait_short", ("Short wait", [(N, 0)], True, 4)),
    ]
    out = {}
    for key, act in extra:
        out[key] = len(actions)
        actions.append(act)
    return out


# ------------------------------------------------------------------------------------------------ writing ----
S_INPUT = 'uid://qkcdnntram58'
S_ACTION = 'uid://be0e6utc5xgk8'
S_DATA = 'uid://dhvotekjrqw07'
S_COND = 'uid://bogcblgipf4f7'
S_PACK = 'uid://c6pe4r5xpq803'
S_BEHAV = 'uid://bdbcupbr6mour'


def file_uid(path, seed):
    """the uid the file already has (so references to it keep working), else a stable new one"""
    if os.path.exists(path):
        m = re.search(r'uid="(uid://[a-z0-9]+)"', open(path, encoding="utf-8").readline())
        if m:
            return m.group(1)
    rnd = random.Random(seed)
    return "uid://" + rnd.choice("abcd") + "".join(rnd.choice(string.ascii_lowercase + string.digits) for _ in range(12))


def _arr(xs):
    return "PackedInt32Array(%s)" % ", ".join(str(int(x)) for x in xs)


def write_behaviour(path, uid, b):
    lines = [f'[gd_resource type="Resource" script_class="AIBehavior" format=3 uid="{uid}"]', "",
             f'[ext_resource type="Script" uid="{S_COND}" path="res://engine/sakuga/Resources/AI/AICondition.cs" id="1"]',
             f'[ext_resource type="Script" uid="{S_PACK}" path="res://engine/sakuga/Resources/AI/AIActionPack.cs" id="2"]',
             f'[ext_resource type="Script" uid="{S_BEHAV}" path="res://engine/sakuga/Resources/AI/AIBehavior.cs" id="3"]', ""]
    packs = {}
    for key, horiz in [("near", NEAR), ("mid", MID2), ("far", FAR), ("distant", DIST)]:
        ids = []
        for i, cond in enumerate(b[key]):
            cid = f"{key}_{i}"
            ids.append(cid)
            lines += [f'[sub_resource type="Resource" id="{cid}"]', 'script = ExtResource("1")',
                      f"Distance = Vector2i({cond['dist']}, 0)",
                      f"UseOnGround = {'true' if cond['ground'] else 'false'}",
                      f"UseOnAir = {'true' if cond['air'] else 'false'}",
                      f"SuperGaugeRequired = {cond['gauge']}",
                      f"Probability = {cond['prob']}",
                      f"ActionMode = {cond['mode']}",
                      f"ActionsList = {_arr(cond['actions'])}",
                      f"ReactChance = {cond.get('chance', 10)}",
                      f"NetsuStartup = {cond.get('startup', -1)}",
                      f"CounterFlags = {cond['counter']}", ""]
        pid = f"pack_{key}"
        lines += [f'[sub_resource type="Resource" id="{pid}"]', 'script = ExtResource("2")',
                  f"HorizontalDistance = {horiz}",
                  "Conditions = [" + ", ".join(f'SubResource("{x}")' for x in ids) + "]", ""]
        packs[key] = pid
    lines += ["[resource]", 'script = ExtResource("3")',
              "DecisionRateFree = Vector2i(%d, %d)" % b["free"],
              "DecisionRateBusy = Vector2i(%d, %d)" % b["busy"],
              "InputRandomness = Vector2i(%d, %d)" % b["inputs"],
              f"BlockingRate = {b['block']}", f"TechingRate = {b['tech']}",
              f"PredictionQuality = {b['predict']}", f"LowHealth = {b['low_health']}",
              f"ComboSkill = {b['combo']}", f"BlockConfirm = {b['confirm']}", f"BlockAccuracy = {b['accuracy']}",
              f"ReactionTime = {b['reaction']}", f"GuardHold = {b['guard_hold']}", f"GuardHabit = {b['guard_habit']}",
              f"AssistRate = {b['assist']}",
              f"WakeupRate = {b['wakeup']}", f"WakeupReversal = {_arr(b.get('wakeup_actions', []))}",
              f"WakeupGauge = {b.get('wakeup_gauge', 0)}",
              f'NearActions = SubResource("{packs["near"]}")', f'MidActions = SubResource("{packs["mid"]}")',
              f'FarActions = SubResource("{packs["far"]}")', f'DistantActions = SubResource("{packs["distant"]}")', ""]
    open(path, "w", encoding="utf-8", newline="\n").write("\n".join(lines))


def write_data(path, uid, folder, tag, actions, behaviour_uids, high_block, low_block, recover, throw_break):
    lines = [f'[gd_resource type="Resource" script_class="AIData" format=3 uid="{uid}"]', "",
             f'[ext_resource type="Script" uid="{S_INPUT}" path="res://engine/sakuga/Resources/AI/AIInput.cs" id="1"]',
             f'[ext_resource type="Script" uid="{S_ACTION}" path="res://engine/sakuga/Resources/AI/AIAction.cs" id="2"]',
             f'[ext_resource type="Script" uid="{S_DATA}" path="res://engine/sakuga/Resources/AI/AIData.cs" id="3"]']
    slots = [("BehaviorBeginner", "Beginner"), ("BehaviorEasy", "Easy"), ("BehaviorMedium", "Normal"),
             ("BehaviorHard", "Hard"), ("BehaviorVeryHard", "VeryHard"), ("BehaviorPro", "Pro")]
    for i, (_, name) in enumerate(slots):
        lines.append(f'[ext_resource type="Resource" uid="{behaviour_uids[name]}" '
                     f'path="res://actors/{folder}/AI/{tag}_AI_{name}.tres" id="b{i}"]')
    lines.append("")
    action_ids = []
    for a, (name, inputs, auto, delay) in enumerate(actions):
        input_ids = []
        for k, (d, btn) in enumerate(inputs):
            iid = f"in_{a}_{k}"
            input_ids.append(iid)
            lines += [f'[sub_resource type="Resource" id="{iid}"]', 'script = ExtResource("1")']
            if d:
                lines.append(f"Direction = {d}")
            if btn:
                lines.append(f"Buttons = {btn}")
            lines.append("")
        aid = f"act_{a}"
        action_ids.append(aid)
        lines += [f'[sub_resource type="Resource" id="{aid}"]', 'script = ExtResource("2")',
                  f'InputName = "{name}"',
                  "Inputs = [" + ", ".join(f'SubResource("{x}")' for x in input_ids) + "]",
                  f"AutoAdvance = {'true' if auto else 'false'}", f"StartDelay = {delay}", ""]
    lines += ["[resource]", 'script = ExtResource("3")',
              "Actions = [" + ", ".join(f'SubResource("{x}")' for x in action_ids) + "]",
              f"HighBlockAction = {high_block}", f"LowBlockAction = {low_block}",
              f"ForwardRecoveryAction = {recover}", f"BackRecoveryAction = {recover}", f"ThrowEscapeAction = {throw_break}"]
    for i, (slot, _) in enumerate(slots):
        lines.append(f'{slot} = ExtResource("b{i}")')
    lines.append("")
    open(path, "w", encoding="utf-8", newline="\n").write("\n".join(lines))


def build(folder, tag, actions, behaviours, common, high_block=1, low_block=8, recover=15):
    """writes actors/<folder>/AI/<tag>_AIData.tres and <tag>_AI_<Level>.tres (keeps their uids)"""
    out = os.path.join(ROOT, "actors", folder, "AI")
    os.makedirs(out, exist_ok=True)
    paths = {name: os.path.join(out, f"{tag}_AI_{name}.tres") for name in ORDER}
    uids = {name: file_uid(paths[name], f"{folder}-ai-{name}") for name in ORDER}   # read before anything is rewritten
    data_path = os.path.join(out, f"{tag}_AIData.tres")
    data_uid = file_uid(data_path, f"{folder}-ai-data")
    for name in ORDER:
        b = dict(LEVELS[name])
        b.update(behaviours[name])
        for key in ("near", "mid", "far", "distant"):
            for cond in b[key]:
                assert all(0 <= x < len(actions) for x in cond["actions"]), (name, key, cond)
        assert all(0 <= x < len(actions) for x in b.get("wakeup_actions", [])), (name, "wakeup")
        write_behaviour(paths[name], uids[name], b)
        print("wrote", os.path.relpath(paths[name], ROOT))
    write_data(data_path, data_uid, folder, tag, actions, uids, high_block, low_block, recover, common["throw"])
    print("wrote", os.path.relpath(data_path, ROOT), "-", len(actions), "actions")
