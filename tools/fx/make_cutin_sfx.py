"""EX / SUPER CUT-IN SOUNDS (Oct 24 2026): synthesized, nothing recorded or downloaded.

    python tools/fx/make_cutin_sfx.py

writes
    assets/audio/sfx/netsu_ex_flash.wav      EX Craft (2 bars): a quick rising whoosh into a bright metal "shing"
    assets/audio/sfx/netsu_super_flash.wav   S-Craft (3 bars): a deep impact, a crash and a rising bell chord
game/ui/battle_hud/netsu_cut_in.gd plays them (volume: ex_volume_db / super_volume_db there).
Change the numbers below and run it again; Godot re-imports the files when the editor gets focus.
Needs numpy (pip install numpy).
"""
import os, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(HERE, '..', '..', 'assets', 'audio', 'sfx'))
SR = 44100
RNG = np.random.default_rng(7)


def t_axis(sec):
    return np.arange(int(SR * sec)) / SR


def env_exp(t, start, tau):
    e = np.where(t >= start, np.exp(-(t - start) / tau), 0.0)
    return e


def attack(t, start, ms):
    return np.clip((t - start) / (ms / 1000.0), 0.0, 1.0)


def onepole_lp(x, hz):
    a = np.exp(-2 * np.pi * hz / SR)
    y = np.zeros_like(x); acc = 0.0
    for i in range(len(x)):
        acc = (1 - a) * x[i] + a * acc; y[i] = acc
    return y


def sweep_bandpass(noise, f_from, f_to, q=4.0):
    """state-variable band-pass whose centre glides from f_from to f_to over the signal"""
    n = len(noise); out = np.zeros(n)
    low = band = 0.0
    for i in range(n):
        f = f_from * (f_to / f_from) ** (i / max(1, n - 1))
        fc = 2 * np.sin(np.pi * min(f, SR / 6) / SR)
        high = noise[i] - low - band / q
        band += fc * high
        low += fc * band
        out[i] = band
    return out


def reverb(x, mix=0.25, decay=0.55):
    """small Schroeder reverb: four combs into two all-passes"""
    out = np.zeros(len(x) + int(SR * 1.2))
    src = np.concatenate([x, np.zeros(len(out) - len(x))])
    wet = np.zeros_like(out)
    for d_ms in (29.7, 37.1, 41.1, 43.7):
        d = int(SR * d_ms / 1000); y = np.zeros_like(out)
        for i in range(len(out)):
            y[i] = src[i] + (decay * y[i - d] if i >= d else 0.0)
        wet += y * 0.25
    for d_ms, g in ((5.0, 0.7), (1.7, 0.7)):
        d = int(SR * d_ms / 1000); y = np.zeros_like(wet)
        for i in range(len(wet)):
            xd = wet[i - d] if i >= d else 0.0
            yd = y[i - d] if i >= d else 0.0
            y[i] = -g * wet[i] + xd + g * yd
        wet = y
    return src * (1 - mix) + wet * mix


def bell(t, start, f0, ratios, taus, amps, detune=0.0015):
    s = np.zeros_like(t)
    for r, tau, a in zip(ratios, taus, amps):
        f = f0 * r
        ph = 2 * np.pi * f * (t - start)
        s += a * (np.sin(ph) + 0.6 * np.sin(ph * (1 + detune))) * env_exp(t, start, tau)
    return s * attack(t, start, 1.5)


def stereo(left, right):
    return np.stack([left, right], axis=1)


def normalize(x, peak_db=-1.0):
    m = np.max(np.abs(x))
    return x * (10 ** (peak_db / 20) / m) if m > 0 else x


def fade_tail(x, sec=0.05):
    n = int(SR * sec)
    x[-n:] *= np.linspace(1, 0, n)[:, None] if x.ndim == 2 else np.linspace(1, 0, n)
    return x


def trim(x, floor_db=-62.0):
    """cut the silent end of the reverb tail"""
    level = np.abs(x).max(axis=1) if x.ndim == 2 else np.abs(x)
    loud = np.nonzero(level > 10 ** (floor_db / 20))[0]
    end = min(len(x), (loud[-1] if len(loud) else len(x)) + int(SR * 0.02))
    return fade_tail(x[:end].copy(), 0.03)


def write(name, x):
    os.makedirs(OUT, exist_ok=True)
    x = trim(x)
    data = (np.clip(x, -1, 1) * 32767).astype('<i2')
    with wave.open(os.path.join(OUT, name), 'wb') as w:
        w.setnchannels(x.shape[1] if x.ndim == 2 else 1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(data.tobytes())
    print('wrote', os.path.relpath(os.path.join(OUT, name)), '%.2f s' % (len(x) / SR))


def ex_flash():
    t = t_axis(0.9)
    # whoosh up into the hit (0 - 0.11 s)
    n = RNG.standard_normal(len(t))
    wh = sweep_bandpass(n, 700, 6500, q=3.0) * attack(t, 0.0, 70) * np.where(t < 0.11, 1.0, np.exp(-(t - 0.11) / 0.03))
    # the "shing": an inharmonic metal ring
    ring = bell(t, 0.085, 1720, [1.0, 2.76, 5.40, 8.93, 13.3], [0.42, 0.3, 0.17, 0.09, 0.05], [1.0, 0.55, 0.35, 0.22, 0.12])
    # a click and a little thump for body
    click = RNG.standard_normal(len(t)) * env_exp(t, 0.085, 0.004)
    click -= onepole_lp(click, 2500)
    thump = np.sin(2 * np.pi * 95 * (t - 0.085)) * env_exp(t, 0.085, 0.06) * attack(t, 0.085, 2)
    dry = wh * 0.5 + ring * 0.5 + click * 0.35 + thump * 0.45
    wet = reverb(dry, mix=0.22, decay=0.5)
    left = wet
    right = np.concatenate([np.zeros(18), wet[:-18]])     # 0.4 ms later: a little width
    return fade_tail(normalize(stereo(left, right), -1.5), 0.08)


def super_flash():
    t = t_axis(2.0)
    # deep impact: a falling sine, saturated
    f = 45 + 95 * np.exp(-t / 0.08)
    ph = 2 * np.pi * np.cumsum(f) / SR
    boom = np.tanh(2.2 * np.sin(ph)) * env_exp(t, 0.0, 0.55) * attack(t, 0.0, 3)
    # crash: noise, dark, fast then slow decay
    n = RNG.standard_normal(len(t))
    crash = onepole_lp(n, 3200) * (0.7 * env_exp(t, 0.0, 0.08) + 0.3 * env_exp(t, 0.0, 0.5))
    # bell chord rising in (A minor add9 up high)
    chord = np.zeros_like(t)
    for i, f0 in enumerate((659.3, 880.0, 1318.5, 1975.5, 2637.0)):
        chord += bell(t, 0.05 + 0.045 * i, f0, [1.0, 2.0, 3.01, 4.2], [1.1, 0.6, 0.35, 0.2], [1.0, 0.35, 0.18, 0.08], detune=0.002)
    shimmer = chord * (0.45 + 0.55 * attack(t, 0.05, 250))
    dry = boom * 0.7 + crash * 0.35 + shimmer * 0.32
    wet = reverb(dry, mix=0.3, decay=0.6)
    left = wet
    right = np.concatenate([np.zeros(26), wet[:-26]])
    return fade_tail(normalize(stereo(left, right), -1.0), 0.15)


if __name__ == '__main__':
    write('netsu_ex_flash.wav', ex_flash())
    write('netsu_super_flash.wav', super_flash())
