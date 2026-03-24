# Millholm Region — Zone Map Draft

Zone-level overview. Each cell represents a district or key junction point,
not individual rooms. "Room scale" is larger outside town — a single cell
in the woods covers more ground than a cell in the town centre.

## District Connections

- Town ↔ Farms: west road
- Town ↔ Woods: east road
- Town ↔ Southern: south gate
- Farms ↔ Southern: south fork east to countryside road
- Town ↓ Sewers: hidden doors (cellar, abandoned house)
- Woods → Deep Woods: procedural passage north
- Deep Woods Clearing ↔ Mine: procedural passage west
- Deep Woods Clearing → Faerie Hollow: invisible door north

## Draft Layout

```
                                 F
                           ~  ~  M--D
                  C        ~  ?  ~
   F     F     T  T  T  R  ~  ~  ~ 
R--#--#--#--#--T--T--T--#--#--#--#--#--Z
      #        T  T  T  R  ~  ~  ~    
      #--?        #        ~  R  ~
      #           #        ~  ~  ~
      #           F
      #           #
      #        ?--~--?
      #           #
      #--#--#--#--#
                  Z          



## Out of Town / Regional Map Key

## this will be harder then an in town key because much of what is shown in town will be standard but there may be significant variability in ouf ot town maps so some legend symbols may have to be generalised to cover serveral possibly meansings

```
# = Roads (out of town)
T = Town / Village / City
C = Cemetary
F = Farm / Resource Harvesting
M = Mine
R = Resource Processing
~ = Woods / Forest / Wilderness
? = Place of interest
D = Dungeon
Z = Zone Exit


```

## Notes

- The main E-W road runs through Farms → Town → Woods as a continuous route
- Farms has 2 cells west of town to represent the road + the farm areas
- Woods has 4 cells east of town: forest path, sawmill area, smelter area, deep woods entry
- Southern hangs below with 2 entry points: south from town gate, east from farms fork
- Deep Woods (~) is reached via procedural passage from the woods — shown as a disconnected node to the north-east to represent the "you can't just walk there" feel
- Sewers are underground (not shown on surface map) — marked with ? above town
- Faerie Hollow and Mine are reached from the deep woods clearing — shown as ? nodes above the clearing
- The map intentionally lacks detail within each district — that's what the district maps are for

## Concerns / Questions

1. Should the sewers appear on this map at all? They're hidden and underground. Maybe omit entirely and let the sewer district map handle it.

no...


2. The deep woods procedural passage means you can't just walk north from the woods — should the connection be shown as a gap (no dash) or a special symbol?

yes

3. Faerie Hollow requires DETECT_INVIS to enter — should it appear on the region map or be a mystery?

only if they survey in one of the squares of the fairie hollow

4. How many cells should each district get? Current thinking:
   - Town: 1 cell (it has its own detailed map)
   - Farms: 3 cells (road west, wheat farm area, cotton farm area)
   - Woods: 4 cells (forest path, sawmill, smelter, deep entry)
   - Southern: 5 cells (rougher town, countryside, gnoll territory, moonpetal, barrows)
   - Deep Woods: 1 cell (clearing hub)
   - Mine: 1 cell (shown as ? — discovered by exploring)
   - Faerie Hollow: 1 cell (shown as ? — discovered by exploring)

already addressed