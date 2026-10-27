CSP TreeFX — bring your own models
==================================

trees.txt places ~21,000 plants along the loop and the north roads (positions, headings and sizes) but this package
ships NO tree models: the build was authored with models taken from other Assetto Corsa mods
(No Hesi 1.10, Algarve Portimão 2023, Shutoko Revival Project) and their authors have not
licensed redistribution.

If you own those mods, copy these files from their extension/trees folders into this one:
  from nohesi_110:              PalmV1.bin PalmV2.bin PalmV3.bin PepperV1.bin SycamoreV1.bin
                                SycamoreV2.bin Sage.bin Yucca.bin Agave.bin
  from algarve_portimao_2023:   Gum.bin Oak3.bin Bush.bin Bush3.bin
  from shuto_revival_project:   Pine_Aleppo_Desktop_5_Forest_custom1.bin  -> rename to Pine_Aleppo.bin

then in extension/ext_config.ini remove the leading ";" from the two lines under [TREES]:
  ;LIST_0 = trees/trees.txt
  ;SURFACE_MATERIALS = 1GRASS_0_mat, 1GRASS_1_mat, 1ROAD_road_mat

Any TreeFX model works under any of those names if you prefer your own species.
