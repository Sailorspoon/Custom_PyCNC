# coding=utf-8
import os
import mmap
import struct
import re
import fcntl
import array
import atexit
import ctypes

# Raspberry Pi registers
# https://www.raspberrypi.org/wp-content/uploads/2012/02/BCM2835-ARM-Peripherals.pdf (1)
# Physical Adress of Peripherals - this is for RPi 1 only
RPI1_PERI_BASE = 0x20000000
# Peripherals address RPi 2 and/or 3 """
RPI2_3_PERI_BASE = 0x3F000000
# detect board version
try:
    with open("/proc/cpuinfo", "r") as f:
        d = f.read()
        r = re.search("^Revision\s+:\s+(.+)$", d, flags=re.MULTILINE)
        h = re.search("^Hardware\s+:\s+(.+)$", d, flags=re.MULTILINE)
        RPI_1_REVISIONS = ['0002', '0003', '0004', '0005', '0006', '0007',
                           '0008', '0009', '000d', '000e', '000f', '0010',
                           '0011', '0012', '0013', '0014', '0015', '900021',
                           '900032']
        if h is None:
            raise ImportError("This is not a raspberry pi board.")
        elif r.group(1) in RPI_1_REVISIONS:
            PERI_BASE = RPI1_PERI_BASE
        elif "BCM2" in h.group(1):
            PERI_BASE = RPI2_3_PERI_BASE
        else:
            raise ImportError("Unknown board.")
except IOError:
    raise ImportError("/proc/cpuinfo not found. Not Linux device?")
# For understanding the following lines of code, (1) page 89 ff. are helpful
# Be aware of the errata list: https://elinux.org/BCM2835_datasheet_errata
# GPIO has up to 54 I/Os with each at least two different functions
PAGE_SIZE = 4096    # determination of pagesize - see, if can be changed later on
GPIO_REGISTER_BASE = 0x200000
GPIO_INPUT_OFFSET = 0x34    # GPLEV0 Input State of all 32 GPIOs
GPIO_SET_OFFSET = 0x1C    # GPSET0 Output Setting
GPIO_CLEAR_OFFSET = 0x28    # GPCLR0 clear all 1's in corresponding register
GPIO_FSEL_OFFSET = 0x0    # GPFSEL0 Function selection
# GPPUD has no read-back functionality
GPIO_PULLUPDN_OFFSET = 0x94    # GPPUD controls the actuation of the internal pull-up/down
GPIO_PULLUPDNCLK_OFFSET = 0x98    # GPPUDCLK0 in conjunction with GPPUD
# See (1) page 101:
# The GPIO Pull-up/down Clock Registers control the actuation of internal pull-downs on
# the respective GPIO pins. These registers must be used in conjunction with the GPPUD
# register to effect GPIO Pull-up/down changes. The following sequence of events is
# required:
# 1. Write to GPPUD to set the required control signal (i.e. Pull-up or Pull-Down or neither
# to remove the current Pull-up/down)
# 2. Wait 150 cycles – this provides the required set-up time for the control signal
# 3. Write to GPPUDCLK0/1 to clock the control signal into the GPIO pads you wish to
# modify – NOTE only the pads which receive a clock will be modified, all others will
# retain their previous state.
# 4. Wait 150 cycles – this provides the required hold time for the control signal
# 5. Write to GPPUD to remove the control signal
# 6. Write to GPPUDCLK0/1 to remove the clock
PHYSICAL_GPIO_BUS = 0x7E000000 + GPIO_REGISTER_BASE     # bus address - VC/ARM MMU

# registers and values for DMA
# for explanation see (1) page 41 ff.
DMA_BASE = 0x007000    # address of DMA channel 0 register set
DMA_CS = 0x00    # global enable register
DMA_CONBLK_AD = 0x04    # DMA control block address
DMA_NEXTCONBK = 0x1C    # Next control block address
DMA_TI_NO_WIDE_BURSTS = 1 << 26    # 0_TI (DMA Transfer Information) Register AXI bursts
DMA_TI_SRC_INC = 1 << 8    # Source transfer width: 1 = Use 128-bit source read width, 0 = Use 32-bit source read width
DMA_TI_DEST_INC = 1 << 4    # Destination Address Increment
# The Destination Address Increment is used in conjunction with Destination Transfer Width (address 1 << 5), which is
# not specified in this list
DMA_SRC_IGNORE = 1 << 11    # is still part of TI (Transfer Information) 1 = do not perform source reads
DMA_DEST_IGNORE = 1 << 7    # is also part of TI, 1 = do not perform destination writes
DMA_TI_TDMODE = 1 << 1    # set mode interpret, 1 = 2D mode, 0 = linear mode
DMA_TI_WAIT_RESP = 1 << 3    # 1 = wait for AXI write response
DMA_TI_SRC_DREQ = 1 << 10    # used in conjuction with Peripheral Mapping, 1 = the data request (DREQ) selected by
# PERMAP (indicates the peripheral number whose reay signal shall be used to control the rate of the transfers)
# will gate the source reads
DMA_TI_DEST_DREQ = 1 << 6    # used in conjuction with Peripheral Mapping, 1 = the data request (DREQ) selected by
# PERMAP will gate the destination writes
DMA_CS_RESET = 1 << 31    # DMA channel reset
DMA_CS_ABORT = 1 << 30    # abort the current DMA CB
DMA_CS_DISDEBUG = 1 << 29    # 1 = DMA will not stop, when debug pause signal is asserted - CHANGED Max 30.11.2019
# I think DMA_CS_DISDEBUG has been assigned to the wrong address register: 1 << 28 points to WAIT_FOR_OUTSTANDING_WRITES
# (1) provides on page 48 the following explanation for this:
# When set to 1, the DMA will keep a tally
# of the AXI writes going out and the write
# responses coming in. At the very end of
# the current DMA transfer it will wait
# until the last outstanding write response
# has been received before indicating the
# transfer is complete. Whilst waiting it
# will load the next CB address (but will
# not fetch the CB), clear the active flag (if
# the next CB address = zero), and it will
# defer setting the END flag or the INT flag
# until the last outstanding write response
# has been received.
# In this mode, the DMA will pause if it has
# more than 13 outstanding writes at any
# one time.
DMA_CS_END = 1 << 1    # end flag: set, when the current transfer (desc. by CB) is complete 1 = clear
DMA_CS_ACTIVE = 1 << 0    # DMA enable - pause possible by clearing and resetting
DMA_TI_PER_MAP_PWM = 5    # the ready signal of peripheral 5 (PWM) shall be used to control the rate of the transfers
# see page 61 in (1)
DMA_TI_PER_MAP_PCM = 2    # the ready signal of peripheral 2 (PCM TX) shall be used to control the rate of the transfers
DMA_TI_PER_MAP = (lambda x: x << 16)    # Peripheral 20:16 bits
DMA_TI_WAITS = (lambda x: x << 21)    # adds wait cycles - sets number of dummy cycles - bits 25:21
DMA_TI_TXFR_LEN_YLENGTH = (lambda y: (y & 0x3fff) << 16)    # is part of TXFR_LEN - bits 29:16
DMA_TI_TXFR_LEN_XLENGTH = (lambda x: x & 0xffff)    # is part of TXFR_LEN - bits 15:0
DMA_TI_STRIDE_D_STRIDE = (lambda x: (x & 0xffff) << 16)    # Signed (2 s complement) byte increment to apply to
# the destination address at the end of each row in 2D mode - bits 31:16
DMA_TI_STRIDE_S_STRIDE = (lambda x: x & 0xffff)    # Signed (2 s complement) byte increment to apply to
# the source address at the end of each row in 2D mode - bits 15:0
DMA_CS_PRIORITY = (lambda x: (x & 0xf) << 16)    # sets the AXI bus priority - bits 19:16
DMA_CS_PANIC_PRIORITY = (lambda x: (x & 0xf) << 20)    # sets the priority (0 is lowest) of panicking AXI bus
# transactions, value is only used, when the panic bit of the selected peripheral channel is 1 - bits 23:20

# hardware PWM controller registers
PWM_BASE = 0x0020C000
PHYSICAL_PWM_BUS = 0x7E000000 + PWM_BASE
# see (1) page 141 ff. for explanation
PWM_CTL = 0x00    # PWM Control Register Address
PWM_DMAC = 0x08    # PWM DMA Configuration Address
PWM_RNG1 = 0x10    # PWM Channel 1 Range
PWM_RNG2 = 0x20    # PWM Channel 2 Range
PWM_FIFO = 0x18    # PWM FIFO Input
PWM_CTL_MODE1 = 1 << 1    # 0 = PWM mode, 1 = Serialiser mode for channel 1 (check errata)
PWM_CTL_MODE2 = 1 << 9    # 0 = PWM mode, 1 = Serialiser mode for channel 2
PWM_CTL_PWEN1 = 1 << 0    # Enable channel 1 (= 1)
PWM_CTL_PWEN2 = 1 << 8    # Enable channel 2 (= 1)
PWM_CTL_CLRF = 1 << 6     # Clear FIFO = 1, 0 = no effect
PWM_CTL_USEF1 = 1 << 5    # Use FIFO for channel 1 (= 1)
PWM_CTL_USEF2 = 1 << 13    # Use FIFO for channel 2 (= 2)
PWM_DMAC_ENAB = 1 << 31    # 1 = Start DMA, 0 = DMA disabled
PWM_DMAC_PANIC = (lambda x: x << 8)    # threshold for PANIC signal (if above 7 -> active) - bits 15:8
PWM_DMAC_DREQ = (lambda x: x)    # threshold for DREQ signal (if above 7 -> active) - bits 7:0

# clock manager module
CM_BASE = 0x00101000
CM_PCM_CNTL = 0x98
CM_PCM_DIV = 0x9C
CM_PWM_CNTL = 0xA0
CM_PWM_DIV = 0xA4
CM_PASSWORD = 0x5A << 24
CM_CNTL_ENABLE = 1 << 4
CM_CNTL_BUSY = 1 << 7
CM_SRC_OSC = 1   # 19.2 MHz
CM_SRC_PLLC = 5  # 1000 MHz
CM_SRC_PLLD = 6  # 500 MHz
CM_SRC_HDMI = 7  # 216 MHz
CM_DIV_VALUE = (lambda x: x << 12)


class PhysicalMemory(object):
    # noinspection PyArgumentList,PyArgumentList
    def __init__(self, phys_address, size=PAGE_SIZE):
        """ Create object which maps physical memory to Python's mmap object.
        :param phys_address: based address of physical memory
        """
        self._size = size
        phys_address -= phys_address % PAGE_SIZE
        fd = self._open_dev("/dev/mem")
        self._memmap = mmap.mmap(fd, size, flags=mmap.MAP_SHARED,
                                 prot=mmap.PROT_READ | mmap.PROT_WRITE,
                                 offset=phys_address)
        self._close_dev(fd)
        atexit.register(self.cleanup)

    def cleanup(self):
        self._memmap.close()

    @staticmethod
    def _open_dev(name):
        fd = os.open(name, os.O_SYNC | os.O_RDWR)
        if fd < 0:
            raise IOError("Failed to open " + name)
        return fd

    @staticmethod
    def _close_dev(fd):
        os.close(fd)

    def write_int(self, address, int_value):
        ctypes.c_uint32.from_buffer(self._memmap, address).value = int_value

    def write(self, address, fmt, data):
        struct.pack_into(fmt, self._memmap, address, *data)

    def read_int(self, address):
        return ctypes.c_uint32.from_buffer(self._memmap, address).value

    def get_size(self):
        return self._size


class CMAPhysicalMemory(PhysicalMemory):
    IOCTL_MBOX_PROPERTY = ctypes.c_long(0xc0046400).value

    def __init__(self, size):
        """ This class allocates continuous memory with specified size, lock it
            and provide access to it with Python's mmap. It uses RPi video
            buffers to allocate it (/dev/vcio).
        :param size: number of bytes to allocate
        """
        size = (size + PAGE_SIZE - 1) // PAGE_SIZE * PAGE_SIZE
        self._vcio_fd = self._open_dev("/dev/vcio")
        # allocate memory
        self._handle = self._send_data(0x3000c, [size, PAGE_SIZE, 0xC])
        if self._handle == 0:
            raise OSError("No memory to allocate with /dev/vcio")
        # lock memory
        self._bus_memory = self._send_data(0x3000d, [self._handle])
        if self._bus_memory == 0:
            # memory should be freed in __del__
            raise OSError("Failed to lock memory with /dev/vcio")
        # print("allocate {} at {} (bus {})".format(size,
        #       hex(self.get_phys_address()), hex(self.get_bus_address())))
        super(CMAPhysicalMemory, self).__init__(self.get_phys_address(), size)
        atexit.register(self.free)

    def free(self):
        """Release and free allocated memory
        """
        self._send_data(0x3000e, [self._handle])  # unlock memory
        self._send_data(0x3000f, [self._handle])  # free memory
        self._close_dev(self._vcio_fd)

    def _send_data(self, request, args):
        data = array.array('I')
        data.append(24 + 4 * len(args))  # total size
        data.append(0)                   # process request
        data.append(request)             # request id
        data.append(4 * len(args))       # size of the buffer
        data.append(4 * len(args))       # size of the data
        data.extend(args)                # arguments
        data.append(0)                   # end mark
        fcntl.ioctl(self._vcio_fd, self.IOCTL_MBOX_PROPERTY, data, True)
        return data[5]

    def get_bus_address(self):
        return self._bus_memory

    def get_phys_address(self):
        return self._bus_memory & ~0xc0000000


class DMAProto(object):
    def __init__(self, memory_size, dma_channel):
        """ This class provides basic access to DMA and creates buffer for
            control blocks.
        """
        self._DMA_CHANNEL_ADDRESS = 0x100 * dma_channel
        # allocate buffer for control blocks
        self._phys_memory = CMAPhysicalMemory(memory_size)
        # prepare dma registers memory map
        self._dma = PhysicalMemory(PERI_BASE + DMA_BASE)

    def _run_dma(self):
        """ Run DMA module from created buffer.
        """
        self._dma.write_int(self._DMA_CHANNEL_ADDRESS + DMA_CS, DMA_CS_END)
        self._dma.write_int(self._DMA_CHANNEL_ADDRESS + DMA_CONBLK_AD,
                            self._phys_memory.get_bus_address())
        cs = DMA_CS_PRIORITY(7) | DMA_CS_PANIC_PRIORITY(7) | DMA_CS_DISDEBUG
        self._dma.write_int(self._DMA_CHANNEL_ADDRESS + DMA_CS, cs)
        cs |= DMA_CS_ACTIVE
        self._dma.write_int(self._DMA_CHANNEL_ADDRESS + DMA_CS, cs)

    def _stop_dma(self):
        """ Stop DMA
        """
        cs = self._dma.read_int(self._DMA_CHANNEL_ADDRESS + DMA_CS)
        cs |= DMA_CS_ABORT
        self._dma.write_int(self._DMA_CHANNEL_ADDRESS + DMA_CS, cs)
        cs &= ~DMA_CS_ACTIVE
        self._dma.write_int(self._DMA_CHANNEL_ADDRESS + DMA_CS, cs)
        cs |= DMA_CS_RESET
        self._dma.write_int(self._DMA_CHANNEL_ADDRESS + DMA_CS, cs)

    def is_active(self):
        """ Check if DMA is working. Method can check if single sequence
            still active or cycle sequence is working.
        :return: boolean value
        """
        cs = self._dma.read_int(self._DMA_CHANNEL_ADDRESS + DMA_CS)
        if cs & DMA_CS_ACTIVE == DMA_CS_ACTIVE:
            return True
        return False

    def current_control_block(self):
        """ Get current dma control block address.
        :return: Currently running DMA control block offset in bytes or None
                 value if DMA is not running.
        """
        cb = self._dma.read_int(self._DMA_CHANNEL_ADDRESS + DMA_CONBLK_AD)
        if cb == 0:
            return None
        return cb - self._phys_memory.get_bus_address()
