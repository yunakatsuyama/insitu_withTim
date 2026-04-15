# Created by Yuna Katsuyama and Tim Suhling
# University of Bremen
# yuna@uni-bremen.de
# timsuh@uni-bremen.de
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Creates KML files from data read by log_insitu
"""
# Icon url https://kml4earth.appspot.com/icons.html

import time
import os
import shutil
import configparser
from datetime import datetime, timedelta
from collections import deque



def read_config(filename):
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

    return config


def sync_buffer_to_local(buffer_dir, local_dir, copied, start_index=0, end_index=None, single_file=True, ):
    """
    Moves files from buffer_dir to local_dir.
    Adds all moved files to the set copied
    Parameters
    ----------
    skip_files
    buffer_dir
    local_dir
    copied

    Returns copied set with moved files
    -------

    """


    os.makedirs(local_dir, exist_ok=True)

    new_files = []

    buffer_files = sorted(os.listdir(buffer_dir))

    if end_index is None:
        end_index = len(buffer_files)

    for f in buffer_files[start_index:end_index]:

        if f.endswith(".tmp"):
            continue

        if f not in copied:

            src = os.path.join(buffer_dir, f)
            dst = os.path.join(local_dir, f)

            try:
                for _ in range(5):
                    try:
                        if os.path.getsize(src) > 0 :
                            shutil.move(src, dst)
                            while True:
                                time.sleep(0.1)
                                if os.path.getsize(dst) > 0:
                                    break
                            copied.add(f)
                            if single_file:
                                yield f
                            else:
                                new_files.append(f)
                        else:
                            # print(f'{f} took to long and was ignored')
                            os.remove(src)
                        break
                    except PermissionError:
                        # print(f'{f} move had a permission error, file still busy.')
                        time.sleep(0.1)

            except FileNotFoundError:
                continue

    return new_files


def reprocess_file_reader(local_dir, copied, skip_files=0):
    os.makedirs(local_dir, exist_ok=True)
    new_files = []

    old_buffer_files = sorted(os.listdir(local_dir))

    if skip_files >= len(old_buffer_files):
        print(f'WARNING: reprocess_skip_files : {skip_files} is bigger than files in LocalBuffer:'
              f' {len(old_buffer_files)}')
        if len(old_buffer_files) > 99:
            skip_files = len(old_buffer_files) - 100
            print('Loading 100 most recent files')
        else:
            skip_files = 0
            print('Less than 100 files in buffer, reprocessing all anyway...')


    for f in old_buffer_files[skip_files:]:
        copied.add(f)
        new_files.append(f)
    print(f'REPROCESSING FILES: {len(new_files)}')
    return new_files


def local_data_reader(local_dir="LocalBuffer"):
    files = sorted(os.listdir(local_dir))

    for fname in files:
        path = os.path.join(local_dir, fname)
        with open(path, "r") as f:
            lines = f.readlines()
            if len(lines) > 1:
                yield lines[1].strip()   # skip header
    return None


# == KML definition ==========
# colors = ["ff0000ff", "ff00ffff", "ff00ff00", "ff00ff00", "ff0000ff"]
def generate_color_scale(nbins):
    colors = []
    r_ = []
    g_ = []
    b_ = []

    for i in range(nbins):
        ratio = i / (nbins - 1)

        if ratio > 0.5:
            r = int(255 * (ratio-0.5) * 2)
            g = int(255 * (1 - (ratio-0.5)*2))
            b = 0
        else:
            r = 0
            g = int(255 * ratio*2)
            b = int(255 * (1 - ratio*2))

        colors.append(f"ff{b:02x}{g:02x}{r:02x}")
        r_.append(r)
        g_.append(g)
        b_.append(b)
    return colors, r_, g_, b_

def generate_styles(nbins, config, compress):
    colors, _, _, _ = generate_color_scale(nbins)
    iconfolder = config['Paths']['iconfolder']
    #icon_path = os.path.abspath(
    #    os.path.join(iconfolder, "road_shield3.png")
    #)
    if compress:
        icon_path ='road_shield3.png'
    else:
        icon_path = '../../icon_folder/road_shield3.png'

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

        #       <href>{icon_path}</href>
    return styles


def init_kml(filename, nbins, config, compress):
    tmp = filename + ".tmp"
    styles = generate_styles(nbins, config, compress)
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
    return None

    
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
    return None
    
    
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
    return None
        
                
def value_to_bin(value, vmin, vmax, nbins):
    if value <= vmin:
        return 0
    if value >= vmax:
        return nbins - 1

    step = (vmax - vmin) / nbins
    return int((value - vmin) / step)


def add_point(lat, lon, name, value, alt, vmin, vmax, nbins, filename="merge2.kml", reprocess: bool = False,
              compress: bool = False):
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
  <ExtendedData>
  <Data name="Concentration">
    <value>{value}</value>
  </Data>
  <Data name="Altitude">
    <value>{alt}</value>
  </Data>
  </ExtendedData>
  <Point>
    <extrude>1</extrude>
    <altitudeMode>relativeToGround</altitudeMode>
    <coordinates>{lon},{lat},{alt}</coordinates>
  </Point>
</Placemark>
"""
    placemark_reprocess = f"""
<Placemark>
  <name>{name}</name>
  <styleUrl>#bin_{style_id}</styleUrl>
  <ExtendedData>
  <Data name="Concentration">
    <value>{value}</value>
  </Data>
  <Data name="Altitude">
    <value>{alt}</value>
  </Data>
  <Data name="lat">
    <value>{lat}</value>
  </Data>
  <Data name="lon">
    <value>{lon}</value>
  </Data>
  </ExtendedData>
  <Point>
    <extrude>1</extrude>
    <altitudeMode>relativeToGround</altitudeMode>
    <coordinates>{lon},{lat},{alt}</coordinates>
  </Point>
</Placemark>
"""
    if reprocess:
        used_placemark = placemark_reprocess
    else:
        used_placemark = placemark


    new_text = text.replace(
        "<!-- INSERT_HERE -->",
        used_placemark + "\n<!-- INSERT_HERE -->"
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
    return None

    
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

    # os.replace(tmp, filename)
    for _ in range(5):  # tries 5 times to write the file, incase the program is still writing the last file
        try:
            os.replace(tmp, filename)
            break
        except PermissionError:
            time.sleep(0.1)
    else:
        print(f"WARNING: Could not write {filename}")
    return None

        
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

    # os.replace(tmp, output_file)
    for _ in range(5):  # tries 5 times to write the file, incase the program is still writing the last file
        try:
            os.replace(tmp, output_file)
            break
        except PermissionError:
            time.sleep(0.1)
    else:
        print(f"WARNING: Could not write {output_file}")
    return None


def extract_coordinates(cols, config, reverse=False):
    device = config['Default']['device']

    lat_idx = int(config[device]['lat'])
    lon_idx = int(config[device]['lon'])
    alt_idx = int(config[device]['alt'])

    if reverse:
        # To compensate if amount of data given from device varies by shifting given columns relative to end of cols.
        # Will only work for external gps because of the fixed relativ idx to the end of cols
        len_cols = len(cols)
        max_idx = max(alt_idx, lat_idx, lon_idx)
        offset_idx = len_cols - max_idx - 2
        lat_idx += offset_idx
        lon_idx += offset_idx
        alt_idx += offset_idx
    else:
        pass

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



def parse_timestamp(fname):
    base = os.path.basename(fname)
    timestamp_str = base.split("_")[0]  # YYMMDDtHHMMSS
    return datetime.strptime(timestamp_str, "%y%m%dt%H%M%S")


def find_closest_file(buffer, target_time):
    closest = None
    min_diff = None

    for t, path in buffer:
        diff = abs((t - target_time).total_seconds())

        if min_diff is None or diff < min_diff:
            min_diff = diff
            closest = path
    return closest, min_diff


def override_config(config, value, header, variable, config_filename):
    config[header][variable] = str(value)
    with open(config_filename, 'w') as configfile:
        config.write(configfile)


def update_buffer_skip_files(config_filename, new_value):
    with open(config_filename, "r") as f:
        content = f.read()

    content = content.replace(
        f"buffer_skip_files : {new_value+1}",
        f"buffer_skip_files : {new_value}"
    )

    with open(config_filename, "w") as f:
        f.write(content)


# ===============
#  MAIN 
# ===============
def write_KML(config_filename, compress: bool = False):
    
    config = read_config(config_filename)
    device = config['Default']['device']
    # -------------------------
    # Paths
    # -------------------------
    reprocessfolder = config['Paths']['reprocessfolder']
    bufferfolder = config['Paths']['remotefolder']
    kml_savefolder = config['Paths']['kmlpath']
    if compress:
        reprocess = True
        reprocess_skip_files = 0
        buffer_skip_files = 0
        points_per_file = 100000000
    else:
        reprocess = eval(config['Paths']['reprocess'])
        reprocess_skip_files = int(config['Paths']['reprocess_skip_files'])
        buffer_skip_files = int(config['Paths']['buffer_skip_files'])
        points_per_file = int(config['LogParams']['points_per_file'])
    external_gps = eval(config[device]['external_gps'])
    timelag = config[device].getint('timelag', fallback=3)

    if reprocess:
        # Reset KML files
        if os.path.exists(kml_savefolder):
            print('Clearing old KML files and reprocessing new KML files...')
            shutil.rmtree(kml_savefolder)
    os.makedirs(kml_savefolder, exist_ok=True)
    # -------------------------
    # Device settings
    # -------------------------
    species = config[device]['species'].split()
    nbins = config.getint(device, 'nbins')

    # print("Species:", species)

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
    # points_per_file = 300

    state = {}

    for specie in species:

        file_index = 1

        kmlfile = f"{kml_savefolder}/{specie}_{file_index}.kml"

        init_kml(kmlfile, nbins, config, compress)

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

    # ----------------------------------
    # Initialize current flight position
    # -----------------------------------

    current_position_kml = f"{kml_savefolder}/current_position.kml"
    init_current_kml(config, current_position_kml)   

    # =============================+
    # Realtime loop
    # =============================+
    copied_files = set()
    time_buffer = deque()

    initial_reprocess = reprocess

    time_end_loop = None

    while True:
        time_start_loop = time.time()

        # Moving skipped files from Buffer to LocalBuffer when program is not busy to clean up buffer.
        # If previous processing took less than 0.8 seconds enough time should be free to move one file without blocking
        # the rest of the program.
        if time_end_loop is not None and buffer_skip_files != 0:
            time_delta = time_end_loop - time_start_loop
            if time_delta < 0.8:
                moved_files = sync_buffer_to_local(bufferfolder, reprocessfolder, set(), 0, 1)
                for f in moved_files:
                    #print(f'Moved {f} without creating KML')
                    pass
                buffer_skip_files -= 1
                # Update the number of files left to skip in the config file to be consistent after restart
                update_buffer_skip_files(config_filename, buffer_skip_files)

        os.makedirs(reprocessfolder, exist_ok=True)
        if initial_reprocess:
            # Mark files in LocalBuffer as new_files
            new_files = reprocess_file_reader(reprocessfolder, copied_files, reprocess_skip_files,)

            # Set reprocess as False to only reprocess them once!
            initial_reprocess = False

        elif not initial_reprocess:
            # Copy only new buffer files
            new_files = sync_buffer_to_local(
                buffer_dir=bufferfolder,
                local_dir=reprocessfolder,
                copied=copied_files,
                start_index=buffer_skip_files,
            )
        else:
            raise ValueError(f'reprocess is either "True" or "False", currently {reprocess}')

        for fname in new_files:

            with open(os.path.join(reprocessfolder, fname), "r") as f:
                line = f.readline().strip()

            line = line.replace(",", "")
            cols = line.split()

            # Trying to set GPS DATA and values
            try:
                lat, lon, alt = extract_coordinates(cols, config)
                values = extract_species_values(cols, config)
            except (IndexError, ValueError):
                if external_gps:
                    try:
                        lat, lon, alt = extract_coordinates(cols, config, reverse=True)
                        values = extract_species_values(cols, config)
                        print('Different amount of data given from Device than expected, trying to adjust...!')
                    except (IndexError, ValueError):
                        print('GPS Index Problem, skipping file!')
                        continue
                else:
                    print('GPS Index Problem, skipping file!')
                    continue

            if lat == 0.0 or lon == 0.0:
                print('One or more GPS at 0°, skipping file!')
                continue

            # ------------------
            # Timelag
            # ------------------

            full_path = os.path.join(reprocessfolder, fname)
            current_time = parse_timestamp(fname)

            # Add good data point to time_buffer
            time_buffer.append((current_time, full_path))

            # Keep time_buffer with only needed times
            while len(time_buffer) > timelag * 5:
                time_buffer.popleft()

            try:
                target_time = current_time - timedelta(seconds=timelag)
                lagged_file, time_error = find_closest_file(time_buffer, target_time)

                if lagged_file is not None:
                    if time_error not in [0.0, 1.0]:
                        print(f'Timelag off by {time_error:.0f} seconds from selected device timelag.')

                    with open(lagged_file, "r") as f:
                        lag_line = f.readline().strip()

                    lag_line = lag_line.replace(",", "")
                    lag_cols = lag_line.split()

                    lag_lat, lag_lon, lag_alt = extract_coordinates(lag_cols, config)

                    lat, lon, alt = lag_lat, lag_lon, lag_alt

            except Exception as e:
                print(f'Timelag failed, Exception: {e}')


            # Update all species
            for specie in species:

                try:
                    value = values[specie]
                except KeyError:
                    print(f'{fname} had index problems, skipping file!')
                    continue
                s = state[specie]

                try:
                    _ = int(lat)
                    _ = int(lon)
                    _ = int(alt)
                except ValueError:
                    print('GPS Value Error, could not convert to int!')
                    continue

                add_point(
                    lat,
                    lon,
                    cols[1],
                    value,
                    alt,
                    s["vmin"],
                    s["vmax"],
                    nbins,
                    s["kmlfile"],
                    reprocess,
                    compress
                )

                try:
                    print(f'{specie}: {value}')
                except KeyError:
                    pass

                s["point_counter"] += 1

                # Rotate file after points_per_file amount of points
                if s["point_counter"] >= points_per_file:

                    s["point_counter"] = 0
                    s["file_index"] += 1

                    newfile = f"{kml_savefolder}/{specie}_{s['file_index']}.kml"

                    init_kml(newfile, nbins, config, False)

                    s["kmlfile"] = newfile
                    s["all_files"].append(newfile)

                    write_current_pointer(
                        s["all_files"],
                        active_index=s["file_index"] - 1,
                        output_file=f"{kml_savefolder}/current_{specie}.kml"
                    )

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

            print(f"Processed {fname}")
        time_end_loop = time.time()
        if compress:
            print('KML creation finished')
            return config, kml_savefolder, species


if __name__ == '__main__':
    write_KML('insitu.cfg')