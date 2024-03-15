const asyncForEach = async (array, callback) => {
  for (let index = 0; index < array.length; index += 1) {
    await callback(array[index], index, array);
  }
};

var system_mode = true;

$(function peripheral() {
  $.getJSON('/peripherals', function(result) {
    console.log(result);

    $(`#mq2-adc`).html(result['adc']);
    $(`#mq2-ppm`).html(result['air_quality']);

    $(`#dht-temp`).html(result['temperature']);
    $(`#dht-humi`).html(result['humidity']);

    $('#fan-relay').bootstrapToggle('enable');
    $(`#fan-relay`).bootstrapToggle(result['fan'] ? 'on' : 'off', true);
    $(`#speed-relay`).bootstrapToggle(result['speed'] ? 'on' : 'off', true);

    if (system_mode === true) {
      $('#fan-relay').bootstrapToggle('disable');
    }
    setTimeout(function() {
      peripheral();
    }, 5000);
  });
});

$(document).ready(async () => {
  console.log(`Ready`);
  await initialize_schedule();
  await display_config();
  await read_systemtime();
});

const change_relay_switch = async (id) => {
  const toggle_value = $(`#${id}`).prop('checked') === true;
  var command = {};
  command[id] = toggle_value;

  const result = await $.ajax({
    url: '/forcerelay',
    type: 'POST',
    data: command,
  });
};

const change_ble_name = async () => {
  const new_ble_name = $(`#blename`).val();
  const {value: confirmed} = await Swal.fire({
    title: 'Are you sure?',
    text: `You are going to change BLE name to [${new_ble_name}]?`,
    type: 'warning',
    showCancelButton: true,
    confirmButtonText: 'Yes!',
  });
  if (!confirmed) return;

  await Swal.fire({
    text: `Service will be restarted!`,
    icon: `info`,
  });

  const result = await $.ajax({
    url: '/configuration',
    type: 'POST',
    data: {advertise_name: new_ble_name},
  });
};

const change_configuration = async (id) => {
  var config = {};
  if (id === `system-mode`) {
    const toggle_value = $(`#${id}`).prop('checked') === true;
    config[`system_mode`] = toggle_value;
  } else if (id === `smoke-enable`) {
    const toggle_value = $(`#${id}`).prop('checked') === true;
    config[`smoke_detection`] = toggle_value;
  } else if (id === `temp-monitor`) {
    const toggle_value = $(`#${id}`).prop('checked') === true;
    config[`temperature_monitor`] = toggle_value;
  } else if (id === `temp-threshold`) {
    const value = $(`#${id}`).val();
    config[`temperature_threshold`] = value;
  }

  const result = await $.ajax({
    url: '/configuration',
    type: 'POST',
    data: config,
  });

  display_config();
};

const display_config = async () => {
  const config = await $.ajax({
    url: '/configuration',
  });

  $(`#blename`).val(config.advertise_name);
  $(`#system-mode`).bootstrapToggle(config.system_mode ? 'on' : 'off', true);
  $(`#smoke-enable`)
      .bootstrapToggle(config.smoke_detection ? 'on' : 'off', true);
  $(`#temp-monitor`)
      .bootstrapToggle(config.temperature_monitor ? 'on' : 'off', true);
  $(`#temp-threshold`).val(config.temperature_threshold);
  $(`#wifi-ssid`).val(config.ssid);

  $(`#app-version`).html(config.version);

  system_mode = Boolean(config.system_mode);
  if (config.system_mode === true) {
    $('#fan-relay').bootstrapToggle('disable');
  } else {
    $('#fan-relay').bootstrapToggle('enable');
  }
};

$(`#update-time-btn`).click(async () => {
  try {
    const result = await $.ajax({
      url: '/systemtime',
      type: 'POST',
      data: {systemtime: $(`#settime`).val()},
    });
  } catch (err) {
  }
});

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const read_systemtime = async () => {
  try {
    const result = await $.ajax({
      url: '/systemtime',
    });
    $(`#localtime`).val(result.systemtime);
  } catch (err) {
    console.log(`Failed from GET API ${err}`);
  }
  await delay(4000);
  await read_systemtime();
};

const update_hostspot = async () => {
  const ssid = $(`#wifi-ssid`).val();
  const psk = $(`#wifi-psk`).val();

  if (ssid.length < 6) {
    await Swal.fire({
      text: `SSID should be minimum 6 characteristics!`,
      icon: `error`,
    });
    return;
  }

  if (psk.length < 6) {
    await Swal.fire({
      text: `PSK should be minimum 8 characteristics!`,
      icon: `error`,
    });
    return;
  }

  const {value: confirmed} = await Swal.fire({
    title: 'Are you sure?',
    text: `You are going to change WiFi hotspot?`,
    type: 'warning',
    showCancelButton: true,
    confirmButtonText: 'Yes!',
  });
  if (!confirmed) return;

  const result = await $.ajax({
    url: '/hostspot',
    type: 'POST',
    data: {ssid: ssid, psk: psk},
  });
  await Swal.fire({
    text: `Hostapd service will be rebooted!`,
    icon: 'success',
  });
};

const update_schedule = async (index) => {
  const {value: confirmed} = await Swal.fire({
    title: `Are you sure?`,
    text: `Maybe schedule will be updated!`,
    icon: `warning`,
    showCancelButton: true,
    confirmButtonText: 'Yes!',
  });
  if (!confirmed) return;

  let schedule = {};
  schedule['index'] = index;

  schedule['active'] =
      $(`#schedule_activate_${index}`).prop('checked') === true;
  schedule['fan'] =
      $(`#schedule_fan_${index}`).prop('checked') === true ? `on` : `off`;
  schedule['speed'] =
      $(`#schedule_speed_${index}`).prop('checked') === true ? `fast` : `slow`;

  schedule['dayofweeks'] = [];
  for (var idx = 0; idx < 7; idx++) {
    if ($(`#schedule_${idx}_${index}`).prop('checked') === true) {
      schedule['dayofweeks'].push(idx.toString());
    }
  }

  schedule['start'] = $(`#schedule_starttime_${index}`).val();
  schedule['end'] = $(`#schedule_endtime_${index}`).val();

  console.log(schedule);
  const result = await $.ajax({
    url: '/schedules',
    type: 'POST',
    data: schedule,
  });
};

const initialize_schedule = async () => {
  const schedules = await $.ajax({
    url: '/schedules',
  });

  await asyncForEach(schedules, async (schedule, index) => {
    $('#schedules').append(`<div class="card card-default mt-3 mb-3">
              <div class="card-header h5 bg-white">
                <div class="row justify-content-between">
                  <span class="ml-2" id="schedule_id_${index}">
                  ${schedule.id}</span>
                  <div class="row mr-2">
                    <input
                      type="checkbox"
                      data-toggle="toggle"
                      data-size="sm"
                      data-onstyle="success"
                      data-on="On"
                      data-off="Off"
                      data-style="ios"
                      class="col"
                      id="schedule_activate_${index}"
                      ${schedule.fan === 'on' ? 'checked' : ''}
                    />
                    <input type="button" class="ml-2 btn btn-primary btn-sm" value="Update" 
                    onclick="update_schedule(${index})"/>
                  </div>
                </div>
              </div>
              <div class="card-body">
                <div class="row form-inline">
                  <label class="col-sm-2 col-4 text-left">Start:</label>
                  <input type="time" required class="col-sm-4 col-8" 
                  id="schedule_starttime_${index}"
                  value="${schedule.start}" />

                  <label class="col-sm-2 col-4 text-left">End:</label>
                  <input type="time" required class="col-sm-4 col-8" 
                  id="schedule_endtime_${index}"
                  value="${schedule.end}"/>
                </div>

                <label class="text-left mt-4">Select Date</label>
                <div class="row form-inline">
                  <div class="col-sm col-3">
                    <input
                      type="checkbox"
                      data-toggle="toggle"
                      data-size="xs"
                      data-onstyle="danger"
                      data-on="Mon"
                      data-off="Mon"
                      data-style="ios"
                      class="col"
                      id="schedule_0_${index}"
                      ${schedule.dayofweeks.includes(`0`) ? 'checked' : ''}
                    />
                  </div>
                  <div class="col-sm col-3">
                    <input
                      type="checkbox"
                      data-toggle="toggle"
                      data-size="xs"
                      data-onstyle="danger"
                      data-on="Tue"
                      data-off="Tue"
                      data-style="ios"
                      class="col"
                      id="schedule_1_${index}"
                      ${schedule.dayofweeks.includes(`1`) ? 'checked' : ''}
                    />
                  </div>
                  <div class="col-sm col-3">
                    <input
                      type="checkbox"
                      data-toggle="toggle"
                      data-size="xs"
                      data-onstyle="danger"
                      data-on="Wed"
                      data-off="Wed"
                      data-style="ios"
                      id="schedule_2_${index}"
                      ${schedule.dayofweeks.includes(`2`) ? 'checked' : ''}
                    />
                  </div>

                  <div class="col-sm col-3">
                    <input
                      type="checkbox"
                      data-toggle="toggle"
                      data-size="xs"
                      data-onstyle="danger"
                      data-on="Thu"
                      data-off="Thu"
                      data-style="ios"
                      id="schedule_3_${index}"
                      ${schedule.dayofweeks.includes(`3`) ? 'checked' : ''}
                    />
                  </div>

                  <div class="col-sm col-3">
                    <input
                      type="checkbox"
                      data-toggle="toggle"
                      data-size="xs"
                      data-onstyle="danger"
                      data-on="Fri"
                      data-off="Fri"
                      data-style="ios"
                      class="col"
                      id="schedule_4_${index}"
                      ${schedule.dayofweeks.includes(`4`) ? 'checked' : ''}
                    />
                  </div>
                  <div class="col-sm col-3">
                    <input
                      type="checkbox"
                      data-toggle="toggle"
                      data-size="xs"
                      data-onstyle="danger"
                      data-on="Sat"
                      data-off="Sat"
                      data-style="ios"
                      class="col"
                      id="schedule_5_${index}"
                      ${schedule.dayofweeks.includes(`5`) ? 'checked' : ''}
                    />
                  </div>
                  <div class="col-sm col-3">
                    <input
                      type="checkbox"
                      data-toggle="toggle"
                      data-size="xs"
                      data-onstyle="danger"
                      data-on="Sun"
                      data-off="Sun"
                      data-style="ios"
                      class="col"
                      id="schedule_6_${index}"
                      ${schedule.dayofweeks.includes(`6`) ? 'checked' : ''}
                    />
                  </div>
                </div>

                <div class="row form-inline mt-4">
                  <div class="col-sm row form-inline">
                    <div class="text-center col-sm-2 col-4">
                      <i class="fas fa-fan fa-2x"></i>
                    </div>
                    <div class="text-center col-sm-4 col-4">
                      Fan
                    </div>
                    <div class="text-right col-sm-6 col-4">
                      <input
                        type="checkbox"
                        data-toggle="toggle"
                        data-size="sm"
                        data-onstyle="danger"
                        data-on="On"
                        data-off="Off"
                        data-style="ios"
                        id="schedule_fan_${index}"
                        ${schedule.fan === 'on' ? 'checked' : ''}
                      />
                    </div>
                  </div>

                  <div class="col-sm row form-inline">
                    <div class="text-center col-sm-2 col-4">
                      <i class="fas fa-tachometer-alt fa-2x"></i>
                    </div>
                    <div class="text-center col-sm-4 col-4">
                      Speed
                    </div>
                    <div class="text-right col-sm-6 col-4">
                      <input
                        type="checkbox"
                        data-toggle="toggle"
                        data-size="sm"
                        data-onstyle="warning"
                        data-offstyle="success"
                        data-on="Fast"
                        data-off="Slow"
                        data-style="ios"
                        id="schedule_speed_${index}"
                        ${schedule.speed === 'fast' ? 'checked' : ''}
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>`);
  });



  $('[data-toggle=\'toggle\']').bootstrapToggle('destroy');
  $('[data-toggle=\'toggle\']').bootstrapToggle();
};
