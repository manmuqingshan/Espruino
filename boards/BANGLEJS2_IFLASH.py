#!/bin/false
# This file is part of Espruino, a JavaScript interpreter for Microcontrollers
#
# Copyright (C) 2013 Gordon Williams <gw@pur3.co.uk>
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# ----------------------------------------------------------------------------------------
# This file contains information for a specific board - the available pins, and where LEDs,
# Buttons, and other in-built peripherals are. It is used to build documentation as well
# as various source and header files for Espruino.
# ----------------------------------------------------------------------------------------
#
# This version of the Bangle.js 2 firmware splits storage into two parts - some of the
# on-chip flash is now used for storage of any .js files (drive can be manually forced
# by writing to a file named "C:filename" for example.
#
# In order to make a bit of room, Tensorflow is removed from this build
#
# TODO: We could remove/compress libs/banglejs/banglejs2_storage_default.c (factory firmware) to save another 120k

import pinutils;

info = {
 'name' : "Bangle.js 2 (use Internal + External flash)", # Using SMA Q3
 'boardname' : "BANGLEJS2",
 'link' :  [ "https://espruino.com/Bangle.js2" ],
 'espruino_page_link' : 'Bangle.js2',
 'default_console' : "EV_TERMINAL",
 #'default_console' : "EV_SERIAL1",
# 'default_console_tx' : "D6",
# 'default_console_rx' : "D8",
# 'default_console_baudrate' : "9600",
 'variables' : 12000, # How many variables are allocated for Espruino to use. RAM will be overflowed if this number is too high and code won't compile.
                      # Currently leaves around 38k of free stack - *loads* more than we need
 'io_buffer_size' : 2048, # How big is the input buffer (in bytes). Default on nRF52 is 1024
 'bootloader' : 1,
 'binary_name' : 'espruino_%v_banglejs2_iflash.hex',
 'build' : {
   'optimizeflags' : '-Os',
   'libraries' : [
     'BLUETOOTH',
     'TERMINAL',
     'GRAPHICS',
     'CRYPTO','SHA256','SHA512',
     'AES_CCM',
     'LCD_MEMLCD',
     'SWDCON', # RTT console over SWD
     'JIT' # JIT compiler enabled
   ],
   'makefile' : [
     'DEFINES+=-DESPR_OFFICIAL_BOARD', # Don't display the donations nag screen
     'DEFINES += -DESPR_HWVERSION=2 -DBANGLEJS -DBANGLEJS_Q3',
#     'DEFINES += -DCONFIG_GPIO_AS_PINRESET', # Allow the reset pin to work
     'DEFINES += -DCONFIG_NFCT_PINS_AS_GPIOS', # Allow us to use NFC pins as GPIO
     #'DEFINES += -DESPR_REGOUT0_1_8V=1', # this increases power draw, so probably not correct!
     'DEFINES += -DESPR_LSE_ENABLE', # Ensure low speed external osc enabled
     'DEFINES += -DNRF_SDH_BLE_GATT_MAX_MTU_SIZE=131', # 23+x*27 rule as per https://devzone.nordicsemi.com/f/nordic-q-a/44825/ios-mtu-size-why-only-185-bytes
     'DEFINES += -DNRF_SDH_BLE_GAP_EVENT_LENGTH=6', # Needed to allow coded phy connections
     'DEFINES += -DCENTRAL_LINK_COUNT=2 -DNRF_SDH_BLE_CENTRAL_LINK_COUNT=2', # allow two outgoing connections at once
     'LDFLAGS += -Xlinker --defsym=LD_APP_RAM_BASE=0x3b70', # set RAM base to match MTU=131 + CENTRAL_LINK_COUNT=2 + GAP_EVENT_LENGTH=6
     'DEFINES += -DESPR_DCDC_ENABLE=1', # Use DC/DC converter
     'ESPR_BLUETOOTH_ANCS=1', # Enable ANCS (Apple notifications) support
     'DEFINES += -DSPIFLASH_SLEEP_CMD', # SPI flash needs to be explicitly slept and woken up
     'DEFINES += -DSPIFLASH_READ2X', # Read SPI flash at 2x speed using MISO and MOSI for IO
     'DEFINES += -DESPR_JSVAR_FLASH_BUFFER_SIZE=32', # The buffer size we use when executing/iterating over data in flash memory (default 16). Should be set based on benchmarks.
     'DEFINES += -DAPP_TIMER_OP_QUEUE_SIZE=6', # Bangle.js accelerometer poll handler needs something else in queue size
     'DEFINES+=-DBLUETOOTH_NAME_PREFIX=\'"Bangle.js"\'',
     'DEFINES+=-DCUSTOM_GETBATTERY=jswrap_banglejs_getBattery',
     'DEFINES+=-DESPR_UNICODE_SUPPORT=1',
     'DEFINES+=-DDUMP_IGNORE_VARIABLES=\'"g\\0"\'',
     'DEFINES+=-DESPR_GRAPHICS_INTERNAL=1',
     'DEFINES+=-DESPR_BATTERY_FULL_VOLTAGE=0.3144',
     'DEFINES+=-DUSE_FONT_6X8 -DGRAPHICS_PALETTED_IMAGES -DGRAPHICS_ANTIALIAS -DESPR_PBF_FONTS',
     'DEFINES+=-DNO_DUMP_HARDWARE_INITIALISATION', # don't dump hardware init - not used and saves 1k of flash
     'INCLUDE += -I$(ROOT)/libs/banglejs -I$(ROOT)/libs/misc',
     'WRAPPERSOURCES += libs/banglejs/jswrap_bangle.c',
     'WRAPPERSOURCES += libs/graphics/jswrap_font_14.c',
     'WRAPPERSOURCES += libs/graphics/jswrap_font_17.c',
     'WRAPPERSOURCES += libs/graphics/jswrap_font_22.c',
     'WRAPPERSOURCES += libs/graphics/jswrap_font_28.c',
     'WRAPPERSOURCES += libs/graphics/jswrap_font_6x15.c',
     'WRAPPERSOURCES += libs/graphics/jswrap_font_12x20.c',
     'SOURCES += libs/misc/nmea.c',
     'SOURCES += libs/misc/stepcount.c',
     'SOURCES += libs/misc/hrm_vc31.c',
# Standard open-source heart rate algorithm:
#    'SOURCES += libs/misc/heartrate.c',
# Proprietary heart rate algorithm:
     'SOURCES += libs/misc/heartrate_vc31_binary.c', 'DEFINES += -DHEARTRATE_VC31_BINARY=1', 'PRECOMPILED_OBJS += libs/misc/vc31_binary/algo.o libs/misc/vc31_binary/modle5_10.o libs/misc/vc31_binary/modle5_11.o libs/misc/vc31_binary/modle5_12.o libs/misc/vc31_binary/modle5_13.o libs/misc/vc31_binary/modle5_14.o libs/misc/vc31_binary/modle5_15.o libs/misc/vc31_binary/modle5_16.o libs/misc/vc31_binary/modle5_17.o libs/misc/vc31_binary/modle5_18.o libs/misc/vc31_binary/modle5_1.o libs/misc/vc31_binary/modle5_2.o libs/misc/vc31_binary/modle5_3.o libs/misc/vc31_binary/modle5_4.o libs/misc/vc31_binary/modle5_5.o libs/misc/vc31_binary/modle5_6.o libs/misc/vc31_binary/modle5_7.o libs/misc/vc31_binary/modle5_8.o libs/misc/vc31_binary/modle5_9.o',
# ------------------------
     'SOURCES += libs/misc/unistroke.c',
     'WRAPPERSOURCES += libs/misc/jswrap_unistroke.c',
     'DEFINES += -DESPR_BANGLE_UNISTROKE=1',
     'SOURCES += libs/banglejs/banglejs2_storage_default.c',
     'DEFINES += -DESPR_STORAGE_INITIAL_CONTENTS=1', # use banglejs2_storage_default
     'DEFINES += -DESPR_USE_STORAGE_CACHE=32', # Add a 32 entry cache to speed up finding files
     'JSMODULESOURCES += libs/js/banglejs/locale.min.js',
     'JSMODULESOURCES += libs/js/banglejs/Layout.min.js',

     'DFU_SETTINGS=--application-version 0xff --hw-version 52 --sd-req 0xa9,0xae,0xb6',
     'DFU_PRIVATE_KEY=targets/nrf5x_dfu/dfu_private_key.pem',
     'DEFINES += -DNRF_BOOTLOADER_NO_WRITE_PROTECT=1', # By default the bootloader protects flash. Avoid this (a patch for NRF_BOOTLOADER_NO_WRITE_PROTECT must be applied first)
     'DEFINES += -DBUTTONPRESS_TO_REBOOT_BOOTLOADER',
     'BOOTLOADER_SETTINGS_FAMILY=NRF52840',
     'DEFINES += -DESPR_BOOTLOADER_SPIFLASH', # Allow bootloader to flash direct from SPI flash
     'DEFINES += -DESPR_BLE_PRIVATE_ADDRESS_SUPPORT',
     'NRF_SDK15=1'
   ]
 }
};


chip = {
  'part' : "NRF52840",
  'family' : "NRF52",
  'package' : "AQFN73",
  'ram' : 256,
  'flash' : 1024,
  'speed' : 64,
  'usart' : 2,
  'spi' : 1,
  'i2c' : 1,
  'adc' : 1,
  'dac' : 0,
  'saved_code' : {
    'page_size' : 4096,
    'address' : ((246 - 68) * 4096), # Bootloader takes pages 248-255, FS takes 246-247
    'pages' : 68,
    'flash_available' : 1024 - ((38 + 8 + 2 + 68)*4), # Softdevice uses 0x26=38 pages of flash, bootloader 8, FS 2, code 68. Each page is 4 kb.
    'address2' : 0x60000000, # put this in external spiflash (see below)
    'pages2' : 2048, # Entire 8MB of external flash

#    'address' : 0x60000000, # put this in external spiflash (see below)
#    'pages' : 2048, # Entire 8MB of external flash
  },
};

devices = {
  'BTN1' : { 'pin' : 'D17', 'pinstate' : 'IN_PULLDOWN' }, # Pin negated in software
  'LED1' : { 'pin' : 'D8', 'novariable':True }, # Backlight flash for low level debug - but in code we just use 'fake' LEDs
  'LCD' : {
            'width' : 176, 'height' : 176,
            'bpp' : 3, # LCD is native 3 bit (fastest transfers), but 4 is faster for drawing and slow to transfer
            'controller' : 'LPM013M126', # LPM013M126C
            'pin_cs' : 'D5',
            'pin_extcomin' : 'D6',
            'pin_disp' : 'D7',
            'pin_sck' : 'D26',
            'pin_mosi' : 'D27',
            'pin_bl' : 'D8',
          },
  'TOUCH' : {
            'device' : 'CST816S', 'addr' : 0x15,
            'pin_sda' : 'D33',
            'pin_scl' : 'D34',
            'pin_rst' : 'D35',
            'pin_irq' : 'D36'
          },
  'VIBRATE' : { 'pin' : 'D19' },
  'GPS' : {
            'device' : 'Casic URANUS',
            'pin_en' : 'D29',
            'pin_rx' : 'D30',
            'pin_tx' : 'D31'
          },
  'BAT' : {
            'pin_charging' : 'D23', # active low
            'pin_voltage' : 'D3'
          },
  'HEARTRATE' : {
            'device' : 'VC31', 'addr' : 0x33,
            'pin_sda' : 'D24',
            'pin_scl' : 'D32',
            'pin_en' : 'D21',
            'pin_int' : 'D22'
          },
  'ACCEL' : {
            'device' : 'KX023', 'addr' : 0x1e,
            'pin_sda' : 'D38',
            'pin_scl' : 'D37'
          },
  'MAG' : { # Magnetometer/compass
            'device' : 'UNKNOWN_0C',
            'addr' : 0x0C,
            'pin_sda' : 'D44',
            'pin_scl' : 'D45'
          },
  'PRESSURE' : {
            'device' : 'BMP280', # v2.1 uses Goertek SPL06-001 - we handle both
            'addr' : 0x76, # both versions use the same address
            'pin_sda' : 'D47',
            'pin_scl' : 'D2'
  },
  'SPIFLASH' : {
            'pin_cs' : 'D14',
            'pin_sck' : 'D16',
            'pin_mosi' : 'D15', # D0
            'pin_miso' : 'D13', # D1
#            'pin_wp' : 'D', # D2
#            'pin_rst' : 'D', # D3
            'size' : 4096*2048, # 8MB
            'memmap_base' : 0x60000000 # map into the address space (in software)
          }
};

# left-right, or top-bottom order
board = {
};


def get_pins():
  pins = pinutils.generate_pins(0,47) # 48 General Purpose I/O Pins.
  pinutils.findpin(pins, "PD0", True)["functions"]["XL1"]=0;
  pinutils.findpin(pins, "PD1", True)["functions"]["XL2"]=0;
  pinutils.findpin(pins, "PD2", True)["functions"]["ADC1_IN0"]=0;
  pinutils.findpin(pins, "PD3", True)["functions"]["ADC1_IN1"]=0;
  pinutils.findpin(pins, "PD4", True)["functions"]["ADC1_IN2"]=0;
  pinutils.findpin(pins, "PD5", True)["functions"]["ADC1_IN3"]=0;
  pinutils.findpin(pins, "PD28", True)["functions"]["ADC1_IN4"]=0;
  pinutils.findpin(pins, "PD29", True)["functions"]["ADC1_IN5"]=0;
  pinutils.findpin(pins, "PD30", True)["functions"]["ADC1_IN6"]=0;
  pinutils.findpin(pins, "PD31", True)["functions"]["ADC1_IN7"]=0;
  # Make buttons and LEDs negated
  pinutils.findpin(pins, "PD17", True)["functions"]["NEGATED"]=0; # button

  # everything is non-5v tolerant
  for pin in pins:
    pin["functions"]["3.3"]=0;
    pin["functions"]["NO_BLOCKLY"]=0;  # hide in blockly
  #The boot/reset button will function as a reset button in normal operation. Pin reset on PD21 needs to be enabled on the nRF52832 device for this to work.
  return pins
