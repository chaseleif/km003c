#! /usr/bin/env python3

import usb.core, usb.util
from ctypes import c_int32
from time import perf_counter
from sys import byteorder, exit

def collectpower(dev):
  # The command used to obtain data from the device
  cmd = bytes([0x0c, 0x0f, 0x02, 0x00]).decode('utf-8')

  # Our beginning time, for elapsed
  start = perf_counter()
  # The header of a csv
  print('elapsed,volt,amp,watt')

  # For some count, or timerange, or while True
  for count in range(20):
    # The current elapsed time
    elapsed = perf_counter()-start
    # Send our command to the offset for the interface, we should send 4 bytes
    sent = dev.write(0x3, cmd)

    # This shouldn't happen, not sure if we can recover so just quit
    if dev.write(0x1, cmd) != 4:
      print(f'ERROR: sent bytes != 4')
      return

    # Read the response from the offset for the interface
    data = dev.read(0x83, 64)

    # Get voltage and amps and scale them
    volt = int.from_bytes(data[8:12], byteorder) / 1000000
    # Amps can be negative, treat as a 32-bit int for two's complement
    amps = c_int32(int.from_bytes(data[12:16], byteorder)).value / 1000000
    if amps < 0: amps = -amps

    # Print the measurement
    print(f'{elapsed:.2f},{volt:.6f},{amps:.6f},{volt*amps:.6f}')

if __name__ == '__main__':
  # POWER-Z KM003C
  # Reference our power meter
  dev = usb.core.find(idVendor=0x5fc9, idProduct=0x0063)
  if dev is None:
    print('Unable to locate POWER-Z KM003C meter')
    exit(1)

  # print(dev) <~ can get IF numbers and IN/OUT offsets
  # from tests, I receive these sample rates using the above function:
  # interface | samples | write to | read from
  #     0     |  ~1/sec |   0x1    |   0x81
  #     1     |  ~5/sec |   0x5    |   0x85
  #     3     | ~10/sec |   0x3    |   0x83

  # Ensure the kernel is not attached on any interface
  for cfg in dev:
    for intf in cfg:
      intf = intf.bInterfaceNumber
      if dev.is_kernel_driver_active(intf):
        dev.detach_kernel_driver(intf)

  # Claim our interface (see note above regarding sample rate and offsets)
  usb.util.claim_interface(dev, 3)

  # Enter our power collection loop
  try:
    collectpower(dev)
  except KeyboardInterrupt as e: pass
  except Exception as e: print(e)

  # Release the power meter
  dev.reset()
  usb.util.dispose_resources(dev)
