import os
import shutil
from write_KML import read_config

config_filename = 'insitu.cfg'
config = read_config(config_filename)

reprocessfolder = config['Paths']['reprocessfolder']
empty_reprocess_folder = eval(config['Paths']['empty_reprocess_folder'])
emtpy_remote_folder = eval(config['Paths']['emtpy_remote_folder'])

if os.path.exists(reprocessfolder):
    print(f'Deleting all files in {reprocessfolder}!')
    shutil.rmtree(reprocessfolder)
else:
    pass

if os.path.exists(emtpy_remote_folder):
    print(f'Deleting all files in {emtpy_remote_folder}!')
    shutil.rmtree(emtpy_remote_folder)
else:
    pass
