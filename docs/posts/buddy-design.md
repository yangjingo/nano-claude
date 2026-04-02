# Buddy Pet System

> 终端伴侣：Zelda Champions 收集系统

---

## 问题

CLI 是冰冷的。黑底白字，光标闪烁。

没有情感，没有陪伴。

Claude Code 团队做了一个有趣的尝试：**Buddy**。

> 一只小鸭子、一只猫、或者一条龙，坐在你的终端里。

我们做一个 Zelda 版本。

---

## 发现

Claude Code 有一个隐藏的宠物系统：

```
    ○     ┌─────────────────┐
   /|\    │ Ready to help!  │
   / \    └─────────────────┘
```

不是装饰。是**确定性生成**的伴侣。

---

## 核心设计

### Species: 10 Champions & Monsters

| ID | Name | Divine Beast | Signature Weapon |
|----|------|--------------|------------------|
| `link` | Link | N/A | Master Sword |
| `mipha` | Mipha | Vah Ruta | Lightscale Trident |
| `revali` | Revali | Vah Medoh | Great Eagle Bow |
| `daruk` | Daruk | Vah Rudania | Boulder Breaker |
| `urbosa` | Urbosa | Vah Naboris | Scimitar of the Seven |
| `zelda` | Zelda | N/A | Sealing Power |
| `bokoblin` | Bokoblin | N/A | Boko Club |
| `lynel` | Lynel | N/A | Lynel Sword |
| `guardian` | Guardian | N/A | Guardian Sword |
| `ganon` | Ganon | N/A | Calamity Power |

**Four Divine Beasts**:
- **Vah Ruta** (Water) - Mipha's elephant-shaped beast
- **Vah Medoh** (Wind) - Revali's bird-shaped beast
- **Vah Rudania** (Fire) - Daruk's lizard-shaped beast
- **Vah Naboris** (Lightning) - Urbosa's camel-shaped beast

### Rarity: Gacha System

| Rarity | Chance | Rich Color |
|--------|--------|-------|
| common | 60% | `#99a5b2` |
| uncommon | 25% | `#a4bf8d` |
| rare | 10% | `#86c0d0` |
| epic | 4% | `#b78aaf` |
| legendary | 1% | `#ebca89` |

**Shiny**: 1% rainbow shimmer.

### Attributes: Zelda Combat System

```
Health  [+] [+] [+] [ ] [ ]  73
Stamina [#] [#] [.] [.] [.]  45
Skill   ██████░░░░ 65
```

Three core attributes:

| Attr | Range | Display |
|------|-------|---------|
| Health | 1-100 | `[+]` / `[ ]` |
| Stamina | 1-100 | `[#]` / `[.]` |
| Skill | 1-100 | `█░` bar |

### Customization

**Eyes**: `·` `✦` `×` `◉` `@` `°`

**Hats**: none, crown, tophat, propeller, halo, wizard, beanie, tinyduck

---

## Deterministic Generation

Same user, same buddy forever.

```python
seed = hash(user_id)
rng = Mulberry32(seed)

species = uniform_select(SPECIES, rng)
rarity = weighted_select(RARITIES, rng)
is_shiny = rng.random() < 0.01
```

**Mulberry32**:

```python
class Mulberry32:
    def __init__(self, seed: int):
        self.seed = seed

    def next(self) -> int:
        self.seed += 0x6D2B79F5
        t = self.seed
        t = ((t ^ (t >> 15)) * t | 1)
        t ^= t + ((t ^ (t >> 7)) * (t | 0x6D2B79F5))
        return t & 0xFFFFFFFF
```

---

## File Structure

```
src/buddy/
├── __init__.py      # Module exports
├── models.py        # Buddy, PetSpecies, PetAttributes
├── prng.py          # Mulberry32 PRNG
├── species.py       # 10 Zelda characters
├── rarities.py      # 5 rarity tiers
├── eyes.py          # 6 eye styles
├── hats.py          # 8 hats
├── generator.py     # Deterministic generation
└── renderer.py      # Rich rendering

tests/
└── test_buddy.py    # 30 unit tests
```

---

## Usage

```python
from src.buddy import roll_buddy, render_registry

# Roll a random buddy with gacha animation
buddy = roll_buddy()

print(f'Character: {buddy.species.name}')
print(f'Divine Beast: {buddy.species.divine_beast or "N/A"}')
print(f'Weapon: {buddy.species.signature_weapon}')
print(f'Rarity: {buddy.rarity.name}')
print(buddy.render())
print(buddy.attributes.summary())

# Show all characters
render_registry()
```

**CLI Commands:**

```bash
nano-claude buddy           # Random roll with animation
nano-claude buddy --registry  # Show all champions
```

**REPL Commands:**

```
/buddy      # Random roll
/help       # Show help
```

**Future: Character matching based on CLAUDE.md**

The buddy system will analyze your project's CLAUDE.md to match the most suitable champion:

- **Link** - General purpose, versatile projects
- **Mipha** - Healing/recovery utilities, data pipelines
- **Revali** - Performance-critical, async systems
- **Daruk** - Heavy infrastructure, DevOps tools
- **Urbosa** - Security-focused, authentication systems
- **Zelda** - Documentation, knowledge management

Output:

```
==================================================
Character: Link
Divine Beast: N/A
Weapon: Master Sword
Rarity: Common
==================================================

   /\__
  / _ `.
 |✦✦|
 | _L_ /
  \'--'/
   '--'
  /|__|\\
 //| | \\

==================================================
Health  [+] [+] [+] [ ] [ ]  73
Stamina [.] [.] [.] [.] [.]  11
Skill   ██████░░░░ 65
==================================================
```

---

## Persistence

`~/.nano-claude/buddy.json`:

```json
{
  "id": "buddy_9392c4eab170",
  "species": "link",
  "rarity": "uncommon",
  "is_shiny": false,
  "eye_style": "star",
  "hat": "beanie",
  "attributes": {
    "health": 73,
    "stamina": 11,
    "skill": 65
  }
}
```

---

## Registry Table

```
                  Hyrule Hero & Monster Registry                   
┌───────────┬──────────────┬───────────────────────┬──────────────┐
│ Character │ Divine Beast │ Signature Weapon      │ ASCII Avatar │
├───────────┼──────────────┼───────────────────────┼──────────────┤
│ Link      │     N/A      │ Master Sword          │ /\__         │
│ Mipha     │   Vah Ruta   │ Lightscale Trident    │ ..-..        │
│ Revali    │  Vah Medoh   │ Great Eagle Bow       │ _ __         │
│ Daruk     │ Vah Rudania  │ Boulder Breaker       │ .#####.      │
│ Urbosa    │ Vah Naboris  │ Scimitar of the Seven │ /|           │
│ Zelda     │     N/A      │ Sealing Power         │ ___          │
│ Bokoblin  │     N/A      │ Boko Club             │ .-----.      │
│ Lynel     │     N/A      │ Lynel Sword           │ __/\__       │
│ Guardian  │     N/A      │ Guardian Sword        │ [:::::]      │
│ Ganon     │     N/A      │ Calamity Power        │ /\/\         │
└───────────┴──────────────┴───────────────────────┴──────────────┘
```

---

## Design Notes

| Decision | Why |
|----------|-----|
| Deterministic generation | Same user = same buddy, emotional connection |
| 3 attributes (not 5) | Simpler, Zelda-themed |
| ASCII-only display | No encoding issues |
| Uniform species selection | All champions equal chance |

---

## References

- [Claude Buddy Gallery](https://claude-buddy.vercel.app/)
- [Rich Documentation](https://rich.readthedocs.io/)
- [Mulberry32 PRNG](https://gist.github.com/tommyettinger/46a874533a3876551e07)
