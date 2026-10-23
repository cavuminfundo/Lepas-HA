"""Entity naming: the Italian keys this integration grew with, and their English names.

Why this table exists instead of 110 edited declarations. The keys were derived from
Italian entity names, so they ended up in two places at once: the translation lookup
and the `entity_id`. Renaming them at the declaration sites would spread the change
over thirteen files and make it unreviewable; here it is one table, one line per
entity, readable next to the old name it replaces.

The English names are not invented. Every one of them was already written and
reviewed in `translations/en.json`; this is that file's own wording, slugified.

Two English names appear twice - "Cool everything" and "Heat everything" - because a
button and a switch carry each. That is not a collision: entity ids are separated by
the entity type (`button.` vs `switch.`) and Home Assistant namespaces translation
keys per type as well. It looks like a bug in review, so it is said here.
"""
from __future__ import annotations

# Prefix of the object_id: default entity prefix for native Lepas integration.
ID_PREFIX = "lepas"

# old translation key (Italian, derived from the entity name) -> new key (English).
# The `entity_id` follows: f"{ID_PREFIX}_{new key}".
ENGLISH_KEYS: dict[str, str] = {
    # --- binary_sensor ---
    "a_casa":                         "at_home",              # At home
    "alta_tensione_attiva":           "high_voltage_active",  # High voltage active
    "auto_sveglia":                   "car_awake",            # Car awake
    "avviso_carburante_basso":        "low_fuel_warning",     # Low fuel warning
    "avviso_gomma_ant_dx":            "tire_warning_front_right",# Tire warning front right
    "avviso_gomma_ant_sx":            "tire_warning_front_left",# Tire warning front left
    "avviso_gomma_post_dx":           "tire_warning_rear_right",# Tire warning rear right
    "avviso_gomma_post_sx":           "tire_warning_rear_left",# Tire warning rear left
    "avviso_ricarica_necessaria":     "charge_needed_warning",# Charge needed warning
    "batteria_scarica":               "low_battery",          # Low battery
    "cofano":                         "hood",                 # Hood
    "connessa":                       "connection",           # Connection
    "finestrino_anteriore_dx":        "front_right_window",   # Front right window
    "finestrino_anteriore_sx":        "front_left_window",    # Front left window
    "finestrino_posteriore_dx":       "rear_right_window",    # Rear right window
    "finestrino_posteriore_sx":       "rear_left_window",     # Rear left window
    "motore":                         "engine",               # Engine
    "porta_anteriore_dx":             "front_right_door",     # Front right door
    "porta_anteriore_sx":             "front_left_door",      # Front left door
    "porta_posteriore_dx":            "rear_right_door",      # Rear right door
    "porta_posteriore_sx":            "rear_left_door",       # Rear left door
    "portellone_in_movimento":        "tailgate_moving",      # Tailgate moving
    "purificazione_aria":             "air_purification",     # Air purification
    "riscaldamento_parabrezza":       "windshield_heating",   # Windshield heating
    "sessione":                       "session",              # Session
    "spina_ricarica":                 "charging_cable",       # Charging cable
    "tendina_tetto":                  "sunroof_blind",        # Sunroof blind
    # --- button ---
    "aggiorna_posizione":             "refresh_location",     # Refresh location
    "aggiorna_stato_completo":        "refresh_full_status",  # Refresh full status
    "antifurto_off":                  "alarm_off",            # Alarm off
    "antifurto_on":                   "alarm_on",             # Alarm on
    "clima_raffredda_off":            "cool_everything_off",  # Cool everything off
    "clima_raffredda_on":             "cool_everything",      # Cool everything
    "clima_riscalda_off":             "heat_everything_off",  # Heat everything off
    "clima_riscalda_on":              "heat_everything",      # Heat everything
    "conferma_otp":                   "confirm_otp",          # Confirm OTP
    "finestrini_ventila":             "vent_windows",         # Vent windows
    "tetto_ventila":                  "vent_sunroof",         # Vent sunroof
    "localizza":                      "locate_car_gps",       # Locate car (GPS)
    "richiedi_codice_otp":            "request_otp_code",     # Request OTP code
    "sveglia_auto":                   "wake_car",             # Wake car
    "trova_auto":                     "find_car_flash_lights",# Find car (flash lights)
    # --- climate ---
    "clima":                          "climate",              # Climate
    # --- cover ---
    "baule":                          "trunk",                # Trunk
    "finestrini":                     "windows",              # Windows
    "tetto":                          "sunroof",              # Sunroof
    # --- device_tracker ---
    "posizione":                      "location",             # Location
    # --- lock ---
    "serratura":                      "lock",                 # Lock
    # --- number ---
    "durata_clima":                   "climate_duration",     # Climate duration
    "ricarica_durata":                "charge_duration",      # Charge duration
    # --- sensor ---
    # Solo su BEV confermata: nascono dopo, quando le capability sono state sondate,
    # quindi non c'erano nel registro da cui questa tabella e' stata generata. Il primo
    # rapporto da un'auto elettrica vera li ha trovati ancora in italiano.
    "potenza_di_ricarica":            "charging_power",             # Charging power
    "autonomia_wltp":                 "wltp_range",                 # WLTP range
    "efficienza_elettrica_mi_kwh":    "electric_efficiency_mi_kwh", # Electric efficiency (mi/kWh)
    "autonomia_benzina":              "fuel_range",           # Fuel range
    "autonomia_benzina_miglia":       "petrol_range_miles",   # Petrol range (miles)
    "autonomia_elettrica":            "electric_range",       # Electric range
    "autonomia_totale":               "total_range",          # Total range
    "batteria":                       "battery",              # Battery
    "carburante_residuo":             "fuel_remaining",       # Fuel remaining
    "chilometraggio_ibrido":          "hybrid_mileage",       # Hybrid mileage
    "consumo_medio_carburante":       "average_fuel_consumption",# Average fuel consumption
    "consumo_medio_elettrico":        "average_energy_consumption",# Average energy consumption
    "corrente_batteria_hv":           "hv_battery_current",   # HV battery current
    "dati_auto_aggiornati":           "car_data_updated",     # Car data updated
    "energia_ricarica_a_casa":        "home_charging_energy", # Home charging energy
    "energia_ricarica_fuori_casa":    "away_charging_energy", # Away charging energy
    "esito_comando":                  "command_result",       # Command result
    "esito_sonda_posizione":          "location_probe_result",# Location probe result
    "esito_sveglia":                  "wake_up_result",       # Wake-up result
    "odometro":                       "odometer",             # Odometer
    "partenza_programmata":           "scheduled_departure",  # Scheduled departure
    "presa_ricarica_rapida":          "fast_charging_port",   # Fast charging port
    "pressione_gomma_ant_dx":         "tire_pressure_front_right",# Tire pressure front right
    "pressione_gomma_ant_sx":         "tire_pressure_front_left",# Tire pressure front left
    "pressione_gomma_post_dx":        "tire_pressure_rear_right",# Tire pressure rear right
    "pressione_gomma_post_sx":        "tire_pressure_rear_left",# Tire pressure rear left
    "ricarica_programmata_stato":     "scheduled_charging_status",# Scheduled charging status
    "riscaldamento_sedile_post_centrale": "rear_center_seat_heating",# Rear center seat heating
    "stato_ricarica":                 "charging_status",      # Charging status
    "stato_sessione":                 "session_status",       # Session status
    "temperatura_gomma_ant_dx":       "tire_temperature_front_right",# Tire temperature front right
    "temperatura_gomma_ant_sx":       "tire_temperature_front_left",# Tire temperature front left
    "temperatura_gomma_post_dx":      "tire_temperature_rear_right",# Tire temperature rear right
    "temperatura_gomma_post_sx":      "tire_temperature_rear_left",# Tire temperature rear left
    "temperatura_impostata_dx":       "set_temperature_right",# Set temperature right
    "temperatura_impostata_sx":       "set_temperature_left", # Set temperature left
    "tempo_di_ricarica_residuo":      "remaining_charge_time",# Remaining charge time
    "tensione_batteria_hv":           "hv_battery_voltage",   # HV battery voltage
    "tetto_stato_movimento":          "sunroof_movement_state",# Sunroof movement state
    "ultima_posizione":               "last_position",        # Last position
    "ultima_sveglia":                 "last_wake_up",         # Last wake-up
    "ultimo_contatto":                "last_seen",            # Last seen
    "velocita":                       "speed",                # Speed
    "ventilazione_sedile_post_centrale": "rear_center_seat_ventilation",# Rear center seat ventilation
    # --- switch ---
    "aggiornamento_automatico":       "automatic_updates",    # Automatic updates
    "antifurto":                      "alarm",                # Alarm
    "disappannamento_parabrezza":     "windshield_defog",     # Windshield defog
    "raffredda_tutto":                "cool_everything",      # Cool everything
    "ricarica":                       "charging",             # Charging
    "ricarica_programmata":           "scheduled_charging",   # Scheduled charging
    "riscalda_tutto":                 "heat_everything",      # Heat everything
    "riscaldamento_lunotto":          "rear_window_heating",  # Rear window heating
    "riscaldamento_sedile_guida":     "driver_seat_heating",  # Driver seat heating
    "riscaldamento_sedile_passeggero": "passenger_seat_heating",# Passenger seat heating
    "riscaldamento_sedile_post_dx":   "rear_right_seat_heating",# Rear right seat heating
    "riscaldamento_sedile_post_sx":   "rear_left_seat_heating",# Rear left seat heating
    "riscaldamento_volante":          "steering_wheel_heating",# Steering wheel heating
    "sbrinamento_parabrezza":         "windshield_defrost",   # Windshield defrost
    "ventilazione_sedile_guida":      "driver_seat_ventilation",# Driver seat ventilation
    "ventilazione_sedile_passeggero": "passenger_seat_ventilation",# Passenger seat ventilation
    "ventilazione_sedile_post_dx":    "rear_right_seat_ventilation",# Rear right seat ventilation
    "ventilazione_sedile_post_sx":    "rear_left_seat_ventilation",# Rear left seat ventilation
    # --- text ---
    "codice_otp":                     "otp_code",             # OTP code
    # --- time ---
    "ricarica_orario_di_inizio":      "charge_start_time",    # Charge start time
}


# (piattaforma, suffisso unique_id) -> entity_id canonico Lepas.
# Indicizzata sul suffisso e non sulla chiave di traduzione: le due cose non coincidono.
CANON_ENTITY_ID: dict[tuple[str, str], str] = {
    ("binary_sensor", "airPurification"):               "binary_sensor.lepas_air_purification",
    ("binary_sensor", "at_home"):                       "binary_sensor.lepas_at_home",
    ("binary_sensor", "awake"):                         "binary_sensor.lepas_car_awake",
    ("binary_sensor", "backLeftDoor"):                  "binary_sensor.lepas_rear_left_door",
    ("binary_sensor", "backLeftWindowState"):           "binary_sensor.lepas_rear_left_window",
    ("binary_sensor", "backRightDoor"):                 "binary_sensor.lepas_rear_right_door",
    ("binary_sensor", "backRightWindowState"):          "binary_sensor.lepas_rear_right_window",
    ("binary_sensor", "chargeGunState"):                "binary_sensor.lepas_charging_cable",
    ("binary_sensor", "engineState"):                   "binary_sensor.lepas_engine",
    ("binary_sensor", "fWinHeatingState"):              "binary_sensor.lepas_windshield_heating",
    ("binary_sensor", "frontLeftDoor"):                 "binary_sensor.lepas_front_left_door",
    ("binary_sensor", "frontLeftWindowState"):          "binary_sensor.lepas_front_left_window",
    ("binary_sensor", "frontRightDoor"):                "binary_sensor.lepas_front_right_door",
    ("binary_sensor", "frontRightWindowState"):         "binary_sensor.lepas_front_right_window",
    ("binary_sensor", "hood"):                          "binary_sensor.lepas_hood",
    ("binary_sensor", "liftgateOperateState"):          "binary_sensor.lepas_tailgate_moving",
    ("binary_sensor", "online"):                        "binary_sensor.lepas_connection",
    ("binary_sensor", "rt_alta_tensione"):              "binary_sensor.lepas_high_voltage_active",
    ("binary_sensor", "rt_avviso_carburante_basso"):    "binary_sensor.lepas_low_fuel_warning",
    ("binary_sensor", "rt_avviso_gomma_ant_dx"):        "binary_sensor.lepas_tire_warning_front_right",
    ("binary_sensor", "rt_avviso_gomma_ant_sx"):        "binary_sensor.lepas_tire_warning_front_left",
    ("binary_sensor", "rt_avviso_gomma_post_dx"):       "binary_sensor.lepas_tire_warning_rear_right",
    ("binary_sensor", "rt_avviso_gomma_post_sx"):       "binary_sensor.lepas_tire_warning_rear_left",
    ("binary_sensor", "rt_avviso_ricarica"):            "binary_sensor.lepas_charge_needed_warning",
    ("binary_sensor", "rt_batteria_scarica"):           "binary_sensor.lepas_low_battery",
    ("binary_sensor", "session"):                       "binary_sensor.lepas_session",
    ("binary_sensor", "sunshadeState"):                 "binary_sensor.lepas_sunroof_blind",
    ("button", "cmd_antifurto_off"):                    "button.lepas_alarm_off",
    ("button", "cmd_antifurto_on"):                     "button.lepas_alarm_on",
    ("button", "cmd_clima_raffredda_off"):              "button.lepas_cool_everything_off",
    ("button", "cmd_clima_raffredda_on"):               "button.lepas_cool_everything",
    ("button", "cmd_clima_riscalda_off"):               "button.lepas_heat_everything_off",
    ("button", "cmd_clima_riscalda_on"):                "button.lepas_heat_everything",
    ("button", "cmd_finestrini_ventila"):               "button.lepas_vent_windows",
    ("button", "cmd_localizza"):                        "button.lepas_locate_car_gps",
    ("button", "cmd_trova_auto"):                       "button.lepas_find_car_flash_lights",
    ("button", "otp_confirm"):                          "button.lepas_confirm_otp",
    ("button", "otp_request"):                          "button.lepas_request_otp_code",
    ("button", "refresh_full"):                         "button.lepas_refresh_full_status",
    ("button", "refresh_pos"):                          "button.lepas_refresh_location",
    ("button", "wake"):                                 "button.lepas_wake_car",
    ("climate", "climate"):                             "climate.lepas_climate",
    ("cover", "baule"):                                 "cover.lepas_trunk",
    ("cover", "finestrini"):                            "cover.lepas_windows",
    ("cover", "tetto"):                                 "cover.lepas_sunroof",
    ("device_tracker", "position"):                     "device_tracker.lepas_location",
    ("lock", "lock"):                                   "lock.lepas_lock",
    ("number", "clima_durata"):                         "number.lepas_climate_duration",
    ("number", "ricarica_durata_ore"):                  "number.lepas_charge_duration",
    ("sensor", "battery"):                              "sensor.lepas_battery",
    ("sensor", "car_data_ts"):                          "sensor.lepas_car_data_updated",
    ("sensor", "cmd_status"):                           "sensor.lepas_command_result",
    ("sensor", "energy_charged_away"):                  "sensor.lepas_away_charging_energy",
    ("sensor", "energy_charged_home"):                  "sensor.lepas_home_charging_energy",
    ("sensor", "lastseen"):                             "sensor.lepas_last_seen",
    ("sensor", "mSeatHeatingState2"):                   "sensor.lepas_rear_center_seat_heating",
    ("sensor", "mSeatVentilateState2"):                 "sensor.lepas_rear_center_seat_ventilation",
    ("sensor", "pos_fix"):                              "sensor.lepas_last_position",
    ("sensor", "probe_status"):                         "sensor.lepas_location_probe_result",
    ("sensor", "rt_carburante_residuo"):                "sensor.lepas_fuel_remaining",
    ("sensor", "rt_consumo_carburante"):                "sensor.lepas_average_fuel_consumption",
    ("sensor", "rt_consumo_elettrico"):                 "sensor.lepas_average_energy_consumption",
    ("sensor", "rt_corrente_hv"):                       "sensor.lepas_hv_battery_current",
    ("sensor", "rt_gomma_ant_dx_press"):                "sensor.lepas_tire_pressure_front_right",
    ("sensor", "rt_gomma_ant_dx_temp"):                 "sensor.lepas_tire_temperature_front_right",
    ("sensor", "rt_gomma_ant_sx_press"):                "sensor.lepas_tire_pressure_front_left",
    ("sensor", "rt_gomma_ant_sx_temp"):                 "sensor.lepas_tire_temperature_front_left",
    ("sensor", "rt_gomma_post_dx_press"):               "sensor.lepas_tire_pressure_rear_right",
    ("sensor", "rt_gomma_post_dx_temp"):                "sensor.lepas_tire_temperature_rear_right",
    ("sensor", "rt_gomma_post_sx_press"):               "sensor.lepas_tire_pressure_rear_left",
    ("sensor", "rt_gomma_post_sx_temp"):                "sensor.lepas_tire_temperature_rear_left",
    ("sensor", "rt_km_ibrido"):                         "sensor.lepas_hybrid_mileage",
    ("sensor", "rt_odometro"):                          "sensor.lepas_odometer",
    ("sensor", "rt_partenza_programmata"):              "sensor.lepas_scheduled_departure",
    ("sensor", "rt_presa_rapida"):                      "sensor.lepas_fast_charging_port",
    ("sensor", "rt_range_benzina"):                     "sensor.lepas_fuel_range",
    ("sensor", "rt_range_combinato"):                   "sensor.lepas_petrol_range_miles",
    ("sensor", "rt_range_elettrico"):                   "sensor.lepas_electric_range",
    ("sensor", "rt_range_totale"):                      "sensor.lepas_total_range",
    ("sensor", "rt_ricarica_prog_stato"):               "sensor.lepas_scheduled_charging_status",
    ("sensor", "rt_stato_ricarica"):                    "sensor.lepas_charging_status",
    ("sensor", "rt_temp_imp_dx"):                       "sensor.lepas_set_temperature_right",
    ("sensor", "rt_temp_imp_sx"):                       "sensor.lepas_set_temperature_left",
    ("sensor", "rt_tempo_ricarica"):                    "sensor.lepas_remaining_charge_time",
    ("sensor", "rt_tensione_hv"):                       "sensor.lepas_hv_battery_voltage",
    ("sensor", "session_detail"):                       "sensor.lepas_session_status",
    ("sensor", "speed"):                                "sensor.lepas_speed",
    ("sensor", "sunroofMoveState"):                     "sensor.lepas_sunroof_movement_state",
    ("sensor", "wake_status"):                          "sensor.lepas_wake_up_result",
    ("sensor", "wake_ts"):                              "sensor.lepas_last_wake_up",
    ("switch", "antifurto"):                            "switch.lepas_alarm",
    ("switch", "dSeatHeatingState"):                    "switch.lepas_driver_seat_heating",
    ("switch", "dSeatVentilateState"):                  "switch.lepas_driver_seat_ventilation",
    ("switch", "disappannamento_parabrezza"):           "switch.lepas_windshield_defog",
    ("switch", "frontWindshieldHeat"):                  "switch.lepas_windshield_defrost",
    ("switch", "lSeatHeatingState2"):                   "switch.lepas_rear_left_seat_heating",
    ("switch", "lSeatVentilateState2"):                 "switch.lepas_rear_left_seat_ventilation",
    ("switch", "pSeatHeatingState"):                    "switch.lepas_passenger_seat_heating",
    ("switch", "pSeatVentilateState"):                  "switch.lepas_passenger_seat_ventilation",
    ("switch", "polling_auto"):                         "switch.lepas_automatic_updates",
    ("switch", "rSeatHeatingState2"):                   "switch.lepas_rear_right_seat_heating",
    ("switch", "rSeatVentilateState2"):                 "switch.lepas_rear_right_seat_ventilation",
    ("switch", "rWinHeatingState"):                     "switch.lepas_rear_window_heating",
    ("switch", "raffredda_tutto"):                      "switch.lepas_cool_everything",
    ("switch", "ricarica"):                             "switch.lepas_charging",
    ("switch", "ricarica_programmata"):                 "switch.lepas_scheduled_charging",
    ("switch", "riscalda_tutto"):                       "switch.lepas_heat_everything",
    ("switch", "steerWheelHeating"):                    "switch.lepas_steering_wheel_heating",
    ("text", "otp_code"):                               "text.lepas_otp_code",
    ("time", "ricarica_orario_inizio"):                 "time.lepas_charge_start_time",
}

