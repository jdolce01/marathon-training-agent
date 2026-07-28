# Prehab & Targeted Exercise Knowledge Base
PREHAB_EXERCISES = {
    "it_band": [
        "Side-lying Clamshells (3x15)",
        "Standing IT Band Wall Stretch (30s hold)",
        "Lateral Band Walks (3x10/side)"
    ],
    "knee_patellar": [
        "Spanish Squats / Isometric Wall Sits (4x45s holds)",
        "Eccentric Single-Leg Step-Downs (3x10)",
        "VMO Quad Sets"
    ],
    "shin_splints": [
        "Tibialis Wall Raises (3x20)",
        "Soleus/Gastrocnemius Eccentric Heel Drops (3x15)",
        "Toe Curls with Towel"
    ],
    "plantar_achilles": [
        "Bent-Knee Calf Stretch (Soleus bias)",
        "Golf Ball / Foam Roller Foot Arch Rolling (2 mins)",
        "Straight-Leg Eccentric Calf Drops"
    ]
}

def get_prehab_suggestions(pain_location: str) -> list:
    """Returns tailored mobility and strength exercises for specific pain locations."""
    key = pain_location.lower().replace(" ", "_")
    for k in PREHAB_EXERCISES:
        if k in key:
            return PREHAB_EXERCISES[k]
    return ["Foam roll quads, hamstrings, and calves (10 mins)", "Light dynamic mobility flow"]
