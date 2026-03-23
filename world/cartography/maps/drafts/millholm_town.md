# Millholm Town — District Map Draft

Reference document matching the implemented map in `millholm_town.py`.

## Layout

```
              C
              |
              @
              |
              #
              |
            I # H
            | | |
      T S W # # # B A J
    X-#-#-#-#-#-#-#-#-#-X
      h h * # # # $ P L
            | | |
            + # G
            | | |
            # # G
            | | |
            I # g
              |
              @
```

## Legend

```
#  Road           @  Gate           C  Cemetery
I  Inn            S  Smithy         $  Bank
+  Temple         G  Guild          g  Gaol
*  Shop           B  Bakery         H  Stable
W  Woodshop       T  Tailor         L  Leathershop
A  Apothecary     J  Jeweller       P  Post Office
h  House          X  Zone Exit
```

## Room-to-Cell Mapping

### Row 0-2: Cemetery and North Road
| Cell | Point Key | POI | Game Room |
|------|-----------|-----|-----------|
| C | cemetery | cemetery | Millholm Cemetery |
| @ | cemetery_gates | gate | Cemetery Gates |
| # | north_road | road | North Road |

### Row 3: Above Square
| Cell | Point Key | POI | Game Room |
|------|-----------|-----|-----------|
| I | inn | inn | The Harvest Moon Inn |
| # | sq_n | road | Market Square - North (also occupies row 4 centre) |
| H | stables | stable | Stables |

### Row 4: North Shops + Square Top Row
| Cell | Point Key | POI | Game Room |
|------|-----------|-----|-----------|
| T | textiles | tailor | Textiles |
| S | smithy | smithy | Old Hendricks Smithy |
| W | woodshop | woodshop | Woodshop |
| # | sq_nw | road | Market Square - Northwest |
| (sq_n) | — | — | (second cell of sq_n from row 3) |
| # | sq_ne | road | Market Square - Northeast |
| B | bakery | bakery | Goldencrust Bakery |
| A | apothecary | apothecary | Apothecary |
| J | jeweller | jeweller | The Gilded Setting |

### Row 5: The Old Trade Way (Main E-W Road)
| Cell | Point Key | POI | Game Room |
|------|-----------|-----|-----------|
| X | road_far_west | zone_exit | The Old Trade Way (west end → Farms) |
| # | road_west | road | The Old Trade Way |
| # | road_mid_west | road | The Old Trade Way |
| # | sq_w | road | Market Square - West |
| # # # | sq_center | road | Market Square - Centre (3 cells wide) |
| # | sq_e | road | Market Square - East |
| # | road_east | road | The Old Trade Way |
| # | road_mid_east | road | The Old Trade Way |
| X | road_far_east | zone_exit | The Old Trade Way (east end → Woods) |

### Row 6: South Shops + Square Bottom Row
| Cell | Point Key | POI | Game Room |
|------|-----------|-----|-----------|
| h | elena_house | house | Elena's House |
| h | abandoned_house | house | Abandoned House |
| * | general_store | shop | General Store |
| # | sq_sw | road | Market Square - Southwest |
| # | sq_s | road | Market Square - South |
| # | sq_se | road | Market Square - Southeast |
| $ | bank | bank | Order of the Golden Scale |
| P | post_office | post_office | Millholm Post Office |
| L | leathershop | leathershop | The Tanned Hide |

### Row 7-9: South Road
| Cell | Point Key | POI | Game Room |
|------|-----------|-----|-----------|
| + | shrine | temple | Shrine |
| # | south_road | road | South Road |
| G | warriors_guild | guild | The Iron Company |
| # | beggars_alley | road | Beggar's Alley |
| # | mid_south_road | road | Mid South Road |
| G | mages_guild | guild | Mages Guild |
| I | broken_crown | inn | The Broken Crown |
| # | far_south_road | road | Far South Road |
| g | gaol | gaol | Millholm Gaol |

### Row 10: South Gate
| Cell | Point Key | POI | Game Room |
|------|-----------|-----|-----------|
| @ | south_gate | gate | South Gate (→ Southern District) |

## Design Decisions

- **Market square = road.** The 3x3 square is 9 road cells. Shops line the edges.
- **sq_center spans 3 cells** horizontally to represent the wide market square.
- **sq_n spans 2 cells** vertically (rows 3 and 4) to give the inn/stables breathing room.
- **Gareth's House omitted.** Shares grid position with General Store (both enter from the same block). General Store is more useful to players.
- **NOT mapped:** building interiors, secret passage (Gareth→Abandoned), NPC back rooms (hendricks_house, mara_house, priest_quarters, arcane_study, barracks), Hilda's Distillery (back room of apothecary).
- **Zone exits (X):** west end connects to Farms district, east end connects to Woods district.
- **South gate (@):** connects to Southern District.
- **Sewers not shown.** Underground access points (cellar, abandoned house) are hidden doors — the sewer has its own district map.
