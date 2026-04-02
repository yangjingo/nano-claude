"""Deterministic buddy pet generator."""

from __future__ import annotations

import uuid
from datetime import datetime

from .models import Buddy, PetAttributes
from .prng import Mulberry32, hash_string
from .species import SPECIES
from .rarities import RARITIES, SHINY_CHANCE, total_weight
from .eyes import EYE_STYLES
from .hats import HATS


def weighted_select(items: tuple, rng: Mulberry32) -> object:
    """
    Select item based on weight attribute.

    Args:
        items: Tuple of items with .weight attribute
        rng: Mulberry32 PRNG instance

    Returns:
        Selected item
    """
    total = sum(item.weight for item in items)
    roll = rng.random() * total

    cumulative = 0
    for item in items:
        cumulative += item.weight
        if roll <= cumulative:
            return item

    return items[-1]  # fallback


def uniform_select(items: tuple, rng: Mulberry32) -> object:
    """
    Select item uniformly (equal probability).

    Args:
        items: Tuple of items
        rng: Mulberry32 PRNG instance

    Returns:
        Selected item
    """
    index = rng.range(len(items))
    return items[index]


def generate_attributes(rng: Mulberry32) -> PetAttributes:
    """Generate random pet attributes (1-100 each)."""
    return PetAttributes(
        health=rng.randint(1, 100),
        stamina=rng.randint(1, 100),
        skill=rng.randint(1, 100),
    )


def generate_uuid(rng: Mulberry32) -> str:
    """Generate deterministic UUID from RNG."""
    # Use 4 random 32-bit values to create UUID-like string
    parts = [rng.next() for _ in range(4)]
    return "buddy_" + "".join(f"{p:08x}" for p in parts)[:12]


def generate_buddy(user_id: str) -> Buddy:
    """
    Generate deterministic buddy pet from user ID.

    Same user ID always produces the same buddy.

    Args:
        user_id: User identifier string

    Returns:
        Buddy pet instance
    """
    seed = hash_string(user_id)
    rng = Mulberry32(seed)

    species = uniform_select(SPECIES, rng)
    rarity = weighted_select(RARITIES, rng)
    is_shiny = rng.random() < SHINY_CHANCE
    eye_style = EYE_STYLES[rng.range(len(EYE_STYLES))]
    hat = HATS[rng.range(len(HATS))]
    attributes = generate_attributes(rng)

    return Buddy(
        id=generate_uuid(rng),
        user_seed=seed,
        species=species,
        rarity=rarity,
        is_shiny=is_shiny,
        eye_style=eye_style,
        hat=hat,
        attributes=attributes,
        created_at=datetime.now(),
    )


def roll_buddy(rng: Mulberry32 | None = None) -> Buddy:
    """
    Roll a random buddy (for simulation/testing).

    Args:
        rng: Optional Mulberry32 instance (creates new if None)

    Returns:
        Randomly generated buddy
    """
    if rng is None:
        import random
        import time
        # Combine multiple entropy sources for better randomness
        seed = int(time.time() * 1000000) ^ random.randint(0, 0xFFFFFFFF)
        rng = Mulberry32(seed & 0xFFFFFFFF)
        # Advance the RNG a few times to mix up the state
        for _ in range(random.randint(1, 10)):
            rng.next()

    species = uniform_select(SPECIES, rng)
    rarity = weighted_select(RARITIES, rng)
    is_shiny = rng.random() < SHINY_CHANCE
    eye_style = EYE_STYLES[rng.range(len(EYE_STYLES))]
    hat = HATS[rng.range(len(HATS))]
    attributes = generate_attributes(rng)

    return Buddy(
        id=generate_uuid(rng),
        user_seed=rng.state,
        species=species,
        rarity=rarity,
        is_shiny=is_shiny,
        eye_style=eye_style,
        hat=hat,
        attributes=attributes,
        created_at=datetime.now(),
    )