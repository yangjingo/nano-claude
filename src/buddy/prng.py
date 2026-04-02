"""Mulberry32 PRNG - Deterministic pseudo-random number generator."""

from __future__ import annotations


class Mulberry32:
    """
    Mulberry32 PRNG implementation.

    A simple, fast, deterministic PRNG suitable for generating
    consistent buddy pets from user IDs.

    Reference: https://gist.github.com/tommyettinger/46a874533a3876551e07
    """

    def __init__(self, seed: int):
        """Initialize with seed value."""
        self.state = seed & 0xFFFFFFFF

    def next(self) -> int:
        """Generate next random integer (32-bit)."""
        self.state = (self.state + 0x6D2B79F5) & 0xFFFFFFFF
        t = self.state
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
        t ^= t + ((t ^ (t >> 7)) * (t | 0x6D2B79F5)) & 0xFFFFFFFF
        return t & 0xFFFFFFFF

    def random(self) -> float:
        """Generate random float in [0, 1)."""
        return self.next() / 0xFFFFFFFF

    def randint(self, min_val: int, max_val: int) -> int:
        """Generate random integer in [min_val, max_val]."""
        return min_val + int(self.random() * (max_val - min_val + 1))

    def range(self, n: int) -> int:
        """Generate random integer in [0, n)."""
        return int(self.random() * n)

    def clone(self) -> "Mulberry32":
        """Create a copy with current state."""
        return Mulberry32(self.state)


def hash_string(s: str) -> int:
    """Hash string to 32-bit integer seed."""
    # Simple hash function for deterministic seeding
    h = 0
    for char in s:
        h = ((h << 5) - h + ord(char)) & 0xFFFFFFFF
    return h