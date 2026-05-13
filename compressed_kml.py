# Created by Tim Suhling
# University of Bremen
# timsuh@uni-bremen.de
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Overrides points_per_file to create single KML for each species.
"""
import os
import shutil
from write_KML import write_KML, read_config

if __name__ == '__main__':
    config, kml_savefolder, species = write_KML('insitu.cfg', compress=True)
    compressed_path = config['Paths']['compressed_path']
    os.makedirs(compressed_path, exist_ok=True)
    for specie in species:
        shutil.move(
            f"{kml_savefolder}/{specie}_1.kml",
            f"{compressed_path}/{specie}.kml"
        )
    shutil.copy(
        f"{config['Paths']['iconfolder']}/road_shield3.png",
        f"{compressed_path}/road_shield3.png"
    )
    print(f'Compressed KMLs moved to {compressed_path}')
