## Linux USB utility for the POWER-Z KM003C USB-C power meter
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

| Interface | Sample Rate | Write Address | Read Address |
|-----------|-------------|---------------|--------------|
|    0      | ~1/second   |     0x1       |     0x81     |
|    1      | ~5/second   |     0x5       |     0x85     |
|    3      | ~10/second  |     0x3       |     0x83     |

The script is setup to use interface 3
___
### The data received

The amperage received can be either negative or positive.

To address this, the value received must be treated as a 32-bit integer to obtain the correct value.

This was not observed for the voltage, but could apply to voltage or any of the signed integer types in the data.

### The messages

POWER-Z provides an archive, `hiddemo_vs2019_for-KM002C3C.zip`, which contains a document and C++ source
___

The message sent to the device correspond to what is shown in `KM002C&3C API Description.docx` provided by POWER-Z:

Replicating the source for the request, filling out `MsgHeader_TypeDef`, we get:

The header is zeroed out: `head.object = 0;`

The header control type is set to 0xc: `head.ctrl.type = CMD_GET_DATA;`

The header attribute type is set to 0x1: `head.ctrl.att = ATT_ADC;`

The hex can be printed:
```c++
  printf("0x");
  for (int i=0;i<4;++i) {
    printf("%.2x",tbuf[i]);
  }
  printf("\n");
```
To get output which matches the document: 0x0c000200

***NOTE:*** 
The header used in the example source is actually a union, and `tbuf` is a 64-byte array of uint8.

There is a memcpy to tbuf from the header for sizeof(header) which is 4 bytes.
___

The received data goes into a 64-byte buffer and has bytes:
|      byte      |  0-3   |   4-7  | 8-47 |
|----------------|--------|--------|------|
| data structure | header | header | data |

The second header is an "extended header", which is the same union type.

The data structure is as follows:
```c++
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
Byte locations for struct members inside the entire received data buffer (starting at +8, past the 2 headers):
| Vbus | Ibus | Vbus_avg | Ibus_avg | Vbus_ori_avg | Ibus_ori_avg | Temp | Vcc1 | Vcc2 | Vdp | Vdm | Vdd | Rate | n |
|------|------|----------|----------|--------------|--------------|------|------|------|-----|-----|-----|------|---|
| 8-11 | 12-15 | 16-19   | 20-23    | 24-27        | 28-31        | 32-33 | 34-35 | 36-37 | 38-39 | 40-41 | 42-43 | 44 | 45-47 |

Rate has space for a byte but has "only" 2 bits, n is 3 separate bytes, i.e., n[0], n[1], n[2]
___
### Resources
#### Looking for a power meter that didn't need Windows, I came across this [article](https://www.anandtech.com/show/18944/usbc-power-metering-with-the-chargerlab-km003c-a-google-twinkie-alternative) as a starting point.

#### The document and source mentioned in [the message section](#the-messages) above were obtained from:

In the FAQ section of the [product support page](https://www.chargerlab.com/km003c-km002c-technical-support/):

__Q: Are there any open APIs available for further self-development?__

A: We currently only provide limited toolkit for reference.

[hiddemo_vs2019_for KM002C&3C](https://www.chargerlab.com/wp-content/uploads/2019/05/hiddemo_vs2019_for-KM002C3C.zip)
___
