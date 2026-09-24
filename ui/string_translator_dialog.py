import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import logging
import re
import csv

def log_error(msg, exc_info=False):
    logging.error(msg, exc_info=exc_info)

def log_warning(msg):
    logging.warning(msg)

# --- FUNÇÕES AUXILIARES MATEMÁTICAS ---
def hex_to_dec(hex_str):
    try:
        return int(hex_str, 16)
    except Exception:
        return 0

def hex_to_bin(hex_str):
    try:
        return bin(int(hex_str, 16))[2:]
    except Exception:
        return ""

def parse_datetime(hex_str):
    try:
        y = int(hex_str[0:2], 16)
        m = int(hex_str[2:4], 16)
        d = int(hex_str[4:6], 16)
        h = int(hex_str[6:8], 16)
        mi = int(hex_str[8:10], 16)
        s = int(hex_str[10:12], 16)
        return f"20{y:02d}-{m:02d}-{d:02d} {h:02d}:{mi:02d}:{s:02d}"
    except Exception:
        return "Data Inválida"

def calc_lat_lon_gt06(hex_str):
    try:
        return int(hex_str, 16) / 1800000.0
    except Exception:
        return 0.0

def calc_lat_lon_crx3(hex_str):
    try:
        return int(hex_str, 16) / 1000000.0
    except Exception:
        return 0.0

# --- PARSERS ENVIADOS ---
def parse_login_01(hex_str):
    try:
        imei_hex = hex_str[8:24] if len(hex_str) >= 24 else "Desconhecido"
        serie_hex = hex_str[-12:-8] if len(hex_str) >= 12 else ""
        serie_dec = hex_to_dec(serie_hex) if serie_hex else 0
        return [f"IMEI: {imei_hex}", str(serie_dec)]
    except Exception as e:
        return ["Erro", "Erro"]

def parse_heartbeat_13(hex_str):
    try:
        if len(hex_str) <= 22:
            serie_hex = hex_str[-12:-8] if len(hex_str) >= 12 else ""
            serie_dec = hex_to_dec(serie_hex) if serie_hex else 0
            return ["Resposta do Servidor (ACK)"] + ["N/A"] * 8 + [str(serie_dec)]

        if len(hex_str) < 26:
            return ["Incompleto"] * 10

        term_info_hex = hex_str[8:10]
        volt_hex = hex_str[10:12]
        gsm_hex = hex_str[12:14]
        alarm_hex = hex_str[14:16]
        lang_hex = hex_str[16:18]

        term_int = int(term_info_hex, 16)
        saida = "Ativada (Bloqueado)" if (term_int & 0x80) else "Desativada (Liberado)"
        gps_status = "GPS ON" if (term_int & 0x40) else "GPS OFF"
        
        evento_val = (term_int & 0x38) >> 3
        event_map = {0: "Normal", 1: "Shock Alarm", 2: "Power Cut", 3: "Low Battery", 4: "SOS"}
        evento = event_map.get(evento_val, f"Desconhecido ({evento_val})")
        
        carga = "Charge ON" if (term_int & 0x04) else "Charge OFF"
        acc = "ACC ON" if (term_int & 0x02) else "ACC OFF"
        ativacao = "Ativado" if (term_int & 0x01) else "Desativado"

        volt_map = {0:"0-Sem Força", 1:"1-Crítica", 2:"2-Muito Baixa", 3:"3-Baixa", 4:"4-Média", 5:"5-Alta", 6:"6-Cheia"}
        voltage_level = volt_map.get(hex_to_dec(volt_hex), "Desconhecido")

        gsm_map = {0:"0-Sem Sinal", 1:"1-Muito Fraco", 2:"2-Fraco", 3:"3-Bom", 4:"4-Forte"}
        gsm_signal = gsm_map.get(hex_to_dec(gsm_hex), "Desconhecido")

        alarm_map = {
            0: "Normal", 1: "SOS", 2: "Corte Energia", 3: "Choque", 4: "Cerca In",
            5: "Cerca Out", 6: "Excesso Velocidade", 7: "Recup. Energia", 14: "Bat Baixa",
            18: "Input Active", 19: "Input Inactive",
            25: "Bat Bank Baixa", 245: "Jammer", 246: "Jammer Normal", 254: "ACC ON", 255: "ACC OFF"
        }
        tipo_alarme = alarm_map.get(hex_to_dec(alarm_hex), f"Desconhecido ({alarm_hex})")

        lang_map = {1: "Chinês", 2: "Inglês"}
        idioma = lang_map.get(hex_to_dec(lang_hex), f"Outro ({lang_hex})")

        serie_hex = hex_str[-12:-8] if len(hex_str) >= 12 else ""
        serie_dec = hex_to_dec(serie_hex) if serie_hex else 0

        return [saida, gps_status, evento, carga, acc, ativacao, voltage_level, gsm_signal, tipo_alarme, idioma, str(serie_dec)]
    except Exception as e:
        return ["Erro"] * 11

def parse_location_60(hex_str):
    try:
        if len(hex_str) < 100:
            return ["Pacote Incompleto"] * 20

        imei_hex = hex_str[8:24]
        data_hora_hex = hex_str[24:36]
        satelites_hex = hex_str[36:38]
        lat_hex = hex_str[38:46]
        lon_hex = hex_str[46:54]
        speed_hex = hex_str[54:56]
        course_status_hex = hex_str[56:60]
        mcc_hex = hex_str[60:64]
        mnc_hex = hex_str[64:66]
        lac_hex = hex_str[66:70]
        cell_id_hex = hex_str[70:78]
        ext_volt_hex = hex_str[78:82]
        bat_int_hex = hex_str[82:84]
        ign_time_hex = hex_str[84:92]
        mileage_hex = hex_str[92:100]

        imei = f"IMEI: {imei_hex}"
        data_hora_formatada = parse_datetime(data_hora_hex)
        satelites_qtd = str(hex_to_dec(satelites_hex[1])) if len(satelites_hex) == 2 else "0"
        
        course_int = int(course_status_hex, 16)
        ignicao = "IGN ON" if (course_int & 0x8000) else "IGN OFF"
        bloqueio = "Saída Ativada" if (course_int & 0x4000) else "Saída Desativada"
        tipo_posicao = "Tempo Real" if (course_int & 0x2000) else "Memória"
        gps_fix = "GPS Fixo" if (course_int & 0x1000) else "GPS Inválido"
        
        latitude = calc_lat_lon_gt06(lat_hex)
        longitude = calc_lat_lon_gt06(lon_hex)
        
        if (course_int & 0x0800): longitude = -longitude
        if (course_int & 0x0400) == 0: latitude = -latitude
        
        lat_formatada = f"{latitude:.6f}"
        lon_formatada = f"{longitude:.6f}"
        
        velocidade_kmh = str(hex_to_dec(speed_hex))
        curso_graus = course_int & 0x03FF
        
        mcc = str(hex_to_dec(mcc_hex))
        mnc = str(hex_to_dec(mnc_hex))
        lac = str(hex_to_dec(lac_hex))
        cell_id = str(hex_to_dec(cell_id_hex))
        
        ext_volt = f"{hex_to_dec(ext_volt_hex) / 10.0:.1f}V"
        bat_int = f"{hex_to_dec(bat_int_hex) / 10.0:.1f}V"
        ign_time = f"{hex_to_dec(ign_time_hex)} min"
        hodometro = f"{hex_to_dec(mileage_hex)} km"

        serie_hex = hex_str[-12:-8] if len(hex_str) >= 12 else ""
        serie_dec = hex_to_dec(serie_hex) if serie_hex else 0

        return [
            imei, data_hora_formatada, ignicao, bloqueio, tipo_posicao, gps_fix,
            satelites_qtd, lat_formatada, lon_formatada, velocidade_kmh, f"{curso_graus}°",
            mcc, mnc, lac, cell_id, ext_volt, bat_int, ign_time, hodometro, str(serie_dec)
        ]
    except Exception as e:
        return ["Erro"] * 20
        
def parse_location_61(hex_str):
    try:
        if len(hex_str) < 120:
            return ["Pacote Incompleto"] * 23

        imei_hex = hex_str[8:24]
        data_hora_hex = hex_str[24:36]
        satelites_hex = hex_str[36:38]
        lat_hex = hex_str[38:46]
        lon_hex = hex_str[46:54]
        speed_hex = hex_str[54:56]
        course_status_hex = hex_str[56:60]
        mcc_hex = hex_str[60:64]
        mnc_hex = hex_str[64:66]
        lac_hex = hex_str[66:70]
        cell_id_hex = hex_str[70:78]
        ext_volt_hex = hex_str[78:82]
        bat_int_hex = hex_str[82:84]
        ign_time_hex = hex_str[84:92]
        mileage_hex = hex_str[92:100]
        driver_id_hex = hex_str[100:116]
        rfid_status_hex = hex_str[116:118]
        input_state_hex = hex_str[118:120]

        imei = f"{imei_hex}"
        data_hora_formatada = parse_datetime(data_hora_hex)
        satelites_qtd = str(hex_to_dec(satelites_hex[1])) if len(satelites_hex) == 2 else "0"
        
        course_int = int(course_status_hex, 16)
        ignicao = "IGN ON" if (course_int & 0x8000) else "IGN OFF"
        bloqueio = "Saída Ativada" if (course_int & 0x4000) else "Saída Desativada"
        tipo_posicao = "Tempo Real" if (course_int & 0x2000) else "Memória"
        gps_fix = "GPS Fixo" if (course_int & 0x1000) else "GPS Inválido"
        
        latitude = calc_lat_lon_gt06(lat_hex)
        longitude = calc_lat_lon_gt06(lon_hex)
        
        if (course_int & 0x0800): longitude = -longitude 
        if (course_int & 0x0400) == 0: latitude = -latitude 
        
        lat_formatada = f"{latitude:.6f}"
        lon_formatada = f"{longitude:.6f}"
        velocidade_kmh = str(hex_to_dec(speed_hex))
        curso_graus = course_int & 0x03FF 
        
        mcc = str(hex_to_dec(mcc_hex))
        mnc = str(hex_to_dec(mnc_hex))
        lac = str(hex_to_dec(lac_hex))
        cell_id = str(hex_to_dec(cell_id_hex))
        
        ext_volt = f"{hex_to_dec(ext_volt_hex) / 10.0:.1f}V"
        bat_int = f"{hex_to_dec(bat_int_hex) / 10.0:.1f}V"
        ign_time = f"{hex_to_dec(ign_time_hex)} min"
        hodometro = f"{hex_to_dec(mileage_hex)} km"

        driver_id = driver_id_hex if driver_id_hex != "0000000000000000" else "Nenhum/Removido"
        rfid_map = {0: "0x00 - Inválido (Antes IGN)", 1: "0x01 - Válido (Antes IGN)", 2: "0x02 - Direção Normal", 3: "0x03 - Estacionado", 4: "0x04 - Inválido (Em Direção)", 5: "0x05 - Válido (Em Direção)"}
        status_rfid = rfid_map.get(hex_to_dec(rfid_status_hex), f"Desconhecido ({rfid_status_hex})")
        input_state = "ACC Ligado" if input_state_hex == "01" else "ACC Desligado"

        serie_hex = hex_str[-12:-8] if len(hex_str) >= 12 else ""
        serie_dec = hex_to_dec(serie_hex) if serie_hex else 0

        return [
            imei, data_hora_formatada, ignicao, bloqueio, tipo_posicao, gps_fix,
            satelites_qtd, lat_formatada, lon_formatada, velocidade_kmh, f"{curso_graus}°",
            mcc, mnc, lac, cell_id, ext_volt, bat_int, ign_time, hodometro,
            driver_id, status_rfid, input_state, str(serie_dec)
        ]
    except Exception as e:
        return ["Erro"] * 23

def parse_alarm_16_26(hex_str):
    try:
        if len(hex_str) <= 22:
            serie_hex = hex_str[-12:-8] if len(hex_str) >= 12 else ""
            serie_dec = hex_to_dec(serie_hex) if serie_hex else 0
            return ["Resposta do Servidor (ACK)"] + ["N/A"] * 8 + [str(serie_dec)]

        if len(hex_str) < 72:
            return ["Pacote Incompleto"] * 10

        data_hora_hex = hex_str[8:20]
        satelites_hex = hex_str[20:22]
        lat_hex = hex_str[22:30]
        lon_hex = hex_str[30:38]
        speed_hex = hex_str[38:40]
        course_status_hex = hex_str[40:44]
        term_info_hex = hex_str[62:64]
        volt_hex = hex_str[64:66]
        gsm_hex = hex_str[66:68]
        alarm_hex = hex_str[68:70]
        
        data_hora_formatada = parse_datetime(data_hora_hex)
        satelites_qtd = str(hex_to_dec(satelites_hex[1])) if len(satelites_hex) == 2 else "0"
        velocidade_kmh = str(hex_to_dec(speed_hex))
        
        course_int = int(course_status_hex, 16)
        latitude = calc_lat_lon_gt06(lat_hex)
        longitude = calc_lat_lon_gt06(lon_hex)
        
        if (course_int & 0x0800): longitude = -longitude
        if (course_int & 0x0400) == 0: latitude = -latitude
        
        lat_formatada = f"{latitude:.6f}"
        lon_formatada = f"{longitude:.6f}"

        term_int = int(term_info_hex, 16)
        bloqueio = "Bloqueado" if (term_int & 0x80) else "Desbloqueado"
        carga = "Carga ON" if (term_int & 0x04) else "Carga OFF"
        acc = "ACC ON" if (term_int & 0x02) else "ACC OFF"
        info_terminal = f"{acc} | {carga} | {bloqueio}"

        volt_map = {0:"0-Sem Força", 1:"1-Crítica", 2:"2-Muito Baixa", 3:"3-Baixa", 4:"4-Média", 5:"5-Alta", 6:"6-Cheia"}
        voltage_level = volt_map.get(hex_to_dec(volt_hex), "Desconhecido")
        
        gsm_map = {0:"0-Sem Sinal", 1:"1-Muito Fraco", 2:"2-Fraco", 3:"3-Bom", 4:"4-Forte"}
        gsm_signal = gsm_map.get(hex_to_dec(gsm_hex), "Desconhecido")

        alarm_map = {
            0: "Normal", 1: "SOS", 2: "Corte de Energia", 3: "Vibração/Choque",
            4: "Entrou na Cerca", 5: "Saiu da Cerca", 6: "Excesso de Velocidade",
            7: "Restauração Energia", 14: "Bateria Baixa", 18: "Input Active",
            19: "Input Inactive", 25: "Alarme Bateria (Bank)",
            245: "Jammer", 246: "Jammer Normalizado", 254: "ACC ON", 255: "ACC OFF"
        }
        tipo_alarme = alarm_map.get(hex_to_dec(alarm_hex), f"Alarme Desconhecido ({alarm_hex})")

        serie_hex = hex_str[-12:-8] if len(hex_str) >= 12 else ""
        serie_dec = hex_to_dec(serie_hex) if serie_hex else 0

        return [data_hora_formatada, satelites_qtd, lat_formatada, lon_formatada, velocidade_kmh, info_terminal, voltage_level, gsm_signal, tipo_alarme, str(serie_dec)]

    except Exception as e:
        return ["Erro"] * 10

def parse_cmd_15_21_80(hex_str):
    try:
        is_79 = hex_str.startswith("7979")
        min_len = 36 if is_79 else 34
        if len(hex_str) < min_len: return ["Incompleto"] * 6

        len_cmd_hex = hex_str[8:10]
        flag_servidor_hex = hex_str[10:18]
        start_offset = 20 if is_79 else 18
        comando_hex = hex_str[start_offset:-16]
        lang_hex = hex_str[-16:-12]

        comando_ascii = ""
        if comando_hex:
            try: comando_ascii = bytes.fromhex(comando_hex).decode('ascii', errors='replace')
            except: comando_ascii = "Erro ASCII"
        else:
            comando_ascii = "[Vazio]"

        lang_map = {1: "Chinês", 2: "Inglês"}
        idioma = lang_map.get(hex_to_dec(lang_hex), f"Desconhecido ({lang_hex})")
        len_cmd_dec = hex_to_dec(len_cmd_hex)
        serie_hex = hex_str[-12:-8] if len(hex_str) >= 12 else ""
        serie_dec = hex_to_dec(serie_hex) if serie_hex else 0

        return [str(len_cmd_dec), flag_servidor_hex, comando_hex, comando_ascii, idioma, str(serie_dec)]
    except Exception as e:
        return ["Erro"] * 6

def parse_ext_voltage_94(hex_str):
    try:
        info_type = hex_str[10:12]
        if info_type == "00":
            tipo = "00 - Voltagem Externa"
            volt_hex = hex_str[12:16]
            volt_dec = hex_to_dec(volt_hex)
            conteudo = f"{volt_dec / 100:.2f}V"
        else:
            tipo = f"Outro ({info_type})"
            conteudo = hex_str[12:-12]
            
        serie_hex = hex_str[-12:-8] if len(hex_str) >= 12 else ""
        serie_dec = hex_to_dec(serie_hex) if serie_hex else 0
        return [tipo, conteudo, str(serie_dec)]
    except Exception as e:
        return ["Erro"] * 3

def parse_location_22(hex_str):
    try:
        if len(hex_str) < 66: return ["Incompleto"] * 15

        data_hora_hex = hex_str[8:20]
        satelites_hex = hex_str[20:22]
        lat_hex = hex_str[22:30]
        lon_hex = hex_str[30:38]
        speed_hex = hex_str[38:40]
        course_status_hex = hex_str[40:44]
        mcc_hex = hex_str[44:48]
        mnc_hex = hex_str[48:50]
        lac_hex = hex_str[50:54]
        cell_id_hex = hex_str[54:60]
        acc_hex = hex_str[60:62]
        upload_mode_hex = hex_str[62:64]
        
        mileage = "N/A"
        if len(hex_str) >= 78:
            mileage = f"{hex_to_dec(hex_str[66:74]) / 100:.2f} km"

        rfid = "N/A"
        if len(hex_str) >= 100:
            rfid = hex_str[-28:-12]

        data_hora_formatada = parse_datetime(data_hora_hex)
        satelites_qtd = str(hex_to_dec(satelites_hex[1])) if len(satelites_hex) == 2 else "0"
        velocidade_kmh = str(hex_to_dec(speed_hex))
        
        latitude = calc_lat_lon_crx3(lat_hex)
        longitude = calc_lat_lon_crx3(lon_hex)
        
        course_int = int(course_status_hex, 16)
        if (course_int & 0x0800): longitude = -longitude
        if (course_int & 0x0400) == 0: latitude = -latitude
        
        curso_graus = course_int & 0x03FF
        mcc = str(hex_to_dec(mcc_hex))
        mnc = str(hex_to_dec(mnc_hex))
        lac = str(hex_to_dec(lac_hex))
        cell_id = str(hex_to_dec(cell_id_hex))
        
        acc_status = "ACC Ligado" if acc_hex == "01" else "ACC Desligado"
        mode_map = {"00": "Por Tempo", "01": "Por Distância", "02": "Por Curva", "03": "Por ACC"}
        upload_mode = mode_map.get(upload_mode_hex, f"Outro ({upload_mode_hex})")
        serie_dec = hex_to_dec(hex_str[-12:-8]) if len(hex_str) >= 12 else 0

        return [data_hora_formatada, satelites_qtd, f"{latitude:.6f}", f"{longitude:.6f}", velocidade_kmh, f"{curso_graus}°", mcc, mnc, lac, cell_id, acc_status, upload_mode, mileage, rfid, str(serie_dec)]
    except Exception as e:
        return ["Erro"] * 15

def parse_location_12(hex_str):
    try:
        if len(hex_str) < 60: return ["Incompleto"] * 16

        data_hora_hex = hex_str[8:20]
        satelites_hex = hex_str[20:22]
        lat_hex = hex_str[22:30]
        lon_hex = hex_str[30:38]
        speed_hex = hex_str[38:40]
        course_status_hex = hex_str[40:44]
        mcc_hex = hex_str[44:48]
        mnc_hex = hex_str[48:50]
        lac_hex = hex_str[50:54]
        cell_id_hex = hex_str[54:60]

        rfid = hex_str[-28:-12] if len(hex_str) >= 88 else "N/A"
        data_hora_formatada = parse_datetime(data_hora_hex)
        satelites_qtd = str(hex_to_dec(satelites_hex[1])) if len(satelites_hex) == 2 else "0"
        velocidade_kmh = str(hex_to_dec(speed_hex))

        latitude = calc_lat_lon_gt06(lat_hex)
        longitude = calc_lat_lon_gt06(lon_hex)

        course_int = int(course_status_hex, 16)
        ignicao = "IGN ON" if (course_int & 0x8000) else "IGN OFF"
        bloqueio = "Saída Ativada" if (course_int & 0x4000) else "Saída Desativada"
        tipo_posicao = "Tempo Real" if (course_int & 0x2000) else "Memória"
        gps_fix = "GPS Fixo" if (course_int & 0x1000) else "GPS Inválido"

        if (course_int & 0x0800): longitude = -longitude
        if (course_int & 0x0400) == 0: latitude = -latitude

        curso_graus = course_int & 0x03FF
        mcc = str(hex_to_dec(mcc_hex))
        mnc = str(hex_to_dec(mnc_hex))
        lac = str(hex_to_dec(lac_hex))
        cell_id = str(hex_to_dec(cell_id_hex))
        serie_dec = hex_to_dec(hex_str[-12:-8]) if len(hex_str) >= 12 else 0

        return [data_hora_formatada, satelites_qtd, f"{latitude:.6f}", f"{longitude:.6f}", velocidade_kmh, f"{curso_graus}°", ignicao, bloqueio, tipo_posicao, gps_fix, mcc, mnc, lac, cell_id, rfid, str(serie_dec)]
    except Exception as e:
        return ["Erro"] * 16

def parse_rfid_17(hex_str):
    try:
        if len(hex_str) < 90: return ["Incompleto"] * 14
        data_hora_formatada = parse_datetime(hex_str[8:20])
        satelites_qtd = str(hex_to_dec(hex_str[20:22]))
        latitude = calc_lat_lon_gt06(hex_str[22:30])
        longitude = calc_lat_lon_gt06(hex_str[30:38])
        velocidade_kmh = str(hex_to_dec(hex_str[38:40]))
        
        course_int = int(hex_str[40:44], 16)
        ignicao = "IGN ON" if (course_int & 0x8000) else "IGN OFF"
        if (course_int & 0x0800): longitude = -longitude
        if (course_int & 0x0400) == 0: latitude = -latitude

        curso_graus = course_int & 0x03FF
        mcc = str(hex_to_dec(hex_str[44:48]))
        mnc = str(hex_to_dec(hex_str[48:50]))
        lac = str(hex_to_dec(hex_str[50:54]))
        cell_id = str(hex_to_dec(hex_str[54:60]))
        rfid_hex = hex_str[60:76]
        valido = "Sim" if hex_str[76:78] == "01" else "Não"
        serie_dec = hex_to_dec(hex_str[-12:-8]) if len(hex_str) >= 12 else 0

        return [data_hora_formatada, satelites_qtd, f"{latitude:.6f}", f"{longitude:.6f}", velocidade_kmh, f"{curso_graus}°", ignicao, mcc, mnc, lac, cell_id, rfid_hex, valido, str(serie_dec)]
    except Exception:
        return ["Erro"] * 14

def unescape_jt808(hex_str):
    body = hex_str[2:-2] if hex_str.upper().startswith("7E") and hex_str.upper().endswith("7E") else hex_str
    try:
        b = bytes.fromhex(body)
        b = b.replace(b'\x7d\x02', b'\x7e').replace(b'\x7d\x01', b'\x7d')
        return b.hex().upper()
    except ValueError:
        return body.upper()

def parse_jt808_0200(hex_str):
    try:
        unescaped = unescape_jt808(hex_str)
        props = unescaped[4:8]
        terminal_id = unescaped[8:20].lstrip("0") or "0" 
        serial = unescaped[20:24]
        has_subpackage = (int(props, 16) & 0x2000) != 0
        body_start = 28 if has_subpackage else 24
        body = unescaped[body_start:-2]
        
        if len(body) < 56: return ["Tamanho Inválido"] * 12
        alarm_hex = body[0:8]
        status_hex = body[8:16]
        lat_hex = body[16:24]
        lon_hex = body[24:32]
        alt_hex = body[32:36]
        spd_hex = body[36:40]
        course_hex = body[40:44]
        time_bcd = body[44:56]
        extras_hex = body[56:]
        
        status_int = int(status_hex, 16)
        gps_valid = "GPS Fixo" if (status_int & 0x00000002) else "GPS Inválido"
        acc_status = "ACC Ligado" if (status_int & 0x00000001) else "ACC Desligado"
        status_final = f"{gps_valid} | {acc_status}"
        
        lat = int(lat_hex, 16) / 1000000.0
        if (status_int & 0x00000004): lat = -lat
        lon = int(lon_hex, 16) / 1000000.0
        if (status_int & 0x00000008): lon = -lon
        
        alt = int(alt_hex, 16)
        spd = int(spd_hex, 16) / 10.0
        course = int(course_hex, 16)
        time_fmt = f"20{time_bcd[0:2]}-{time_bcd[2:4]}-{time_bcd[4:6]} {time_bcd[6:8]}:{time_bcd[8:10]}:{time_bcd[10:12]}"
        
        extras_parsed = []
        idx = 0
        while idx < len(extras_hex):
            if idx + 4 > len(extras_hex): break
            e_id = extras_hex[idx:idx+2]
            e_len = int(extras_hex[idx+2:idx+4], 16) * 2
            e_data = extras_hex[idx+4:idx+4+e_len]
            idx += 4 + e_len
            
            if e_id == "56" and len(e_data) >= 4:
                lvl = int(e_data[0:2], 16)
                pct = int(e_data[2:4], 16)
                extras_parsed.append(f"Bat: {pct}%")
            elif e_id == "01": extras_parsed.append(f"Hodo: {int(e_data, 16)/10.0}km")
            elif e_id == "31": extras_parsed.append(f"Sat: {int(e_data, 16)}")
            else: extras_parsed.append(f"ID[{e_id}]:{e_data}")
        extras_str = " | ".join(extras_parsed) if extras_parsed else "Sem Extras"
        
        return [terminal_id, alarm_hex, status_final, f"{lat:.6f}", f"{lon:.6f}", f"{alt}m", f"{spd} km/h", f"{course}°", time_fmt, extras_str, str(int(serial, 16))]
    except Exception:
        return ["Erro"] * 12

def parse_tag_location_32(hex_str):
    try:
        data_hora = parse_datetime(hex_str[8:20])
        sat = str(hex_to_dec(hex_str[20:22]))
        lat = calc_lat_lon_gt06(hex_str[22:30])
        lon = calc_lat_lon_gt06(hex_str[30:38])
        vel = str(hex_to_dec(hex_str[38:40]))
        course_int = int(hex_str[40:44], 16)
        curso = f"{course_int & 0x3FF}°"
        
        if (course_int & 0x0800): lon = -lon
        if (course_int & 0x0400) == 0: lat = -lat
        
        acc_hex = hex_str[62:64]
        mode_hex = hex_str[64:66]
        rt_hex = hex_str[66:68]
        
        acc = "IGN Ligada" if acc_hex == "01" else "IGN Desligada"
        mode = "Por Tempo" if mode_hex == "00" else f"Outro ({mode_hex})"
        rt = "Realtime" if rt_hex == "00" else "Re-upload"
        
        hodo = f"{hex_to_dec(hex_str[68:76])} km"
        volt = f"{hex_to_dec(hex_str[76:80]) / 100.0:.2f}V" 
        acc_time = f"{hex_to_dec(hex_str[80:88])}s"
        serie = str(hex_to_dec(hex_str[-12:-8]))
        
        return [data_hora, sat, f"{lat:.6f}", f"{lon:.6f}", vel, curso, acc, mode, rt, hodo, volt, acc_time, serie]
    except Exception:
        return ["Erro"] * 13

# --- LÓGICA DE DETECÇÃO AUTOMÁTICA ---
def parse_generic_string(hex_input):
    hex_str = hex_input.replace(" ", "").upper()
    if not hex_str:
        return "Vazio", [], []

    if hex_str.startswith("7E"):
        msg_id = hex_str[2:6]
        if msg_id == "0200": 
            return "JT808 - Loc (0200)", parse_jt808_0200(hex_str), ["ID", "Alarme", "Status", "Lat", "Lon", "Alt", "Vel", "Curso", "Data", "Extras", "Série"]
        else:
            return f"JT808 - Outro ({msg_id})", [hex_str], ["Dados Brutos"]

    elif hex_str.startswith("7878") or hex_str.startswith("7979"):
        protocol = hex_str[6:8]
        
        if protocol == "01": return "Login (01)", parse_login_01(hex_str), ["IMEI", "Série"]
        elif protocol == "13": return "Heartbeat (13)", parse_heartbeat_13(hex_str), ["Bloqueio", "Status GPS", "Evento", "Carga", "ACC", "Ativação", "Volts", "Sinal GSM", "Alarme", "Idioma", "Série"]
        elif protocol == "60": return "Loc (60)", parse_location_60(hex_str), ["IMEI", "Data", "Ignição", "Bloqueio", "Posição", "GPS", "Sat", "Lat", "Lon", "Vel", "Curso", "MCC", "MNC", "LAC", "CID", "Volt Ext", "Bat Int", "Ign", "Odo", "Série"]
        elif protocol == "61": return "Loc+RFID (61)", parse_location_61(hex_str), ["IMEI", "Data", "Ignição", "Bloqueio", "Posição", "GPS", "Sat", "Lat", "Lon", "Vel", "Curso", "MCC", "MNC", "LAC", "CID", "Volt Ext", "Bat Int", "Ign", "Odo", "Motorista", "RFID", "Input", "Série"]
        elif protocol in ["16", "26"]: return f"Alarme ({protocol})", parse_alarm_16_26(hex_str), ["Data", "Sat", "Lat", "Lon", "Vel", "Terminal", "Volt", "GSM", "Alarme", "Série"]
        elif protocol in ["15", "21", "80"]: return f"Comando ({protocol})", parse_cmd_15_21_80(hex_str), ["Tam", "Flag", "HEX", "ASCII", "Lang", "Série"]
        elif protocol == "94": return "Voltagem (94)", parse_ext_voltage_94(hex_str), ["Tipo", "Voltagem", "Série"]
        elif protocol == "22": return "Loc CRX3 (22)", parse_location_22(hex_str), ["Data", "Sat", "Lat", "Lon", "Vel", "Curso", "MCC", "MNC", "LAC", "CID", "ACC", "Upload", "Odo", "RFID", "Série"]
        elif protocol == "12": return "Loc (12)", parse_location_12(hex_str), ["Data", "Sat", "Lat", "Lon", "Vel", "Curso", "Ignição", "Bloqueio", "Pos", "GPS", "MCC", "MNC", "LAC", "CID", "RFID", "Série"]
        elif protocol == "17": return "RFID (17)", parse_rfid_17(hex_str), ["Data", "Sat", "Lat", "Lon", "Vel", "Curso", "Ignição", "MCC", "MNC", "LAC", "CID", "RFID", "Válido", "Série"]
        elif protocol == "32": return "Loc V4 (32)", parse_tag_location_32(hex_str), ["Data", "Sat", "Lat", "Lon", "Vel", "Curso", "Ignição", "Upload", "GPS RT", "Odo", "Volt", "Tempo ACC", "Série"]
        else: return f"Desconhecido ({protocol})", [f"Protocolo {protocol} sem mapeamento."], ["Aviso"]
    
    return "Inválido", ["Pacote não inicia com 7878, 7979 ou 7E"], ["Erro"]


# --- INTERFACE GRÁFICA DO TRADUTOR ---
class StringTranslatorDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Tradutor de Strings em Lote")
        
        # Geometria base
        self.geometry("1300x750")
        
        # Garante que a janela possa ser maximizada livremente e não fique travada atrás
        self.minsize(800, 500)
        self.resizable(True, True)
        
        # Truque avançado para forçar a janela para a frente no Windows
        self.lift()
        self.attributes('-topmost', True)
        
        # Dá tempo para o Windows renderizar a janela antes de puxar o foco e soltar a trava
        self.after(200, self.focus_force)
        self.after(500, lambda: self.attributes('-topmost', False))

        # Dicionário com as colunas reais para cada Aba
        self.tab_columns = {
            "Login (0x01)": ["String Bruta", "Protocolo", "IMEI", "Série"],
            "Location (0x60)": ["String Bruta", "Protocolo", "IMEI", "Data", "Ignição", "Bloqueio", "Posição", "GPS", "Sat", "Lat", "Lon", "Vel", "Curso", "MCC", "MNC", "LAC", "CID", "Volt Ext", "Bat Int", "Ign", "Odo", "Série"],
            "Location (0x61)": ["String Bruta", "Protocolo", "IMEI", "Data", "Ignição", "Bloqueio", "Posição", "GPS", "Sat", "Lat", "Lon", "Vel", "Curso", "MCC", "MNC", "LAC", "CID", "Volt Ext", "Bat Int", "Ign", "Odo", "Motorista", "RFID", "Input", "Série"],
            "Location (0x22)": ["String Bruta", "Protocolo", "Data", "Sat", "Lat", "Lon", "Vel", "Curso", "MCC", "MNC", "LAC", "CID", "ACC", "Upload", "Odo", "RFID", "Série"],
            "Location (0x12)": ["String Bruta", "Protocolo", "Data", "Sat", "Lat", "Lon", "Vel", "Curso", "Ignição", "Bloqueio", "Pos", "GPS", "MCC", "MNC", "LAC", "CID", "RFID", "Série"],
            "RFID (0x17)": ["String Bruta", "Protocolo", "Data", "Sat", "Lat", "Lon", "Vel", "Curso", "Ignição", "MCC", "MNC", "LAC", "CID", "RFID", "Válido", "Série"],
            "Heartbeat (0x13)": ["String Bruta", "Protocolo", "Bloqueio", "Status GPS", "Evento", "Carga", "ACC", "Ativação Defense", "Volts", "Sinal GSM", "Alarme", "Idioma", "Série"],
            "Alarm (0x16, 0x26)": ["String Bruta", "Protocolo", "Data", "Sat", "Lat", "Lon", "Vel", "Terminal", "Volt", "GSM", "Alarme", "Série"],
            "CMD (0x15, 0x21, 0x80)": ["String Bruta", "Protocolo", "Tam", "Flag", "HEX", "ASCII", "Lang", "Série"],
            "Ext Voltage (0x94)": ["String Bruta", "Protocolo", "Tipo", "Voltagem", "Série"],
            "ACKs (Servidor)": ["String Bruta", "Protocolo", "Status", "Série"],
            "Outros": ["String Bruta", "Protocolo", "Detalhes"],
            "TAG Loc (0x12)": ["String Bruta", "Protocolo", "Data", "Sat", "Lat", "Lon", "Vel", "Curso", "Série"],
            "TAG Loc (0x32)": ["String Bruta", "Protocolo", "Data", "Sat", "Lat", "Lon", "Vel", "Curso", "Ignição", "Upload", "GPS RT", "Odo", "Volt", "Tempo ACC", "Série"],
            "TAG JT808 (0200)": ["String Bruta", "Protocolo", "ID", "Alarme", "Status", "Lat", "Lon", "Alt", "Vel", "Curso", "Data", "Extras", "Série"]
        }

        # Arrays internos
        self.treeviews = {}
        self.tab_buttons = {}
        self.tab_frames = {}
        self.current_tab = None

        # Configura Layout Grid Principal
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # 1. Campo de Entrada
        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.grid(row=0, column=0, padx=20, pady=(20, 0), sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(input_frame, text="Cole as Strings Hexadecimais abaixo (suporta múltiplas linhas):", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w")
        
        self.input_text = ctk.CTkTextbox(input_frame, height=80)
        self.input_text.grid(row=1, column=0, sticky="ew", pady=(5, 0))

        # 2. Botões
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        
        self.translate_btn = ctk.CTkButton(btn_frame, text="Traduzir Lote", command=self.on_translate, fg_color="#1f538d", width=120)
        self.translate_btn.pack(side="left")

        self.clear_btn = ctk.CTkButton(btn_frame, text="Limpar", command=self.on_clear, fg_color="gray", hover_color="darkgray", width=100)
        self.clear_btn.pack(side="left", padx=10)

        # Botão de Exportar CSV
        self.export_btn = ctk.CTkButton(btn_frame, text="Exportar CSV da Aba", command=self.on_export, fg_color="#27AE60", hover_color="#1E8449", width=150)
        self.export_btn.pack(side="left", padx=5)

        self.status_label = ctk.CTkLabel(btn_frame, text="Status: Aguardando...", text_color="#F39C12", font=ctk.CTkFont(weight="bold"))
        self.status_label.pack(side="right")

        # 3. Abas (Grade de Botões)
        self.tabs_container = ctk.CTkFrame(self, fg_color="transparent")
        self.tabs_container.grid(row=2, column=0, padx=20, pady=(10, 0), sticky="ew")
        
        # 4. Container do Conteúdo (Tabelas)
        self.content_container = ctk.CTkFrame(self, corner_radius=10, fg_color="#1E1E1E")
        self.content_container.grid(row=3, column=0, padx=20, pady=(5, 20), sticky="nsew")

        self._setup_tabs()

    def _setup_tabs(self):
        colunas_por_linha = 8
        for i in range(colunas_por_linha):
            self.tabs_container.grid_columnconfigure(i, weight=1)

        row_idx, col_idx = 0, 0

        # Criação de cada aba/tabela
        for tab_name, columns in self.tab_columns.items():
            # Botão simulando a Aba
            btn = ctk.CTkButton(
                self.tabs_container, text=tab_name, font=ctk.CTkFont(size=11), 
                fg_color="#1C2833", hover_color="#007EA7", corner_radius=4,
                command=lambda t=tab_name: self.select_tab(t)
            )
            btn.grid(row=row_idx, column=col_idx, padx=2, pady=3, sticky="ew")
            self.tab_buttons[tab_name] = btn

            # Frame oculto (guarda a tabela)
            frame = ctk.CTkFrame(self.content_container, fg_color="transparent")
            self.tab_frames[tab_name] = frame
            
            # Tabela (Treeview)
            style = ttk.Style(self)
            style.theme_use("default")
            style.configure("Treeview", background="#21252B", foreground="white", rowheight=28, fieldbackground="#21252B", borderwidth=0, font=("Segoe UI", 10))
            style.map('Treeview', background=[('selected', '#007EA7')])
            style.configure("Treeview.Heading", background="#2C313A", foreground="white", relief="flat", font=("Segoe UI", 10, "bold"))
            
            scroll_y = ttk.Scrollbar(frame)
            scroll_y.pack(side="right", fill="y")
            scroll_x = ttk.Scrollbar(frame, orient="horizontal")
            scroll_x.pack(side="bottom", fill="x")
            
            tree = ttk.Treeview(frame, columns=columns, show="headings", yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
            
            for col in columns:
                tree.heading(col, text=col)
                # stretch=False garante que as colunas fiquem com um tamanho fixo (igual Excel) e não elásticas
                tree.column(col, minwidth=50, width=150, anchor="center", stretch=False)
            
            tree.pack(fill="both", expand=True)
            scroll_y.config(command=tree.yview)
            scroll_x.config(command=tree.xview)
            
            # Inteligência do Excel (duplo clique no cabeçalho ou separador)
            tree.bind("<Double-1>", lambda event, t=tree: self.on_tree_double_click(event, t))
            
            self.treeviews[tab_name] = tree

            # Controle da quebra de linha
            col_idx += 1
            if col_idx >= colunas_por_linha:
                col_idx = 0
                row_idx += 1

        # Seleciona a primeira aba por padrão
        self.select_tab(list(self.tab_columns.keys())[0])

    def select_tab(self, tab_name):
        """Gerencia a troca de abas no nosso sistema customizado multi-line"""
        if self.current_tab:
            self.tab_frames[self.current_tab].pack_forget()
            self.tab_buttons[self.current_tab].configure(fg_color="#1C2833") 
            
        self.tab_frames[tab_name].pack(fill="both", expand=True)
        self.tab_buttons[tab_name].configure(fg_color="#007EA7") 
        self.current_tab = tab_name

    def on_tree_double_click(self, event, tree):
        """ Auto-ajusta a largura da coluna (estilo Excel) ao dar duplo clique no cabeçalho ou separador """
        region = tree.identify_region(event.x, event.y)
        if region in ("separator", "heading"):
            col_id = tree.identify_column(event.x)
            if not col_id: return
            
            col_idx = int(col_id.replace('#', '')) - 1
            col_name = tree["columns"][col_idx]
            
            # Largura base calculada pelo tamanho do título da coluna
            max_width = len(str(col_name)) * 9 + 30
            
            for item in tree.get_children():
                valor = str(tree.set(item, col_name))
                tamanho = len(valor) * 8 + 30
                if tamanho > max_width:
                    max_width = tamanho
            
            # Limita a 600 pixels para evitar colunas gigantescas
            tree.column(col_name, width=min(max_width, 600))

    def on_clear(self):
        self.input_text.delete("1.0", "end")
        self.status_label.configure(text="Status: Limpo")
        for tree in self.treeviews.values():
            tree.delete(*tree.get_children())

    def on_translate(self):
        # Limpa tabelas atuais
        for tree in self.treeviews.values():
            tree.delete(*tree.get_children())
            
        text = self.input_text.get("1.0", "end-1c").strip()
        if not text:
            messagebox.showwarning("Aviso", "Por favor, cole uma ou mais strings para traduzir.")
            return

        hex_pattern = re.compile(
            r"((?:78[-\s]*78|79[-\s]*79)(?:[-\s]*[0-9A-Fa-f][-\s]*[0-9A-Fa-f]){5,500}?(?:[-\s]*0D[-\s]*0A|[-\s]*0d[-\s]*0a)|7E(?:[-\s]*[0-9A-Fa-f][-\s]*[0-9A-Fa-f]){10,500}?[-\s]*7E)",
            re.IGNORECASE
        )
        
        lines = text.splitlines()
        count = 0
        
        for line in lines:
            line = line.strip()
            if not line: continue

            hex_match = hex_pattern.search(line)
            raw = hex_match.group(1) if hex_match else line
            clean_hex = raw.replace(" ", "").replace("-", "").upper()
            
            if len(clean_hex) < 10: continue
            count += 1
            
            # Roteamento baseado no seu TrackerParserApp original
            start_bit = clean_hex[0:4]
            tab_target = "Outros"
            translated_info = ["Não Traduzido"]
            protocol = ""

            if clean_hex.startswith("7E"):
                msg_id = clean_hex[2:6]
                if msg_id == "0200":
                    tab_target = "TAG JT808 (0200)"
                    translated_info = parse_jt808_0200(clean_hex)
                else:
                    tab_target = "Outros"
                    translated_info = [f"JT808 {msg_id}"]
            else:
                if start_bit == "7979":
                    packet_len = clean_hex[4:8]
                    protocol = clean_hex[8:10]
                else:
                    packet_len = clean_hex[4:6]
                    protocol = clean_hex[6:8]

                if ((start_bit == "7878" and packet_len == "05") or (start_bit == "7979" and packet_len == "0005")) and protocol != "8A":
                    tab_target = "ACKs (Servidor)"
                    serie_hex = clean_hex[-12:-8] if len(clean_hex) >= 12 else ""
                    serie_dec = int(serie_hex, 16) if serie_hex else 0
                    translated_info = ["ACK", str(serie_dec)]
                elif protocol == "01":
                    tab_target = "Login (0x01)"
                    translated_info = parse_login_01(clean_hex)
                elif protocol == "60":
                    tab_target = "Location (0x60)"
                    translated_info = parse_location_60(clean_hex)
                elif protocol == "61":
                    tab_target = "Location (0x61)"
                    translated_info = parse_location_61(clean_hex)
                elif protocol == "22":
                    tab_target = "Location (0x22)"
                    translated_info = parse_location_22(clean_hex)
                elif protocol == "12":
                    if packet_len == "1F": 
                        tab_target = "TAG Loc (0x12)"
                        translated_info = parse_tag_location_12(clean_hex)
                    else: 
                        tab_target = "Location (0x12)"
                        translated_info = parse_location_12(clean_hex)
                elif protocol == "32":
                    tab_target = "TAG Loc (0x32)"
                    translated_info = parse_tag_location_32(clean_hex)
                elif protocol == "13":
                    tab_target = "Heartbeat (0x13)"
                    translated_info = parse_heartbeat_13(clean_hex)
                elif protocol == "17":  
                    tab_target = "RFID (0x17)"  
                    translated_info = parse_rfid_17(clean_hex)  
                elif protocol in ["16", "26"]:
                    tab_target = "Alarm (0x16, 0x26)"
                    translated_info = parse_alarm_16_26(clean_hex)
                elif protocol in ["15", "21", "80"]:
                    tab_target = "CMD (0x15, 0x21, 0x80)"
                    translated_info = parse_cmd_15_21_80(clean_hex)
                elif protocol == "94":
                    tab_target = "Ext Voltage (0x94)"
                    translated_info = parse_ext_voltage_94(clean_hex)
                else:
                    tab_target = "Outros"
                    translated_info = [str(clean_hex)]
            
            # --- NOVO: Pular pacotes incompletos ou de tamanho inválido ---
            if any(erro in translated_info for erro in ["Incompleto", "Pacote Incompleto", "Tamanho Inválido"]):
                count -= 1  # Reverte a contagem de sucesso desta linha
                continue
            # --------------------------------------------------------------
            
            # Monta a linha ("String Bruta", "Protocolo" e o Resto da tradução)
            row_data = [raw.strip(), protocol]
            row_data.extend(translated_info)
            
            # Preenche o resto com vazio se faltar
            expected_cols = len(self.tab_columns[tab_target])
            while len(row_data) < expected_cols:
                row_data.append("")
                
            tuple_data = tuple(row_data[:expected_cols])
            self.treeviews[tab_target].insert("", "end", values=tuple_data)
            
            # Auto-seleciona a primeira aba útil encontrada
            if count == 1:
                self.select_tab(tab_target)

        if count == 0:
            self.status_label.configure(text="Status: Nada encontrado")
            messagebox.showinfo("Resultado", "Nenhum pacote hexadecimal válido encontrado no texto.")
        else:
            self.status_label.configure(text=f"Status: {count} linha(s) processada(s)")

    def on_export(self):
        """Exporta os resultados da aba atual para um arquivo CSV/Excel"""
        if not self.current_tab:
            return
            
        tree = self.treeviews[self.current_tab]
        if not tree.get_children():
            messagebox.showwarning("Aviso", f"A aba '{self.current_tab}' está vazia.")
            return
            
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv", 
            filetypes=[("Arquivos CSV (Abre no Excel)", "*.csv")], 
            title=f"Exportar - {self.current_tab}"
        )
        
        if filepath:
            try:
                with open(filepath, mode='w', newline='', encoding='utf-8-sig') as file:
                    # Usamos ponto-e-vírgula porque o Excel no Brasil reconhece direto
                    writer = csv.writer(file, delimiter=';') 
                    
                    # Cabeçalhos
                    columns = self.tab_columns[self.current_tab]
                    writer.writerow(columns)
                    
                    # Dados
                    for item in tree.get_children():
                        values = tree.item(item, "values")
                        writer.writerow(values)
                        
                messagebox.showinfo("Sucesso", "Aba exportada com sucesso!")
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao exportar arquivo: {e}")

def show_string_translator(parent_window):
    """Função pública que será chamada pelo actions_frame.py para exibir a janela."""
    dialog = StringTranslatorDialog(parent_window)
    return dialog