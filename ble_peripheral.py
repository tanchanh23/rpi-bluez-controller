import sys
import threading
import time
import logging

import dbus, dbus.mainloop.glib
from gi.repository import GLib
from advertisement import Advertisement
from advertisement import register_ad_cb, register_ad_error_cb
from gatt_server import (
    Service,
    Characteristic,
    CharacteristicUserDescriptionDescriptor,
    Descriptor,
)
from gatt_server import register_app_cb, register_app_error_cb

BLUEZ_SERVICE_NAME = "org.bluez"
DBUS_OM_IFACE = "org.freedesktop.DBus.ObjectManager"
LE_ADVERTISING_MANAGER_IFACE = "org.bluez.LEAdvertisingManager1"
GATT_MANAGER_IFACE = "org.bluez.GattManager1"
GATT_CHRC_IFACE = "org.bluez.GattCharacteristic1"
ELEVATOR_SERVICE_UUID = "0d7e0001-3e26-454e-9669-1a8b67b52161"
PERIPHERALS_CHARACTERISTIC_UUID = "0d7e0002-b5a3-f393-e0a9-e50e24dcca9e"
CONFIGURATION_CHARACTERISTIC_UUID = "0d7e0003-b5a3-f393-e0a9-e50e24dcca9e"
FORCERELAY_CHARACTERISTIC_UUID = "0d7e0004-b5a3-f393-e0a9-e50e24dcca9e"
SELECT_SCHEDULE_CHARACTERISTIC_UUID = "0d7e0005-b5a3-f393-e0a9-e50e24dcca9e"
SYSTEMTIME_CHARACTERISTIC_UUID = "0d7e0006-b5a3-f393-e0a9-e50e24dcca9e"

UART_RX_CHARACTERISTIC_UUID = "0d7e0002-b5a3-f393-e0a9-e50e24dcca9e"
UART_TX_CHARACTERISTIC_UUID = "0d7e0003-b5a3-f393-e0a9-e50e24dcca9e"


class TxCharacteristic(Characteristic):
    def __init__(self, bus, index, service):
        Characteristic.__init__(
            self, bus, index, UART_TX_CHARACTERISTIC_UUID, ["notify"], service
        )
        self.notifying = False

    def send_tx(self, s):
        if not self.notifying:
            return
        value = []
        for c in s:
            value.append(dbus.Byte(c.encode()))
        self.PropertiesChanged(GATT_CHRC_IFACE, {"Value": value}, [])

    def StartNotify(self):
        if self.notifying:
            return
        self.notifying = True

    def StopNotify(self):
        if not self.notifying:
            return
        self.notifying = False


class RxCharacteristic(Characteristic):
    def __init__(self, bus, index, service):
        Characteristic.__init__(
            self, bus, index, UART_RX_CHARACTERISTIC_UUID, ["write"], service
        )

    def WriteValue(self, value, options):
        print("remote: {}".format(bytearray(value).decode()))


class PeripheralChrc(Characteristic):
    """
    """

    def __init__(self, bus, index, service):
        Characteristic.__init__(
            self, bus, index, PERIPHERALS_CHARACTERISTIC_UUID, ["notify"], service
        )
        self.notifying = False

    def notify(self, s):
        if not self.notifying:
            return
        value = []
        for c in s:
            value.append(dbus.Byte(c.encode()))
        self.PropertiesChanged(GATT_CHRC_IFACE, {"Value": value}, [])

    def StartNotify(self):
        if self.notifying:
            return
        self.notifying = True

    def StopNotify(self):
        if not self.notifying:
            return
        self.notifying = False


class ForceRelaysChrc(Characteristic):
    """
    """

    def __init__(self, bus, index, service):
        Characteristic.__init__(
            self, bus, index, FORCERELAY_CHARACTERISTIC_UUID, ["write"], service,
        )
        self._force_callback = None

    def set_force_callback(self, callback):
        self._force_callback = callback

    def WriteValue(self, value, options):
        try:
            logging.info("Force relay: ".format(repr(value)))
            if self._write_configure_callback != None:
                self._force_callback(bytearray(value).decode())
        except Exception as error:
            logging.error(repr(error), exc_info=True)


class ConfigurationChrc(Characteristic):
    """
    """

    def __init__(self, bus, index, service):
        Characteristic.__init__(
            self,
            bus,
            index,
            CONFIGURATION_CHARACTERISTIC_UUID,
            ["read", "write", "writable-auxiliaries"],
            service,
        )
        self._write_configure_callback = None
        self.value = []

    def ReadValue(self, options):
        try:
            logging.info("Read configuration: ".format(repr(self.value)))
        except Exception as error:
            logging.error(repr(error), exc_info=True)
        return self.value

    def WriteValue(self, value, options):
        try:
            logging.info("Write configuration: ".format(repr(value)))
            self.value = value
            if self._write_configure_callback != None:
                self._write_configure_callback(bytearray(value).decode())
        except Exception as error:
            logging.error(repr(error), exc_info=True)

    def set_write_configure_callback(self, callback):
        self._write_configure_callback = callback

    def update(self, payload):
        self.value = []
        for c in payload:
            self.value.append(dbus.Byte(c.encode()))


class ScheduleChrc(Characteristic):
    """
    """

    def __init__(self, bus, index, service):
        Characteristic.__init__(
            self,
            bus,
            index,
            SELECT_SCHEDULE_CHARACTERISTIC_UUID,
            ["read", "write", "writable-auxiliaries"],
            service,
        )
        self.schedules = []

    def ReadValue(self, options):
        try:
            logging.info("Read schedules: ".format(repr(self.schedules)))
        except Exception as error:
            logging.error(repr(error), exc_info=True)
        return self.schedules

    def WriteValue(self, value, options):
        try:
            logging.info("Write schedules: ".format(repr(schedules)))
            self.schedules = value
            if self._write_schedule_callback != None:
                self._write_schedule_callback(bytearray(value).decode())
        except Exception as error:
            logging.error(repr(error), exc_info=True)

    def set_write_schedule_callback(self, callback):
        self._write_schedule_callback = callback

    def update(self, payload):
        try:
            self.schedules = []
            for c in payload:
                self.schedules.append(dbus.Byte(c.encode()))
        except Exception as error:
            logging.error(repr(error), exc_info=True)


class SystemTimeChrc(Characteristic):
    """
    """

    def __init__(self, bus, index, service):
        Characteristic.__init__(
            self,
            bus,
            index,
            SYSTEMTIME_CHARACTERISTIC_UUID,
            ["notify", "write", "writable-auxiliaries"],
            service,
        )
        self._set_datetime_callback = None
        self.notifying = False

    def notify(self, s):
        if not self.notifying:
            return
        value = []
        for c in s:
            value.append(dbus.Byte(c.encode()))
        self.PropertiesChanged(GATT_CHRC_IFACE, {"Value": value}, [])

    def StartNotify(self):
        if self.notifying:
            return
        self.notifying = True

    def StopNotify(self):
        if not self.notifying:
            return
        self.notifying = False

    def WriteValue(self, value, options):
        try:
            logging.info("Set system time: {}".format(repr(value)))
            if self._set_datetime_callback != None:
                self._set_datetime_callback(bytearray(value).decode())
        except Exception as error:
            logging.error(repr(error), exc_info=True)

    def set_datetime_callback(self, callback):
        self._set_datetime_callback = callback


class ElevatorService(Service):
    def __init__(self, bus, index):
        Service.__init__(self, bus, index, ELEVATOR_SERVICE_UUID, True)
        self.add_characteristic(PeripheralChrc(bus, 0, self))
        self.add_characteristic(ConfigurationChrc(bus, 1, self))
        self.add_characteristic(ForceRelaysChrc(bus, 2, self))
        self.add_characteristic(ScheduleChrc(bus, 3, self))
        self.add_characteristic(SystemTimeChrc(bus, 4, self))


class ElevatorApplication(dbus.service.Object):
    def __init__(self, bus):
        self.path = "/"
        self.services = []
        dbus.service.Object.__init__(self, bus, self.path)
        self.add_service(ElevatorService(bus, 0))

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service(self, service):
        self.services.append(service)

    @dbus.service.method(DBUS_OM_IFACE, out_signature="a{oa{sa{sv}}}")
    def GetManagedObjects(self):
        response = {}
        for service in self.services:
            response[service.get_path()] = service.get_properties()
            chrcs = service.get_characteristics()
            for chrc in chrcs:
                response[chrc.get_path()] = chrc.get_properties()
        return response


class ElevatorAdvertisement(Advertisement):
    def __init__(self, bus, index, local_name):
        Advertisement.__init__(self, bus, index, "peripheral")
        self.add_service_uuid(ELEVATOR_SERVICE_UUID)
        self.add_local_name(local_name)
        self.include_tx_power = True


def find_adapter(bus):
    remote_om = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, "/"), DBUS_OM_IFACE)
    objects = remote_om.GetManagedObjects()
    for o, props in objects.items():
        if LE_ADVERTISING_MANAGER_IFACE in props and GATT_MANAGER_IFACE in props:
            return o
        print("Skip adapter:", o)
    return None


class ElevatorAirBlePeripheral(threading.Thread):
    def __init__(self, local_name):
        threading.Thread.__init__(self)
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus()
        adapter = find_adapter(bus)
        if not adapter:
            raise Exception("BLE adapter not found")

        service_manager = dbus.Interface(
            bus.get_object(BLUEZ_SERVICE_NAME, adapter), GATT_MANAGER_IFACE
        )
        ad_manager = dbus.Interface(
            bus.get_object(BLUEZ_SERVICE_NAME, adapter), LE_ADVERTISING_MANAGER_IFACE
        )

        self.app = ElevatorApplication(bus)
        self.adv = ElevatorAdvertisement(bus, 0, local_name)

        self.mainloop = GLib.MainLoop()

        service_manager.RegisterApplication(
            self.app.get_path(),
            {},
            reply_handler=register_app_cb,
            error_handler=register_app_error_cb,
        )
        ad_manager.RegisterAdvertisement(
            self.adv.get_path(),
            {},
            reply_handler=register_ad_cb,
            error_handler=register_ad_error_cb,
        )
        self.start()

    def notify_peripherals(self, payload):
        self.app.services[0].characteristics[0].notify(payload)

    def initialize(
        self,
        force_callback,
        update_config_callback,
        update_schedule_callback,
        set_datetime_callback,
    ):
        self.app.services[0].characteristics[1].set_write_configure_callback(
            update_config_callback
        )
        self.app.services[0].characteristics[2].set_force_callback(force_callback)
        self.app.services[0].characteristics[3].set_write_schedule_callback(
            update_schedule_callback
        )
        self.app.services[0].characteristics[4].set_datetime_callback(
            set_datetime_callback
        )

    def update_configuration(self, payload):
        self.app.services[0].characteristics[1].update(payload)

    def update_schedule(self, payload):
        self.app.services[0].characteristics[3].update(payload)

    def notify_systemtime(self, payload):
        self.app.services[0].characteristics[4].notify(payload)

    def run(self):
        self.mainloop.run()

    def terminate(self):
        self.adv.Release()
