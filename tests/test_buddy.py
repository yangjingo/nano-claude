"""Unit tests for Buddy Pet System."""

import unittest
from datetime import datetime

from src.buddy.models import (
    Buddy,
    PetSpecies,
    Rarity,
    EyeStyle,
    Hat,
    PetAttributes,
)
from src.buddy.prng import Mulberry32, hash_string
from src.buddy.species import SPECIES, get_species, list_species
from src.buddy.rarities import RARITIES, get_rarity, total_weight, SHINY_CHANCE
from src.buddy.eyes import EYE_STYLES, get_eye_style
from src.buddy.hats import HATS, get_hat
from src.buddy.generator import (
    generate_buddy,
    roll_buddy,
    weighted_select,
    uniform_select,
    generate_attributes,
)


class TestMulberry32(unittest.TestCase):
    """Test Mulberry32 PRNG."""

    def test_deterministic(self):
        """Same seed produces same sequence."""
        rng1 = Mulberry32(12345)
        rng2 = Mulberry32(12345)

        seq1 = [rng1.random() for _ in range(10)]
        seq2 = [rng2.random() for _ in range(10)]

        self.assertEqual(seq1, seq2)

    def test_range(self):
        """Range produces values within bounds."""
        rng = Mulberry32(42)

        for _ in range(100):
            val = rng.range(10)
            self.assertGreaterEqual(val, 0)
            self.assertLess(val, 10)

    def test_randint(self):
        """Randint produces values within inclusive bounds."""
        rng = Mulberry32(100)

        for _ in range(100):
            val = rng.randint(1, 100)
            self.assertGreaterEqual(val, 1)
            self.assertLessEqual(val, 100)

    def test_clone(self):
        """Clone preserves state."""
        rng = Mulberry32(999)
        rng.next()  # Advance state

        clone = rng.clone()
        self.assertEqual(rng.next(), clone.next())


class TestHashString(unittest.TestCase):
    """Test string hashing."""

    def test_consistent(self):
        """Same string produces same hash."""
        self.assertEqual(hash_string("test"), hash_string("test"))

    def test_different(self):
        """Different strings produce different hashes."""
        self.assertNotEqual(hash_string("test1"), hash_string("test2"))

    def test_32bit(self):
        """Hash is 32-bit value."""
        h = hash_string("any string")
        self.assertGreaterEqual(h, 0)
        self.assertLess(h, 0xFFFFFFFF + 1)


class TestModels(unittest.TestCase):
    """Test data models."""

    def test_pet_species_frozen(self):
        """PetSpecies is frozen (immutable)."""
        species = PetSpecies(
            id="test",
            name="Test",
            ascii_art="(o)",
        )
        with self.assertRaises(Exception):  # FrozenInstanceError
            species.id = "changed"

    def test_pet_attributes_to_bar(self):
        """Attribute bar rendering."""
        attrs = PetAttributes(health=50, stamina=50, skill=50)
        bar = attrs.to_bar("health", width=10)

        self.assertEqual(len(bar), 10)
        self.assertIn("#", bar)
        self.assertIn("-", bar)

    def test_pet_attributes_summary(self):
        """Summary renders all attributes."""
        attrs = PetAttributes(health=80, stamina=40, skill=60)
        summary = attrs.summary()

        self.assertIn("Health", summary)
        self.assertIn("Stamina", summary)
        self.assertIn("Skill", summary)


class TestSpecies(unittest.TestCase):
    """Test species registry."""

    def test_species_count(self):
        """Has expected species count."""
        self.assertGreaterEqual(len(SPECIES), 10)

    def test_get_species(self):
        """Can get species by ID."""
        species = get_species("link")
        self.assertIsNotNone(species)
        self.assertEqual(species.id, "link")

    def test_get_species_invalid(self):
        """Invalid ID returns None."""
        self.assertIsNone(get_species("invalid"))

    def test_list_species(self):
        """List returns all IDs."""
        ids = list_species()
        self.assertIn("link", ids)
        self.assertIn("mipha", ids)


class TestRarities(unittest.TestCase):
    """Test rarity system."""

    def test_rarities_count(self):
        """Has 5 rarity tiers."""
        self.assertEqual(len(RARITIES), 5)

    def test_total_weight(self):
        """Total weight equals 100."""
        self.assertEqual(total_weight(), 100)

    def test_shiny_chance(self):
        """Shiny chance is 1%."""
        self.assertEqual(SHINY_CHANCE, 0.01)

    def test_get_rarity(self):
        """Can get rarity by ID."""
        rarity = get_rarity("legendary")
        self.assertIsNotNone(rarity)
        self.assertEqual(rarity.weight, 1)


class TestEyeStyles(unittest.TestCase):
    """Test eye styles."""

    def test_eye_styles_count(self):
        """Has 6 eye styles."""
        self.assertEqual(len(EYE_STYLES), 6)

    def test_eye_symbols(self):
        """Each has unique symbol."""
        symbols = [e.symbol for e in EYE_STYLES]
        self.assertEqual(len(symbols), len(set(symbols)))

    def test_get_eye_style(self):
        """Can get by ID."""
        eye = get_eye_style("star")
        self.assertIsNotNone(eye)
        self.assertEqual(eye.symbol, "*")


class TestHats(unittest.TestCase):
    """Test hat accessories."""

    def test_hats_count(self):
        """Has 8 hats."""
        self.assertEqual(len(HATS), 8)

    def test_none_hat(self):
        """Has 'none' hat option."""
        hat = get_hat("none")
        self.assertIsNotNone(hat)
        self.assertEqual(hat.ascii_art, "")


class TestGenerator(unittest.TestCase):
    """Test buddy generator."""

    def test_generate_buddy_deterministic(self):
        """Same user ID produces same buddy."""
        buddy1 = generate_buddy("user123")
        buddy2 = generate_buddy("user123")

        self.assertEqual(buddy1.id, buddy2.id)
        self.assertEqual(buddy1.species.id, buddy2.species.id)
        self.assertEqual(buddy1.rarity.id, buddy2.rarity.id)
        self.assertEqual(buddy1.is_shiny, buddy2.is_shiny)

    def test_generate_buddy_different_users(self):
        """Different users produce different buddies."""
        buddy1 = generate_buddy("user1")
        buddy2 = generate_buddy("user2")

        # Different IDs (likely different everything)
        self.assertNotEqual(buddy1.id, buddy2.id)

    def test_generate_attributes_range(self):
        """Attributes are in valid range."""
        rng = Mulberry32(42)
        attrs = generate_attributes(rng)

        for val in [attrs.health, attrs.stamina, attrs.skill]:
            self.assertGreaterEqual(val, 1)
            self.assertLessEqual(val, 100)

    def test_weighted_select(self):
        """Weighted select respects weights."""
        # Common should be selected most often
        rng = Mulberry32(100)
        counts = {r.id: 0 for r in RARITIES}

        for _ in range(1000):
            rarity = weighted_select(RARITIES, rng.clone())
            counts[rarity.id] += 1

        # Common (60%) should be most frequent
        self.assertEqual(max(counts, key=counts.get), "common")

    def test_buddy_to_dict(self):
        """Buddy serializes to dict."""
        buddy = generate_buddy("test_user")
        data = buddy.to_dict()

        self.assertIn("id", data)
        self.assertIn("species", data)
        self.assertIn("rarity", data)
        self.assertIn("attributes", data)

    def test_roll_buddy(self):
        """Roll buddy creates valid instance."""
        buddy = roll_buddy()

        self.assertIsNotNone(buddy.species)
        self.assertIsNotNone(buddy.rarity)
        self.assertIsNotNone(buddy.attributes)


class TestBuddyRender(unittest.TestCase):
    """Test buddy rendering."""

    def test_buddy_render_replaces_eyes(self):
        """Render replaces eye placeholders."""
        species = get_species("link")
        eye = get_eye_style("star")

        buddy = Buddy(
            id="test",
            user_seed=123,
            species=species,
            rarity=get_rarity("common"),
            is_shiny=False,
            eye_style=eye,
            hat=get_hat("none"),
            attributes=PetAttributes(50, 50, 50),
        )

        rendered = buddy.render()
        # Should contain star symbol, not (o)
        self.assertIn("*", rendered)
        self.assertNotIn("(o)", rendered)


class TestRarityExtraction(unittest.TestCase):
    """Test that all rarities can be extracted."""

    def test_extract_all_rarities(self):
        """Roll until all rarities are found."""
        from src.buddy.rarities import RARITIES
        from src.buddy.generator import roll_buddy

        found_rarities = set()
        max_rolls = 1000

        for _ in range(max_rolls):
            buddy = roll_buddy()
            found_rarities.add(buddy.rarity.id)

            # Found all 5 rarities
            if len(found_rarities) == 5:
                break

        expected = {"common", "uncommon", "rare", "epic", "legendary"}
        self.assertEqual(
            found_rarities, expected, f"Missing rarities: {expected - found_rarities}"
        )

    def test_shiny_can_be_found(self):
        """Test that shiny can be found (may take many rolls)."""
        from src.buddy.generator import roll_buddy

        found_shiny = False
        max_rolls = 500

        for _ in range(max_rolls):
            buddy = roll_buddy()
            if buddy.is_shiny:
                found_shiny = True
                break

        # Note: This test has a small chance of false failure (0.99^500 ≈ 0.6%)
        # In practice, we should find at least one shiny in 500 rolls
        self.assertTrue(
            found_shiny,
            f"Shiny not found in {max_rolls} rolls (statistically unlikely)",
        )

    def test_all_colors_defined(self):
        """All rarities have valid Rich colors (hex or named)."""
        import re
        from src.buddy.rarities import RARITIES

        # Rich color names that are valid
        valid_named_colors = {
            "white",
            "black",
            "red",
            "green",
            "yellow",
            "blue",
            "magenta",
            "cyan",
            "bright_red",
            "bright_green",
            "bright_yellow",
            "bright_blue",
            "bright_magenta",
            "bright_cyan",
            "bright_white",
        }

        # Hex color pattern (#RRGGBB)
        hex_pattern = re.compile(r"^#[0-9a-fA-F]{6}$")

        for rarity in RARITIES:
            is_valid = (
                rarity.color in valid_named_colors
                or hex_pattern.match(rarity.color) is not None
            )
            self.assertTrue(
                is_valid, f"Invalid color '{rarity.color}' for rarity '{rarity.name}'"
            )

    def test_rarity_distribution(self):
        """Test rarity distribution roughly matches weights."""
        from src.buddy.generator import roll_buddy

        rolls = 500
        counts = {r.id: 0 for r in RARITIES}

        for _ in range(rolls):
            buddy = roll_buddy()
            counts[buddy.rarity.id] += 1

        # Common should be most frequent (60% expected)
        self.assertGreater(counts["common"], counts["legendary"])
        self.assertGreater(counts["common"], counts["epic"])

        # Common should be roughly 50-70% of rolls
        common_ratio = counts["common"] / rolls
        self.assertGreater(common_ratio, 0.4, f"Common ratio {common_ratio} too low")
        self.assertLess(common_ratio, 0.8, f"Common ratio {common_ratio} too high")

        # Print distribution for visibility
        print(f"\nRarity distribution over {rolls} rolls:")
        for rarity_id, count in sorted(counts.items()):
            pct = count / rolls * 100
            print(f"  {rarity_id:12}: {count:4} ({pct:5.1f}%)")


if __name__ == "__main__":
    unittest.main()
