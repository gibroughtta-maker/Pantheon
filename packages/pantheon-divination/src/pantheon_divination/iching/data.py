"""易经 64 hexagram metadata loader.

Data sourced from the canonical 易经 itself (BCE — Public Domain). The
brief English keywords follow the Wilhelm/Baynes line of common-knowledge
translation; they are reference labels, not full Wilhelm commentary.
The real lookup key is the hexagram NUMBER (1–64) per King Wen ordering.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache


@dataclass
class Hexagram:
    number: int
    chinese: str
    pinyin: str
    english: str
    lines: list[int]     # 6 lines bottom→top, 1=yang, 0=yin
    judgement: str
    image: str
    upper_trigram: str
    lower_trigram: str


# Canonical trigram → 3-line binary code (bottom→top, 1=yang).
_TRIGRAM_LINES = {
    "乾": "111", "坤": "000",
    "震": "100", "坎": "010", "艮": "001",
    "巽": "110", "離": "101", "兌": "011",
}

# Authoritative King Wen ordering: hex# → (lower, upper) trigram.
# Line strings in _RAW are AUTO-DERIVED from this; do not edit _RAW lines.
_KING_WEN: dict[int, tuple[str, str]] = {
    1: ("乾","乾"),  2: ("坤","坤"),  3: ("震","坎"),  4: ("坎","艮"),
    5: ("乾","坎"),  6: ("坎","乾"),  7: ("坎","坤"),  8: ("坤","坎"),
    9: ("乾","巽"), 10: ("兌","乾"), 11: ("乾","坤"), 12: ("坤","乾"),
    13: ("離","乾"), 14: ("乾","離"), 15: ("艮","坤"), 16: ("坤","震"),
    17: ("震","兌"), 18: ("巽","艮"), 19: ("兌","坤"), 20: ("坤","巽"),
    21: ("震","離"), 22: ("離","艮"), 23: ("坤","艮"), 24: ("震","坤"),
    25: ("震","乾"), 26: ("乾","艮"), 27: ("震","艮"), 28: ("巽","兌"),
    29: ("坎","坎"), 30: ("離","離"), 31: ("艮","兌"), 32: ("巽","震"),
    33: ("艮","乾"), 34: ("乾","震"), 35: ("坤","離"), 36: ("離","坤"),
    37: ("離","巽"), 38: ("兌","離"), 39: ("艮","坎"), 40: ("坎","震"),
    41: ("兌","艮"), 42: ("震","巽"), 43: ("乾","兌"), 44: ("巽","乾"),
    45: ("坤","兌"), 46: ("巽","坤"), 47: ("坎","兌"), 48: ("巽","坎"),
    49: ("離","兌"), 50: ("巽","離"), 51: ("震","震"), 52: ("艮","艮"),
    53: ("艮","巽"), 54: ("兌","震"), 55: ("離","震"), 56: ("艮","離"),
    57: ("巽","巽"), 58: ("兌","兌"), 59: ("坎","巽"), 60: ("兌","坎"),
    61: ("兌","巽"), 62: ("艮","震"), 63: ("離","坎"), 64: ("坎","離"),
}


def _line_string_for(number: int) -> str:
    lower, upper = _KING_WEN[number]
    return _TRIGRAM_LINES[lower] + _TRIGRAM_LINES[upper]


# Trigrams (八卦)
TRIGRAMS = {
    "111": ("乾", "qián", "Heaven"),
    "000": ("坤", "kūn",  "Earth"),
    "100": ("震", "zhèn", "Thunder"),
    "010": ("坎", "kǎn",  "Water"),
    "001": ("艮", "gèn",  "Mountain"),
    "110": ("巽", "xùn",  "Wind"),
    "101": ("離", "lí",   "Fire"),
    "011": ("兌", "duì",  "Lake"),
}


# 64 hexagrams in King Wen order. Lines list is top-trigram + bottom-trigram
# joined; reading order in `lines` field is bottom to top for cast logic.
# Format: (number, 中, pinyin, English, "yyyyyy" bottom→top, brief judgement, brief image)
_RAW: list[tuple[int, str, str, str, str, str, str]] = [
    (1, "乾", "qián", "The Creative",            "111111", "元、亨、利、貞。", "天行健，君子以自强不息。"),
    (2, "坤", "kūn",  "The Receptive",           "000000", "元亨。利牝馬之貞。", "地勢坤，君子以厚德載物。"),
    (3, "屯", "zhūn", "Difficulty at the Beginning", "100010", "元亨利貞。勿用，有攸往。利建侯。", "雲雷屯，君子以經綸。"),
    (4, "蒙", "méng", "Youthful Folly",          "010001", "亨。匪我求童蒙，童蒙求我。", "山下出泉，蒙；君子以果行育德。"),
    (5, "需", "xū",   "Waiting (Nourishment)",   "111010", "有孚，光亨。貞吉。利涉大川。", "雲上於天，需；君子以飲食宴樂。"),
    (6, "訟", "sòng", "Conflict",                "010111", "有孚窒。惕中吉。終凶。利見大人，不利涉大川。", "天與水違行，訟；君子以作事謀始。"),
    (7, "師", "shī",  "The Army",                "010000", "貞，丈人吉，无咎。", "地中有水，師；君子以容民畜眾。"),
    (8, "比", "bǐ",   "Holding Together",        "000010", "吉。原筮，元永貞，无咎。", "地上有水，比；先王以建萬國親諸侯。"),
    (9, "小畜", "xiǎo chù", "The Taming Power of the Small", "111011", "亨。密雲不雨，自我西郊。", "風行天上，小畜；君子以懿文德。"),
    (10, "履", "lǚ",  "Treading (Conduct)",      "110111", "履虎尾，不咥人。亨。", "上天下澤，履；君子以辨上下，定民志。"),
    (11, "泰", "tài", "Peace",                   "111000", "小往大來，吉，亨。", "天地交，泰；后以財成天地之道。"),
    (12, "否", "pǐ",  "Standstill (Stagnation)", "000111", "之匪人，不利君子貞，大往小來。", "天地不交，否；君子以儉德辟難。"),
    (13, "同人", "tóng rén", "Fellowship with Men", "101111", "于野。亨。利涉大川，利君子貞。", "天與火，同人；君子以類族辨物。"),
    (14, "大有", "dà yǒu", "Possession in Great Measure", "111101", "元亨。", "火在天上，大有；君子以遏惡揚善。"),
    (15, "謙", "qiān", "Modesty",                "001000", "亨。君子有終。", "地中有山，謙；君子以裒多益寡。"),
    (16, "豫", "yù",  "Enthusiasm",              "000100", "利建侯行師。", "雷出地奮，豫；先王以作樂崇德。"),
    (17, "隨", "suí", "Following",               "100011", "元亨，利貞，无咎。", "澤中有雷，隨；君子以嚮晦入宴息。"),
    (18, "蠱", "gǔ",  "Work on the Decayed",     "110001", "元亨。利涉大川。先甲三日，後甲三日。", "山下有風，蠱；君子以振民育德。"),
    (19, "臨", "lín", "Approach",                "110000", "元亨利貞。至于八月有凶。", "澤上有地，臨；君子以教思无窮。"),
    (20, "觀", "guān", "Contemplation",          "000011", "盥而不薦，有孚顒若。", "風行地上，觀；先王以省方觀民設教。"),
    (21, "噬嗑", "shì kè", "Biting Through",     "100101", "亨。利用獄。", "雷電，噬嗑；先王以明罰勑法。"),
    (22, "賁", "bì",  "Grace",                   "101001", "亨。小利有所往。", "山下有火，賁；君子以明庶政，無敢折獄。"),
    (23, "剝", "bō",  "Splitting Apart",         "000001", "不利有攸往。", "山附於地，剝；上以厚下安宅。"),
    (24, "復", "fù",  "Return (The Turning Point)", "100000", "亨。出入无疾，朋來无咎。", "雷在地中，復；先王以至日閉關。"),
    (25, "无妄", "wú wàng", "Innocence",         "100111", "元亨利貞。其匪正有眚，不利有攸往。", "天下雷行，物與无妄；先王以茂對時育萬物。"),
    (26, "大畜", "dà chù", "The Taming Power of the Great", "111001", "利貞。不家食，吉。利涉大川。", "天在山中，大畜；君子以多識前言往行以畜其德。"),
    (27, "頤", "yí",  "The Corners of the Mouth (Providing Nourishment)", "100001", "貞吉。觀頤，自求口實。", "山下有雷，頤；君子以慎言語節飲食。"),
    (28, "大過", "dà guò", "Preponderance of the Great", "011110", "棟橈。利有攸往，亨。", "澤滅木，大過；君子以獨立不懼，遯世无悶。"),
    (29, "坎", "kǎn", "The Abysmal (Water)",     "010010", "習坎，有孚，維心亨，行有尚。", "水洊至，習坎；君子以常德行，習教事。"),
    (30, "離", "lí",  "The Clinging (Fire)",     "101101", "利貞，亨。畜牝牛，吉。", "明兩作，離；大人以繼明照於四方。"),
    (31, "咸", "xián", "Influence (Wooing)",     "001110", "亨，利貞。取女吉。", "山上有澤，咸；君子以虛受人。"),
    (32, "恆", "héng", "Duration",               "011100", "亨，无咎，利貞。利有攸往。", "雷風，恆；君子以立不易方。"),
    (33, "遯", "dùn", "Retreat",                 "001111", "亨，小利貞。", "天下有山，遯；君子以遠小人，不惡而嚴。"),
    (34, "大壯", "dà zhuàng", "The Power of the Great", "111100", "利貞。", "雷在天上，大壯；君子以非禮弗履。"),
    (35, "晉", "jìn", "Progress",                "000101", "康侯用錫馬蕃庶，晝日三接。", "明出地上，晉；君子以自昭明德。"),
    (36, "明夷", "míng yí", "Darkening of the Light", "101000", "利艱貞。", "明入地中，明夷；君子以蒞眾，用晦而明。"),
    (37, "家人", "jiā rén", "The Family (The Clan)", "101011", "利女貞。", "風自火出，家人；君子以言有物而行有恆。"),
    (38, "睽", "kuí", "Opposition",              "110101", "小事吉。", "上火下澤，睽；君子以同而異。"),
    (39, "蹇", "jiǎn", "Obstruction",            "001010", "利西南，不利東北。利見大人，貞吉。", "山上有水，蹇；君子以反身修德。"),
    (40, "解", "xiè", "Deliverance",             "010100", "利西南。无所往，其來復吉。有攸往，夙吉。", "雷雨作，解；君子以赦過宥罪。"),
    (41, "損", "sǔn", "Decrease",                "110001", "有孚，元吉，无咎，可貞，利有攸往。", "山下有澤，損；君子以懲忿窒欲。"),
    (42, "益", "yì",  "Increase",                "100011", "利有攸往，利涉大川。", "風雷，益；君子以見善則遷，有過則改。"),
    (43, "夬", "guài", "Break-through (Resoluteness)", "111110", "揚于王庭，孚號有厲。告自邑，不利即戎，利有攸往。", "澤上於天，夬；君子以施祿及下，居德則忌。"),
    (44, "姤", "gòu", "Coming to Meet",          "011111", "女壯，勿用取女。", "天下有風，姤；后以施命誥四方。"),
    (45, "萃", "cuì", "Gathering Together",      "000110", "亨。王假有廟，利見大人，亨利貞。用大牲吉，利有攸往。", "澤上於地，萃；君子以除戎器，戒不虞。"),
    (46, "升", "shēng", "Pushing Upward",        "011000", "元亨。用見大人，勿恤。南征吉。", "地中生木，升；君子以順德，積小以高大。"),
    (47, "困", "kùn", "Oppression (Exhaustion)", "010110", "亨，貞，大人吉，无咎。有言不信。", "澤无水，困；君子以致命遂志。"),
    (48, "井", "jǐng", "The Well",               "011010", "改邑不改井，无喪无得。往來井井。", "木上有水，井；君子以勞民勸相。"),
    (49, "革", "gé",  "Revolution",              "101110", "巳日乃孚。元亨利貞，悔亡。", "澤中有火，革；君子以治曆明時。"),
    (50, "鼎", "dǐng", "The Cauldron",           "011101", "元吉，亨。", "木上有火，鼎；君子以正位凝命。"),
    (51, "震", "zhèn", "The Arousing (Shock)",   "100100", "亨。震來虩虩，笑言啞啞。震驚百里，不喪匕鬯。", "洊雷，震；君子以恐懼修省。"),
    (52, "艮", "gèn", "Keeping Still (Mountain)", "001001", "艮其背，不獲其身；行其庭，不見其人。无咎。", "兼山，艮；君子以思不出其位。"),
    (53, "漸", "jiàn", "Development (Gradual Progress)", "001011", "女歸吉，利貞。", "山上有木，漸；君子以居賢德善俗。"),
    (54, "歸妹", "guī mèi", "The Marrying Maiden", "110100", "征凶，无攸利。", "澤上有雷，歸妹；君子以永終知敝。"),
    (55, "豐", "fēng", "Abundance",              "101100", "亨，王假之。勿憂，宜日中。", "雷電皆至，豐；君子以折獄致刑。"),
    (56, "旅", "lǚ",  "The Wanderer",            "001101", "小亨，旅貞吉。", "山上有火，旅；君子以明慎用刑而不留獄。"),
    (57, "巽", "xùn", "The Gentle (Penetrating, Wind)", "011011", "小亨，利有攸往，利見大人。", "隨風，巽；君子以申命行事。"),
    (58, "兌", "duì", "The Joyous (Lake)",       "110110", "亨，利貞。", "麗澤，兌；君子以朋友講習。"),
    (59, "渙", "huàn", "Dispersion",             "010011", "亨。王假有廟，利涉大川，利貞。", "風行水上，渙；先王以享于帝立廟。"),
    (60, "節", "jié", "Limitation",              "110010", "亨。苦節不可貞。", "澤上有水，節；君子以制數度，議德行。"),
    (61, "中孚", "zhōng fú", "Inner Truth",      "110011", "豚魚吉。利涉大川，利貞。", "澤上有風，中孚；君子以議獄緩死。"),
    (62, "小過", "xiǎo guò", "Preponderance of the Small", "001100", "亨，利貞。可小事，不可大事。", "山上有雷，小過；君子以行過乎恭，喪過乎哀，用過乎儉。"),
    (63, "既濟", "jì jì", "After Completion",    "101010", "亨，小利貞，初吉終亂。", "水在火上，既濟；君子以思患而豫防之。"),
    (64, "未濟", "wèi jì", "Before Completion",  "010101", "亨。小狐汔濟，濡其尾，无攸利。", "火在水上，未濟；君子以慎辨物居方。"),
]


def _trigram_pair(line_str: str) -> tuple[str, str]:
    """Return (upper_english, lower_english) for the 6-char line string."""
    lower = line_str[:3]
    upper = line_str[3:]
    return TRIGRAMS.get(upper, ("?", "?", "?"))[2], TRIGRAMS.get(lower, ("?", "?", "?"))[2]


@lru_cache(maxsize=1)
def load_hexagrams() -> dict[int, Hexagram]:
    """Load all 64 hexagrams. Line patterns are AUTHORITATIVELY derived
    from the King Wen trigram pairs above; metadata (Chinese names,
    judgements, images) comes from _RAW. The line_str column in _RAW is
    ignored — kept only for diff-friendliness."""
    out: dict[int, Hexagram] = {}
    for n, ch, py, en, _line_str_unused, judg, img in _RAW:
        canonical_line_str = _line_string_for(n)
        lines = [int(c) for c in canonical_line_str]
        lower_ch, upper_ch = _KING_WEN[n]
        out[n] = Hexagram(
            number=n,
            chinese=ch,
            pinyin=py,
            english=en,
            lines=lines,
            judgement=judg,
            image=img,
            upper_trigram=TRIGRAMS[_TRIGRAM_LINES[upper_ch]][2],
            lower_trigram=TRIGRAMS[_TRIGRAM_LINES[lower_ch]][2],
        )
    return out


def hexagram_by_lines(lines: list[int]) -> Hexagram:
    """Look up hexagram by 6-line yin/yang pattern (bottom to top)."""
    target = "".join(str(x) for x in lines)
    for hx in load_hexagrams().values():
        if "".join(str(x) for x in hx.lines) == target:
            return hx
    raise ValueError(f"no hexagram matches line pattern {target}")
