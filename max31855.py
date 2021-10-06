import time
import sys
from smbus2 import SMBus

class MAX31855:
  MAX31855_ADDR = 0x10
  def __init__(self):
    self.bus = SMBus(1)
  
  def readData(self):
    a = self.bus.read_byte_data(self.MAX31855_ADDR, 0)
    b = self.bus.read_byte_data(self.MAX31855_ADDR, 1)
    d = self.bus.read_byte_data(self.MAX31855_ADDR, 3)
    return a, b, d
  
  def readCelsius(self):
    a, b, d = self.readData()
    if(d&0x7):
      return False
    if(a&0x80):
      a = 0xff - a
      b = 0xff - b
      temp = -((((a << 8) | b) >> 2)+1)*0.25
      return temp
    temp = (((a << 8) | b) >> 2)*0.25
    return temp

  def readFahrenheit(self):
     return self.readCelsius() * 1.8 + 32

  def getTemperature(self, n=100):
        n = min(max(n, 5), 100)
        sample = sorted([self.readFahrenheit() for i in range(n)])
        return sample[int(n / 2)]
        

