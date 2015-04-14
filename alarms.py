#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
alarms.py - Handles PiFace Digital 2 inputs
"""

import pifacedigitalio
import time
import smbus

bus = smbus.SMBus(1)
address = 0x04

colors = [
          (  0,  63,   0), # zöld
          (  0,   0,  63), # kék
          ( 63,  63,   0), # sárga
          ( 63,   0,   0), # vörös
          ( 63,   0,  63), # rózsaszín
          (  0,  63,  63), # türkiz
          (  0,   0,   0), # fekete
          ( 63,  63,  63)  # fehér
          ]

config_params = dict()  # Konfigurációs paraméterek     {'iPORT0' : [<default_portvalue>, <priority>, <group>]}
piface_iports = dict()  # PiFace Digital 2 input ports  {'iPORT0' : piface_iport()}
piface_oports = dict()  # PiFace Digital 2 output ports {'oPORT0' : piface_oport()}
iport_groups = dict()   # Az input portok csoportjai    {'GRP0'   : ['iPORT0', 'iPORT1', 'iPORT2']}
leds = dict()           # a LED-ek színe és villogása {'GRP0' : [color, blink]}

class piface_iport(object) :
    ID = None       # a port egyedi azonosítója
    board = None    # a piface kártya, melyen a port található
    port = None     # a port száma a kártyán
    state = None    # a riasztás állapota: 0=nincs, 1=várakozik, 2=nyugtázott, 3=aktív
    priority = None # a riasztás fontossága: 0=nincs, 1=info, 2=figyelmeztetés, 3=riasztás
    group = None    # a port csoportja
    default_portvalue = None # A port alapállapota (0=nyitott, 1=zárt)

    def __init__(self, ID, board, port, config_params) :
        self.ID = ID
        self.board = board
        self.port = port
        self.state = 0
        self.priority = int(config_params[1])
        self.group = config_params[2]
        self.default_portvalue = int(config_params[0])
        
    def refresh(self) :
        current_portvalue = self.board.input_pins[self.port].value
        if current_portvalue == self.default_portvalue :
            if self.state == 1 :
                self.state = 0
                self.set_time = time.time()
            elif self.state == 3 :
                self.state = 2
                self.set_time = time.time()
        else :
            if self.state == 0 :
                self.state = 1
                self.set_time = time.time()
            elif self.state == 1 :
                if (time.time() - self.set_time) > 1 :
                    self.state = 3
                    self.set_time = time.time()
            elif self.state == 2 :
                self.state = 3
                self.set_time = time.time()

class piface_oport(object) :
    ID = None       # a port egyedi azonosítója
    board = None    # a piface kártya, melyen a port található
    port = None     # a port száma a kártyán

    def __init__(self, ID, board, port, config_params) :
        self.ID = ID
        self.board = board
        self.port = port



def init() :

    # a konfigurációs állomány beolvasása és feldolgozása
    try : 
        config_file = open('config.txt')
    except :
        print "A konfigurációs állomány hiányzik! (config.txt)"
        quit()
    for line in config_file :
        if line.startswith("#") :
            continue
        line = line.rstrip()
        params = line.split("=")    # params[0] lesz a kulcs a config_params{}-ban
        if len(params) == 2 :
            config_params[params[0]] = params[1].split(",") # a params[1]-ből készült lista az értéke a config_params{}-nak
#            for i in range(len(config_params[params[0]])) :
#config_params[params[0]][i] = int(config_params[params[0]][i])  # a paramétereket át kell alakítani számmá

    # A PiFace kártyák és azok portjainak inicializálása
    for board_addr in range(4) :     # Maximum 4 darab PiFace Digital 2 csatlakoztatható egy RPi-hez
        try:
            piface_board = pifacedigitalio.PiFaceDigital(hardware_addr = board_addr)
        except:
            continue
        for port_addr in range(8) : # Nyolc darab input és output port található egy kártyán
            ID = "PORT" + str(( board_addr * 8 ) + port_addr)
            iport = "i" + ID
            oport = "o" + ID
            piface_iports[iport] = piface_iport(iport, piface_board, port_addr, config_params[iport])
            piface_oports[oport] = piface_oport(oport, piface_board, port_addr, config_params[oport])

    # create groups and LEDs
    for portid, port in piface_iports.items() :
        group = port.group
        if group not in iport_groups :
            iport_groups[group] = list()
        iport_groups[group].append(port)
        if group not in leds :
            leds[group] = colors[0]



def refresh() :

# Azt aktuális portstátuszok beállítása után megkeresem minden csoport legmagasabb státuszú aktív portját.
    highest_level = {}
    highest_state = {}
    for portid, port in piface_iports.items() :
        port.refresh()
        iport_group = port.group
        if piface_iports[iport].state > highest_state :
            highest_state[group] = port.state
            highest_level[group] = port.priority
        elif port.state == highest_state[group] and port.priority > highest_level[group] :
            highest_level[group] = port.priority
# a csoportstátuszoknak megfelelő színek beállítása
# a csoportstátusz-jelző LED-ek bekapcsolása
    for led in range(len(leds)) :
        group = 'GRP' + str(led)
        color = leds[group]
        try :
            bus.write_i2c_block_data(address, led, color)
        except :
            continue



# Főprogram
if __name__ == "__main__" :     # Ha nem modulként importálnák ezt a file-t
    start_time = time.time()
    init()
    while ( time.time() - start_time ) <= 120 :
        print len(piface_iports)
        for portid, port in piface_iports.items() :
            refresh()
            print portid, ":", str(port.state),
        print
    quit()

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4