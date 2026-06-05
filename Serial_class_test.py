# -*- coding: utf-8 -*-
"""
Created on Wed Oct 19 13:42:19 2022

@author: lucas
"""
import serial
import serial.tools.list_ports
import datetime
import os 
import time 
import numpy as np

from collections import deque

map_freq ={

182 : 250,    
181 : 500,
180 : 1000,
179 : 2000,
178 : 4000,
177 : 8000,
176 : 16000
    
    
}

map_gain ={

40  :  4 ,   
72  :  8 ,
82  : 12 ,
104 : 24,    
4   : 40,
8   :72,
12  :82, 
24  :104    
}


class serial_class():
    def __init__(self, buffer, buffer_window):
        self._running = True
        self.serialPort = None
        self.buffer = buffer
        
        if (self.buffer):
            # CHANGES : Implementation of circular buffer
            
            BUFFER_TIME = buffer_window
            SAMPLE_RATE = 250
            MAX_SAMPLES = BUFFER_TIME * SAMPLE_RATE
            
            self.bytes_data     = deque(maxlen=200)
            
            self.data           = deque(maxlen=MAX_SAMPLES)
            self.timestamp      = deque(maxlen=MAX_SAMPLES)
            self.time_adu       = deque(maxlen=MAX_SAMPLES)
            self.vecteur_trigger= deque(maxlen=MAX_SAMPLES)
        
        else:
            self.bytes_data     =[]
            self.data           =[]
            self.timestamp      =[]
            self.time_adu       =[]
            self.vecteur_trigger=[]
        
        self.adu = ( 4.5 * 1E6 / (24* pow(2,23) )) 
        
        self.nb_elec  = 8
        self.gain     = 24
        self.Fe       = 250  
        self.name_subject ='Nicolas'
        self.bytes_capt1= int('00001111',2)
        self.bytes_capt2= int('00111111',2)

        
    def terminate(self):
        self._running = False
        self.serialPort.write('stop\n'.encode('utf-8'))
        time.sleep(0.1)
        self.serialPort.close()
        
    def init_port(self):
        ports = serial.tools.list_ports.comports()
        com = ports[0].name   # 'COM3'
        self.serialPort = serial.Serial(
            port='/dev/ttyUSB0',\
            baudrate=2000000,\
            bytesize=serial.EIGHTBITS)
    
    def change_gain(self,new_gain):
        self.gain = new_gain 
        self.adu = ( 4.5 * 1E6 / (new_gain * pow(2,23) )) 
    
    def reception(self):
        self.serialPort.write('connect\n'.encode('utf-8')) 
        time.sleep(0.1)
        self.serialPort.write(("{\"cmd\":\"cut\",\"stateS1_8\":"+str(self.bytes_capt1)+",\"stateS9_16\":"+str(self.bytes_capt2)+"}\n").encode('utf-8'))
        time.sleep(0.1)
        self.serialPort.write(("{\"cmd\":\"gain\", \"level\":"+str(map_gain[self.gain])+"}\n").encode('utf-8'))
        time.sleep(0.1)
        self.serialPort.flush()
        
        self.buffer = b''
        
        while(self._running):
            
            chunk = self.serialPort.read(512)
            if not chunk:
                time.sleep(0.001)
                continue
            self.buffer += chunk
            
            while b'\n' in self.buffer:
                line, self.buffer = self.buffer.split(b'\n', 1)
                serialString = line + b'\n'
                
                if serialString[2:4] == b'nb':
                    self.read_header(serialString)
                elif serialString[2:4] == b'ts':
                    t,d = self.read_line(serialString)
                    self.bytes_data.append(d)
                    try:
                        self.data.extend(np.array_split(self.adu_to_data(d, self.nb_elec),4))
                    except:
                        self.data.extend([self.data[-1],self.data[-1],self.data[-1],self.data[-1]])
                    
                    self.time_adu.extend([t]*4)
                    self.vecteur_trigger.extend([0]*4)
                    self.timestamp.extend([time.time()]*4)
                    
            
    def read_header(self,tram):
        str_tram = tram.decode()
        list_tram = str_tram.split('"')
        for i in range(len(list_tram)):
            if list_tram[i] == 'nb':
                nb = list_tram[i+1]
                nb = nb.replace(':', '')
                nb = nb.replace(',', '')
                self.nb_elec = int(nb)
                
            if list_tram[i] == 'fq':
                fq = list_tram[i+1]
                fq = fq.replace(':', '')
                fq = fq.replace(',', '')
                fq = int(fq)
                self.Fe = map_freq[fq]
            if list_tram[i] == 'gn':
                gn = list_tram[i+1]
                gn = gn.replace(':', '')
                gn = gn.replace(',', '')
                gn = int(gn)
                self.change_gain(map_gain[gn])
        
    def read_line(self,tram):
        str_tram = tram.decode()
        list_tram = str_tram.split('"')
        timestamp=0
        data=[]
        try: 
            for i in range(len(list_tram)):
                if list_tram[i] == 'ts':
                    timestamp=list_tram[i+1]
                    timestamp = timestamp.replace(':', '')
                    timestamp = timestamp.replace(',', '')
                    timestamp =int(timestamp)
                if list_tram[i] == 'sx':
                    data_str=list_tram[i+1]
                    data_str = data_str.replace(':', '')
                    data_str = data_str.replace('[', '')
                    data_str = data_str.replace(']', '')
                    data = data_str.split(',')
                    data.pop(-1)
                    data = [int(numeric_string) for numeric_string in data]
        except:
            timestamp = self.timestamp[-1]
            data= self.bytes_data[-1]
        return timestamp,data

    def adu2uV(self,data_adu):
        # print(data_adu)
        data_uV = self.adu * data_adu
        return data_uV

    def adu_to_data(self,data,nb_elec):
        list_adu = []
        for i in range(4):
            for j in range(nb_elec):
                temp_adu = data[j]
                if i>0:
                    temp_adu = temp_adu - data[j+(i*nb_elec)] 
                              
                temp_adu = self.adu2uV(temp_adu)
                list_adu.append(temp_adu)
        return list_adu    
        
    def update_last_trig(self,var_trig):
        self.vecteur_trigger[-1]=var_trig    
            
    def generate_name(self):
        
        name_file ='dataset/'+ self.name_subject+'/'+datetime.datetime.fromtimestamp(time.time()).strftime("%d-%m-%Y_%H-%M") + '.csv'

        if not os.path.exists('dataset/'+self.name_subject):
            os.makedirs('dataset/'+self.name_subject)
        
        return name_file
    
    def save_file(self):
            
            if not self._running :
                ######### Sauvegarde Fichier 
                self.data=np.array(self.data)
                self.time_adu=np.array(self.time_adu)
                self.vecteur_trigger=np.array(self.vecteur_trigger)
                self.timestamp=np.array(self.timestamp)
                ##sauvegarde fichier
                fichier_save=self.time_adu
                for i in range(self.data.shape[1]):
                    fichier_save=np.vstack([fichier_save,self.data[:,i]])
    
                fichier_save=np.vstack([fichier_save,self.vecteur_trigger,self.timestamp])
    
    
                np.savetxt(self.generate_name(),fichier_save.T,delimiter=",")
                       
        
        
        
        
        
