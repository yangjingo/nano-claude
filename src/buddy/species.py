"""Zelda character species definitions with ASCII art."""

from __future__ import annotations

from .models import PetSpecies

# Zelda Champions & Monsters
SPECIES: tuple[PetSpecies, ...] = (
    # --- Champions ---
    PetSpecies(
        id="link",
        name="Link",
        divine_beast="",  # Hero of Hyrule, no Divine Beast
        signature_weapon="Master Sword",
        ascii_art=r"""
   /\__
  / _ `.
 |(o)(o)|
 | _L_ /
  \'--'/
   '--'
  /|__|\\
 //| | \\
""",
        animation_frames=(
            r"""
   /\__
  / _ `.
 |(o)(o)|
 | _L_ /
  \'--'/
   '--'
""",
            r"""
   /\__
  / _ `.
 |(-)(-)|
 | _L_ /
  \'--'/
   '--'
""",
        ),
    ),
    PetSpecies(
        id="mipha",
        name="Mipha",
        divine_beast="Vah Ruta",  # Water Divine Beast
        signature_weapon="Lightscale Trident",
        ascii_art=r"""
   ..-..
  / /_ _ \.
 | |(o)(o)|
 | |  __/ |
  \ \|  | /
   \ `--' /
   < '--' >
    /|||\
""",
    ),
    PetSpecies(
        id="revali",
        name="Revali",
        divine_beast="Vah Medoh",  # Wind Divine Beast
        signature_weapon="Great Eagle Bow",
        ascii_art=r"""
    _ __
   / /  \.
  < (o) (o)
   \  V  /
    \_-_/
   /|||| \
  /_|||| _\
""",
    ),
    PetSpecies(
        id="daruk",
        name="Daruk",
        divine_beast="Vah Rudania",  # Fire Divine Beast
        signature_weapon="Boulder Breaker",
        ascii_art=r"""
  .#####.
 /#######\
|#(o)(o)#|
|   ..   |
 \ WWWW /
  '#####'
 /#######\
""",
    ),
    PetSpecies(
        id="urbosa",
        name="Urbosa",
        divine_beast="Vah Naboris",  # Lightning Divine Beast
        signature_weapon="Scimitar of the Seven",
        ascii_art=r"""
               /|
              / |
           __/_ \_
          | `_  _`|
          |(o)(o)|
          |  /\  |
          < (||) >
          //\--/\\
""",
    ),
    PetSpecies(
        id="zelda",
        name="Zelda",
        divine_beast="",  # Princess, no Divine Beast
        signature_weapon="Sealing Power",
        ascii_art=r"""
      ___
     /   \
    |(o)(o)|
    |  __  |
     \    /
    /|    |\
   (_|____|_)
""",
    ),
    # --- Monsters ---
    PetSpecies(
        id="bokoblin",
        name="Bokoblin",
        divine_beast="",
        signature_weapon="Boko Club",
        ascii_art=r"""
   .-----.
 .'       '.
/ _  (o)(o) \
| \   oo   / |
 \ \ vvvv / /
  ' .____. '
     /  \
""",
    ),
    PetSpecies(
        id="lynel",
        name="Lynel",
        divine_beast="",
        signature_weapon="Lynel Sword",
        ascii_art=r"""
   __/\__
  /__||__\
 | (o)(o) |
  \  WW  /
   |'--'|
  //\__/\_
 ||___\____\
 ||    | | |
 ||---||-||
\_|   \_|\_|
""",
    ),
    PetSpecies(
        id="guardian",
        name="Guardian",
        divine_beast="",
        signature_weapon="Guardian Sword",
        ascii_art=r"""
   [:::::]
  |(o)(o)|
   |____|
  /|    |\
 (_|____|_)
    ||  ||
""",
    ),
    PetSpecies(
        id="ganon",
        name="Ganon",
        divine_beast="",
        signature_weapon="Calamity Power",
        ascii_art=r"""
    /\/\
   /    \
  |(o)(o)|
  |  ==  |
   \    /
    |~~|
   /|  |\
  (_|  |_)
""",
    ),
)


def get_species(id: str) -> PetSpecies | None:
    """Get species by ID."""
    for species in SPECIES:
        if species.id == id:
            return species
    return None


def list_species() -> list[str]:
    """List all species IDs."""
    return [s.id for s in SPECIES]