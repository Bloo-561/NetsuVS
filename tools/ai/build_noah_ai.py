"""Builds Noah's CPU (AI) files for all six difficulties.

    python tools/ai/build_noah_ai.py        (run from the project folder)

Writes actors/noah/AI/NOA_AIData.tres (his action list) and NOA_AI_Beginner / Easy / Normal / Hard / VeryHard /
Pro.tres. The files keep their uids. How the engine reads these: tools/ai/ai_common.py.

His plan (a mid-range controller with a devil arm, from tools/sprite_port/moves_noah.py): Shade Wave (236A / B)
from mid and far range, a black hole (623A near / 623B far) and the snap (623 again) to drag them in, Void Grasp
(214A, a lunging grab-strike) to stock energy, then 214A again = the Overflow Ray (the stock turns 214 + A into the
beam), Abyss Hammer (214B) as an overhead, 6C against jumpers, and meter into Umbral Wall (236C), Void Devour (214C)
or the supers (236BC Raging Storm, 214BC God Press).
Distances: 10000 = 1 metre.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ai_common import *

QCF = lambda b: [(D, 0), (D | F, 0), (F, b), (N, 0)]
QCB = lambda b: [(D, 0), (D | B, 0), (B, b), (N, 0)]
DP = lambda b: [(F, 0), (D, 0), (D | F, b), (N, 0)]
ACTIONS = [
    ("Walk Forward",        [(F, 0)], False, 0),                              # 0
    ("Walk Back / Guard",   [(B, 0)], False, 0),                              # 1
    ("Dash Forward",        [(F, 0), (N, 0), (F, 0)], True, 0),               # 2
    ("Back Dash",           [(B, 0), (N, 0), (B, 0), (N, 0)], True, 0),       # 3
    ("Jump Neutral",        [(U, 0), (N, 0)], True, 0),                       # 4
    ("Jump Forward",        [(U | F, 0), (N, 0)], True, 0),                   # 5
    ("Jump Back",           [(U | B, 0), (N, 0)], True, 0),                   # 6
    ("Crouch",              [(D, 0)], False, 0),                              # 7
    ("Crouch Guard",        [(D | B, 0)], False, 0),                          # 8
    ("A",                   [(N, BA), (N, 0)], False, 0),                     # 9   5A / j.A
    ("B",                   [(N, BB), (N, 0)], False, 0),                     # 10  5B / j.B
    ("C",                   [(N, BC), (N, 0)], False, 0),                     # 11  5C / j.C
    ("2A",                  [(D, BA), (N, 0)], False, 0),                     # 12
    ("2B",                  [(D, BB), (N, 0)], False, 0),                     # 13
    ("2C",                  [(D, BC), (N, 0)], False, 0),                     # 14
    ("Tech / Recover",      [(N, BA), (N, 0)], False, 0),                     # 15
    ("236A Shade Wave",     QCF(BA), False, 0),                               # 16
    ("236B Twin Shade",     QCF(BB), False, 0),                               # 17
    ("236C Umbral Wall",    QCF(BC), False, 0),                               # 18  (4000) invincible start
    ("623A Event Horizon",  DP(BA), False, 0),                                # 19  near hole (again: the snap)
    ("623B Event Horizon",  DP(BB), False, 0),                                # 20  far hole (again: the snap)
    ("623C Twin Horizon",   DP(BC), False, 0),                                # 21  (4000)
    ("214A Void Grasp",     QCB(BA), False, 0),                               # 22  (stocked: Overflow Ray)
    ("214B Abyss Hammer",   QCB(BB), False, 0),                               # 23  overhead
    ("214C Void Devour",    QCB(BC), False, 0),                               # 24  (4000) invincible
    ("236BC Raging Storm",  [(D, 0), (D | F, 0), (F, 0), (N, BB | BC), (N, 0)], False, 0),   # 25 (6000)
    ("214BC God Press",     [(D, 0), (D | B, 0), (B, 0), (N, BB | BC), (N, 0)], False, 0),   # 26 (6000)
    ("6C",                  [(F, BC), (N, 0)], False, 0),                     # 27  devil-arm uppercut: anti-air
    ("Wait",                [(N, 0)], True, 10),                              # 28
    ("Jump-in B (late)",    [(N, BB), (N, 0)], False, 14),                    # 29
    ("Jump-in C (late)",    [(N, BC), (N, 0)], False, 14),                    # 30
    ("2B after landing",    [(D, BB), (N, 0)], False, 10),                    # 31
    ("2A after dash",       [(D, BA), (N, 0)], False, 6),                     # 32
    ("Snap (623A again)",   DP(BA), False, 30),                               # 33  after a hole: wait, then set it off
    ("j.214A Fallen Grasp", QCB(BA), False, 8),                               # 34  in the air
]
X = add_common_actions(ACTIONS)
THROW, BACK_THROW, DASH_THROW_A, WAIT_LONG = X["throw"], X["back_throw"], X["dash_throw"], X["wait_long"]

BNB = [9, 10, 13, 22]                     # 5A > 5B > 2B > 214A Void Grasp (stocks)
LOW_BNB = [12, 13, 17]                    # 2A > 2B > 236B
SHORT = [9, 10]
LOW_SHORT = [12, 13]
METER_BNB = [9, 10, 13, 24]               # ... > 214C Void Devour (4000)
SUPER_BNB = [9, 10, 13, 25]               # ... > 236BC Raging Storm (6000)
GRAB_SUPER = [26]                         # 214BC God Press (6000)
WAVE = [16]
TWIN = [17]
HOLE_NEAR = [19, 33]                      # near hole, then the snap
HOLE_FAR = [20, 33]
RAY = [22]                                # with the stock, 214A is the beam; without, the lunge
HAMMER = [23]
FRAME_TRAP = [12, 28, 12, 13]
DASH_IN = [2, 32, 13, 22]
DASH_THROW = [2, DASH_THROW_A]
JUMP_IN = [5, 29, 31]
JUMP_IN_C = [5, 30, 31]
AIR_GRAB = [5, 34]
MEATY = [28, 12, 13, 17]
TICK_THROW = [WAIT_LONG, THROW]
KEEP_OUT = [3]
AIR_TO_AIR = [4, 9]
ANTI_AIR = [27]
AA_T, A2A_T = 7, 10
WAKEUP = [18]                             # wake-up: Umbral Wall (invincible start, 4000) when he has the meter

def level(n):
    """n 0 (Beginner) .. 5 (Pro): the same plan, more of it"""
    m = lambda base, step=1: max(1, base + step * (n - 2))
    near = [c(NEAR, BNB if n >= 2 else SHORT), c(NEAR, LOW_BNB if n >= 2 else LOW_SHORT, m(5)), c(NEAR, [THROW], m(3, 0)),
            c(NEAR, KEEP_OUT, 2), c(NEAR, [8], m(3, -1), DEF), c(NEAR, HAMMER, m(2, 0))]
    mid = [c(MID1, [0]), c(MID1, TWIN, m(4)), c(MID1, HOLE_NEAR, m(2)), c(MID1, [1], 3, DEF), c(MID1, KEEP_OUT, 2),
           c(MID2, WAVE), c(MID2, HOLE_FAR, m(3)), c(MID2, [2], 3), c(MID2, RAY, m(2))]
    far = [c(FAR, WAVE), c(FAR, HOLE_FAR, m(3)), c(FAR, [0], 4), c(FAR, [2], 2)]
    dist = [c(DIST, [2]), c(DIST, WAVE, 4)]
    near.append(react(AA, AIR_TO_AIR, AIR, startup=A2A_T))
    if n >= 1:
        near += [react(NEAR, SHORT, RECOVERY)]
    if n >= 2:
        near += [c(NEAR, FRAME_TRAP, 3), react(AA_DP, ANTI_AIR, AIR, startup=AA_T), react(NEAR, BNB, RECOVERY),
                 react(NEAR, TICK_THROW, BLOCKSTUN), react(NEAR, MEATY, KNOCKDOWN)]
        mid += [c(MID1, JUMP_IN, 3), react(MID1, TWIN, RECOVERY), react(MID2, RAY, RECOVERY)]
        far += [react(FAR, WAVE, RECOVERY)]
    if n >= 3:
        near += [c(NEAR, METER_BNB, m(5), gauge=4000), react(NEAR, GRAB_SUPER, RECOVERY, gauge=6000, chance=4),
                 c(NEAR, SUPER_BNB, m(5), AGG, gauge=6000)]
        mid += [c(MID1, AIR_GRAB, 2), c(MID1, DASH_IN, 3), react(MID1, MEATY, KNOCKDOWN),
                react(MID1, GRAB_SUPER, ATTACK, gauge=6000, chance=2)]
        far += [c(FAR, JUMP_IN, 2)]
    if n >= 4:
        mid += [c(MID1, JUMP_IN_C, 3), c(MID1, DASH_THROW, 2)]
    b = dict(near=near, mid=mid, far=far, distant=dist)
    if n >= 1: b['wakeup_actions'] = WAKEUP
    return b

BEHAVIOURS = {name: level(i) for i, name in enumerate(ORDER)}

if __name__ == "__main__":
    build("noah", "NOA", ACTIONS, BEHAVIOURS, X)
