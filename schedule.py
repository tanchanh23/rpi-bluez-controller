# -*- coding: utf-8 -*-


import json
import os
import sys
import logging


class Schedule(object):
    # Here will be the instance stored.
    __instance = None

    @classmethod
    def getInstance(cls):
        """ Static access method. """
        if Schedule.__instance == None:
            raise Exception("Any Schedule is not initialized yet!")
        return Schedule.__instance

    def __init__(self, url):
        """ Virtually private constructor. """
        if Schedule.__instance != None:
            raise Exception("This class is a singleton!")
        else:
            self.schedules = []
            self.load(url)
            self._url = url
            Schedule.__instance = self

    def load(self, url):
        try:
            self.schedules = json.load(open(url))
            logging.info(self.schedules)
        except Exception as error:
            logging.error(error, exc_info=True)
        return self.schedules

    def store(self):
        try:
            with open(self._url, "w") as outfile:
                json.dump(self.schedules, outfile, indent=4)
        except Exception as error:
            logging.error(error, exc_info=True)
