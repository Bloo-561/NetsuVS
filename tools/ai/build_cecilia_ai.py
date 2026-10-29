"""Builds Cecilia's CPU (AI) files for all six difficulties.

    python tools/ai/build_cecilia_ai.py        (run from the project folder)

Writes actors/cecilia/AI/CEC_AIData.tres (her action list) and CEC_AI_Beginner / Easy / Normal / Hard /
VeryHard / Pro.tres (one behaviour per difficulty). The files keep their uids, so nothing that points at them
breaks. How the engine reads these, and the difficulty levels every fighter shares (speed, reactions,
guarding...): tools/ai/ai_common.py.

Her plan (rushdown with a sword): dash in or jump in, 5A / 2A strings into 236B Dash Slash, frame traps and
throws on block, anti-air with 623B Teleport Slash (invincible start), punish whiffs with a dash-in combo or a
Dash Slash from range, and cash meter into 236C (EX Dash Slash, a rush on hit) or 236BC Thunder Plunge.
Distances: 10000 = 1 metre.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ai_common import *

# name, inputs [(direction, buttons)], auto_advance, start_delay
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
    ("236C EX Dash Slash", [(D, 0), (D | F, 0), (F, BC), (N, 0)], False, 0),   # 16  (4000) dash; on hit a lightning rush
    ("236B Dash Slash",   [(D, 0), (D | F, 0), (F, BB), (N, 0)], False, 0),    # 17  dash slash, wall bounce (combo ender)
    ("236A Dash Slash", [(D, 0), (D | F, 0), (F, BA), (N, 0)], False, 0),      # 18  short dash slash
    ("623C EX Teleport Slash", [(F, 0), (D, 0), (D | F, BC), (N, 0)], False, 0),   # 19  (4000) invincible anti-air
    ("214C EX Lightning Dash", [(D, 0), (D | B, 0), (B, BC), (N, 0)], False, 0),  # 20  (4000) lightning dash, three slashes
    ("236BC Thunder Plunge",        [(D, 0), (D | F, 0), (F, 0), (N, BB | BC), (N, 0)], False, 0),  # 21 (6000) invincible
    ("6C",                  [(F, BC), (N, 0)], False, 0),                     # 22
    ("Wait",                [(N, 0)], True, 10),                              # 23  short pause (timing)
    ("Jump-in B (late)",    [(N, BB), (N, 0)], False, 14),                    # 24
    ("Jump-in C (late)",    [(N, BC), (N, 0)], False, 14),                    # 25
    ("2B after landing",    [(D, BB), (N, 0)], False, 10),                    # 26
    ("623B Teleport Slash",   [(F, 0), (D, 0), (D | F, BB), (N, 0)], False, 0),    # 27  invincible anti-air (no meter)
    ("2A after dash",       [(D, BA), (N, 0)], False, 6),                     # 28
    ("214BC Counter Thunderclap", [(D, 0), (D | B, 0), (B, 0), (N, BB | BC), (N, 0)], False, 0),  # 29 (6000) counter super
    ("214B Lightning Dash", [(D, 0), (D | B, 0), (B, BB), (N, 0)], False, 0),  # 30  lightning dash
    ("623A Teleport Slash A", [(F, 0), (D, 0), (D | F, BA), (N, 0)], False, 0),    # 31  anti-air, vulnerable start
]
X = add_common_actions(ACTIONS)            # throw, back_throw, dash_throw, wait_long, wait_short
THROW, BACK_THROW, DASH_THROW_A, WAIT_LONG = X["throw"], X["back_throw"], X["dash_throw"], X["wait_long"]

# Combos and plans (lists of action numbers)
BNB = [9, 10, 13, 17]                     # 5A > 5B > 2B > 236B Dash Slash
LOW_BNB = [12, 13, 17]                    # 2A > 2B > 236B
SHORT = [9, 10]                           # 5A > 5B
LOW_SHORT = [12, 13]                      # 2A > 2B
METER_BNB = [9, 10, 13, 16]               # ... > 236C EX Dash Slash (4000)
SUPER_BNB = [9, 10, 13, 21]               # ... > 236BC Thunder Plunge (6000)
FRAME_TRAP = [12, 23, 12, 13]             # 2A, pause, 2A > 2B
DASH_IN = [2, 28, 13, 17]                 # dash > 2A > 2B > 236B
DASH_THROW = [2, DASH_THROW_A]            # dash > throw
JUMP_IN = [5, 24, 26]                     # jump in > late j.B > land 2B
JUMP_IN_C = [5, 25, 26]                   # same with j.C
MEATY = [23, 12, 13, 17]                  # wait for wake-up > 2A > 2B > 236B
TICK_THROW = [WAIT_LONG, THROW]           # (they're blocking) let blockstun end > throw
AIR_TO_AIR = [4, 9]                       # neutral jump > j.A
ANTI_AIR = [27]                           # 623B Teleport Slash (invincible)
ANTI_AIR_EX = [19]                        # 623C EX Teleport Slash (4000)
AA_T, AA_EX_T, A2A_T = 7, 0, 10           # anti-air start-ups: frames from the press to the hit (the EX's flash freezes them first)
COUNTER_SUPER = [29]                      # 214BC Counter Thunderclap: waits for their attack (6000)
DASH_SLASH = [17]                         # 236B from range (punish / approach)
LIGHTNING = [30]                          # 214B Lightning Dash (approach, slashes when it reaches them)
WAKEUP = [27]                             # wake-up reversal: 623B

BEHAVIOURS = {
    "Beginner": dict(
        near=[c(NEAR, [9]), c(NEAR, [12], 4), c(NEAR, [10], 3), c(NEAR, [1], 3, DEF), c(NEAR, [4], 2), c(NEAR, [23], 3),
              react(AA, AIR_TO_AIR, AIR, startup=A2A_T)],
        mid=[c(MID2, [0]), c(MID2, [18], 2), c(MID2, [23], 3), c(MID2, [1], 3, DEF), c(MID2, [5], 2)],
        far=[c(FAR, [0]), c(FAR, [23], 4), c(FAR, [5], 1)],
        distant=[c(DIST, [0]), c(DIST, [23], 3)],
    ),
    "Easy": dict(
        near=[c(NEAR, SHORT), c(NEAR, LOW_SHORT, 5), c(NEAR, [10], 3), c(NEAR, [THROW], 2), c(NEAR, [9], 3),
              c(NEAR, [1], 3, DEF), c(NEAR, [4], 2),
              react(AA, AIR_TO_AIR, AIR, startup=A2A_T), react(NEAR, SHORT, RECOVERY)],
        mid=[c(MID2, [0]), c(MID2, [2], 4), c(MID2, [5, 24], 3), c(MID2, [1], 3, DEF), c(MID2, [18], 2)],
        far=[c(FAR, [0]), c(FAR, [2], 4), c(FAR, [5], 2)],
        distant=[c(DIST, [2]), c(DIST, [0], 5)],
        wakeup_actions=WAKEUP,
    ),
    "Normal": dict(
        near=[c(NEAR, BNB), c(NEAR, LOW_BNB, 5), c(NEAR, FRAME_TRAP, 3), c(NEAR, [THROW], 3), c(NEAR, SHORT, 3),
              c(NEAR, [8], 2, DEF), c(NEAR, [3], 2, DEF),
              react(AA_DP, ANTI_AIR, AIR, startup=AA_T), react(AA, AIR_TO_AIR, AIR, startup=A2A_T),
              react(NEAR, BNB, RECOVERY), react(NEAR, LOW_SHORT, BLOCKSTUN), react(NEAR, TICK_THROW, BLOCKSTUN),
              react(NEAR, MEATY, KNOCKDOWN)],
        mid=[c(MID1, [0]), c(MID1, DASH_IN, 4), c(MID1, JUMP_IN, 3), c(MID1, DASH_THROW, 2), c(MID1, [1], 2, DEF),
             react(MID1, DASH_IN, RECOVERY),
             c(MID2, [0]), c(MID2, [2], 5), c(MID2, [5], 3), c(MID2, DASH_SLASH, 2)],
        far=[c(FAR, [2]), c(FAR, [0], 4), c(FAR, [5], 3), c(FAR, LIGHTNING, 2)],
        distant=[c(DIST, [2]), c(DIST, [0], 4)],
        wakeup_actions=WAKEUP,
    ),
    "Hard": dict(
        near=[c(NEAR, BNB), c(NEAR, LOW_BNB, 6), c(NEAR, METER_BNB, 5, gauge=4000), c(NEAR, FRAME_TRAP, 3),
              c(NEAR, [THROW], 3), c(NEAR, [BACK_THROW], 1), c(NEAR, [8], 2, DEF),
              c(NEAR, SUPER_BNB, 5, AGG, gauge=6000),   # last = wins most often
              react(AA_DP, ANTI_AIR, AIR, startup=AA_T), react(AA_DP, ANTI_AIR_EX, AIR, gauge=4000, startup=AA_EX_T),
              react(NEAR, BNB, RECOVERY), react(NEAR, SUPER_BNB, RECOVERY, gauge=6000, chance=5),
              react(NEAR, COUNTER_SUPER, ATTACK, gauge=6000, chance=2),
              react(NEAR, FRAME_TRAP, BLOCKSTUN), react(NEAR, TICK_THROW, BLOCKSTUN), react(NEAR, MEATY, KNOCKDOWN)],
        mid=[c(MID1, DASH_IN), c(MID1, JUMP_IN, 4), c(MID1, DASH_THROW, 3), c(MID1, [0], 3), c(MID1, [1], 2, DEF),
             react(MID1, DASH_IN, RECOVERY), react(MID1, MEATY, KNOCKDOWN),
             c(MID2, [2]), c(MID2, JUMP_IN, 3), c(MID2, [0], 3), c(MID2, DASH_SLASH, 2),
             react(MID2, DASH_SLASH, RECOVERY)],
        far=[c(FAR, [2]), c(FAR, JUMP_IN, 3), c(FAR, [0], 3), c(FAR, LIGHTNING, 2)],
        distant=[c(DIST, [2])],
        wakeup_actions=WAKEUP,
    ),
    "VeryHard": dict(
        near=[c(NEAR, BNB), c(NEAR, LOW_BNB, 6), c(NEAR, METER_BNB, 6, gauge=4000), c(NEAR, FRAME_TRAP, 4),
              c(NEAR, [THROW], 4), c(NEAR, [BACK_THROW], 2), c(NEAR, [8], 2, DEF),
              c(NEAR, SUPER_BNB, 6, AGG, gauge=6000),
              react(AA_DP, ANTI_AIR, AIR, startup=AA_T), react(AA_DP, ANTI_AIR_EX, AIR, gauge=4000, startup=AA_EX_T),
              react(NEAR, BNB, RECOVERY), react(NEAR, SUPER_BNB, RECOVERY, gauge=6000, chance=5),
              react(NEAR, COUNTER_SUPER, ATTACK, gauge=6000, chance=2),
              react(NEAR, FRAME_TRAP, BLOCKSTUN), react(NEAR, TICK_THROW, BLOCKSTUN), react(NEAR, LOW_BNB, BLOCKSTUN),
              react(NEAR, MEATY, KNOCKDOWN)],
        mid=[c(MID1, DASH_IN), c(MID1, JUMP_IN, 4), c(MID1, JUMP_IN_C, 3), c(MID1, DASH_THROW, 3), c(MID1, [1], 2, DEF),
             react(MID1, DASH_IN, RECOVERY), react(MID1, MEATY, KNOCKDOWN),
             c(MID2, [2]), c(MID2, JUMP_IN, 3), c(MID2, DASH_SLASH, 2),
             react(MID2, DASH_SLASH, RECOVERY)],
        far=[c(FAR, [2]), c(FAR, JUMP_IN, 3), c(FAR, LIGHTNING, 2)],
        distant=[c(DIST, [2])],
        wakeup_actions=WAKEUP,
    ),
    "Pro": dict(
        near=[c(NEAR, BNB), c(NEAR, LOW_BNB, 6), c(NEAR, METER_BNB, 7, gauge=4000), c(NEAR, FRAME_TRAP, 4),
              c(NEAR, [THROW], 4), c(NEAR, [BACK_THROW], 2), c(NEAR, [8], 2, DEF),
              c(NEAR, SUPER_BNB, 7, AGG, gauge=6000),
              react(AA_DP, ANTI_AIR, AIR, startup=AA_T), react(AA_DP, ANTI_AIR_EX, AIR, gauge=4000, startup=AA_EX_T),
              react(NEAR, BNB, RECOVERY), react(NEAR, SUPER_BNB, RECOVERY, gauge=6000, chance=5),
              react(NEAR, COUNTER_SUPER, ATTACK, gauge=6000, chance=2),
              react(NEAR, FRAME_TRAP, BLOCKSTUN), react(NEAR, TICK_THROW, BLOCKSTUN), react(NEAR, LOW_BNB, BLOCKSTUN),
              react(NEAR, MEATY, KNOCKDOWN)],
        mid=[c(MID1, DASH_IN), c(MID1, JUMP_IN, 3), c(MID1, JUMP_IN_C, 4), c(MID1, DASH_THROW, 3), c(MID1, [1], 2, DEF),
             react(MID1, DASH_IN, RECOVERY), react(MID1, MEATY, KNOCKDOWN),
             c(MID2, [2]), c(MID2, JUMP_IN, 3), c(MID2, DASH_SLASH, 2),
             react(MID2, DASH_SLASH, RECOVERY)],
        far=[c(FAR, [2]), c(FAR, JUMP_IN, 2), c(FAR, LIGHTNING, 2)],
        distant=[c(DIST, [2])],
        wakeup_actions=WAKEUP,
    ),
}

if __name__ == "__main__":
    build("cecilia", "CEC", ACTIONS, BEHAVIOURS, X)
