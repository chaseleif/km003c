## USB utility for the POWER-Z KM003C USB-C power meter
### Requirements
Uses the Python3 module pyusb

Setup requirements using pip:
```bash
$ python3 -m venv venv
$ source venv/bin/activate
$ pip install pyusb
```
Check out [PyUSB's git](https://github.com/pyusb/pyusb) for a tutorial and FAQ, if interested

They discuss addressing USB device permission issues in their [FAQ](https://github.com/pyusb/pyusb/blob/master/docs/faq.rst#how-to-practically-deal-with-permission-issues-on-linux)
___
### Usage
This version's usage is basic
1) Run the script
2) Press enter to begin collection
3) Press ctrl-c to end the script
___
### The KM003C interfaces
There are 3 interfaces available to communicate with the power meter

| Interface | Write Address | Read Address |     bInterfaceClass    |
|-----------|---------------|--------------|------------------------|
|    0      |     0x1       |     0x81     |    Vendor Specific     |
|    1      |     0x5       |     0x85     | Human Interface Device |
|    3      |     0x3       |     0x83     |        CDC Data        |

From my usage, I found interfaces 0 and 3 provide 1000 samples/sec, and interface 1 provides 500 samples/sec.

The script uses interface 1, and the interface can be changed by just changing the variable `interfacenum`.
___
### The data received

The amperage received can be either negative or positive.

To address this, the value received must be (and it is) treated as a 32-bit integer to obtain the correct value.

This was not observed for the voltage, but could apply to voltage or any of the signed integer types in the data.

If you get some other signed int out of the data, *int rather than uint*, you may need to account for this as is done for amps in this script:
```python
    amps = c_int32(int.from_bytes(data[12:16], byteorder)).value / 1000000
    if amps < 0: amps = -amps
```
___
### Enums and Structs

```c++
enum cmd_ctrl_msg_type {
  /* 0 Reserved */
  CMD_SYNC = 1,
  CMD_CONNECT,
  CMD_DISCONNECT,
  CMD_RESET,
  CMD_ACCEPT,
  CMD_REJECT,
  CMD_FINISHED,
  CMD_JUMP_APROM,
  CMD_JUMP_DFU,
  CMD_GET_STATUS,
  CMD_ERROR,
  /*app*/
  CMD_GET_DATA,
  CMD_GET_FILE
};
enum attribute_data_type {
  /* 0 - 63 Reserved */
  ATT_ADC = 0x001,
  ATT_ADC_QUEUE = 0x002,
  ATT_ADC_QUEUE_10K = 0x004,
  ATT_SETTINGS = 0x008,
  ATT_PD_PACKET = 0x010,
  ATT_PD_STATUS = 0x020,
  ATT_QC_PACKET = 0x040,
  ATT_TICK = 0x080,
  ATT_TICK__ = 0x100,
};
typedef union {
  uint32_t object;
  uint16_t word[2];
  uint8_t byte[4];
  struct {
    uint32_t type : 7;
    uint32_t extend : 1;
    uint32_t id : 8;
    uint32_t : 1;
    uint32_t att : 15;
  }ctrl;
  struct {
    uint32_t type : 7;
    uint32_t extend : 1;
    uint32_t id : 8;
    uint32_t encode : 1;
    uint32_t permi : 2;
    uint32_t : 3;
    uint32_t obj : 10;
  }data;
  struct {
    uint32_t att : 15;
    uint32_t next : 1;
    uint32_t chunk : 6;
    uint32_t size : 10;
  }header;
}MsgHeader_TypeDef;
typedef struct {
  int32_t         Vbus;
  int32_t         Ibus;
  int32_t         Vbus_avg;
  int32_t         Ibus_avg;
  int32_t         Vbus_ori_avg;
  int32_t         Ibus_ori_avg;
  int16_t         Temp;
  uint16_t        Vcc1;
  uint16_t        Vcc2;
  uint16_t        Vdp;
  uint16_t        Vdm;
  uint16_t        Vdd;
  uint8_t         Rate : 2;
  uint8_t         n[3];
}AdcData_TypeDef;
```

___
### Getting data

POWER-Z provides an archive, `hiddemo_vs2019_for-KM002C3C.zip`, which contains a document and example C++ source

The message sent to the device corresponds to what is shown in `KM002C&3C API Description.docx` provided by POWER-Z

Using the following print function we will print the values of the header:
```c++
static void prints(unsigned char *data) {
  static int step = 0;
  printf("step %d:\n0x", ++step);
  for (int i=0;i<4;++i) {
    printf("%x",data[i]);
  }
  printf("\n");
  for (int i=0;i<4;++i) {
    for (int x=7;x>=0;--x) {
      printf("%u",(data[i]>>x)&1);
    }
  }
  printf("\n");
}
```

Replicating the source of the demo for the filling out a data request, we fill out `MsgHeader_TypeDef`:

**note the header is a *union*

1) Transfers are done with a buffer size of 64 bytes
2) We create a buffer: `uint8_t tbuf[64];`
3) The header is created: `MsgHeader_TypeDef head;`
4) The header union is set to zero: `head.object = 0;`
5) The header control type is set to 0xc: `head.ctrl.type = CMD_GET_DATA;`
6) The header attribute type is set to 0x1: `head.ctrl.att = ATT_ADC;`
7) A memcpy is performed into tbuf from header for sizeof(header) = 4 bytes

For each step in steps 3-6, we print the values of the header, for step 7 we print the first 4 bytes of tbuf

Output:
```bash
$ ./a.out
step 3:
0xe07d87f3
11100000011111011000011111110011
step 4:
0x0000
00000000000000000000000000000000
step 5:
0xc000
00001100000000000000000000000000
step 6:
0xc020
00001100000000000000001000000000
step 7:
0xc020
00001100000000000000001000000000
```

To duplicate this in Python, we need to send the 4 bytes: `0xc020`
___

The received data goes into a 64-byte buffer and has bytes:
|      byte      |  0-3   |   4-7  | 8-47 |
|----------------|--------|--------|------|
| data structure | header | header | data |

The second header is an "extended header", which is the same type.

Byte locations for struct members inside the entire received data buffer (starting at +8, past the 2 headers):
| Vbus | Ibus | Vbus_avg | Ibus_avg | Vbus_ori_avg | Ibus_ori_avg | Temp | Vcc1 | Vcc2 | Vdp | Vdm | Vdd | Rate | n |
|------|------|----------|----------|--------------|--------------|------|------|------|-----|-----|-----|------|---|
| 8-11 | 12-15 | 16-19   | 20-23    | 24-27        | 28-31        | 32-33 | 34-35 | 36-37 | 38-39 | 40-41 | 42-43 | 44 | 45-47 |

*byte 44:* Rate has space for a byte but has "only" 2 bits

*bytes 45-47:* n is 3 separate bytes, i.e., n[0], n[1], n[2]
___
### Resources
#### Looking for a power meter that didn't need Windows, I came across this [article](https://www.anandtech.com/show/18944/usbc-power-metering-with-the-chargerlab-km003c-a-google-twinkie-alternative) as a starting point.

#### The document and source mentioned in [the message section](#the-messages) above were obtained from:

In the FAQ section of the [product support page](https://www.chargerlab.com/km003c-km002c-technical-support/):

__Q: Are there any open APIs available for further self-development?__

A: We currently only provide limited toolkit for reference.

[hiddemo_vs2019_for KM002C&3C](https://www.chargerlab.com/wp-content/uploads/2019/05/hiddemo_vs2019_for-KM002C3C.zip)
___
