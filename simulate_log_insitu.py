import os
import time
import shutil
import configparser

def getconfig(filename='insitu.cfg'):
    cfg = configparser.ConfigParser()
    cfgfile = os.path.abspath('./' + filename)
    cfg.read(cfgfile)

    print(cfgfile)
    return cfg

log_path = 'Logfiles_260325_1'
time_between_datapoints = 1
config_filename = 'insitu.cfg'

config = getconfig(config_filename)
maindir = config['Paths']['maindir']
reprocessfolder = config['Paths']['reprocessfolder']
bufferfolder = config['Paths']['remotefolder']
kml_savefolder = config['Paths']['kmlpath']
flighttrack_buffer = config['Paths']['flighttrackfolder']

os.makedirs(maindir + '/Buffer', exist_ok=True)
os.makedirs(maindir + '/Buffer_flighttrack', exist_ok=True)

for f in sorted(os.listdir(maindir + '/' + log_path + '/LocalBuffer')):
    print(f'Copying {f}')
    src1 = os.path.join(maindir , log_path + '/LocalBuffer/' + f)
    src2 = os.path.join(maindir , log_path + '/LocalBuffer_track/' + f)
    dst1 = os.path.join(bufferfolder, f)
    dst2 = os.path.join(flighttrack_buffer, f)

    shutil.copy2(src1, dst1)
    shutil.copy2(src2, dst2)
    time.sleep(time_between_datapoints)

print(f'All files copied to {bufferfolder}')
