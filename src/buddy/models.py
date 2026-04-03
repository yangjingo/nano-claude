"""Data models for Buddy Pet System."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass(frozen=True)
class PetSpecies:
    """Pet species definition with ASCII art."""

    id: str
    name: str
    ascii_art: str
    divine_beast: str = ""  # 四神兽名称
    signature_weapon: str = ""  # 专属武器
    animation_frames: tuple[str, ...] = field(default_factory=tuple)

    def get_frame(self, index: int = 0) -> str:
        """Get animation frame by index."""
        if self.animation_frames:
            return self.animation_frames[index % len(self.animation_frames)]
        return self.ascii_art


@dataclass(frozen=True)
class Rarity:
    """Rarity tier definition."""

    id: str
    name: str
    weight: int  # For weighted selection
    color: str  # Rich color code


@dataclass(frozen=True)
class EyeStyle:
    """Eye style definition."""

    id: str
    symbol: str
    name: str = ""


@dataclass(frozen=True)
class Hat:
    """Hat/accessory definition."""

    id: str
    name: str
    ascii_art: str


@dataclass(frozen=True)
class PetAttributes:
    """Zelda-style combat attributes."""

    health: int  # 血条 (生命值) 1-100
    stamina: int  # 体力 (耐力值) 1-100
    skill: int  # 技能 (战斗技巧) 1-100

    def to_bar(self, attr: str, width: int = 10) -> str:
        """Render attribute as progress bar."""
        value = getattr(self, attr)
        filled = int(value / 100 * width)
        return "#" * filled + "-" * (width - filled)

    def health_display(self) -> str:
        """Render health as hearts (ASCII only)."""
        full_hearts = self.health // 20
        empty_hearts = 5 - full_hearts
        return "[+] " * full_hearts + "[ ] " * empty_hearts

    def stamina_display(self) -> str:
        """Render stamina as segments (ASCII only)."""
        segments = self.stamina // 20
        empty = 5 - segments
        return "[#] " * segments + "[.] " * empty

    def summary(self) -> str:
        """Render all attributes."""
        return f"""Health  {self.health_display()} {self.health}
Stamina {self.stamina_display()} {self.stamina}
Skill   {self.to_bar('skill')} {self.skill}"""


@dataclass
class Buddy:
    """Complete buddy pet instance."""

    id: str
    user_seed: int
    species: PetSpecies
    rarity: Rarity
    is_shiny: bool
    eye_style: EyeStyle
    hat: Hat
    attributes: PetAttributes
    created_at: datetime = field(default_factory=datetime.now)

    def render(self) -> str:
        """Render buddy ASCII with customizations."""
        # Replace eye placeholder with custom eye
        art = self.species.ascii_art
        art = art.replace("(o)", self.eye_style.symbol)
        art = art.replace("(O)", self.eye_style.symbol)
        return art

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "user_seed": self.user_seed,
            "species": self.species.id,
            "rarity": self.rarity.id,
            "is_shiny": self.is_shiny,
            "eye_style": self.eye_style.id,
            "hat": self.hat.id,
            "attributes": {
                "health": self.attributes.health,
                "stamina": self.attributes.stamina,
                "skill": self.attributes.skill,
            },
            "created_at": self.created_at.isoformat(),
        }
