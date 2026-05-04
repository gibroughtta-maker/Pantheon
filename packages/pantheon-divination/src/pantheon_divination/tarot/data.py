"""78-card tarot deck data — Major Arcana (22) + Minor Arcana (56).

Card meanings are common-knowledge interpretations of the
Rider-Waite-Smith deck (1909, public domain in many jurisdictions; the
underlying symbolism is centuries old). Only short keywords ship in this
file; LLM contextualization is what produces conversational output.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache


@dataclass
class TarotCard:
    id: str                    # short id e.g. "major_00_fool", "wands_03"
    arcana: str                # "major" | "wands" | "cups" | "swords" | "pentacles"
    name: str
    name_zh: str
    upright: str               # short keyword phrase
    reversed: str
    image: str                 # short visual symbol


# 22 Major Arcana
_MAJOR: list[tuple[str, str, str, str, str, str]] = [
    # (name_en,            name_zh,    upright,                          reversed,                          image)
    ("The Fool",          "愚者",     "beginnings, innocence, leap",      "recklessness, naivety",            "stepping over a cliff"),
    ("The Magician",      "魔法师",   "manifestation, willpower, skill",  "manipulation, scattered focus",    "infinity above one hand"),
    ("The High Priestess","女祭司",   "intuition, hidden knowledge",      "secrets withheld, blocked intuition", "veil between two pillars"),
    ("The Empress",       "皇后",     "abundance, nurturing, fertility",  "dependence, smothering",          "throne in a wheat field"),
    ("The Emperor",       "皇帝",     "authority, structure, fatherhood", "tyranny, rigidity",               "stone throne with rams"),
    ("The Hierophant",    "教皇",     "tradition, institution, mentorship","dogma, rebellion",                "twin keys at his feet"),
    ("The Lovers",        "恋人",     "union, choice, alignment",         "misalignment, false choice",       "angel above two figures"),
    ("The Chariot",       "战车",     "willed motion, victory, control",  "loss of control, drift",           "two sphinxes in tandem"),
    ("Strength",          "力量",     "courage, gentle power, endurance", "self-doubt, brittle force",        "woman closing a lion's jaw"),
    ("The Hermit",        "隐士",     "solitude, inner light, search",    "isolation, withdrawal",            "cloaked figure with a lantern"),
    ("Wheel of Fortune",  "命运之轮", "turning, cycles, fortune",         "bad luck, resistance to change",   "wheel with four creatures"),
    ("Justice",           "正义",     "fairness, accountability, truth",  "unfairness, evasion",              "scales and a sword"),
    ("The Hanged Man",    "倒吊人",   "pause, surrender, new perspective","stalling, sacrifice without gain", "figure suspended by one foot"),
    ("Death",             "死神",     "ending, transformation, rebirth",  "resistance to change, stagnation", "skeleton with a banner"),
    ("Temperance",        "节制",     "balance, blending, patience",      "imbalance, excess, haste",         "pouring water between cups"),
    ("The Devil",         "恶魔",     "attachment, addiction, shadow",    "release, breaking chains",         "two figures chained loosely"),
    ("The Tower",         "塔",       "sudden change, revelation, fall",  "averted disaster, slow fall",      "lightning strikes a tower"),
    ("The Star",          "星星",     "hope, renewal, gentle clarity",    "discouragement, lost faith",       "kneeling figure with two jugs"),
    ("The Moon",          "月亮",     "illusion, dream, deep emotion",    "confusion clearing, truth surfacing","crayfish under twin towers"),
    ("The Sun",           "太阳",     "joy, vitality, success",           "delayed joy, dimmed warmth",       "child on a horse beneath the sun"),
    ("Judgement",         "审判",     "reckoning, calling, awakening",    "self-doubt, missed call",          "angel with a trumpet"),
    ("The World",         "世界",     "completion, integration, fulfillment","unfinished, almost-there",     "figure within a wreath of leaves"),
]


_MINOR_RANKS = [
    "Ace", "Two", "Three", "Four", "Five",
    "Six", "Seven", "Eight", "Nine", "Ten",
    "Page", "Knight", "Queen", "King",
]
_MINOR_RANKS_ZH = [
    "王牌", "二", "三", "四", "五",
    "六", "七", "八", "九", "十",
    "侍从", "骑士", "王后", "国王",
]

# Suit themes (canonical R-W-S):
#   wands     — fire    — passion, action
#   cups      — water   — emotion, relationship
#   swords    — air     — thought, conflict
#   pentacles — earth   — body, work, money
_MINOR_SUITS = {
    "wands":     ("权杖", "passion / inspiration / action"),
    "cups":      ("圣杯", "emotion / love / intuition"),
    "swords":    ("宝剑", "thought / conflict / clarity"),
    "pentacles": ("钱币", "body / work / material"),
}

# Brief upright/reversed keywords per (suit, rank). Generic but faithful.
_MINOR_KEYS: dict[tuple[str, str], tuple[str, str]] = {
    ("wands", "Ace"):    ("creative spark, new venture", "delay, missed inspiration"),
    ("wands", "Two"):    ("planning, partnership, vision", "fear of unknown, hesitation"),
    ("wands", "Three"):  ("foresight, expansion, ships coming in", "delays, frustration"),
    ("wands", "Four"):   ("celebration, homecoming, milestone", "tension at home, transition"),
    ("wands", "Five"):   ("conflict, competition, friction", "diplomacy, end of strife"),
    ("wands", "Six"):    ("public success, recognition", "fall from favor, ego"),
    ("wands", "Seven"):  ("defending position, perseverance", "overwhelm, giving up the high ground"),
    ("wands", "Eight"):  ("rapid movement, news in flight", "delay, miscommunication"),
    ("wands", "Nine"):   ("resilience, last stand", "battle fatigue, paranoia"),
    ("wands", "Ten"):    ("burden, end-of-cycle responsibility", "release of burden"),
    ("wands", "Page"):   ("eager messenger, exploration", "scattered enthusiasm"),
    ("wands", "Knight"): ("bold action, charge ahead", "impulsiveness, recklessness"),
    ("wands", "Queen"):  ("warm authority, magnetic confidence", "burnout, jealousy"),
    ("wands", "King"):   ("visionary leadership", "domineering, impatient"),

    ("cups",  "Ace"):    ("new feeling, love, creative source", "blocked emotion, delayed news"),
    ("cups",  "Two"):    ("partnership, mutual attraction", "imbalance, mismatch"),
    ("cups",  "Three"):  ("celebration, friendship, abundance", "third-party trouble, overindulgence"),
    ("cups",  "Four"):   ("apathy, contemplation, missed offer", "renewed interest, awareness"),
    ("cups",  "Five"):   ("loss, regret, mourning", "moving on, recovery"),
    ("cups",  "Six"):    ("nostalgia, childhood, warmth", "stuck in the past"),
    ("cups",  "Seven"):  ("many options, daydream, illusion", "clarity returning, decisive choice"),
    ("cups",  "Eight"):  ("walking away, deeper search", "fear of leaving, returning"),
    ("cups",  "Nine"):   ("emotional satisfaction, the wish", "smugness, shallow pleasure"),
    ("cups",  "Ten"):    ("family joy, lasting harmony", "broken bonds, idealized family"),
    ("cups",  "Page"):   ("intuitive message, gentle openness", "emotional immaturity"),
    ("cups",  "Knight"): ("romantic offer, charming pursuit", "moodiness, false promises"),
    ("cups",  "Queen"):  ("compassion, emotional depth", "overwhelmed feeling, codependency"),
    ("cups",  "King"):   ("emotional mastery, calm authority", "manipulation, repression"),

    ("swords","Ace"):    ("breakthrough idea, mental clarity", "confusion, misuse of force"),
    ("swords","Two"):    ("stalemate, weighing options", "indecision tipping, lifting blindfold"),
    ("swords","Three"):  ("heartbreak, painful truth", "healing, processed grief"),
    ("swords","Four"):   ("rest, recovery, retreat", "restlessness, premature return"),
    ("swords","Five"):   ("conflict won at cost, betrayal", "reconciliation attempted"),
    ("swords","Six"):    ("transition, leaving behind", "returning, unable to leave"),
    ("swords","Seven"):  ("cunning, theft, partial truth", "coming clean, return of what was taken"),
    ("swords","Eight"):  ("self-imposed restriction, paralysis", "freeing yourself, awareness"),
    ("swords","Nine"):   ("anxiety, sleepless worry", "morning relief, hope returning"),
    ("swords","Ten"):    ("rock bottom, painful end", "scraping bottom, only up from here"),
    ("swords","Page"):   ("vigilance, news, sharp curiosity", "gossip, harshness"),
    ("swords","Knight"): ("incisive action, swift mind", "aggression, recklessness in argument"),
    ("swords","Queen"):  ("clarity, independence, sharp mind", "coldness, bitterness"),
    ("swords","King"):   ("intellectual authority, judgement", "tyranny of the mind, manipulation"),

    ("pentacles","Ace"):    ("new opportunity, material gift", "missed chance, scarcity mindset"),
    ("pentacles","Two"):    ("juggling, balance, flexibility", "overwhelm, dropped balls"),
    ("pentacles","Three"):  ("collaboration, craftsmanship", "lack of teamwork, shoddy work"),
    ("pentacles","Four"):   ("saving, security, holding tight", "greed, generosity blocked"),
    ("pentacles","Five"):   ("hardship, exclusion", "recovery, finding shelter"),
    ("pentacles","Six"):    ("generosity, fair exchange", "uneven debts, strings attached"),
    ("pentacles","Seven"):  ("patience, harvest pending", "wasted effort, impatient pivot"),
    ("pentacles","Eight"):  ("apprenticeship, careful practice", "perfectionism, rote work"),
    ("pentacles","Nine"):   ("solo abundance, cultivated independence", "image over substance"),
    ("pentacles","Ten"):    ("legacy, family wealth, heritage", "broken legacy, inheritance trouble"),
    ("pentacles","Page"):   ("learning, opportunity, study", "neglected learning"),
    ("pentacles","Knight"): ("steady progress, dependability", "stagnation, plodding"),
    ("pentacles","Queen"):  ("nurturing prosperity, practical care", "self-neglect, smothering"),
    ("pentacles","King"):   ("financial mastery, stable abundance", "miserliness, stubborn materialism"),
}


@lru_cache(maxsize=1)
def load_cards() -> list[TarotCard]:
    out: list[TarotCard] = []
    for i, (name, name_zh, up, rev, img) in enumerate(_MAJOR):
        out.append(
            TarotCard(
                id=f"major_{i:02d}_{name.lower().replace(' ', '_').replace('the_', '')}",
                arcana="major", name=name, name_zh=name_zh,
                upright=up, reversed=rev, image=img,
            )
        )
    for suit, (suit_zh, _theme) in _MINOR_SUITS.items():
        for rank, rank_zh in zip(_MINOR_RANKS, _MINOR_RANKS_ZH):
            up, rev = _MINOR_KEYS.get((suit, rank), ("(unset)", "(unset)"))
            out.append(
                TarotCard(
                    id=f"{suit}_{rank.lower()}",
                    arcana=suit,
                    name=f"{rank} of {suit.capitalize()}",
                    name_zh=f"{suit_zh}{rank_zh}",
                    upright=up,
                    reversed=rev,
                    image=f"{rank} of {suit}",
                )
            )
    return out
