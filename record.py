#! /usr/bin/env python3

import usb.core, usb.util
from collections import namedtuple
from ctypes import c_int32
from time import perf_counter
from sys import byteorder, exit

def collectpower(powermeter):
  # The command used to obtain data from the device
  cmd = bytes([0xc, 0x0, 0x2, 0x0]).decode('utf-8')

  # Our beginning time, for elapsed
  start = perf_counter()
  # The header of a csv
  print('elapsed,volt,amp,watt')

  while True:
    # Send our command to the offset for the interface, we should send 4 bytes
    if powermeter.dev.write(powermeter.write, cmd) != 4:
      # This shouldn't happen, not sure if we can recover so just quit
      print('ERROR: sent bytes != 4')
      return

    # Read the response from the offset for the interface
    data = powermeter.dev.read(powermeter.read, 64)

    # Get voltage and amps and scale them
    volt = int.from_bytes(data[8:12], byteorder) / 1000000
    # Amps can be negative, treat as a 32-bit int for two's complement
    amps = c_int32(int.from_bytes(data[12:16], byteorder)).value / 1000000
    if amps < 0: amps = -amps

    # Print the measurements
    print(f'{perf_counter()-start:.3f},{volt:.6f},{amps:.6f},{volt*amps:.6f}')

if __name__ == '__main__':
  # POWER-Z KM003C
  # Reference our power meter
  dev = usb.core.find(idVendor=0x5fc9, idProduct=0x0063)
  if dev is None:
    print('Unable to locate POWER-Z KM003C meter')
    exit(1)

  # Ensure the kernel is not attached on any interface
  for cfg in dev:
    for intf in cfg:
      intf = intf.bInterfaceNumber
      if dev.is_kernel_driver_active(intf):
        dev.detach_kernel_driver(intf)

  # Claim our interface (see note above regarding sample rate and offsets)
  # interface 0, 1, or 3
  interfacenum = 1
  usb.util.claim_interface(dev, interfacenum)

  # Group the device and associated read/write addresses
  powermeter = namedtuple('meter', ['dev','write','read'])
  if interfacenum == 0:
    powermeter = powermeter(dev, 0x1, 0x81) # IF = 0, ~1000 samples/sec
  elif interfacenum == 1:
    powermeter = powermeter(dev, 0x5, 0x85) # IF = 1 ~500 samples/sec
  else: # if interfacenum == 3
    powermeter = powermeter(dev, 0x3, 0x83) # IF = 3 ~ 1000 samples/sec

  input('Press enter to begin power collection\n')
  try:
    collectpower(powermeter)
  except KeyboardInterrupt as e: pass
  except Exception as e: print(e)

  # Release the power meter
  dev.reset()
  usb.util.dispose_resources(dev)
