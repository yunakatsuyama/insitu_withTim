# Icon url https://kml4earth.appspot.com/icons.html

import pandas as pd
import numpy as np
import time
import os
import shutil
from datetime import datetime
import configparser

def read_config(filename):
#def read_config(filename = ):
    """Reads config file and returns config dictionary.

    Parameters
    ----------
    filename : :class:`str <python:str>`
        relative or absolute path to file and filename of the config file.

    Returns
    -------
    :class:`dict <python:dict>`
        Dictionary containing the config values.

    Notes
    -----
    Conversion of the different fields should take place in this routine


    """

    config = configparser.ConfigParser(allow_no_value=True)
    file = os.path.abspath(filename)
    config.read(file)
    print("CONFIG FILE:", file)
    print("EXISTS:", os.path.exists(file))

    config.read(file)
    print("FILES READ:", config.read(file))   
    print("SECTIONS FOUND:", config.sections())    
        #files_read = config.read(file)
        #print("Config file read:", files_read)
        #print("Sections found:", config.sections())
        

    return config

    
    
def sync_buffer_to_local(buffer_dir, local_dir, copied):
    os.makedirs(local_dir, exist_ok=True)

    new_files = []

    for f in sorted(os.listdir(buffer_dir)):

        if f.endswith(".tmp"):
            continue

        if f not in copied:

            src = os.path.join(buffer_dir, f)
            dst = os.path.join(local_dir, f)

            try:
                #shutil.copy2(src, dst)
                # shutil.move(src, dst)
                for _ in range(5):
                    try:
                        print(f"filesiye {os.path.getsize(src)}")
                        if os.path.getsize(src) > 0 :
                            shutil.move(src, dst)
                            while True:
                                time.sleep(0.1)
                                if os.path.getsize(dst) > 0:
                                    break
                            copied.add(f)
                            new_files.append(f)
                        else:
                            print("remove")
                            os.remove(buffer_dir)

                        break
                    except PermissionError:
                        print(f'{f} move had a permission error, file still busy.')
                        time.sleep(0.1)


            except FileNotFoundError:
                continue



    return new_files


def local_data_reader(local_dir="LocalBuffer"):
    files = sorted(os.listdir(local_dir))

    for fname in files:
        path = os.path.join(local_dir, fname)
        with open(path, "r") as f:
            lines = f.readlines()
            if len(lines) > 1:
                yield lines[1].strip()   # skip header


# == KML definition ==========
# colors = ["ff0000ff", "ff00ffff", "ff00ff00", "ff00ff00", "ff0000ff"]
def generate_color_scale(nbins):
    colors = []

    for i in range(nbins):
        ratio = i / (nbins - 1)

        if ratio > 0.5:
            r = int(255 * ratio*2)
            g = int(255 * (1 - ratio*2))
            b = 0
        else:
            r = 0
            g = int(255 * ratio)
            b = int(255 * (1 - ratio))

        # KML format: AABBGGRR
        color = f"ff{b:02x}{g:02x}{r:02x}"
        colors.append(color)

    return colors

def generate_styles(nbins, config):
    colors = generate_color_scale(nbins)
    iconfolder = config['Paths']['iconfolder']
    icon_path = os.path.abspath(
        os.path.join(iconfolder, "road_shield3.png")
    )
    styles = ""
    for i, color in enumerate(colors):
        styles += f"""
<Style id="bin_{i}">
  <IconStyle>
    <color>{color}</color>
    <scale>0.6</scale>
    <Icon>
      <href>{icon_path}</href>
    </Icon>
  </IconStyle>
  <LabelStyle>
    <scale>0</scale>
</LabelStyle>
</Style>
"""
    return styles

def init_kml(filename, nbins, config):
    

    tmp = filename + ".tmp"
    styles = generate_styles(nbins, config)
    content = f"""<?xml version="1.0" encoding="UTF-8"?>
    <kml xmlns="http://www.opengis.net/kml/2.2">
    <Document>
    <name>Realtime Track</name>
    {styles}
    <Folder>
    <!-- INSERT_HERE -->
    </Folder>
    </Document>
    </kml>
    """
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)

    os.replace(tmp, filename)

    
def init_track_kml(filename):

    tmp = filename + ".tmp"
    content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
<name>Flight Track</name>

<Style id="trackStyle">
  <LineStyle>
    <color>ff00ffff</color>
    <width>4</width>
  </LineStyle>
</Style>

<Placemark>
<name>Aircraft Track</name>
<styleUrl>#trackStyle</styleUrl>
<LineString>
<tessellate>1</tessellate>
<altitudeMode>absolute</altitudeMode>
<coordinates>
<!-- TRACK_INSERT -->
</coordinates>
</LineString>
</Placemark>

</Document>
</kml>
"""

    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp, filename)
    
    
def init_current_kml(config, filename):
    # get icon
    iconfolder = config['Paths']['iconfolder']
    icon_path = os.path.abspath(
        os.path.join(iconfolder, "airports.png")
    )
    
    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
<name>Current Position</name>
<!-- CURRENT_POINT -->
<Style id="currentStyle">
<IconStyle>
    <scale>0.6</scale>
    <Icon>
    <href>{icon_path}</href>
    </Icon>
</IconStyle>
</Style>
</Document>
</kml>
"""
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
        
                
def value_to_bin(value, vmin, vmax, nbins):
    if value <= vmin:
        return 0
    if value >= vmax:
        return nbins - 1

    step = (vmax - vmin) / nbins
    return int((value - vmin) / step)

def add_point(lat, lon, name, value, alt, vmin, vmax, nbins, filename="merge2.kml"):
    """
    data_dict: {column_name: value, ...}
    """
    
    style_id = value_to_bin(value, vmin, vmax, nbins)   # how to deal with seveeral spieces ???? 
    
    # table_rows = "".join([f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in data_dict.items()])
    # html_table = f"<table border='1'>{table_rows}</table>"

    tmp = filename + ".tmp"

    with open(filename, "r", encoding="utf-8") as f:
        text = f.read()

    placemark = f"""
<Placemark>
  <name>{name}</name>
  <styleUrl>#bin_{style_id}</styleUrl>
  <ExtendedData><Data name="concentration">
    <value>{value}</value>
  </Data>
  </ExtendedData>
  <Point>
    <extrude>1</extrude>
    <altitudeMode>relativeToGround</altitudeMode>
    <coordinates>{lon},{lat},{alt}</coordinates>
  </Point>
</Placemark>
"""

    new_text = text.replace(
        "<!-- INSERT_HERE -->",
        placemark + "\n<!-- INSERT_HERE -->"
    )

    with open(tmp, "w", encoding="utf-8") as f:
        f.write(new_text)

    # os.replace(tmp, filename)
    for _ in range(5):  # tries 5 times to write the file, incase the program is still writing the last file
        try:
            os.replace(tmp, filename)
            break
        except PermissionError:
            time.sleep(0.1)
    else:
        print(f"WARNING: Could not write {filename}")

def add_track_point(lat, lon, alt, filename):

    tmp = filename + ".tmp"

    coord = f"{lon},{lat},{alt}"

    with open(filename, "r", encoding="utf-8") as f:
        text = f.read()

    new_text = text.replace(
        "<!-- TRACK_INSERT -->",
        coord + "\n<!-- TRACK_INSERT -->"
    )

    with open(tmp, "w", encoding="utf-8") as f:
        f.write(new_text)

    os.replace(tmp, filename)
    
def update_current_position(config, lat, lon, alt, name, filename):
    tmp = filename + ".tmp"
    
    iconfolder = config['Paths']['iconfolder']
    icon_path = os.path.abspath(
        os.path.join(iconfolder, "airports.png")
    )
    
    placemark = f"""
<Placemark>
<name>{name}</name>
<styleUrl>#currentStyle</styleUrl>
<Point>
    <altitudeMode>absolute</altitudeMode>
    <coordinates>{lon},{lat},{alt}</coordinates>
</Point>
</Placemark>
"""

    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
<Style id="currentStyle">
<IconStyle>
    <scale>0.6</scale>
    <Icon>
    <href>{icon_path}</href>
    </Icon>
</IconStyle>
</Style>
<name>Current Position</name>
{placemark}
</Document>
</kml>
"""

    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)

    os.replace(tmp, filename)
        
def write_current_pointer(all_files, active_index, output_file):
    """
    all_files: list of KML filenames in order [merge3d_1.kml, merge3d_2.kml, ...]
    active_index: index of currently live file (0-based)
    """
    links = []

    # Old files (frozen)
    for i, f in enumerate(all_files[:active_index]):
        f = os.path.basename(f)
        
        links.append(f"""
  <NetworkLink>
    <name>{f} (frozen)</name>
    <Link>
      <href>{f}</href>
      <refreshMode>onExpire</refreshMode>
    </Link>
  </NetworkLink>""")

    # Active file (live)
    active_file = all_files[active_index]
    active_file = os.path.basename(active_file)
    links.append(f"""
  <NetworkLink>
    <name>{active_file} (live)</name>
    <Link>
      <href>{active_file}</href>
      <refreshMode>onInterval</refreshMode>
      <refreshInterval>1</refreshInterval>
    </Link>
  </NetworkLink>""")

    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
{''.join(links)}
</Document>
</kml>
"""
    tmp = output_file + ".tmp"

    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)

    os.replace(tmp, output_file)

def extract_coordinates(cols, config, ):

    device = config['Default']['device']

    lat_idx = int(config[device]['lat'])
    lon_idx = int(config[device]['lon'])
    alt_idx = int(config[device]['alt'])
    
    # print(len(cols))
    lat = float(cols[lat_idx])
    lon = float(cols[lon_idx])
    alt = float(cols[alt_idx])

    return lat, lon, alt

def extract_species_values(cols, config):
    device = config['Default']['device']
    species = config[device]['species'].split()

    values = {}

    for sp in species:

        if sp not in config[device]:
            continue

        col_index = int(config[device][sp])

        try:
            values[sp] = float(cols[col_index])
        except (ValueError, IndexError):
            continue

    return values

# ===============
#  MAIN 
# ===============
def write_KML(config_filename):
    
    config = read_config(config_filename)
    device = config['Default']['device']
    # -------------------------
    # Paths
    # -------------------------
    reprocessfolder = config['Paths']['reprocessfolder']
    bufferfolder = config['Paths']['remotefolder']
    kml_savefolder = config['Paths']['kmlpath']
    flighttrack_buffer = config['Paths']['flighttrackfolder']
    reprocess = eval(config['Paths']['reprocess'])
    empty_reprocess_folder = eval(config['Paths']['empty_reprocess_folder'])
    emtpy_remote_folder = eval(config['Paths']['emtpy_remote_folder'])

    if empty_reprocess_folder:
        if os.path.exists(reprocessfolder):
            print(f'Deleting all files in {reprocessfolder}!')
            shutil.rmtree(reprocessfolder)
        else:
            pass
    elif not empty_reprocess_folder:
        pass
    else:
        raise ValueError(f'empty_reprocess_folder is either "True" or "False", currently {empty_reprocess_folder}')

    if emtpy_remote_folder:
        if os.path.exists(emtpy_remote_folder):
            print(f'Deleting all files in {emtpy_remote_folder}!')
            shutil.rmtree(emtpy_remote_folder)
        else:
            pass
    elif not emtpy_remote_folder:
        pass
    else:
        raise ValueError(f'emtpy_remote_folder is either "True" or "False", currently {emtpy_remote_folder}')

    if reprocess:
        print('Clearing old KML files and reprocessing new KML files...')
        # Reset KML files
        if os.path.exists(kml_savefolder):
            shutil.rmtree(kml_savefolder)

        # Move LocalBuffer to Buffer
        sync_buffer_to_local(reprocessfolder, bufferfolder, set())
        print('Moved files from LocalBuffer to Buffer.')
    elif not reprocess:
        pass
    else:
        raise ValueError(f'reprocess is either "True" or "False", currently {reprocess}')

    # Reset LocalBuffer for this run
    #if os.path.exists(reprocessfolder):
    #    shutil.rmtree(reprocessfolder)
    #os.makedirs(reprocessfolder)

    os.makedirs(kml_savefolder, exist_ok=True)
    # -------------------------
    # Device settings
    # -------------------------
    species = config[device]['species'].split()
    nbins = config.getint(device, 'nbins')

    print("Species:", species)

    # Read species ranges dynamically
    ranges = {}

    for specie in species:

        key = f"{specie}range"

        if key not in config[device]:
            raise ValueError(f"Missing {key} in config")

        vmin, vmax = [float(v) for v in config[device][key].split()]

        ranges[specie] = (vmin, vmax)

    # -------------------------
    # Initialize per-species state
    # -------------------------
    points_per_file = 300

    state = {}

    for specie in species:

        file_index = 1

        kmlfile = f"{kml_savefolder}/{specie}_{file_index}.kml"

        init_kml(kmlfile, nbins, config)

        vmin, vmax = ranges[specie]

        state[specie] = {
            "file_index": file_index,
            "point_counter": 0,
            "kmlfile": kmlfile,
            "all_files": [kmlfile],
            "vmin": vmin,
            "vmax": vmax
        }

        pointer_file = f"{kml_savefolder}/current_{specie}.kml"

        write_current_pointer(
            state[specie]["all_files"],
            active_index=0,
            output_file=pointer_file
        )
    # ----------------------------
    # Initialize flight track
    # ----------------------------
    flight_state = {
    "file_index": 1,
    "point_counter": 0,
    "kmlfile": f"{kml_savefolder}/flighttrack_1.kml",
    "all_files": [f"{kml_savefolder}/flighttrack_1.kml"]
    }
    
    init_track_kml(flight_state["kmlfile"])

    write_current_pointer(
        flight_state["all_files"],
        active_index=0,
        output_file=f"{kml_savefolder}/current_flighttrack.kml"
    )
    
    # ----------------------------------
    # Initialize current flight position
    # -----------------------------------
    current_position_kml = f"{kml_savefolder}/current_position.kml"
    init_current_kml(config, current_position_kml)   
     
     
     
    # =============================+
    
    # Realtime loop
    
    # =============================+
    
    # copied_files = set(os.listdir(bufferfolder))
    copied_files = set()
    #copied_track_files = set(os.listdir(flighttrack_buffer))
    copied_track_files = set()

    
    while True:

        # Copy only new buffer files
        new_files = sync_buffer_to_local(
            buffer_dir=bufferfolder,
            local_dir=reprocessfolder,
            copied=copied_files
        )
        new_track_files = sync_buffer_to_local(
            buffer_dir=flighttrack_buffer,
            local_dir=reprocessfolder + "_track",
            copied=copied_track_files
        )
        
        os.makedirs(reprocessfolder , exist_ok=True)
        os.makedirs(reprocessfolder + "_track", exist_ok=True)
        
        for fname in new_files:

            with open(os.path.join(reprocessfolder, fname), "r") as f:
                line = f.readline().strip()

            line = line.replace(",", "")
            cols = line.split()

            lat, lon, alt = extract_coordinates(cols, config)
            values = extract_species_values(cols, config)
            
    
            # Update all species
            for specie in species:

                value = values[specie]
                s = state[specie]

                add_point(
                    lat,
                    lon,
                    cols[0],
                    value,
                    alt,
                    s["vmin"],
                    s["vmax"],
                    nbins,
                    s["kmlfile"]
                )

                s["point_counter"] += 1

                # Rotate file after 300 points
                if s["point_counter"] >= points_per_file:

                    s["point_counter"] = 0
                    s["file_index"] += 1

                    newfile = f"{kml_savefolder}/{specie}_{s['file_index']}.kml"

                    init_kml(newfile, nbins, config)

                    s["kmlfile"] = newfile
                    s["all_files"].append(newfile)

                    write_current_pointer(
                        s["all_files"],
                        active_index=s["file_index"] - 1,
                        output_file=f"{kml_savefolder}/current_{specie}.kml"
                    )

            print(f"Processed {fname}")

        # For flightrack  and current flight position 
        for fname in new_track_files:

            with open(os.path.join(reprocessfolder + "_track", fname), "r") as f:
                line = f.readline().strip()

            cols = line.split()

            try:
                lat = float(cols[1])
                lon = float(cols[2])
                alt = float(cols[3])
            except (ValueError, IndexError):
                continue
            
            # current flight position
            # KML file update
            update_current_position(
                config,
                lat,
                lon,
                alt,
                name="Current Aircraft Position",
                filename=current_position_kml
            )    
            
            # flighttrack
            # add point
            add_track_point(
                lat,
                lon,
                alt,
                flight_state["kmlfile"]
            )

            flight_state["point_counter"] += 1
            
            # rotate file after 300 points (only for flighttrack)
            if flight_state["point_counter"] >= points_per_file:

                flight_state["point_counter"] = 0
                flight_state["file_index"] += 1

                newfile = f"{kml_savefolder}/flighttrack_{flight_state['file_index']}.kml"

                init_track_kml(newfile)

                flight_state["kmlfile"] = newfile
                flight_state["all_files"].append(newfile)

                write_current_pointer(
                    flight_state["all_files"],
                    active_index=flight_state["file_index"] - 1,
                    output_file=f"{kml_savefolder}/current_flighttrack.kml"
                )
                
                
if __name__ == '__main__':
    while True :
        write_KML('insitu.cfg')                   