# Al Input: Ul and Command Specification for LT32 PRO

This document provides a structured specification of the user interface components and corresponding device commands for the LT32 PRO configurator. It is designed to be parsed by an Al for tasks like automated Ul generation or command scripting.

## Section: Network Parameters

### Config: APN Settings

*   **name:** apn_settings
*   **label:** "Configuração APN"
*   **description:** "Configures the APN, username, and password for the mobile network."
*   **fields:**
    *   **field_1:**
        *   **name:** apn
        *   **label:** "APN"
        *   **ui_element:** "text_input"
        *   **validation:** "Accepts a standard APN name, an IP address, or a URL."
    *   **field_2:**
        *   **name:** user
        *   **label:** "Usuário"
        *   **ui_element:** "text_input"
    *   **field_3:**
        *   **name:** password
        *   **label:** "Senha"
        *   **ui_element:** "text_input"
*   **commands:**
    *   **set:** `APN,<apn>,<user>,<password>#`
    *   **read:** `APN#`

### Config: Server Settings

*   **name:** server_settings
*   **label:** "Configuração de Servidor"
*   **description:** "Configures the primary server IP/URL and port."
*   **fields:**
    *   **field_1:**
        *   **name:** address
        *   **label:** "IP / URL"
        *   **ui_element:** "text_input"
        *   **validation:** "Should accept a valid IP address or a valid URL."
    *   **field_2:**
        *   **name:** port
        *   **label:** "PORTA"
        *   **ui_element:** "number_input"
        *   **validation:** "Must be a number between 1 and 65535."
*   **commands:**
    *   **set:** `SERVER,<type>,<address>,<port>,0#` (Note: type is 0 for IP, 1 for domain)
    *   **read:** `SERVER#`

## Section: Time Parameters

### Config: Report Intervals

*   **name:** report_intervals
*   **label:** "Intervalos de Envio"
*   **description:** "Defines the time intervals for sending position data based on ignition status."
*   **fields:**
    *   **field_1:**
        *   **name:** moving_time
        *   **label:** "Tempo em movimento (Ignição ligada)"
        *   **ui_element:** "number_input"
        *   **unit:** "seconds"
    *   **field_2:**
        *   **name:** stopped_time
        *   **label:** "Tempo parado (Ignição desligada)"
        *   **ui_element:** "number_input"
        *   **unit:** "seconds"
*   **commands:**
    *   **set:** `TIMER,<moving_time>,<stopped_time>#`
    *   **read:** `TIMER#`

### Config: Heartbeat Intervals

*   **name:** heartbeat_intervals
*   **label:** "Intervalos de Heartbeat"
*   **description:** "Defines the keep-alive signal interval based on ignition status."
*   **fields:**
    *   **field_1:**
        *   **name:** moving_heartbeat
        *   **label:** "Intervalo (Heartbeat) em movimento"
        *   **ui_element:** "number_input"
        *   **unit:** "seconds"
    *   **field_2:**
        *   **name:** stopped_heartbeat
        *   **label:** "Intervalo (Heartbeat) parado"
        *   **ui_element:** "number_input"
        *   **unit:** "seconds"
*   **commands:**
    *   **set:** `HBT,<moving_heartbeat>,<stopped_heartbeat>#`
    *   **read:** `HBT#`

## Section: Service Parameters

### Config: Protocol

*   **name:** protocol
*   **label:** "Tipo de protocolo"
*   **ui_element:** "dropdown"
*   **options:** ["GT06 (0x60)", "CRX3 (0x22)", "CRX (0x12)"]
*   **commands:**
    *   **set:** `SZCS#GT06SEL=X` (Note: X=0 for GT06, 1 for CRX3, 2 for CRX)
    *   **read:** `CXCS#GT06SEL`

### Config: TCP ACK

*   **name:** tcp_ack
*   **label:** "Habilitar confirmação TCP (ACK)"
*   **ui_element:** "toggle_switch"
*   **options:** ["Enabled", "Disabled"]
*   **commands:**
    *   **set:** `SZCS#POSBYACK=A` (Note: A=1 for enabled, 0 for disabled)
    *   **read:** `CXCS#POSBYACK`

## Section: Ignition

### Config: Ignition Type

*   **name:** ignition_type
*   **label:** "Tipo de ignição"
*   **description:** "Configures the method for detecting ignition status."
*   **fields:**
    *   **field_1:**
        *   **name:** ignition_mode
        *   **label:** "Modo de Ignição"
        *   **ui_element:** "dropdown"
        *   **options:** ["Física (Physical)", "Virtual por acelerômetro (Virtual by accelerometer)", "Virtual por bateria (Virtual by battery)"]
    *   **field_2:**
        *   **name:** on_voltage
        *   **label:** "Tensão para Ligar (ON)"
        *   **ui_element:** "number_input"
        *   **unit:** "V"
        *   **visibility_condition:** "ignition_mode == 'Virtual por bateria (Virtual by battery)'"
    *   **field_3:**
        *   **name:** off_voltage
        *   **label:** "Tensão para Desligar (OFF)"
        *   **ui_element:** "number_input"
        *   **unit:** "V"
        *   **visibility_condition:** "ignition_mode == 'Virtual por bateria (Virtual by battery)'"
*   **commands:**
    *   **set_physical:** `SZCS#ACCLINE=1#ACC_CFG=0-000-000`
    *   **set_accelerometer:** `SZCS#ACCLINE=0#ACC_CFG=0-000-000`
    *   **set_battery:** `SZCS#ACCLINE=1#ACC_CFG=1-<on_voltage>-<off_voltage>` (Note: e.g., ...=1-135-130 for 13.5V and 13.0V)
    *   **read:** `CXCS#ACCLINE#ACC_CFG`

## Section: Speed

### Config: Speed Alert

*   **name:** speed_alert
*   **label:** "Alerta de Velocidade"
*   **description:** "Configures the over-speed alert."
*   **fields:**
    *   **field_1:**
        *   **name:** enabled
        *   **label:** "Habilitar Alerta de limite de velocidade"
        *   **ui_element:** "toggle_switch"
    *   **field_2:**
        *   **name:** detection_time
        *   **label:** "Tempo para detectar (s)"
        *   **ui_element:** "number_input"
        *   **validation:** "5-600"
    *   **field_3:**
        *   **name:** speed_limit
        *   **label:** "Velocidade (km/h)"
        *   **ui_element:** "number_input"
        *   **validation:** "1-255"
    *   **field_4:**
        *   **name:** alert_type
        *   **label:** "Tipo de Alerta"
        *   **ui_element:** "dropdown"
        *   **options:** ["Apenas GPRS", "GPRS+SMS"]
*   **commands:**
    *   **set:** `SPEED,<enabled>,<detection_time>,<speed_limit>,<alert_type>#` (Note: enabled=ON/OFF, alert_type=0/1)
    *   **read:** `SPEED#`

### Config: Speed Buzzer

*   **name:** speed_buzzer
*   **label:** "Ativar o buzzer no alerta de limite de velocidade"
*   **ui_element:** "toggle_switch"
*   **commands:**
    *   **set:** `SZCS#SPD_LED_SHOW=A` (Note: A=1 to enable, 0 to disable)
    *   **read:** "N/A"

## Section: Power Saving

### Config: Sleep Mode

*   **name:** sleep_mode
*   **label:** "Modo Sleep"
*   **ui_element:** "dropdown"
*   **options:** ["Desabilitado (Disabled)", "Sleep (Habilitado)", "Deep Sleep (Ultra-baixo)"]
*   **commands:**
    *   **set:** `SZCS#SLPDISCONNECT=A` (Note: A=0 for Disabled, 1 for Sleep, 2 for Deep Sleep)
    *   **read:** `CXCS#SLPDISCONNECT`

### Config: Sleep Time

*   **name:** sleep_time
*   **label:** "Tempo para entrar em Sleep (minutos)"
*   **ui_element:** "number_input"
*   **unit:** "minutes"
*   **commands:**
    *   **set:** `SZCS#SLEEPT=X` (Note: X is time in minutes)
    *   **read:** `CXCS#SLEEPT`

## Section: Angle

### Config: Angle Report

*   **name:** angle_report
*   **label:** "Envio por Ângulo"
*   **description:** "Configures position reporting based on angle changes."
*   **fields:**
    *   **field_1:**
        *   **name:** enabled
        *   **label:** "Habilitar envio por ângulo"
        *   **ui_element:** "toggle_switch"
    *   **field_2:**
        *   **name:** min_speed
        *   **label:** "Velocidade mínima (km/h)"
        *   **ui_element:** "number_input"
        *   **validation:** "1-20"
        *   **visibility_condition:** "enabled == true"
    *   **field_3:**
        *   **name:** angle_variation
        *   **label:** "Variação do Ângulo (°)"
        *   **ui_element:** "number_input"
        *   **validation:** "5-90"
        *   **visibility_condition:** "enabled == true"
*   **commands:**
    *   **set:** `SZCS#ANGLEVALUE=<min_speed>-<angle_variation>` (Note: e.g., ...=10-015)
    *   **read:** `CXCS#ANGLEVALUE`

## Section: Battery Alerts

### Config: Backup Battery Alert

*   **name:** backup_battery_alert
*   **label:** "Alerta de bateria backup baixa"
*   **ui_element:** "toggle_switch"
*   **commands:**
    *   **set:** `BATALM,<state>,<mode>#` (Note: state=ON/OFF, mode=0 for GPRS, 1 for SMS+GPRS)
    *   **read:** `BATALM#`

### Config: Main Power Alert

*   **name:** main_power_alert
*   **label:** "Alerta de Remoção de Bateria Principal"
*   **description:** "Configures the main power removal alert."
*   **fields:**
    *   **field_1:**
        *   **name:** enabled
        *   **label:** "Habilitar alerta"
        *   **ui_element:** "toggle_switch"
    *   **field_2:**
        *   **name:** alert_type
        *   **label:** "Tipo de Alerta"
        *   **ui_element:** "dropdown"
        *   **options:** ["Apenas GPRS", "GPRS+SMS"]
    *   **field_3:**
        *   **name:** detection_time
        *   **label:** "Tempo de detecção (s)"
        *   **ui_element:** "number_input"
        *   **validation:** "2-60"
    *   **field_4:**
        *   **name:** min_charge_time
        *   **label:** "Tempo mínimo de carga (s)"
        *   **ui_element:** "number_input"
        *   **validation:** "1-3600"
*   **commands:**
    *   **set:** `POWERALM,<enabled>,<alert_type>,<detection_time>,<min_charge_time>#`
    *   **read:** `POWERALM#`

## Section: Vibration Sensor

### Config: Vibration Sensitivity

*   **name:** vibration_sensitivity
*   **label:** "Sensibilidade à Vibração"
*   **fields:**
    *   **field_1:**
        *   **name:** enabled
        *   **label:** "Habilitar sensor de vibração"
        *   **ui_element:** "toggle_switch"
    *   **field_2:**
        *   **name:** level
        *   **label:** "Nível da sensibilidade (1=Baixa, 6=Alta)"
        *   **ui_element:** "slider"
        *   **validation:** "1-6"
*   **commands:**
    *   **set_level:** `SZCS#VIBL=<level>`
    *   **read_level:** `CXCS#VIBL`

## Section: Jammer Detection

### Config: Jammer Detection

*   **name:** jammer_detection
*   **label:** "Detecção de Jammer"
*   **ui_element:** "toggle_switch"
*   **commands:**
    *   **set:** `JAMMER,<state>,<mode>#` (Note: state=ON/OFF, mode=0 for GPRS, 1 for GPRS+SMS)
    *   **read:** `JAMMER#`

### Config: Jammer Relay Action

*   **name:** jammer_relay_action
*   **label:** "Ação da Saída por Jammer"
*   **description:** "Configures the relay (output) behavior upon jammer detection."
*   **fields:**
    *   **field_1:**
        *   **name:** enabled
        *   **label:** "Ativar saída (bloqueio) ao detectar Jammer"
        *   **ui_element:** "toggle_switch"
    *   **field_2:**
        *   **name:** output_operation
        *   **label:** "Operação da Saída"
        *   **ui_element:** "dropdown"
        *   **options:** ["Sem Ação", "Ativar e Manter", "Ativar e Desativar com Jammer"]
    *   **field_3:**
        *   **name:** confirmation_time
        *   **label:** "Tempo para confirmação (s)"
        *   **ui_element:** "number_input"
        *   **validation:** "0-1800"
    *   **field_4:**
        *   **name:** speed_limit
        *   **label:** "Velocidade limite (km/h)"
        *   **ui_element:** "number_input"
        *   **validation:** "0-255"
*   **commands:**
    *   **set:** `JAMRELAY,<op>,<time>,<speed>,<D>,<E>,<F>,<G>#` (Note: This is a complex command with multiple parameters)
    *   **read:** `JAMRELAY#`

## Section: Miscellaneous

### Config: Odometer

*   **name:** odometer
*   **label:** "Ajustar Odômetro"
*   **ui_element:** "number_input"
*   **unit:** "meters"
*   **commands:**
    *   **set:** `MILEAGE=A#` (Note: A is value in km, Ul value in meters needs conversion)
    *   **read:** `MILEAGE#`

### Config: Hourmeter

*   **name:** hourmeter
*   **label:** "Ajustar Horímetro"
*   **ui_element:** "number_input"
*   **unit:** "minutes"
*   **commands:**
    *   **set:** `ACCONT,A#` (Note: A is value in minutes)
    *   **read:** `ACCONT#`
