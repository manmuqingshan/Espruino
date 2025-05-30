/*
 * This file is part of Espruino, a JavaScript interpreter for Microcontrollers
 *
 * Copyright (C) 2013 Gordon Williams <gw@pur3.co.uk>
 *
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/.
 *
 *     2016/05/23, modified to work with bitrate on esp8266

 * ----------------------------------------------------------------------------
 * Hardware interface Layer
 * NOTE: Most definitions of these functions are inside:
 *                                         targets/{target}/jshardware.c
 *       But common functions are inside:  src/jshardware_common.c
 * ----------------------------------------------------------------------------
 */

#ifndef JSHARDWARE_H_
#define JSHARDWARE_H_

#include "jsutils.h"
#include "jsvar.h"
#include "jsdevices.h"
#include "jspin.h"
#include "jspininfo.h"

#ifdef LINUX
#include <inttypes.h>
#endif


/// jshInit is called at start-up, put hardware dependent init stuff in this function
void jshInit();

/// jshReset is called from JS 'reset()' - try to put peripherals back to their power-on state
void jshReset();

/** Code that is executed each time around the idle loop. Prod watchdog timers here,
 * and on platforms without GPIO interrupts you can check watched Pins for changes. */
void jshIdle();

/// Called when Espruino is busy waiting (eg for data to send)
void jshBusyIdle();

/** Enter sleep mode for the given period of time. Can be woken up by interrupts.
 * If time is 0xFFFFFFFFFFFFFFFF then go to sleep without setting a timer to wake
 * up.
 *
 * This function can also check `jsiStatus & JSIS_ALLOW_DEEP_SLEEP`, and if there
 * is no pending serial data and nothing working on Timers, it will put the device
 * into deep sleep mode where the high speed oscillator turns off.
 *
 * Returns true on success
 */
bool jshSleep(JsSysTime timeUntilWake);

/** Clean up ready to stop Espruino. Unused on embedded targets, but used on Linux,
 * where GPIO that have been exported may need unexporting, and so on. */
void jshKill();

/** Get this IC's serial number. Passed max # of chars and a pointer to write to.
 * Returns # of chars of non-null-terminated string.
 *
 * This is reported back to `process.env` and is sometimes used in USB enumeration.
 * It doesn't have to be unique, but some users do use this in their code to distinguish
 * between boards.
 */
int jshGetSerialNumber(unsigned char *data, int maxChars);

/** Is the USB port connected such that we could move the console over to it
 * (and that we should store characters sent to USB). On non-USB boards this just returns false. */
bool jshIsUSBSERIALConnected();

/** The system time is used all over Espruino - for:
 *  * setInterval/setTimeout
 *  * new Date()
 *  * getTime
 *  * scheduling the utility timer (digitalPulse/Waveform/etc)
 *  * timestamping watches (so measuring pulse widths)
 *
 * It is time since 1970 - in whatever units make sense for the platform. For real-time
 * platforms units should really be at the uS level. Often this timer directly counts
 * clock cycles with the SysTick timer.
 */

/// Get the system time (in ticks since the epoch)
JsSysTime jshGetSystemTime();
/** Set the system time (in ticks since the epoch) - this should only be called rarely as it
could mess up things like jsinteractive's timers! */
void jshSetSystemTime(JsSysTime time);
/// Convert a time in Milliseconds since the epoch to one in ticks
JsSysTime jshGetTimeFromMilliseconds(JsVarFloat ms);
/// Convert ticks to a time in Milliseconds since the epoch
JsVarFloat jshGetMillisecondsFromTime(JsSysTime time);

// software IO functions...
void jshInterruptOff(); ///< disable interrupts to allow short delays to be accurate
void jshInterruptOn();  ///< re-enable interrupts
bool jshIsInInterrupt(); ///< Are we currently in an interrupt?
void jshDelayMicroseconds(int microsec);  ///< delay a few microseconds. Should use used sparingly and for very short periods - max 1ms

void jshPinSetValue(Pin pin, bool value); ///< Set a digital output to 1 or 0. DOES NOT change pin state OR CHECK PIN VALIDITY
bool jshPinGetValue(Pin pin); ///< Get the value of a digital input. DOES NOT change pin state OR CHECK PIN VALIDITY


/// Set the pin state (Output, Input, etc)
void jshPinSetState(Pin pin, JshPinState state);

/** Get the pin state (only accurate for simple IO - won't return
 * JSHPINSTATE_USART_OUT for instance). Note that you should use
 * JSHPINSTATE_MASK as other flags may have been added
 * (like JSHPINSTATE_PIN_IS_ON if pin was set to output) */
JshPinState jshPinGetState(Pin pin);

/// Check if state is default - return true if default
bool jshIsPinStateDefault(Pin pin, JshPinState state);

/** Returns an analog value between 0 and 1. 0 is expected to be 0v, and
 * 1 means jshReadVRef() volts. On most devices jshReadVRef() would return
 * around 3.3, so a reading of 1 represents 3.3v. */
JsVarFloat jshPinAnalog(Pin pin);

/** Returns a quickly-read analog value in the range 0-65535.
 * This is basically `jshPinAnalog()*65535`
 * For use from an IRQ where high speed is needed */
int jshPinAnalogFast(Pin pin);

/// Flags for jshPinAnalogOutput
typedef enum {
  JSAOF_NONE,
  JSAOF_ALLOW_SOFTWARE = 1,  ///< Can use software PWM
  JSAOF_FORCE_SOFTWARE = 2,  ///< MUST use software PWM
} JshAnalogOutputFlags;

/// Output an analog value on a pin - either via DAC, hardware PWM, or software PWM
JshPinFunction jshPinAnalogOutput(Pin pin, JsVarFloat value, JsVarFloat freq, JshAnalogOutputFlags flags); // if freq<=0, the default is used

/// Flags for jshPinAnalogOutput
typedef enum {
  JSPW_NONE,
  JSPW_HIGH_SPEED = 1,  ///< Should use high accuracy if available (higher power draw)
} JshPinWatchFlags;

/// Can the given pin be watched? it may not be possible because of conflicts
bool jshCanWatch(Pin pin);
/// start watching pin - return the EXTI (IRQ number flag) associated with it
IOEventFlags jshPinWatch(Pin pin, bool shouldWatch, JshPinWatchFlags flags);

/// Given a Pin, return the current pin function associated with it
JshPinFunction jshGetCurrentPinFunction(Pin pin);

/** Given a pin function, set that pin to the 16 bit value
 * (used mainly for fast DAC and PWM handling from Utility Timer) */
void jshSetOutputValue(JshPinFunction func, int value);

/// Enable watchdog with a timeout in seconds, it'll reset the chip if jshKickWatchDog isn't called within the timeout
void jshEnableWatchDog(JsVarFloat timeout);

// Kick the watchdog
void jshKickWatchDog();

/* Sometimes we allow a Ctrl-C or button press (eg. Bangle.js) to cause an interruption if there
is no response from the interpreter, and that interruption can then break out of Flash Writes
for instance. But there are certain things (like compaction) that we REALLY don't want to
break out of, so they can call jshKickSoftWatchDog to stop it. */
void jshKickSoftWatchDog();

/// Check the pin associated with this EXTI - return true if the pin's input is a logic 1
bool jshGetWatchedPinState(IOEventFlags device);

/// Given an event, check the EXTI flags and see if it was for the given pin
bool jshIsEventForPin(IOEventFlags eventFlags, Pin pin);

/** Is the given device initialised?
 * eg. has jshUSARTSetup/jshI2CSetup/jshSPISetup been called previously? */
bool jshIsDeviceInitialised(IOEventFlags device);


#define DEFAULT_BAUD_RATE               9600
#define DEFAULT_BYTESIZE                8
#define DEFAULT_PARITY                  0
#define DEFAULT_STOPBITS                1

/// Settings passed to jshUSARTSetup to set it the USART up
typedef struct {
  int baudRate;            /// FIXME uint32_t ???
  Pin pinRX;
  Pin pinTX;
  Pin pinCK;               ///< Clock, or PIN_UNDEFINED
  Pin pinCTS;              ///< Clear to send, or PIN_UNDEFINED
  unsigned char bytesize;  ///< size of byte, 7 or 8
  unsigned char parity;    ///< 0=none, 1=odd, 2=even
  unsigned char stopbits;  ///< 1 or 2
  bool xOnXOff;            ///< XON XOFF flow control?
  bool errorHandling;      ///< Whether to forward parity/framing errors
} PACKED_FLAGS JshUSARTInfo;

/// Initialise a JshUSARTInfo struct to default settings
void jshUSARTInitInfo(JshUSARTInfo *inf); // jshardware_common.c

/** Set up a UART, if pins are -1 they will be guessed */
void jshUSARTSetup(IOEventFlags device, JshUSARTInfo *inf);

/** Tear down a UART - there's a weak version of this so it doesn't have to be implemented */
void jshUSARTUnSetup(IOEventFlags device);

/** Kick a device into action (if required). For instance we may have data ready
 * to sent to a USART, but we need to enable the IRQ such that it can automatically
 * fetch the characters to send.
 *
 * Later down the line this could potentially even set up something like DMA.*/
void jshUSARTKick(IOEventFlags device);

/// SPI modes: https://en.wikipedia.org/wiki/Serial_Peripheral_Interface_Bus#Mode_numbers
typedef enum {
  SPIF_CPHA = 1,
  SPIF_CPOL = 2,
  SPIF_SPI_MODE_0 = 0,
  SPIF_SPI_MODE_1 = SPIF_CPHA,
  SPIF_SPI_MODE_2 = SPIF_CPOL,
  SPIF_SPI_MODE_3 = SPIF_CPHA | SPIF_CPOL,
  /* Mode   CPOL  CPHA
        0   0     0
        1   0     1
        2   1     0
        3   1     1
    */

} PACKED_FLAGS JshSPIFlags;

/// How we choose a real baud rate  (on STM32 we can only set it +/- 50%)
typedef enum {
  SPIB_DEFAULT = 0,
  SPIB_MAXIMUM, ///< baudRate is the maximum we'll choose
  SPIB_MINIMUM,///< baudRate is the minimum we'll choose
} PACKED_FLAGS JshBaudFlags;

/// Settings passed to jshSPISetup to set SPI up
typedef struct {
  int baudRate;              //!< Baud rate (must be int because of jsvReadConfigObject)
  JshBaudFlags baudRateSpec; //!< How we choose a real baud rate based on `baudRate` (on STM32 we can only set it +/- 50%)
  Pin pinSCK;                //!< Pin to use for clock.
  Pin pinMISO;               //!< Pin to use for Master In/Slave Out.
  Pin pinMOSI;               //!< Pin to use for Master Out/Slave In.
  unsigned char spiMode;     //!< \see JshSPIFlags
  bool spiMSB;               //!< MSB first?
  int numBits;               //!< Number of bits per send, default 8 (must be int because of jsvReadConfigObject)
} PACKED_FLAGS JshSPIInfo;


/// Initialise a JshSPIInfo struct to default settings
void jshSPIInitInfo(JshSPIInfo *inf); // jshardware_common.c

/** Set up SPI, if pins are -1 they will be guessed */
void jshSPISetup(IOEventFlags device, JshSPIInfo *inf);
/** Send data through the given SPI device (if data>=0), and return the result
 * of the previous send (or -1). If data<0, no data is sent and the function
 * waits for data to be returned */
int jshSPISend(IOEventFlags device, int data);
/** Send 16 bit data through the given SPI device. */
void jshSPISend16(IOEventFlags device, int data);
/** Send data in tx through the given SPI device and return the response in
 * rx (if supplied). Returns true on success. A weak version of this function is provided in jshardware_common.c */
bool jshSPISendMany(IOEventFlags device, unsigned char *tx, unsigned char *rx, size_t count, void (*callback)());
/** Set whether to send 16 bits or 8 over SPI */
void jshSPISet16(IOEventFlags device, bool is16);
/** Set whether to use the receive interrupt or not */
void jshSPISetReceive(IOEventFlags device, bool isReceive);
/** Wait until SPI send is finished, and flush all received data */
void jshSPIWait(IOEventFlags device);

/// Settings passed to jshI2CSetup to set I2C up
typedef struct {
  int bitrate; // (must be int because of jsvReadConfigObject)
  Pin pinSCL;
  Pin pinSDA;
  bool started; ///< Has I2C 'start' condition been sent so far?
  bool clockStretch; ///< In software I2C, should we wait for the device to respond, or do we just soldier on regardless?
#ifdef I2C_SLAVE
  int slaveAddr; ///< if >=0 this is a slave, otherwise master
#endif
} PACKED_FLAGS JshI2CInfo;

/// Initialise a JshI2CInfo struct to default settings
void jshI2CInitInfo(JshI2CInfo *inf); // jshardware_common.c

/** Set up I2C, if pins are -1 they will be guessed */
void jshI2CSetup(IOEventFlags device, JshI2CInfo *inf);

/** Tear down a I2C device - there's a weak version of this so it doesn't have to be implemented */
void jshI2CUnSetup(IOEventFlags device);

/** Write a number of btes to the I2C device. Addresses are 7 bit - that is, between 0 and 0x7F.
 *  sendStop is whether to send a stop bit or not */
void jshI2CWrite(IOEventFlags device, unsigned char address, int nBytes, const unsigned char *data, bool sendStop);
/** Read a number of bytes from the I2C device. */
void jshI2CRead(IOEventFlags device, unsigned char address, int nBytes, unsigned char *data, bool sendStop);

/** Return start address and size of the flash page the given address resides in. Returns false if
  * the page is outside of the flash address range */
bool jshFlashGetPage(uint32_t addr, uint32_t *startAddr, uint32_t *pageSize);
/** Return a JsVar array containing objects of the form `{addr, length}` for each contiguous block of free
 * memory available. These should be one complete pages, so that erasing the page containing any address in
 * this block won't erase anything useful! */
JsVar *jshFlashGetFree();
/// Erase the flash page containing the address
void jshFlashErasePage(uint32_t addr);
/// Erase the flash pages containing the address - return true on success
bool jshFlashErasePages(uint32_t addr, uint32_t byteLength);
/** Read data from flash memory into the buffer, the flash address has no alignment restrictions
  * and the len may be (and often is) 1 byte */
void jshFlashRead(void *buf, uint32_t addr, uint32_t len);
/** Write data to flash memory from the buffer, the buffer address and flash address are
  * guaranteed to be 4-byte aligned, and length is a multiple of 4.  */
void jshFlashWrite(void *buf, uint32_t addr, uint32_t len);
/** Like FlashWrite but can be unaligned (it uses a read first). This is in jshardware_common.c */
void jshFlashWriteAligned(void *buf, uint32_t addr, uint32_t len);

/** On most platforms, the address of something really is that address.
 * In ESP32/ESP8266 the flash memory is mapped up at a much higher address,
 * so we need to tweak any pointers that we use.
 * */
size_t jshFlashGetMemMapAddress(size_t ptr);


/** Utility timer handling functions
 *  ------------------------------------------
 * The utility timer is intended to generate an interrupt and then call jstUtilTimerInterruptHandler
 * as interrupt handler so Espruino can process tasks that are queued up on the timer. Typical
 * functions used in the interrupt handler include reading/write GPIO pins, reading analog and
 * writing analog. See jstimer.c for the implementation.
 *
 * These are exposed through functions like `jsDigitalPulse`, `analogWrite(..., {soft:true})`
 * and the `Waveform` class.
 */

/// Start the timer and get it to interrupt once after 'period' (i.e. it should not auto-reload)
void jshUtilTimerStart(JsSysTime period);
/** Reschedule the timer (it should already be running) to interrupt after 'period'.
With the timer running this should ideally set the time period from the last time the
timer triggered (so as to factor out any execution delay in jstUtilTimerInterruptHandler).  */
void jshUtilTimerReschedule(JsSysTime period);
/// Stop the timer
void jshUtilTimerDisable();

// ---------------------------------------------- LOW LEVEL

#ifdef ARM
// On SYSTick interrupt, call this
void jshDoSysTick();
#endif // ARM

#if defined(STM32) || defined(STM32_LL)
// push a byte into SPI buffers (called from IRQ)
void jshSPIPush(IOEventFlags device, uint16_t data);

typedef enum {
  JSGPAF_INPUT,
  JSGPAF_OUTPUT,
} JshGetPinAddressFlags;
// Get the address to read/write to in order to change the state of this pin. Or 0.
volatile uint32_t *jshGetPinAddress(Pin pin, JshGetPinAddressFlags flags);

/// Set the prescaler used for the RTC - can be used for course RTC adjustment
void jshSetupRTCPrescalerValue(unsigned int prescale);
/// Get the current prescaler value, or the calculated correct value if calibrate=true
int jshGetRTCPrescalerValue(bool calibrate);
// Reset timers and average systick duration counters for RTC - when coming out of sleep or changing prescaler
void jshResetRTCTimer();
/// Flags that we've been able to send data down USB, so it's ok to have data in the output buffer
void jshClearUSBIdleTimeout();
#endif

/// Called when we have had an event that means we should execute JS
extern void jshHadEvent();
/// set if we've had an event we need to deal with
extern volatile bool jshHadEventDuringSleep;

#if defined(NRF51_SERIES) || defined(NRF52_SERIES)
/// Enable/disable(if level==NAN) the LPCOMP comparator
bool jshSetComparator(Pin pin, JsVarFloat level);
#endif

/// the temperature from the internal temperature sensor, in degrees C
JsVarFloat jshReadTemperature();

/// The voltage that a reading of 1 from `analogRead` actually represents, in volts
JsVarFloat jshReadVRef();
/// On nRF52833/40 this is the VDDH value (before the internal voltage regulator)
JsVarFloat jshReadVDDH();

/** Get a random number - either using special purpose hardware or by
 * reading noise from an analog input. If unimplemented, this should
 * default to `rand()` */
unsigned int jshGetRandomNumber();

/** Change the processor clock info. What's in options is platform
 * specific - you should update the docs for jswrap_espruino_setClock
 * to match what gets implemented here. The return value is the clock
 * speed in Hz though. */
unsigned int jshSetSystemClock(JsVar *options);
/** Get processor clock info. What's returned is platform
 * specific - you should update the docs for jswrap_espruino_getClock
 * to match what gets implemented here */
JsVar *jshGetSystemClock();

/* Adds the estimated power usage of the microcontroller in uA to the 'devices' object. The CPU should be called 'CPU' */
void jsvGetProcessorPowerUsage(JsVar *devices);

/// Perform a proper hard-reboot of the device
void jshReboot();

#if defined(STM32F4) || defined(ESPR_HAS_BOOTLOADER_UF2)
/// Reboot into DFU mode
/// If the device has an UF2 bootloader, the device will reappear as a USB drive.
void jshRebootToDFU();
#endif

#if JSH_PORTV_COUNT>0
/// handler for virtual ports (eg. pins on an IO Expander). This should be defined for each type of board used
void jshVirtualPinInitialise();
/// handler for virtual ports (eg. pins on an IO Expander). This should be defined for each type of board used
void jshVirtualPinSetValue(Pin pin, bool state);
/// handler for virtual ports (eg. pins on an IO Expander). This should be defined for each type of board used
bool jshVirtualPinGetValue(Pin pin);
/// handler for virtual ports (eg. pins on an IO Expander). This should be defined for each type of board used. Return NaN if not implemented
JsVarFloat jshVirtualPinGetAnalogValue(Pin pin);
/// handler for virtual ports (eg. pins on an IO Expander). This should be defined for each type of board used
void jshVirtualPinSetState(Pin pin, JshPinState state);
/// handler for virtual ports (eg. pins on an IO Expander). This should be defined for each type of board used. Return JSHPINSTATE_UNDEFINED if not implemented
JshPinState jshVirtualPinGetState(Pin pin);
#endif

/** Hacky definition of wait cycles used for WAIT_UNTIL.
 * TODO: make this depend on known system clock speed? */
#if defined(STM32F401xx) || defined(STM32F411xx)
#define WAIT_UNTIL_N_CYCLES 2000000
#elif defined(STM32F4)
#define WAIT_UNTIL_N_CYCLES 2000000 // Was 5000000
#else
#define WAIT_UNTIL_N_CYCLES 2000000
#endif

/** Wait for the condition to become true, checking a certain amount of times
 * (or until interrupted by Ctrl-C) before leaving and writing a message. */
#define WAIT_UNTIL(CONDITION, REASON) { \
    int timeout = WAIT_UNTIL_N_CYCLES;                                              \
    while (!(CONDITION) && !jspIsInterrupted() && (timeout--)>0);                  \
    if (jspIsInterrupted()) { jsExceptionHere(JSET_INTERNALERROR, "Interrupted in " REASON); }  \
    else if (timeout<=0) { jsExceptionHere(JSET_INTERNALERROR, "Timeout on " REASON ); }  \
}

#endif /* JSHARDWARE_H_ */
