# -*- coding: utf-8 -*-
""" Singleton class to manage configuration
Description:
Todo:

"""

import json
import os
import sys
import logging
import constant


class Config(object):
    # Here will be the instance stored.
    __instance = None

    @classmethod
    def getInstance(cls):
        """ Static access method. """
        if Config.__instance == None:
            raise Exception("Any configuration is not initialized yet!")
        return Config.__instance

    def __init__(self, url):
        """ Virtually private constructor. """
        if Config.__instance != None:
            raise Exception("This class is a singleton!")
        else:
            self.config = dict()
            self.load(url)
            self._url = url
            Config.__instance = self

    def load(self, url):
        try:
            self.config = json.load(open(url))
            self.config["version"] = constant.APPVERSION
            logging.info(self.config)
        except Exception as error:
            logging.error(error, exc_info=True)
        return self.config

    def store(self):
        try:
            with open(self._url, "w") as outfile:
                json.dump(self.config, outfile, indent=4)
        except Exception as error:
            logging.error(error, exc_info=True)
