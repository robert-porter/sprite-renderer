"""Explicit, replayable torso and head offsets (degrees toward the viewer)."""


def value_at(value, phase):
    if isinstance(value, (int, float)):
        return float(value)
    if phase <= value[0][0]:
        return value[0][1]
    for (a, av), (b, bv) in zip(value, value[1:]):
        if phase <= b:
            t = (phase-a)/(b-a)
            t = t*t*(3-2*t)
            return av+(bv-av)*t
    return value[-1][1]


def turns_at(recipe, phase):
    torso = value_at(recipe['turn'], phase)
    head = value_at(recipe['head_turn'], phase) if 'head_turn' in recipe else torso-recipe['head_compensation']
    return torso, head
