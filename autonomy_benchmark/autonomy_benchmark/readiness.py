def stable(z, vz, target, altitude_tolerance, vertical_speed_tolerance):
    return (
        abs(z - target) <= altitude_tolerance
        and abs(vz) <= vertical_speed_tolerance
    )
