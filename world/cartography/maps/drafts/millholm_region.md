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
                        ?               ?
                        |               |
            F---F---F---T---W---W---W---W
            |                           |
            F                           W
            |                           |
            S---S-------S               ~
                        |
                        S
                        |
                        S
```

## Key

```
T = Town (Millholm Town district centre)
F = Farms (Millholm Farms — road, windmill, cotton farm, wheat farm)
W = Woods (Millholm Woods — forest path, sawmill, smelter, southern grid)
S = Southern (Millholm Southern — rougher town, gnoll territory, moonpetal, barrows)
~ = Deep Woods (clearing — hub for mine and faerie hollow)
? = Hidden/special (Sewers below town, Faerie Hollow, Mine)
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
2. The deep woods procedural passage means you can't just walk north from the woods — should the connection be shown as a gap (no dash) or a special symbol?
3. Faerie Hollow requires DETECT_INVIS to enter — should it appear on the region map or be a mystery?
4. How many cells should each district get? Current thinking:
   - Town: 1 cell (it has its own detailed map)
   - Farms: 3 cells (road west, wheat farm area, cotton farm area)
   - Woods: 4 cells (forest path, sawmill, smelter, deep entry)
   - Southern: 5 cells (rougher town, countryside, gnoll territory, moonpetal, barrows)
   - Deep Woods: 1 cell (clearing hub)
   - Mine: 1 cell (shown as ? — discovered by exploring)
   - Faerie Hollow: 1 cell (shown as ? — discovered by exploring)
