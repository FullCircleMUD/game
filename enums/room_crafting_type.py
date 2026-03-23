from enum import Enum



class RoomCraftingType(Enum):

    WINDMILL = "windmill" # wheat to flour - no related skill - just process and cost
    BAKERY = "bakery" # flour + wood to bread - PROCESSING (no skill required)

    SMELTER = "smelter" # ore to ingot (iron, gold, silver, etc) - no related skill - just process and cost
    JEWELLER = "jeweller" # various metal items - jewellry atc - SKILL RELATED
    SMITHY = "smithy" # various metal items  - SKILL RELATED

    TANNERY = "tannery" # hide to leather - no related skill - just process and cost
    LEATHERSHOP = "leathershop" # various leather items - SKILL RELATED

    SAWMILL = "sawmill" # logs to timber - no related skill - just process and cost
    WOODSHOP = "woodshop" # various timbe based items - SKILL RELATED
    
    TEXTILEMILL = "textilemill" # wool to cloth - no related skill - just process and cost
    TAILOR = "tailor" # various cloth items - SKILL RELATED

    APOTHECARY = "apothecary" # various potions and other consumables - SKILL RELATED

    WIZARDS_WORKSHOP = "wizards_workshop" # enchanting items - SKILL RELATED (mage only)

    SHIPYARD = "shipyard" # build and repair ships - SKILL RELATED (shipwright)

