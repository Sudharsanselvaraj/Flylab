"""Lossless spike archive and versioned, little-endian live activity packets."""
import struct
import numpy as np
MAGIC=0x31534E43 # bytes CNS1

def packet(tick,rates,events):
    rates=np.asarray(rates,dtype='<f4');pairs=events.astype('<u4',copy=False) if isinstance(events,np.ndarray) else np.asarray([(e['tick'],e['neuron']) for e in events],dtype='<u4').reshape(-1,2)
    return struct.pack('<4I',MAGIC,tick,len(rates),len(pairs))+rates.tobytes()+pairs.tobytes()

class SpikeArchive:
    def __init__(self,path):self.file=path.open('wb');self.count=0
    def append(self,tick,fired):
        rows=np.empty((len(fired),2),dtype='<u4');rows[:,0]=tick;rows[:,1]=fired
        self.file.write(rows.tobytes());self.count+=len(fired)
    def close(self):self.file.close()
