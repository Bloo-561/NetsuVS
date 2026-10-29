"""Builds Flan's CPU (AI) files for all six difficulties.

    python tools/ai/build_flan_ai.py        (run from the project folder)

Writes actors/flan/AI/FLN_AIData.tres (her action list) and FLN_AI_Beginner / Easy / Normal / Hard / VeryHard /
Pro.tres (one behaviour per difficulty). The files keep their uids, so nothing that points at them breaks.
How the engine reads these, and the difficulty levels every fighter shares (speed, reactions, guarding...):
tools/ai/ai_common.py.

Her plan (an armoured brawler, from her moves in tools/sprite_port/moves_flan.py): walk in, press with 5A / 2A
strings into 236B (the twirl absorbs one hit), mix up with Meteor Drop (214A/B: a rising knee, then an overhead
falling punch) and throws, anti-air with 6C or Rising Star (623B, with the Falling Star follow-up), punish with
a dash-in combo or Star Fist from range, and cash meter into Supernova Fist (236C) or Radiant Breaker (236BC).
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
    ("2C",                  [(D, BC), (N, 0)], False, 0),                     # 14  slide
    ("Tech / Recover",      [(N, BA), (N, 0)], False, 0),                     # 15
    ("236C Supernova Fist", [(D, 0), (D | F, 0), (F, BC), (N, 0)], False, 0),            # 16  (4000) invincible, crumples
    ("236B Twirling Star Fist", [(D, 0), (D | F, 0), (F, BB), (N, 0)], False, 0),        # 17  absorbs one hit
    ("236A Star Fist",      [(D, 0), (D | F, 0), (F, BA), (N, 0)], False, 0),            # 18  lunge
    ("623C Spiral Star",    [(F, 0), (D, 0), (D | F, BC), (N, 0)], False, 0),            # 19  (4000) invincible
    ("214C Meteor Impact",  [(D, 0), (D | B, 0), (B, BC), (N, 0)], False, 0),            # 20  (4000)
    ("236BC Radiant Breaker", [(D, 0), (D | F, 0), (F, 0), (N, BB | BC), (N, 0)], False, 0),   # 21 (6000) dash punch super
    ("Falling Star (any button)", [(N, BA), (N, 0)], False, 16),                         # 22  after 623A/B, at the top
    ("Wait",                [(N, 0)], True, 10),                              # 23  short pause (timing)
    ("Jump-in B (late)",    [(N, BB), (N, 0)], False, 14),                    # 24  knee
    ("Jump-in C (late)",    [(N, BC), (N, 0)], False, 14),                    # 25  swipe
    ("2B after landing",    [(D, BB), (N, 0)], False, 10),                    # 26
    ("623B Rising Star",    [(F, 0), (D, 0), (D | F, BB), (N, 0)], False, 0),            # 27  invincible start: anti-air
    ("2A after dash",       [(D, BA), (N, 0)], False, 6),                     # 28
    ("214BC Big Bang Crash", [(D, 0), (D | B, 0), (B, 0), (N, BB | BC), (N, 0)], False, 0),    # 29 (6000) rising punch super
    ("214A Meteor Drop",    [(D, 0), (D | B, 0), (B, BA), (N, 0)], False, 0),            # 30  knee, then overhead
    ("623A Rising Star",    [(F, 0), (D, 0), (D | F, BA), (N, 0)], False, 0),            # 31
    ("214B Meteor Drop",    [(D, 0), (D | B, 0), (B, BB), (N, 0)], False, 0),            # 32  higher
    ("6C fist pump",        [(F, BC), (N, 0)], False, 0),                     # 33  anti-air normal
]
X = add_common_actions(ACTIONS)            # throw, back_throw, dash_throw, wait_long, wait_short
THROW, BACK_THROW, DASH_THROW_A, WAIT_LONG = X["throw"], X["back_throw"], X["dash_throw"], X["wait_long"]

# Combos and plans (lists of action numbers)
BNB = [9, 10, 11, 18]                     # 5A > 5B > 5C > 236A Star Fist (236B is too slow to combo)
LOW_BNB = [12, 13, 18]                    # 2A > 2B > 236A
SHORT = [9, 10]                           # 5A > 5B
LOW_SHORT = [12, 13]                      # 2A > 2B
SLIDE = [12, 13, 14]                      # 2A > 2B > 2C (knockdown)
METER_BNB = [9, 10, 11, 16]               # ... > 236C Supernova Fist (4000)
SUPER_BNB = [9, 10, 11, 21]               # ... > 236BC Radiant Breaker (6000)
ARMOR = [17]                              # 236B: walks through a poke
LUNGE = [18]                              # 236A from mid range
METEOR = [30]                             # 214A: knee, overhead punch
METEOR_B = [32]
FRAME_TRAP = [12, 23, 13]                 # 2A, pause, 2B (her 2A is too short after the pushback)
DASH_IN = [2, 28, 13, 18]                 # dash > 2A > 2B > 236A
DASH_THROW = [2, DASH_THROW_A]            # dash > throw
JUMP_IN = [5, 24, 26]                     # jump in > late j.B knee > land 2B
JUMP_IN_C = [5, 25, 26]                   # same with j.C
MEATY = [23, 12, 13, 18]                  # wait for wake-up > 2A > 2B > 236A
TICK_THROW = [WAIT_LONG, THROW]           # (they're blocking) let blockstun end > throw
AIR_TO_AIR = [4, 9]                       # neutral jump > j.A
ANTI_AIR = [27, 22]                       # 623B Rising Star (invincible start) > Falling Star
ANTI_AIR_6C = [33]                        # 6C fist pump
ANTI_AIR_EX = [19]                        # 623C Spiral Star (4000)
AA_T, AA_6C_T, AA_EX_T = 5, 16, 0        # anti-air start-ups: frames from the press to the hit (the EX's flash freezes them first)
AA_SUPER = [29]                           # 214BC Big Bang Crash: rising punch that catches jumps (6000)
WAKEUP = [27, 22]                         # wake-up reversal: 623B > Falling Star

BEHAVIOURS = {
    "Beginner": dict(
        near=[c(NEAR, [9]), c(NEAR, [12], 4), c(NEAR, [10], 3), c(NEAR, [1], 3, DEF), c(NEAR, [4], 2), c(NEAR, [23], 3),
              react(AA, ANTI_AIR_6C, AIR, startup=AA_6C_T)],
        mid=[c(MID2, [0]), c(MID2, LUNGE, 2), c(MID2, [23], 3), c(MID2, [1], 3, DEF), c(MID2, [5], 2)],
        far=[c(FAR, [0]), c(FAR, [23], 4), c(FAR, [5], 1)],
        distant=[c(DIST, [0]), c(DIST, [23], 3)],
    ),
    "Easy": dict(
        near=[c(NEAR, SHORT), c(NEAR, LOW_SHORT, 5), c(NEAR, [10], 3), c(NEAR, [9], 3), c(NEAR, [THROW], 3),
              c(NEAR, [1], 3, DEF), c(NEAR, METEOR, 2),
              react(AA, ANTI_AIR_6C, AIR, startup=AA_6C_T), react(NEAR, SHORT, RECOVERY)],
        mid=[c(MID2, [0]), c(MID2, LUNGE, 4), c(MID2, [5, 24], 3), c(MID2, [1], 3, DEF)],
        far=[c(FAR, [0]), c(FAR, [2], 3)],
        distant=[c(DIST, [0]), c(DIST, [2], 3)],
        wakeup_actions=WAKEUP,
    ),
    "Normal": dict(
        near=[c(NEAR, BNB), c(NEAR, LOW_BNB, 5), c(NEAR, FRAME_TRAP, 3), c(NEAR, [THROW], 4), c(NEAR, METEOR, 3),
              c(NEAR, [8], 2, DEF), c(NEAR, SLIDE, 3),
              react(AA, ANTI_AIR_6C, AIR, startup=AA_6C_T), react(AA_DP, ANTI_AIR, AIR, startup=AA_T),
              react(NEAR, BNB, RECOVERY), react(NEAR, LOW_SHORT, BLOCKSTUN), react(NEAR, TICK_THROW, BLOCKSTUN),
              react(NEAR, MEATY, KNOCKDOWN)],
        mid=[c(MID1, [0]), c(MID1, ARMOR, 3), c(MID1, JUMP_IN, 3), c(MID1, LUNGE, 3), c(MID1, DASH_THROW, 2),
             c(MID1, [1], 2, DEF),
             react(MID1, DASH_IN, RECOVERY), react(MID1, LUNGE, RECOVERY),
             c(MID2, [0]), c(MID2, LUNGE, 4), c(MID2, [2], 3)],
        far=[c(FAR, [0]), c(FAR, [2], 4), c(FAR, JUMP_IN, 2)],
        distant=[c(DIST, [0]), c(DIST, [2], 4)],
        wakeup_actions=WAKEUP,
    ),
    "Hard": dict(
        near=[c(NEAR, BNB), c(NEAR, LOW_BNB, 6), c(NEAR, METER_BNB, 5, gauge=4000),
              c(NEAR, FRAME_TRAP, 3), c(NEAR, [THROW], 4), c(NEAR, [BACK_THROW], 2), c(NEAR, METEOR, 3),
              c(NEAR, METEOR_B, 2), c(NEAR, [8], 2, DEF),
              c(NEAR, SUPER_BNB, 5, AGG, gauge=6000),   # last = wins most often
              react(AA_DP, ANTI_AIR, AIR, startup=AA_T), react(AA, ANTI_AIR_6C, AIR, startup=AA_6C_T), react(AA_DP, ANTI_AIR_EX, AIR, gauge=4000, startup=AA_EX_T),
              react(NEAR, BNB, RECOVERY), react(NEAR, SUPER_BNB, RECOVERY, gauge=6000, chance=5),
              react(NEAR, FRAME_TRAP, BLOCKSTUN), react(NEAR, TICK_THROW, BLOCKSTUN), react(NEAR, MEATY, KNOCKDOWN)],
        mid=[c(MID1, [0]), c(MID1, ARMOR, 4), c(MID1, JUMP_IN, 4), c(MID1, DASH_IN, 3), c(MID1, DASH_THROW, 3),
             c(MID1, [1], 2, DEF),
             react(MID1, DASH_IN, RECOVERY), react(MID1, AA_SUPER, AIR, gauge=6000, chance=3), react(MID1, MEATY, KNOCKDOWN),
             react(MID1, ARMOR, ATTACK, chance=3),
             c(MID2, [0]), c(MID2, LUNGE, 4), c(MID2, [2], 3), react(MID2, LUNGE, RECOVERY)],
        far=[c(FAR, [0]), c(FAR, [2], 3), c(FAR, JUMP_IN, 2)],
        distant=[c(DIST, [0]), c(DIST, [2], 4)],
        wakeup_actions=WAKEUP,
    ),
    "VeryHard": dict(
        near=[c(NEAR, BNB), c(NEAR, LOW_BNB, 6), c(NEAR, METER_BNB, 6, gauge=4000),
              c(NEAR, FRAME_TRAP, 4), c(NEAR, [THROW], 4), c(NEAR, [BACK_THROW], 2), c(NEAR, METEOR, 3),
              c(NEAR, METEOR_B, 3), c(NEAR, [8], 2, DEF),
              c(NEAR, SUPER_BNB, 6, AGG, gauge=6000),
              react(AA_DP, ANTI_AIR, AIR, startup=AA_T), react(AA, ANTI_AIR_6C, AIR, startup=AA_6C_T), react(AA_DP, ANTI_AIR_EX, AIR, gauge=4000, startup=AA_EX_T),
              react(NEAR, BNB, RECOVERY), react(NEAR, SUPER_BNB, RECOVERY, gauge=6000, chance=5),
              react(NEAR, FRAME_TRAP, BLOCKSTUN), react(NEAR, TICK_THROW, BLOCKSTUN), react(NEAR, METEOR, BLOCKSTUN),
              react(NEAR, MEATY, KNOCKDOWN)],
        mid=[c(MID1, [0]), c(MID1, ARMOR, 4), c(MID1, JUMP_IN, 4), c(MID1, JUMP_IN_C, 3), c(MID1, DASH_IN, 3),
             c(MID1, DASH_THROW, 3), c(MID1, [1], 2, DEF),
             react(MID1, DASH_IN, RECOVERY), react(MID1, AA_SUPER, AIR, gauge=6000, chance=3), react(MID1, MEATY, KNOCKDOWN),
             react(MID1, ARMOR, ATTACK, chance=3),
             c(MID2, [0]), c(MID2, LUNGE, 4), c(MID2, [2], 4), react(MID2, LUNGE, RECOVERY)],
        far=[c(FAR, [0]), c(FAR, [2], 4)],
        distant=[c(DIST, [2]), c(DIST, [0], 4)],
        wakeup_actions=WAKEUP,
    ),
    "Pro": dict(
        near=[c(NEAR, BNB), c(NEAR, LOW_BNB, 6), c(NEAR, METER_BNB, 7, gauge=4000),
              c(NEAR, FRAME_TRAP, 4), c(NEAR, [THROW], 4), c(NEAR, [BACK_THROW], 2), c(NEAR, METEOR, 4),
              c(NEAR, METEOR_B, 3), c(NEAR, [8], 2, DEF),
              c(NEAR, SUPER_BNB, 7, AGG, gauge=6000),
              react(AA_DP, ANTI_AIR, AIR, startup=AA_T), react(AA, ANTI_AIR_6C, AIR, startup=AA_6C_T), react(AA_DP, ANTI_AIR_EX, AIR, gauge=4000, startup=AA_EX_T),
              react(NEAR, BNB, RECOVERY), react(NEAR, SUPER_BNB, RECOVERY, gauge=6000, chance=5),
              react(NEAR, LOW_BNB, BLOCKSTUN), react(NEAR, TICK_THROW, BLOCKSTUN), react(NEAR, METEOR, BLOCKSTUN),
              react(NEAR, MEATY, KNOCKDOWN)],
        mid=[c(MID1, [0]), c(MID1, ARMOR, 4), c(MID1, JUMP_IN, 3), c(MID1, JUMP_IN_C, 4), c(MID1, DASH_IN, 4),
             c(MID1, DASH_THROW, 3), c(MID1, [1], 2, DEF),
             react(MID1, DASH_IN, RECOVERY), react(MID1, AA_SUPER, AIR, gauge=6000, chance=3), react(MID1, MEATY, KNOCKDOWN),
             react(MID1, ARMOR, ATTACK, chance=3),
             c(MID2, [0]), c(MID2, LUNGE, 5), c(MID2, [2], 4), react(MID2, LUNGE, RECOVERY)],
        far=[c(FAR, [0]), c(FAR, [2], 4)],
        distant=[c(DIST, [2]), c(DIST, [0], 4)],
        wakeup_actions=WAKEUP,
    ),
}

if __name__ == "__main__":
    build("flan", "FLN", ACTIONS, BEHAVIOURS, X)
