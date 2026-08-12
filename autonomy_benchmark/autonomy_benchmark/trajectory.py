import math


def line(t, speed=2.0, length=10.0, z=5.0):
    half = length / 2.0
    omega = speed / half
    x = half * math.sin(omega * t)
    vx = speed * math.cos(omega * t)
    return (x, 0.0, z), (vx, 0.0, 0.0)


def circle(t, speed=2.0, radius=5.0, z=5.0):
    omega = speed / radius
    a = omega * t
    x = radius * math.cos(a) - radius
    y = radius * math.sin(a)
    vx = -speed * math.sin(a)
    vy = speed * math.cos(a)
    return (x, y, z), (vx, vy, 0.0)


def figure8(t, speed=2.0, radius=5.0, z=5.0):
    omega = speed / (2.0 * radius)
    a = omega * t
    x = radius * math.sin(2.0 * a) / 2.0
    y = radius * math.sin(a)
    vx = radius * omega * math.cos(2.0 * a)
    vy = radius * omega * math.cos(a)
    return (x, y, z), (vx, vy, 0.0)


GENERATORS = {"line": line, "circle": circle, "figure8": figure8}


if __name__ == "__main__":
    dt = 1e-6
    for name, gen in GENERATORS.items():
        for t in (0.0, 0.7, 3.3, 12.9):
            p0, v = gen(t)
            p1, _ = gen(t + dt)
            for i in range(3):
                num = (p1[i] - p0[i]) / dt
                assert abs(num - v[i]) < 1e-3, (name, t, i, num, v[i])
    for name, gen in GENERATORS.items():
        p, v = gen(0.0)
        assert abs(p[0]) < 1e-9 and abs(p[1]) < 1e-9 and p[2] == 5.0
    print("trajectory self-check ok")
