
import threading

from log_insitu_2 import runlogging
from write_KML import write_KML

cfg = 'insitu.cfg'

def datasave():
    runlogging()

def plot():
    
    write_KML(config_filename=cfg)  

if __name__ == "__main__":
    t1 = threading.Thread(target=datasave, daemon=False)
    t2 = threading.Thread(target=plot, daemon=True)

    t1.start()
    t2.start()

# task left
# once it stops, and automatically rerun
# position file , from external gps
# that Jakob,b had
