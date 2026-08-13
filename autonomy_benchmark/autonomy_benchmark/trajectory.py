import math


def line(t, speed=2.0, length=10.0, z=5.0):
    half = length / 2.0
    omega = speed / half
    x = half * math.sin(omega * t)
    vx = speed * math.cos(omega * t)
    ax = -speed * omega * math.sin(omega * t)
    return (x, 0.0, z), (vx, 0.0, 0.0), (ax, 0.0, 0.0)


def circle(t, speed=2.0, radius=5.0, z=5.0):
    omega = speed / radius
    a = omega * t
    x = radius * math.cos(a) - radius
    y = radius * math.sin(a)
    vx = -speed * math.sin(a)
    vy = speed * math.cos(a)
    ax = -speed * omega * math.cos(a)
    ay = -speed * omega * math.sin(a)
    return (x, y, z), (vx, vy, 0.0), (ax, ay, 0.0)


def figure8(t, speed=2.0, radius=5.0, z=5.0):
    omega = speed / (2.0 * radius)
    a = omega * t
    x = radius * math.sin(2.0 * a) / 2.0
    y = radius * math.sin(a)
    vx = radius * omega * math.cos(2.0 * a)
    vy = radius * omega * math.cos(a)
    ax = -2.0 * radius * omega * omega * math.sin(2.0 * a)
    ay = -radius * omega * omega * math.sin(a)
    return (x, y, z), (vx, vy, 0.0), (ax, ay, 0.0)


GENERATORS = {"line": line, "circle": circle, "figure8": figure8}


def period(name, speed=2.0, size=None):
    if name == "line":
        half = (10.0 if size is None else size) / 2.0
        return 2.0 * math.pi * half / speed
    if name == "circle":
        radius = 5.0 if size is None else size
        return 2.0 * math.pi * radius / speed
    if name == "figure8":
        radius = 5.0 if size is None else size
        return 4.0 * math.pi * radius / speed
    raise ValueError(name)


def spinup_warp(t, t_spin):
    if t >= t_spin:
        return t - t_spin / 2.0, 1.0, 0.0
    ratio = math.pi * t / t_spin
    tau = (t - t_spin / math.pi * math.sin(ratio)) / 2.0
    dtau = (1.0 - math.cos(ratio)) / 2.0
    ddtau = math.pi / (2.0 * t_spin) * math.sin(ratio)
    return tau, dtau, ddtau


def sample(name, t, speed=2.0, size=5.0, z=5.0, t_spin=0.0):
    gen = GENERATORS[name]
    if t_spin <= 0.0:
        return gen(t, speed, size, z)
    tau, dtau, ddtau = spinup_warp(t, t_spin)
    pos, vel, acc = gen(tau, speed, size, z)
    warped_vel = tuple(v * dtau for v in vel)
    warped_acc = tuple(a * dtau * dtau + v * ddtau for a, v in zip(acc, vel))
    return pos, warped_vel, warped_acc


if __name__ == "__main__":
    dt = 1e-6
    for name, gen in GENERATORS.items():
        for t in (0.0, 0.7, 3.3, 12.9):
            p0, v0, a0 = gen(t)
            p1, v1, _ = gen(t + dt)
            for i in range(3):
                num_v = (p1[i] - p0[i]) / dt
                assert abs(num_v - v0[i]) < 1e-3, (name, t, i, num_v, v0[i])
                num_a = (v1[i] - v0[i]) / dt
                assert abs(num_a - a0[i]) < 1e-3, (name, t, i, num_a, a0[i])
    for name, gen in GENERATORS.items():
        p, v, a = gen(0.0)
        assert abs(p[0]) < 1e-9 and abs(p[1]) < 1e-9 and p[2] == 5.0
    for name, gen in GENERATORS.items():
        for speed, size in ((2.0, None), (4.0, 7.0)):
            kwargs = {} if size is None else {
                "length" if name == "line" else "radius": size}
            T = period(name, speed, size)
            p0, v0, _ = gen(0.0, speed, **kwargs)
            p1, v1, _ = gen(T, speed, **kwargs)
            for i in range(3):
                assert abs(p1[i] - p0[i]) < 1e-6, (name, i, p0, p1)
                assert abs(v1[i] - v0[i]) < 1e-6, (name, i, v0, v1)
    t_spin = 7.0
    for name in GENERATORS:
        _, v0, a0 = sample(name, 0.0, 3.0, 5.0, 5.0, t_spin)
        assert all(abs(x) < 1e-9 for x in v0), (name, v0)
        assert all(abs(x) < 1e-9 for x in a0), (name, a0)
        for t in (1.3, 4.1, t_spin - 1e-4, t_spin + 1e-4, 11.7):
            p0, v0, a0 = sample(name, t, 3.0, 5.0, 5.0, t_spin)
            p1, v1, _ = sample(name, t + dt, 3.0, 5.0, 5.0, t_spin)
            for i in range(3):
                num_v = (p1[i] - p0[i]) / dt
                assert abs(num_v - v0[i]) < 1e-3, (name, t, i, num_v, v0[i])
                num_a = (v1[i] - v0[i]) / dt
                assert abs(num_a - a0[i]) < 1e-3, (name, t, i, num_a, a0[i])
        lo = sample(name, t_spin - 1e-9, 3.0, 5.0, 5.0, t_spin)
        hi = sample(name, t_spin + 1e-9, 3.0, 5.0, 5.0, t_spin)
        for a, b in zip(lo, hi):
            for i in range(3):
                assert abs(a[i] - b[i]) < 1e-6, (name, a, b)
    print("trajectory self-check ok")
