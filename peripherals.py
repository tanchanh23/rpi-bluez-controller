# Standard packages
# -*- coding: utf-8 -*-
""" Peripheral controller

Description:

    Management of peripherals
"""
import os
import sys
import threading
import time
import logging

import RPi.GPIO as GPIO
import Adafruit_DHT
from grove.adc import ADC

GPIO.setmode(GPIO.BCM)  # GPIO Numbers instead of board numbers
GPIO.setwarnings(False)


class TempHumiThread(threading.Thread):
    """"""

    def __init__(self, pin):
        """"""
        threading.Thread.__init__(self)
        self.eventSet = threading.Event()
        self._pin = pin
        self.temp = None
        self.humi = None
        #
        self.start()

    def run(self):
        """  """
        while not self.eventSet.is_set():
            try:
                humidity, temperature = Adafruit_DHT.read_retry(
                    Adafruit_DHT.DHT22, self._pin
                )
                logging.info(
                    "Temperature: {}C, Humidity: {}%".format(temperature, humidity)
                )

                if temperature != None:
                    self.temp = temperature

                if humidity != None:
                    self.humi = humidity

            except Exception as error:
                logging.error(error, exc_info=True)
            time.sleep(2.0)


class Peripheral_Handler(threading.Thread):
    def __init__(self, mq2_channel, dht_pin, fan_pin, speed_pin):
        """"""
        threading.Thread.__init__(self)

        self.eventSet = threading.Event()
        self._channel = mq2_channel
        self.grove_dht = TempHumiThread(dht_pin)
        self.adc = ADC()

        self.fan_pin = fan_pin
        self.speed_pin = speed_pin
        GPIO.setup(self.fan_pin, GPIO.OUT)
        GPIO.output(self.fan_pin, GPIO.LOW)
        GPIO.setup(self.speed_pin, GPIO.OUT)
        GPIO.output(self.speed_pin, GPIO.LOW)

        self.fan = False
        self.speed = False
        self.mq2_adc = 0
        self.air_quality = 0

    def run(self):
        """  """
        while not self.eventSet.is_set():
            try:
                self.mq2_adc = self.adc.read(self._channel)
            except Exception as error:
                logging.error(error, exc_info=True)
            time.sleep(2.0)

    def fan_drive(self, on):
        self.fan = on
        GPIO.output(self.fan_pin, on and GPIO.HIGH or GPIO.LOW)

    def fan_speed(self, fast):
        self.speed = fast
        GPIO.output(self.speed_pin, fast and GPIO.HIGH or GPIO.LOW)

    def initialize(self):
        logging.info("Initializing peripheral modules...")
        self.start()

    def terminate(self):
        self.eventSet.set()
