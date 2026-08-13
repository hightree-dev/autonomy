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
    print("trajectory self-check ok")
