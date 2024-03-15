# Standard packages
# -*- coding: utf-8 -*-
""" Main controller

Description:

    Flask Web HTTP Request handlers
"""
import os
import sys
import threading
import time
import logging
import logging.config
import subprocess
import json
import string
from datetime import datetime
import subprocess

from os import path, walk
from flask import Flask, render_template, request, jsonify, url_for, json, redirect
from werkzeug.serving import run_simple
from werkzeug.utils import secure_filename

from constant import *
from peripherals import Peripheral_Handler
from config import Config
from schedule import Schedule
from ble_peripheral import ElevatorAirBlePeripheral

#
logging.config.fileConfig("logging.conf")
app = Flask(__name__)

extra_dirs = [
    "templates",
    "static/js",
    "static/css",
]
extra_files = extra_dirs[:]
for extra_dir in extra_dirs:
    for dirname, dirs, files in walk(extra_dir):
        for filename in files:
            filename = path.join(dirname, filename)
            if path.isfile(filename):
                extra_files.append(filename)
                # logging.info(filename)


system_config = Config("static/data/config.json")
schedule = Schedule("static/data/schedule.json")
peripheral_handler = Peripheral_Handler(MQ2ADC, DHTPIN, FANREALY, FANSPEEDREALY)
ble_handler = ElevatorAirBlePeripheral(system_config.config["advertise_name"])

logfilename = "log/{}.txt".format(datetime.now().strftime("%Y-%m-%d"))
rootlogger = logging.getLogger()
handler = logging.FileHandler(logfilename)
handler.setFormatter(
    logging.Formatter(
        "%(asctime)s, %(filename)s, %(funcName)s, %(lineno)d, %(levelname)s- %(message)s"
    )
)
rootlogger.addHandler(handler)

###########################################################################


@app.route("/")
def index():
    """Index page"""
    return render_template("index.html")


@app.route("/zipupdate", methods=["POST"])
def update_with_zip():
    try:
        uploaded_file = request.files["sourcefile"]
        if uploaded_file.filename != "":
            filename = uploaded_file.filename
            uploaded_file.save("/home/pi/{}".format(filename))
            subprocess.call(
                "sudo unzip -o /home/pi/{} -d /home/pi/".format(filename),
                shell=True,
            )

            subprocess.call(
                "sudo rm -rf /home/pi/elevator_ble/",
                shell=True,
            )

            subprocess.call(
                "sudo mv /home/pi/{} /home/pi/elevator_ble".format(filename[:-4]),
                shell=True,
            )
            threading.Timer(
                3.0,
                lambda: subprocess.call(
                    "sudo systemctl restart elevatorair", shell=True
                ),
            ).start()
        return redirect(url_for("index"))
    except Exception as error:
        logging.error(repr(error), exc_info=True)


@app.route("/hostspot", methods=["POST"])
def post_hostspot():
    system_config = Config.getInstance()
    try:
        system_config.config["ssid"] = request.form["ssid"]
        system_config.store()
        try:
            with open("hostapd.conf", "w") as outfile:
                outfile.write("interface=wlan0" + os.linesep)
                outfile.write("ssid={}".format(request.form["ssid"]) + os.linesep)
                outfile.write("hw_mode=g" + os.linesep)
                outfile.write("channel=7" + os.linesep)
                outfile.write("macaddr_acl=0" + os.linesep)
                outfile.write("auth_algs=1" + os.linesep)
                outfile.write("ignore_broadcast_ssid=0" + os.linesep)
                outfile.write("wpa=2" + os.linesep)
                outfile.write(
                    "wpa_passphrase={}".format(request.form["psk"]) + os.linesep
                )
                outfile.write("wpa_key_mgmt=WPA-PSK" + os.linesep)
                outfile.write("wpa_pairwise=TKIP" + os.linesep)
                outfile.write("rsn_pairwise=CCMP" + os.linesep)

            subprocess.call(
                "sudo mv hostapd.conf /etc/hostapd/hostapd.conf", shell=True
            )
            subprocess.call("sudo systemctl restart hostapd", shell=True)

        except Exception as error:
            logging.error(error, exc_info=True)

    except Exception as error:
        logging.error(repr(error), exc_info=True)
    return jsonify(system_config.config)


@app.route("/configuration", methods=["GET", "POST"])
def configuration():
    system_config = Config.getInstance()
    if request.method == "POST":
        try:
            for field in request.form:
                if field == "advertise_name":
                    system_config.config[field] = request.form[field]
                    system_config.store()

                    with open("machine-info", "w") as outfile:
                        outfile.write(
                            "PRETTY_HOSTNAME={}".format(request.form[field])
                            + os.linesep
                        )
                    subprocess.call(
                        "sudo mv machine-info /etc/machine-info", shell=True
                    )
                    threading.Timer(
                        3.0,
                        lambda: subprocess.call("sudo reboot", shell=True),
                    ).start()
                else:
                    try:
                        system_config.config[field] = float(request.form[field])
                    except:
                        system_config.config[field] = request.form[field] == "true"
            logging.warning(json.dumps(system_config.config))
            system_config.store()
        except Exception as error:
            logging.error(repr(error), exc_info=True)
        ble_handler.update_configuration(json.dumps(system_config.config))
        return jsonify(system_config.config)
    else:
        return jsonify(system_config.config)


@app.route("/forcerelay", methods=["POST"])
def forcerelay():
    try:
        for variable in request.form:
            if variable == "fan-relay":
                peripheral_handler.fan_drive(request.form[variable] == "true")
            elif variable == "speed-relay":
                system_config = Config.getInstance()
                peripheral_handler.fan_speed(request.form[variable] == "true")
                system_config.config["fan_speed"] = (
                    peripheral_handler.speed_pin and "fast" or "slow"
                )
    except Exception as error:
        logging.error(repr(error), exc_info=True)
        return "Failed"
    return "Success"


@app.route("/systemtime", methods=["GET", "POST"])
def systemtime():
    if request.method == "POST":
        try:
            if "systemtime" in request.form:
                logging.warning(
                    "Updating system time from admin web - {}".format(
                        request.form["systemtime"]
                    )
                )
                subprocess.call(
                    "sudo date -s '{}'".format(request.form["systemtime"]), shell=True
                )
                time.sleep(1.0)
                subprocess.call("sudo date", shell=True)
                subprocess.call("sudo hwclock -w", shell=True)
            return jsonify({"systemtime": request.form["systemtime"]})
        except Exception as error:
            logging.error(repr(error), exc_info=True)
    else:
        now = datetime.now()  # current date and time
        date_time_str = now.strftime("%Y-%m-%dT%H:%M")
        return jsonify({"systemtime": date_time_str})


@app.route("/peripherals")
def get_peripherals():
    """"""
    result = dict()

    try:
        result["temperature"] = (
            peripheral_handler.grove_dht.temp != None
            and peripheral_handler.grove_dht.temp
            or "None"
        )
        result["humidity"] = (
            peripheral_handler.grove_dht.humi != None
            and peripheral_handler.grove_dht.humi
            or "None"
        )
        result["fan"] = peripheral_handler.fan
        result["speed"] = peripheral_handler.speed
        result["adc"] = peripheral_handler.mq2_adc
        result["air_quality"] = peripheral_handler.air_quality

    except Exception as error:
        logging.error(repr(error), exc_info=True)
    return jsonify(result)


@app.route("/schedules", methods=["GET", "POST"])
def schedules():
    try:
        schedule = Schedule.getInstance()
        if request.method == "POST":
            try:
                schedule_index = int(request.form["index"])
                schedule.schedules[schedule_index]["dayofweeks"] = request.form.getlist(
                    "dayofweeks[]"
                )
                schedule.schedules[schedule_index]["start"] = request.form["start"]
                schedule.schedules[schedule_index]["end"] = request.form["end"]
                schedule.schedules[schedule_index]["active"] = (
                    request.form["active"] == "true"
                )
                schedule.schedules[schedule_index]["fan"] = request.form["fan"]
                schedule.schedules[schedule_index]["speed"] = request.form["speed"]

                schedule.store()
            except Exception as error:
                logging.error(repr(error), exc_info=True)
            return jsonify(schedule.schedules)
        else:
            return jsonify(schedule.schedules)
    except Exception as error:
        logging.error(repr(error), exc_info=True)
        return "Failed"


###########################################################################


def loop_procedure():
    """"""
    notify_peripheral_time = int(time.time())
    notify_date_time = int(time.time())
    while True:
        try:
            if int(time.time()) - notify_peripheral_time >= 4:
                notify_peripheral_time = int(time.time())
                ble_handler.notify_peripherals(
                    "fan:{}, speed:{}, temp:{}, humi:{}, smoke:{}".format(
                        peripheral_handler.fan and "on" or "off",
                        peripheral_handler.speed and "fast" or "slow",
                        peripheral_handler.grove_dht.temp,
                        peripheral_handler.grove_dht.humi,
                        peripheral_handler.air_quality,
                    )
                )

            if int(time.time()) - notify_date_time >= 4:
                notify_date_time = int(time.time())
                ble_handler.notify_systemtime(datetime.now().strftime("%Y-%m-%dT%H:%M"))

            # Control logic
            if system_config.config["system_mode"]:

                #
                fan = False

                # Schedule check part
                scheules = Schedule.getInstance().schedules
                for schedule in scheules:
                    # If a schedule is activated
                    if schedule["active"]:
                        # Check whether dayofweek is in activated weekday range
                        current_time = datetime.now()
                        if current_time.weekday() in schedule["dayofweeks"]:
                            start_time = datetime(
                                current_time.year,
                                current_time.month,
                                current_time.day,
                                int(schedule["start"].split(":")[0]),
                                int(schedule["start"].split(":")[1]),
                            )

                            end_time = datetime(
                                current_time.year,
                                current_time.month,
                                current_time.day,
                                int(schedule["end"].split(":")[0]),
                                int(schedule["end"].split(":")[1]),
                            )

                            diff_from_start = current_time - start_time
                            diff_to_end = end_time - current_time

                            if diff_from_start.days == 0 and diff_to_end.days == 0:
                                fan = schedule["fan"] == "on"
                                break

                # check fan relay condition
                if system_config.config["temperature_monitor"]:
                    if peripheral_handler.grove_dht.temp != None:
                        if (
                            peripheral_handler.grove_dht.temp
                            > system_config.config["temperature_threshold"]
                        ):
                            fan = True

                # Drive Fan relay
                if fan != peripheral_handler.fan:
                    peripheral_handler.fan_drive(fan)

            else:
                pass
        except Exception as error:
            logging.error(repr(error), exc_info=True)
        time.sleep(1.0)


#######################################################################################


def force_relay_callback(payload):
    logging.warning("BLE force relay: {}".format(payload))
    command = json.loads(payload)
    configuration = Config.getInstance()
    if not configuration.config["system_mode"]:
        for field in command:
            if field == "fan":
                peripheral_handler.fan_drive(command["fan"] == "on")
            elif field == "speed":
                peripheral_handler.fan_drive(command["speed"] == "fast")


def update_config_callback(payload):
    try:
        logging.warning("BLE update configuration: {}".format(payload))
        new_config = json.loads(payload)
        configuration = Config.getInstance()
        for field in new_config:
            configuration.config[field] = new_config[field]
        configuration.store()
    except Exception as error:
        logging.error(repr(error), exc_info=True)


def update_schedule_callback(payload):
    try:
        logging.warning("BLE update schedule: {}".format(payload))
        schedules = json.loads(payload)
        schedule = Schedule.getInstance()
        schedule.schedules = schedules
        schedule.store()
    except Exception as error:
        logging.error(repr(error), exc_info=True)


def ble_set_datetime_callback(payload):
    logging.info(payload)
    try:
        logging.warning(
            "Updating system time from BLE characteristic - {}".format(payload)
        )
        subprocess.call("sudo date -s '{}'".format(payload), shell=True)
        time.sleep(1.0)
        subprocess.call("sudo date", shell=True)
        subprocess.call("sudo hwclock -w", shell=True)

    except Exception as error:
        logging.error(repr(error), exc_info=True)


#######################################################################################

if __name__ == "__main__":
    try:
        #
        peripheral_handler.initialize()
        #
        ble_handler.initialize(
            force_relay_callback,
            update_config_callback,
            update_schedule_callback,
            ble_set_datetime_callback,
        )

        ble_handler.update_configuration(json.dumps(Config.getInstance().config))
        ble_handler.update_schedule(json.dumps(Schedule.getInstance().schedules))

        peripheral_handler.fan_speed(system_config.config["fan_speed"] == "fast")

        #
        threading.Thread(target=loop_procedure).start()
        app.run(
            host="0.0.0.0", port=80, debug=False, threaded=True, extra_files=extra_files
        )
    except KeyboardInterrupt:  # If CTRL+C is pressed, exit cleanly:
        logging.warning("CTRL+C key presses, will exit soon")
    except Exception as error:
        logging.error(repr(error), exc_info=True)
    finally:
        peripheral_handler.terminate()
        ble_handler.terminate()
        time.sleep(2.0)
