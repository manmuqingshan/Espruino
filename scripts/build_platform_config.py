#!/usr/bin/env python

# This file is part of Espruino, a JavaScript interpreter for Microcontrollers
#
# Copyright (C) 2013 Gordon Williams <gw@pur3.co.uk>
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# ----------------------------------------------------------------------------------------
# Reads board information from boards/BOARDNAME.py and uses it to generate a header file
# which describes the available peripherals on the board
# ----------------------------------------------------------------------------------------
import subprocess;
import re;
import json;
import sys;
import os;
import importlib;
import common;

scriptdir = os.path.dirname(os.path.realpath(__file__))
# added os.path.normpath to get a correct reckognition of the subsequent path
# by Ubuntu 14.04 LTS
basedir = os.path.normpath(scriptdir+"/../")
# added leading / as a consequence of use of os.path.normpath
sys.path.append(basedir+"/scripts");
sys.path.append(basedir+"/boards");

import pinutils;

# -----------------------------------------------------------------------------------------

# Now scan AF file
print("Script location "+scriptdir)

if len(sys.argv)<3 :
  print("ERROR, USAGE: build_platform_config.py BOARD_NAME HEADERFILENAME [-Ddefine=1 ...]")
  exit(1)
boardname = sys.argv[1]
headerFilename = sys.argv[2]
defines = sys.argv[3:]

print("HEADER_FILENAME "+headerFilename)
print("BOARD "+boardname)
# import the board def
board = importlib.import_module(boardname)
pins = board.get_pins()
# -----------------------------------------------------------------------------------------
#allow to override board name so we can build for same board from multiple board files
if "boardname" in board.info:
  boardname = board.info["boardname"]
  print("BOARDNAME "+boardname)

LINUX = board.chip["family"]=="LINUX"
EMSCRIPTEN = board.chip["family"]=="EMSCRIPTEN"

if not "default_console" in board.info:
  board.info["default_console"] = "EV_SERIAL1"

has_bootloader = False
if "bootloader" in board.info and board.info["bootloader"]!=0:
  has_bootloader = True

variables=board.info["variables"]
# variables from board-file can bw overwritten. Be careful with this option.
# usually the definition in board file are already the maximum, and adding some more will corrupt firmware
if 'VARIABLES' in os.environ:
  variables=int(os.environ['VARIABLES'])
if variables==0: var_size = 16
elif variables<1023: var_size = 12   # the 'packed bits mean anything under 1023 vars gets into 12 byte JsVars
else: var_size = 16
var_cache_size = var_size*variables
flash_needed = var_cache_size + 4 # for magic number
print("Variables = "+str(variables))
print("JsVar size = "+str(var_size))
print("VarCache size = "+str(var_cache_size))

flash_page_size = 1024

if LINUX:
  flash_saved_code_pages = board.chip['flash']*1024 / flash_page_size
  total_flash = flash_page_size*flash_saved_code_pages
else: # NOT LINUX
  # 100xB and 103xB are mid-density, so have 1k page sizes
  if board.chip["part"][:7]=="STM32F1" and board.chip["part"][10]=="B": board.chip["subfamily"]="MD";

  if board.chip["family"]=="STM32F1":
    flash_page_size = 1024 if "subfamily" in board.chip and board.chip["subfamily"]=="MD" else 2048
  if board.chip["family"]=="STM32F2":
    flash_page_size = 128*1024
  if board.chip["family"]=="STM32F3":
    flash_page_size = 2*1024
  if board.chip["family"]=="STM32F4":
    flash_page_size = 128*1024
  if board.chip["family"]=="NRF51":
    flash_page_size = 1024
  if board.chip["family"]=="NRF52":
    flash_page_size = 4*1024
  if board.chip["family"]=="EFM32GG":
    flash_page_size = 4*1024
  if board.chip["family"]=="STM32L4":
    flash_page_size = 128*1024
  flash_saved_code_pages = round((flash_needed+flash_page_size-1)/flash_page_size + 0.5) #Needs to be a full page, so we're rounding up
  # F4 has different page sizes in different places
  total_flash = board.chip["flash"]*1024

flash_saved_code2_pages = 0
if "saved_code" in board.chip:
  flash_saved_code_start = hex(board.chip["saved_code"]["address"])
  flash_page_size = board.chip["saved_code"]["page_size"]
  flash_saved_code_pages = board.chip["saved_code"]["pages"]
  flash_available_for_code = board.chip["saved_code"]["flash_available"]*1024

  if "address2" in board.chip["saved_code"]:
    flash_saved_code2_start = board.chip["saved_code"]["address2"]
    flash_saved_code2_pages = board.chip["saved_code"]["pages2"]
else:
  flash_saved_code_start = "(FLASH_START + FLASH_TOTAL - FLASH_SAVED_CODE_LENGTH)"
  flash_available_for_code = total_flash - (flash_saved_code_pages*flash_page_size)
  if has_bootloader: flash_available_for_code -= common.get_bootloader_size(board)



print("Flash page size = "+str(flash_page_size))
print("Flash pages = "+str(flash_saved_code_pages))
print("Total flash = "+str(total_flash))
print("Flash available for code = "+str(flash_available_for_code))


# -----------------------------------------------------------------------------------------
headerFile = open(headerFilename, 'w')
def codeOut(s): headerFile.write(s+"\n");
# -----------------------------------------------------------------------------------------
def die(err):
  print("ERROR: "+err)
  sys.exit(1)

def toPinDef(pin):
  for p in pins:
    if p["name"]=="P"+pin:
      return str(pins.index(p))+"/* "+pin+" */";
  die("Pin named '"+pin+"' not found");

def codeOutDevice(device):
  if device in board.devices:
    codeOut("#define "+device+"_PININDEX "+toPinDef(board.devices[device]["pin"]))
    if device[0:3]=="BTN":
      codeOut("#define "+device+"_ONSTATE "+("0" if "inverted" in board.devices[device] else "1"))
      if "pinstate" in board.devices[device]:
        codeOut("#define "+device+"_PINSTATE JSHPINSTATE_GPIO_"+board.devices[device]["pinstate"]);
    if device[0:3]=="LED":
      codeOut("#define "+device+"_ONSTATE "+("0" if "inverted" in board.devices[device] else "1"))
    if "no_bootloader" in board.devices[device]:
      codeOut("#define "+device+"_NO_BOOTLOADER 1 // don't use this in the bootloader");

def codeOutDevicePin(device, pin, definition_name):
  if device in board.devices:
    codeOut("#define "+definition_name+" "+toPinDef(board.devices[device][pin]))

def codeOutDevicePins(device, definition_name):
  for entry in board.devices[device]:
    if entry.startswith("pin_") or entry=="pin":
      codeOut("#define "+definition_name+"_"+entry.upper()+" "+toPinDef(board.devices[device][entry]))
# -----------------------------------------------------------------------------------------


codeOut("""
// Automatically generated header file for """+boardname+"""
// Generated by scripts/build_platform_config.py

#ifndef _PLATFORM_CONFIG_H
#define _PLATFORM_CONFIG_H

""");

codeOut("#define PC_BOARD_ID \""+boardname+"\"")
codeOut("#define PC_BOARD_CHIP \""+board.chip["part"]+"\"")
codeOut("#define PC_BOARD_CHIP_FAMILY \""+board.chip["family"]+"\"")

codeOut("")

# Linker vars used for:
linker_end_var = "_end";     # End of RAM (eg top of stack)
linker_etext_var = "_etext"; # End of text (function) section
# External interrupt count
exti_count = 16


if board.chip["family"]=="LINUX":
  board.chip["class"]="LINUX"
elif board.chip["family"]=="EMSCRIPTEN":
  board.chip["class"]="EMSCRIPTEN"
elif board.chip["family"]=="STM32F1":
  board.chip["class"]="STM32"
  codeOut('#include "stm32f10x.h"')
elif board.chip["family"]=="STM32F2":
  board.chip["class"]="STM32"
  codeOut('#include "stm32f2xx.h"')
  codeOut("#define STM32API2 // hint to jshardware that the API is a lot different")
elif board.chip["family"]=="STM32F3":
  board.chip["class"]="STM32"
  codeOut('#include "stm32f30x.h"')
  codeOut("#define STM32API2 // hint to jshardware that the API is a lot different")
  codeOut("#define USB_INT_DEFAULT") # hack
elif board.chip["family"]=="STM32F4":
  board.chip["class"]="STM32"
  codeOut('#include "stm32f4xx.h"')
  codeOut('#include "stm32f4xx_conf.h"')
  codeOut("#define STM32API2 // hint to jshardware that the API is a lot different")
elif board.chip["family"]=="STM32L4":
  board.chip["class"]="STM32_LL"
  codeOut('#include "stm32l4xx_ll_bus.h"')
  codeOut('#include "stm32l4xx_ll_rcc.h"')
  codeOut('#include "stm32l4xx_ll_adc.h"')
elif board.chip["family"]=="NRF51":
  board.chip["class"]="NRF51"
  linker_etext_var = "__etext";
  linker_end_var = "end";
  exti_count = 4
  codeOut('#include "nrf.h"')
elif board.chip["family"]=="NRF52":
  board.chip["class"]="NRF52"
  linker_etext_var = "__etext";
  linker_end_var = "end";
  exti_count = 8
  codeOut('#include "nrf.h"')
elif board.chip["family"]=="EFM32GG":
  board.chip["class"]="EFM32"
  linker_etext_var = "__etext";
  codeOut('#include "em_device.h"')
elif board.chip["family"]=="LPC1768":
  board.chip["class"]="MBED"
elif board.chip["family"]=="AVR":
  board.chip["class"]="AVR"
elif board.chip["family"]=="ESP8266":
  board.chip["class"]="ESP8266"
elif board.chip["family"]=="ESP32" or board.chip["family"]=="ESP32_IDF4":
  board.chip["class"]="ESP32"
  exti_count = 40
elif board.chip["family"]=="SAMD":
  board.chip["class"]="SAMD"
  codeOut('#include "targetlibs/samd/include/due_sam3x.init.h"')
elif board.chip["family"]=="EMBED":
  board.chip["class"]="EMBED"
else:
  die('Unknown chip family '+board.chip["family"])

codeOut("#define LINKER_END_VAR "+linker_end_var);
codeOut("#define LINKER_ETEXT_VAR "+linker_etext_var);

if board.chip["class"]=="MBED":
  codeOut("""
  #pragma diag_suppress 1295 // deprecated decl
  #pragma diag_suppress 188 // enumerated type mixed with another type
  #pragma diag_suppress 111 // statement is unreachable
  #pragma diag_suppress 68 // integer conversion resulted in a change of sign
  """);

codeOut("""
// SYSTICK is the counter that counts up and that we use as the real-time clock
// The smaller this is, the longer we spend in interrupts, but also the more we can sleep!
#define SYSTICK_RANGE 0x1000000 // the Maximum (it is a 24 bit counter) - on Olimexino this is about 0.6 sec
#define SYSTICKS_BEFORE_USB_DISCONNECT 2

#define DEFAULT_BUSY_PIN_INDICATOR (Pin)-1 // no indicator
#define DEFAULT_SLEEP_PIN_INDICATOR (Pin)-1 // no indicator
""");


util_timer = pinutils.get_device_util_timer(board)
if util_timer!=False:
  codeOut(util_timer['defines']);

codeOut("");
# ------------------------------------------------------------------------------------- Chip Specifics
codeOut("#define RAM_TOTAL ("+str(board.chip['ram'])+"*1024)")
codeOut("#define FLASH_TOTAL ("+str(board.chip['flash'])+"*1024)")
codeOut("");

if variables==0:
  codeOut('#define RESIZABLE_JSVARS // Allocate variables in blocks using malloc - slow, and linux-only')
else:
  codeOut("#define JSVAR_CACHE_SIZE                "+str(variables)+" // Number of JavaScript variables in RAM")
  if LINUX:
    codeOut("#define JSVAR_MALLOC 1")

if LINUX:
  codeOut("#define FLASH_START                     "+hex(0x10000000))
  codeOut("#define FLASH_PAGE_SIZE                 "+str(flash_page_size))
else:
  codeOut("#define FLASH_AVAILABLE_FOR_CODE        "+str(int(flash_available_for_code)))
  if board.chip["class"]=="EFM32":
    codeOut("// FLASH_PAGE_SIZE defined in em_device.h");
  else:
    codeOut("#define FLASH_PAGE_SIZE                 "+str(flash_page_size))
  if board.chip["family"]=="ESP8266":
    codeOut("#define FLASH_START                     "+hex(0x0))
  elif board.chip["family"]=="NRF52" or board.chip["family"]=="NRF51":
    codeOut("#define FLASH_START                     "+hex(0x0))
  elif board.chip["class"]=="EFM32":
    codeOut("#define FLASH_START                     FLASH_BASE // FLASH_BASE defined in em_device.h")
  else:
    codeOut("#define FLASH_START                     "+hex(0x08000000))
  if has_bootloader:
    codeOut("#define BOOTLOADER_SIZE                 "+str(common.get_bootloader_size(board)))
    codeOut("#define ESPRUINO_BINARY_ADDRESS         "+hex(common.get_espruino_binary_address(board)))
  codeOut("")


codeOut("#define FLASH_SAVED_CODE_START            "+flash_saved_code_start)
codeOut("#define FLASH_SAVED_CODE_LENGTH           "+hex(int(flash_page_size*flash_saved_code_pages)))
if flash_saved_code2_pages:
  codeOut("// Extra flash pages in external flash")
  codeOut("#define FLASH_SAVED_CODE2_START            "+hex(flash_saved_code2_start))
  codeOut("#define FLASH_SAVED_CODE2_LENGTH           "+hex(int(flash_page_size*flash_saved_code2_pages)))
codeOut("");

codeOut("#define CLOCK_SPEED_MHZ                      "+str(board.chip["speed"]))
codeOut("#define ESPR_USART_COUNT                     "+str(board.chip["usart"]))
if "spi" in board.chip:
  codeOut("#define ESPR_SPI_COUNT                       "+str(board.chip["spi"]))
codeOut("#define ESPR_I2C_COUNT                       "+str(board.chip["i2c"]))
codeOut("#define ESPR_ADC_COUNT                       "+str(board.chip["adc"]))
codeOut("#define ESPR_DAC_COUNT                       "+str(board.chip["dac"]))
codeOut("#define ESPR_EXTI_COUNT                      "+str(exti_count))
codeOut("");
codeOut("#define DEFAULT_CONSOLE_DEVICE              "+board.info["default_console"]);
if "default_console_tx" in board.info:
  codeOut("#define DEFAULT_CONSOLE_TX_PIN "+toPinDef(board.info["default_console_tx"]))
if "default_console_rx" in board.info:
  codeOut("#define DEFAULT_CONSOLE_RX_PIN "+toPinDef(board.info["default_console_rx"]))
if "default_console_baudrate" in board.info:
  codeOut("#define DEFAULT_CONSOLE_BAUDRATE "+board.info["default_console_baudrate"])


codeOut("");

xoff_thresh = 6 # how full (out of 8) is buffer when we sent the XOFF flow control char to say 'stop'
xon_thresh = 3 # how full (out of 8) is buffer when we sent the XON flow control char to say 'go'

if LINUX:
  bufferSizeIO = 1024
  bufferSizeTX = 256
  bufferSizeTimer = 16
elif EMSCRIPTEN:
  bufferSizeIO = 1024
  bufferSizeTX = 256
  bufferSizeTimer = 16
else:
  # IO buffer - for received chars, setWatch, etc
  bufferSizeIO = 256
  if board.chip["ram"]>=20: bufferSizeIO = 512
  if board.chip["ram"]>=96: bufferSizeIO = 1024
  # NRF52 needs this as Bluetooth traffic is funnelled through the buffer
  if board.chip["family"]=="NRF52":
    bufferSizeIO = 1024
    # we often use increased MTUs and even with a big buffer these mean we need to leave
    # a lot of space when we send XOFF (due to delay in response from sender)
    xoff_thresh = 3
    xon_thresh = 2
  # TX buffer - for print/write/etc
  bufferSizeTX = 32
  if board.chip["ram"]>=20: bufferSizeTX = 128
  if board.chip["ram"]>=128: bufferSizeTX = 256
  bufferSizeTimer = 4 if board.chip["ram"]<20 else 16

if 'util_timer_tasks' in board.info:
  bufferSizeTimer = board.info['util_timer_tasks']

if 'io_buffer_size' in board.info:
  bufferSizeIO = board.info['io_buffer_size']
if 'xoff_thresh' in board.info:
  xoff_thresh = board.info['xoff_thresh']
if 'xon_thresh' in board.info:
  xon_thresh = board.info['xon_thresh']

codeOut("#define IOBUFFERMASK "+str(bufferSizeIO-1)+" // (max 65535, 2^n-1) amount of items in event buffer - each event uses 2+dataLen bytes")
codeOut("#define TXBUFFERMASK "+str(bufferSizeTX-1)+" // (max 255, 2^n-1) amount of items in the transmit buffer - 2 bytes each")
codeOut("#define UTILTIMERTASK_TASKS ("+str(bufferSizeTimer)+") // Must be power of 2 - and max 256")

codeOut("");

codeOut("// When to send the message that the IO buffer is getting full")
codeOut("#define IOBUFFER_XOFF ((IOBUFFERMASK)*"+str(xoff_thresh)+"/8)")
codeOut("// When to send the message that we can start receiving again")
codeOut("#define IOBUFFER_XON ((IOBUFFERMASK)*"+str(xon_thresh)+"/8)")

codeOut("");

usedPinChecks = ["false"];
ledChecks = ["false"];
btnChecks = ["false"];
for device in pinutils.SIMPLE_DEVICES:
  if device in board.devices:
    codeOutDevice(device)
    check = "(PIN)==" + toPinDef(board.devices[device]["pin"])
    if device[:3]=="LED": ledChecks.append(check)
    if device[:3]=="BTN": btnChecks.append(check)
#   usedPinChecks.append(check)
# Actually we don't care about marking used pins for LEDs/Buttons

if "USB" in board.devices:
  if "pin_disc" in board.devices["USB"]: codeOutDevicePin("USB", "pin_disc", "USB_DISCONNECT_PIN")
  if "pin_vsense" in board.devices["USB"]: codeOutDevicePin("USB", "pin_vsense", "USB_VSENSE_PIN")

if "LCD" in board.devices:
  codeOut("#define LCD_CONTROLLER_"+board.devices["LCD"]["controller"].upper())
  if "width" in board.devices["LCD"]:
    codeOut("#define LCD_WIDTH "+str(board.devices["LCD"]["width"]))
  if "height" in board.devices["LCD"]:
    codeOut("#define LCD_HEIGHT "+str(board.devices["LCD"]["height"]))
  if "bpp" in board.devices["LCD"]:
    codeOut("#define LCD_BPP "+str(board.devices["LCD"]["bpp"]))
  if "bitrate" in board.devices["LCD"]:
    codeOut("#define LCD_SPI_BITRATE "+str(board.devices["LCD"]["bitrate"]))
  if "pin_bl" in board.devices["LCD"]:
    codeOutDevicePin("LCD", "pin_bl", "LCD_BL")
  if "pin_en" in board.devices["LCD"]:
    codeOutDevicePin("LCD", "pin_en", "LCD_EN")
  if board.devices["LCD"]["controller"]=="fsmc":
    for i in range(0,16):
      codeOutDevicePin("LCD", "pin_d"+str(i), "LCD_FSMC_D"+str(i))
    codeOutDevicePin("LCD", "pin_rd", "LCD_FSMC_RD")
    codeOutDevicePin("LCD", "pin_wr", "LCD_FSMC_WR")
    codeOutDevicePin("LCD", "pin_cs", "LCD_FSMC_CS")
    if "pin_rs" in board.devices["LCD"]:
      codeOutDevicePin("LCD", "pin_rs", "LCD_FSMC_RS")
    if "pin_reset" in board.devices["LCD"]:
      codeOutDevicePin("LCD", "pin_reset", "LCD_RESET")
  if board.devices["LCD"]["controller"]=="ssd1306" or board.devices["LCD"]["controller"]=="st7567" or board.devices["LCD"]["controller"]=="st7789v" or board.devices["LCD"]["controller"]=="st7735" or board.devices["LCD"]["controller"]=="gc9a01":
    codeOutDevicePin("LCD", "pin_rst", "LCD_SPI_RST")
  if board.devices["LCD"]["controller"]=="LPM013M126":
    codeOutDevicePin("LCD", "pin_disp", "LCD_DISP")
    codeOutDevicePin("LCD", "pin_extcomin", "LCD_EXTCOMIN")
  if "pin_cs" in board.devices["LCD"]:
    codeOutDevicePin("LCD", "pin_cs", "LCD_SPI_CS")
  if "pin_mosi" in board.devices["LCD"]:
    codeOutDevicePin("LCD", "pin_mosi", "LCD_SPI_MOSI")
  if "pin_miso" in board.devices["LCD"]:
    codeOutDevicePin("LCD", "pin_miso", "LCD_SPI_MISO")
  if "pin_sck" in board.devices["LCD"]:
    codeOutDevicePin("LCD", "pin_sck", "LCD_SPI_SCK")
  if "pin_dc" in board.devices["LCD"]:
    codeOutDevicePin("LCD", "pin_dc", "LCD_SPI_DC")
  if "spi_device" in board.devices["LCD"]:
    codeOut("#define LCD_SPI_DEVICE "+board.devices["LCD"]["spi_device"])
  if "pin_tearing" in board.devices["LCD"]:
    codeOutDevicePin("LCD", "pin_tearing", "LCD_TEARING")

  if board.devices["LCD"]["controller"]=="st7789_8bit":
    codeOutDevicePins("LCD","LCD");

if "SD" in board.devices:
  if "pin_cd" in board.devices["SD"]: codeOutDevicePin("SD", "pin_cd", "SD_DETECT_PIN")
  if "pin_pwr" in board.devices["SD"]: codeOutDevicePin("SD", "pin_pwr", "SD_POWER_PIN")
  if "pin_cs" in board.devices["SD"]: codeOutDevicePin("SD", "pin_cs", "SD_CS_PIN")
  if "pin_di" in board.devices["SD"]: codeOutDevicePin("SD", "pin_di", "SD_DI_PIN") # MOSI
  if "pin_do" in board.devices["SD"]: codeOutDevicePin("SD", "pin_do", "SD_DO_PIN") # MISO
  if "pin_clk" in board.devices["SD"]:
    codeOutDevicePin("SD", "pin_clk", "SD_CLK_PIN")
    if not "pin_d3" in board.devices["SD"]: # NOT SDIO - normal SD
      sdClkPin = pinutils.findpin(pins, "P"+board.devices["SD"]["pin_clk"], False)
      spiNum = 0
      for func in sdClkPin["functions"]:
        if func[:3]=="SPI": spiNum = int(func[3])
      if spiNum==0: die("No SPI peripheral found for SD card's CLK pin")
      codeOut("#define SD_SPI EV_SPI"+str(spiNum))
  # SDIO
  if "pin_d0" in board.devices["SD"]: codeOutDevicePin("SD", "pin_d0", "SD_D0_PIN")
  if "pin_d1" in board.devices["SD"]: codeOutDevicePin("SD", "pin_d1", "SD_D1_PIN")
  if "pin_d2" in board.devices["SD"]: codeOutDevicePin("SD", "pin_d2", "SD_D2_PIN")
  if "pin_d3" in board.devices["SD"]: codeOutDevicePin("SD", "pin_d3", "SD_D3_PIN")
  if "pin_cmd" in board.devices["SD"]: codeOutDevicePin("SD", "pin_cmd", "SD_CMD_PIN")

if "IR" in board.devices:
  codeOutDevicePin("IR", "pin_anode", "IR_ANODE_PIN")
  codeOutDevicePin("IR", "pin_cathode", "IR_CATHODE_PIN")

if "CAPSENSE" in board.devices:
  codeOutDevicePin("CAPSENSE", "pin_rx", "CAPSENSE_RX_PIN")
  codeOutDevicePin("CAPSENSE", "pin_tx", "CAPSENSE_TX_PIN")

if "VIBRATE" in board.devices:
  codeOutDevicePins("VIBRATE", "VIBRATE")

if "SPEAKER" in board.devices:
  codeOutDevicePins("SPEAKER", "SPEAKER")

if "HEARTRATE" in board.devices:
  codeOutDevicePins("HEARTRATE", "HEARTRATE")
  if "addr" in board.devices["HEARTRATE"]:
    codeOut("#define HEARTRATE_ADDR "+str(board.devices["HEARTRATE"]["addr"]))
  codeOut("#define HEARTRATE_DEVICE_"+board.devices["HEARTRATE"]["device"].upper()+" 1")

if "BAT" in board.devices:
  codeOutDevicePins("BAT", "BAT")

if "GPS" in board.devices:
  if "pin_en" in board.devices["GPS"]: codeOutDevicePin("GPS", "pin_en", "GPS_PIN_EN")
  codeOutDevicePins("GPS", "GPS")

if "ACCEL" in board.devices:
  codeOut("#define ACCEL_DEVICE \""+board.devices["ACCEL"]["device"].upper()+"\"")
  codeOut("#define ACCEL_DEVICE_"+board.devices["ACCEL"]["device"].upper()+" 1")
  codeOut("#define ACCEL_ADDR "+str(board.devices["ACCEL"]["addr"]))
  codeOutDevicePins("ACCEL", "ACCEL")

if "MAG" in board.devices:
  codeOut("#define MAG_DEVICE \""+board.devices["MAG"]["device"].upper()+"\"")
  codeOut("#define MAG_DEVICE_"+board.devices["MAG"]["device"].upper()+" 1")
  if "addr" in board.devices["MAG"]:
    codeOut("#define MAG_ADDR "+str(board.devices["MAG"]["addr"]))
  codeOutDevicePins("MAG", "MAG")

if "TEMP" in board.devices:
  if "addr" in board.devices["TEMP"]:
    codeOut("#define TEMP_ADDR "+str(board.devices["TEMP"]["addr"]))
  codeOutDevicePins("TEMP", "TEMP")

if "PRESSURE" in board.devices:
  codeOut("#define PRESSURE_DEVICE \""+board.devices["PRESSURE"]["device"].upper()+"\"")
  codeOut("#define PRESSURE_DEVICE_"+board.devices["PRESSURE"]["device"].upper()+" 1")
  codeOut("#define PRESSURE_ADDR "+str(board.devices["PRESSURE"]["addr"]))
  codeOutDevicePins("PRESSURE", "PRESSURE")

if "TOUCH" in board.devices:
  codeOut("#define TOUCH_DEVICE \""+board.devices["TOUCH"]["device"].upper()+"\"")
  if "addr" in board.devices["TOUCH"]:
    codeOut("#define TOUCH_ADDR "+str(board.devices["TOUCH"]["addr"]))
  codeOutDevicePins("TOUCH", "TOUCH")

if "QWIIC0" in board.devices:
  codeOutDevicePins("QWIIC0", "QWIIC0")
if "QWIIC1" in board.devices:
  codeOutDevicePins("QWIIC1", "QWIIC1")
if "QWIIC2" in board.devices:
  codeOutDevicePins("QWIIC2", "QWIIC2")
if "QWIIC3" in board.devices:
  codeOutDevicePins("QWIIC3", "QWIIC3")
if "DRIVER0" in board.devices:
  codeOutDevicePins("DRIVER0", "DRIVER0")
if "DRIVER1" in board.devices:
  codeOutDevicePins("DRIVER1", "DRIVER1")

if "SPIFLASH" in board.devices:
  codeOut("#define SPIFLASH_PAGESIZE 4096")
  codeOut("#define SPIFLASH_LENGTH "+str(board.devices["SPIFLASH"]["size"]))
  if "memmap_base" in board.devices["SPIFLASH"]:
    codeOut("#define SPIFLASH_BASE "+str(board.devices["SPIFLASH"]["memmap_base"])+"UL")
  codeOutDevicePins("SPIFLASH", "SPIFLASH")

for device in pinutils.OTHER_DEVICES:
  if device in board.devices:
    for entry in board.devices[device]:
      if entry[:3]=="pin": usedPinChecks.append("(PIN)==" + toPinDef(board.devices[device][entry])+"/* "+device+" */")

# Specific hacks for nucleo boards
if "NUCLEO_A" in board.devices:
  for n,pin in enumerate(board.devices["NUCLEO_A"]):
      codeOut("#define NUCLEO_A"+str(n)+" "+toPinDef(pin))
if "NUCLEO_D" in board.devices:
  for n,pin in enumerate(board.devices["NUCLEO_D"]):
      codeOut("#define NUCLEO_D"+str(n)+" "+toPinDef(pin))

if "ESP8266" in board.devices:
  for entry in board.devices["ESP8266"]:
    if entry[0:4]=="pin_":
      codeOut("#define ESP8266_"+str(entry[4:].upper())+" "+toPinDef(board.devices["ESP8266"][entry]))

codeOut("")

codeOut("// definition to avoid compilation when Pin/platform config is not defined")
codeOut("#define IS_PIN_USED_INTERNALLY(PIN) (("+")||(".join(usedPinChecks)+"))")
codeOut("#define IS_PIN_A_LED(PIN) (("+")||(".join(ledChecks)+"))")
codeOut("#ifndef IS_PIN_A_BUTTON")
codeOut("#define IS_PIN_A_BUTTON(PIN) (("+")||(".join(btnChecks)+"))")
codeOut("#endif")

# add makefile defines
if len(defines) > 0:
  codeOut("\n#ifndef ESPR_DEFINES_ON_COMMANDLINE")
  codeOut("// The Makefile calls the compiler with ESPR_DEFINES_ON_COMMANDLINE defined so this")
  codeOut("// is ignored and all these defines go on the command line and apply to every file")
  codeOut("// whether or not platform_config was included. However if you're viewing a file in")
  codeOut("// a code editor like VS Code it'll parse this and should then highlight the correct")
  codeOut("// code based on your build")
  for define in defines:
    if not define.startswith("-D"):
      continue
    define = define[2:]
    if "=" in define:
      defSplit = define.split("=")
      codeOut("\t#define " + defSplit[0] + " " + defSplit[1])
    else:
      codeOut("\t#define " + define)
  codeOut("#endif")
# end makefile defines

codeOut("""
#endif // _PLATFORM_CONFIG_H
""");
