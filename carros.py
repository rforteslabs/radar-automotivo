#!/usr/bin/env python3
import requests
import csv
import json
import urllib3
import os
from datetime import date, datetime
import logging
import configparser
import time
import random
import gspread
import pandas as pd
from gspread_dataframe import set_with_dataframe

# --- LOGGING CONFIGURATION ---
# Remove existing handlers to avoid duplicate logs
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler("anuncios.log"),
        logging.StreamHandler()
    ]
)

# --- CONFIGURATION ---
config = configparser.ConfigParser()
config.read('config.ini')
BASE_URL = config['API']['BASE_URL']
# Desativar avisos de SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# --- DATA PROCESSING FUNCTIONS ---

def get_ads_from_google_sheet(sheet_name, worksheet_name):
    """Reads an existing Google Sheet and returns a dictionary of ads keyed by ID."""
    logging.info(f"Buscando dados existentes da planilha '{sheet_name}', aba '{worksheet_name}'...")
    try:
        gc = gspread.service_account(filename='credentials.json')
        spreadsheet = gc.open(sheet_name)
        worksheet = spreadsheet.worksheet(worksheet_name)
        
        all_records = worksheet.get_all_records()
        
        existing_ads = {}
        for row in all_records:
            if row.get('ID'):
                existing_ads[str(row['ID'])] = {k: str(v) for k, v in row.items()}
        
        logging.info(f"Encontrados {len(existing_ads)} anúncios existentes na planilha.")
        return existing_ads

    except Exception as e:
        logging.error(f"Erro ao ler dados do Google Sheets: {e}")
        logging.warning("Continuando a execução com uma base de dados vazia.")
        return {}

def write_to_google_sheet(all_data, sheet_name, worksheet_name):
    """Conecta ao Google Sheets e atualiza a planilha com os dados fornecidos."""
    if not all_data:
        logging.warning("Nenhum dado para escrever na planilha.")
        return

    try:
        logging.info("Autenticando com o Google Sheets...")
        gc = gspread.service_account(filename='credentials.json')
        
        logging.info(f"Abrindo a planilha '{sheet_name}' e a aba '{worksheet_name}'...")
        spreadsheet = gc.open(sheet_name)
        worksheet = spreadsheet.worksheet(worksheet_name)
        
        df = pd.DataFrame(all_data)

        if 'Teve Alteração de Preço' in df.columns:
            df['Teve Alteração de Preço'] = df['Teve Alteração de Preço'].astype(str)

        logging.info("Limpando a aba e enviando os novos dados...")
        worksheet.clear()
        set_with_dataframe(worksheet, df)
        logging.info("Planilha atualizada com sucesso!")

    except FileNotFoundError:
        logging.error("Erro: O arquivo 'credentials.json' não foi encontrado.")
    except gspread.exceptions.SpreadsheetNotFound:
        logging.error(f"Erro: A planilha '{sheet_name}' não foi encontrada.")
    except gspread.exceptions.WorksheetNotFound:
        logging.error(f"Erro: A aba '{worksheet_name}' não foi encontrada na planilha.")
    except Exception as e:
        logging.error(f"Ocorreu um erro inesperado ao tentar escrever no Google Sheets: {e}")

def fetch_all_new_ads(search_term, pausa_min, pausa_max):
    """Fetches all ads from the API for a given search term."""
    all_vehicles = []
    try:
        initial_url = f"{BASE_URL}?q={search_term}&page=1"
        response = requests.get(initial_url, verify=False)
        response.raise_for_status()
        initial_data = response.json()
        total_pages = initial_data.get('offers', {}).get('pages', 1)
        logging.info(f"Total de páginas a serem processadas: {total_pages}")
    except (requests.RequestException, json.JSONDecodeError) as e:
        logging.error(f"Erro ao obter o número total de páginas: {e}")
        return []

    for page in range(1, total_pages + 1):
        url = f"{BASE_URL}?q={search_term}&page={page}"
        try:
            response = requests.get(url, verify=False)
            response.raise_for_status()
            data = response.json()
            all_vehicles.extend(data.get('offers', {}).get('items', []))
            logging.info(f"Página {page} de {total_pages} processada.")
            time.sleep(random.uniform(pausa_min, pausa_max))
        except (requests.RequestException, json.JSONDecodeError) as e:
            logging.error(f"Erro ao processar a página {page}: {e}")
            continue
    return all_vehicles

def process_vehicle_data(vehicle, today_str):
    """Processes raw vehicle data from API into a structured dictionary."""
    owner_info = vehicle.get('owner', {})
    is_personal = owner_info.get('isPersonal', False)
    is_concessionaria = owner_info.get('isConcessionaria', False)
    
    seller_type = 'Revenda'
    if is_personal: seller_type = 'Particular'
    elif is_concessionaria: seller_type = 'Concessionária'

    price_numeric = 0.0
    try:
        price_numeric = float(vehicle.get('priceCurrency', '').replace("R$ ", "").replace(".", "").replace(",", "."))
    except (ValueError, TypeError):
        pass

    custo_por_km = "N/A"
    km_anual = "N/A"
    try:
        km_numeric = int(vehicle.get('km', ''))
        year_numeric = int(vehicle.get('year', ''))
        if km_numeric > 0:
            custo_por_km = round(price_numeric / km_numeric, 2)
        
        current_year = date.today().year
        age = current_year - year_numeric
        if age > 0: km_anual = int(km_numeric / age)
        elif age == 0: km_anual = km_numeric
    except (ValueError, TypeError, ZeroDivisionError):
        pass

    # Process 'options' and 'addons' into comma-separated strings
    options_list = vehicle.get('options', [])
    opcionais_str = ", ".join([opt.get('label', '') for opt in options_list if opt.get('label')])

    addons_list = vehicle.get('addons', [])
    adicionais_str = ", ".join([add.get('label', '') for add in addons_list if add.get('label')])

    # --- Start of WhatsApp extraction logic ---
    whatsapp_number = ''
    if owner_info.get('whatsapp'):
        whatsapp_number = owner_info.get('whatsapp')
    elif vehicle.get('whatsapp'):
        whatsapp_number = vehicle.get('whatsapp')
    elif owner_info.get('phone'):
        whatsapp_number = owner_info.get('phone')
    elif vehicle.get('phone'):
        whatsapp_number = vehicle.get('phone')
    # --- End of WhatsApp extraction logic ---

    return {
        'ID': str(vehicle.get('offerId', '')),
        'Marca': vehicle.get('brand', ''),
        'Modelo': f"{vehicle.get('brand', '')} {vehicle.get('model', '')}",
        'Veículo': f"{vehicle.get('brand', '')} {vehicle.get('model', '')} {vehicle.get('version', '')}",
        'Ano': vehicle.get('year', ''),
        'Ano Fabricação': vehicle.get('yearManufacture', ''),
        'Preço': vehicle.get('priceCurrency', ''),
        'KM': vehicle.get('km', ''),
        'Câmbio': vehicle.get('gear', ''),
        'Combustível': vehicle.get('fuel', ''),
        'Cor': vehicle.get('color', ''),
        'Vendedor': owner_info.get('name', ''),
        'Tipo de Vendedor': seller_type,
        'Localização': f"{owner_info.get('address', {}).get('city', '')}/{owner_info.get('address', {}).get('country', '')}",
        'Link': vehicle.get('link', ''),
        'Descrição': vehicle.get('description', ''),
        'Opcionais': opcionais_str,
        'Adicionais': adicionais_str,
        'Visualizações': vehicle.get('views', ''),
        'Data da Coleta': today_str,
        'Last Check': today_str,
        'Anúncio Removido em': 'Anúncio ativo',
        'Vendido em x dias': '',
        'Dias Anunciado': 0,
        'Faixa de Preço': get_price_range(vehicle.get('priceCurrency', '')),
        'Histórico de Preço': '',
        'Teve Alteração de Preço': False,
        'Variação de Preço': 'Manteve',
        'Diferença de Preço': 0,
        'Custo por KM': custo_por_km,
        'KM Anual': km_anual,
        'WhatsApp': whatsapp_number, # Add the new field here
        'Placa': vehicle.get('licensePlate', '') # Supondo que a API forneça 'licensePlate'
    }

def get_price_range(price_str):
    """Converts a price string to a number and returns its price range category."""
    try:
        price_numeric = float(price_str.replace("R$ ", "").replace(".", "").replace(",", "."))
    except (ValueError, AttributeError):
        return "Preço inválido"

    ranges = {
        40000: "ATÉ 40 MIL", 50000: "DE 40 MIL A 50 MIL", 60000: "DE 50 MIL A 60 MIL", 
        70000: "DE 60 MIL A 70 MIL", 80000: "DE 70 MIL A 80 MIL", 90000: "DE 80 MIL A 90 MIL", 
        100000: "DE 90 MIL A 100 MIL", 120000: "DE 100 MIL A 120 MIL", 150000: "DE 150 MIL A 200 MIL", 200000: "DE 150 MIL A 200 MIL"
    }
    for limit, label in ranges.items():
        if price_numeric <= limit:
            return label
    return "MAIS DE 200 MIL"

def write_csv(filename, all_data):
    """Writes the final list of ads to the CSV file."""
    if not all_data:
        logging.warning("Nenhum dado para escrever.")
        return

    headers = [
        'ID', 'Marca', 'Modelo', 'Veículo', 'Ano', 'Preço', 'KM', 'Câmbio', 'Combustível', 'Cor', 
        'Vendedor', 'Tipo de Vendedor', 'Localização', 'Link', 'Data da Coleta', 
        'Last Check', 'Anúncio Removido em', 'Status', 'Vendido em x dias', 'Dias Anunciado', 'Faixa de Preço', 'Histórico de Preço', 'Teve Alteração de Preço',
        'Variação de Preço', 'Diferença de Preço', 'Custo por KM', 'KM Anual',
        'WhatsApp', 'Placa' # Adicionado o campo Placa
    ]
    
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(all_data)
    except IOError as e:
        logging.error(f"Erro ao escrever no arquivo CSV: {e}")


# --- MAIN EXECUTION ---
if __name__ == "__main__":
    # 1. Configuration
    brands_filename = "marcas.txt"
    today_str = date.today().strftime('%Y-%m-%d')

    PAUSA_MIN_PAGINA = config.getfloat('API', 'PAUSA_MIN_PAGINA', fallback=0.5)
    PAUSA_MAX_PAGINA = config.getfloat('API', 'PAUSA_MAX_PAGINA', fallback=1.5)
    PAUSA_MIN_MARCA = config.getfloat('API', 'PAUSA_MIN_MARCA', fallback=2.0)
    PAUSA_MAX_MARCA = config.getfloat('API', 'PAUSA_MAX_MARCA', fallback=5.0)
    NOME_PLANILHA = config.get('API', 'NOME_PLANILHA', fallback='Anuncio_Veiculos')
    NOME_ABA = config.get('API', 'NOME_ABA', fallback='Carros')

    logging.info(f"--- INICIANDO EXECUÇÃO AUTOMATIZADA ---")

    # 2. Read list of brands to search
    try:
        with open(brands_filename, 'r', encoding='utf-8') as f:
            brands_to_search = [line.strip() for line in f if line.strip()]
        logging.info(f"Carregadas {len(brands_to_search)} marcas do arquivo {brands_filename}.")
    except FileNotFoundError:
        logging.error(f"Arquivo {brands_filename} não encontrado. Saindo.")
        exit()

    # 3. Read all existing ads from Google Sheets
    ads_database = get_ads_from_google_sheet(NOME_PLANILHA, NOME_ABA)

    # 4. Setup for processing loop
    all_fetched_ids = set()
    processed_ad_ids = set()
    total_new_ads, total_updated_ads, total_removed_ads, total_price_changes = 0, 0, 0, 0

    # 5. Main loop - iterate through each brand
    for brand in brands_to_search:
        logging.info(f"--- Buscando marca: {brand.upper()} ---")
        newly_fetched_ads_raw = fetch_all_new_ads(brand, PAUSA_MIN_PAGINA, PAUSA_MAX_PAGINA)
        logging.info(f"Encontrados {len(newly_fetched_ads_raw)} anúncios na API para {brand}.")

        for ad_raw in newly_fetched_ads_raw:
            ad_id = str(ad_raw.get('offerId', ''))
            if not ad_id or ad_id in processed_ad_ids:
                continue
            
            processed_ad_ids.add(ad_id)
            all_fetched_ids.add(ad_id)

            # Process data
            new_ad_data = process_vehicle_data(ad_raw, today_str)
            
            is_new = ad_id not in ads_database
            old_ad_data = ads_database.get(ad_id, {})

            if is_new:
                ads_database[ad_id] = new_ad_data
                total_new_ads += 1
            else:
                # Merge existing data
                old_price_str = old_ad_data.get('Preço', '')
                new_price_str = new_ad_data.get('Preço', '')

                # Preserve the history of price changes. Value from CSV is a string.
                had_price_change_before = old_ad_data.get('Teve Alteração de Preço') == 'True'
                new_ad_data['Teve Alteração de Preço'] = had_price_change_before
                new_ad_data['Variação de Preço'] = old_ad_data.get('Variação de Preço', 'Manteve')
                new_ad_data['Diferença de Preço'] = old_ad_data.get('Diferença de Preço', 0)

                if old_price_str and new_price_str and old_price_str != new_price_str:
                    old_history = old_ad_data.get('Histórico de Preço', '')
                    new_change_record = f"de {old_price_str} para {new_price_str} em {today_str}"
                    
                    if old_history:
                        new_ad_data['Histórico de Preço'] = f"{old_history}\n{new_change_record}"
                    else:
                        new_ad_data['Histórico de Preço'] = new_change_record
                    
                    new_ad_data['Teve Alteração de Preço'] = True
                    total_price_changes += 1

                    try:
                        old_price_numeric = float(old_price_str.replace("R$ ", "").replace(".", "").replace(",", "."))
                        new_price_numeric = float(new_price_str.replace("R$ ", "").replace(".", "").replace(",", "."))
                        price_difference = new_price_numeric - old_price_numeric
                        new_ad_data['Diferença de Preço'] = price_difference
                        
                        if price_difference > 0:
                            new_ad_data['Variação de Preço'] = 'Aumentou'
                        else:
                            new_ad_data['Variação de Preço'] = 'Baixou'
                    except (ValueError, TypeError):
                        new_ad_data['Diferença de Preço'] = 'Erro'
                        new_ad_data['Variação de Preço'] = 'Erro'
                else:
                    new_ad_data['Histórico de Preço'] = old_ad_data.get('Histórico de Preço', '')
                
                new_ad_data['Data da Coleta'] = old_ad_data.get('Data da Coleta', today_str)
                new_ad_data['Vendido em x dias'] = old_ad_data.get('Vendido em x dias', '')

                try:
                    data_coleta = datetime.strptime(new_ad_data['Data da Coleta'], '%Y-%m-%d').date()
                    new_ad_data['Dias Anunciado'] = (date.today() - data_coleta).days
                except (ValueError, KeyError):
                    new_ad_data['Dias Anunciado'] = 'Erro no cálculo'
                
                ads_database[ad_id] = new_ad_data
                total_updated_ads += 1
        
        logging.info(f"Marca {brand.upper()} processada. Pausando de {PAUSA_MIN_MARCA} a {PAUSA_MAX_MARCA} segundos...")
        time.sleep(random.uniform(PAUSA_MIN_MARCA, PAUSA_MAX_MARCA))

    # 6. Handle removed ads
    for ad_id, ad_data in ads_database.items():
        if ad_id not in all_fetched_ids and ad_data.get('Anúncio Removido em') == 'Anúncio ativo':
            ad_data['Anúncio Removido em'] = today_str
            try:
                data_coleta = datetime.strptime(ad_data['Data da Coleta'], '%Y-%m-%d').date()
                ad_data['Vendido em x dias'] = (date.today() - data_coleta).days
            except (ValueError, KeyError):
                ad_data['Vendido em x dias'] = 'Erro no cálculo'
            total_removed_ads += 1

    # 7. Write final data to Google Sheet
    final_list = list(ads_database.values())

    for ad_data in final_list:
        if ad_data.get('Anúncio Removido em', 'Anúncio ativo') == 'Anúncio ativo':
            ad_data['Status'] = 'Ativo'
        else:
            ad_data['Status'] = 'Removido'

        current_value = ad_data.get('Teve Alteração de Preço')
        is_true = (current_value == 'True') or (current_value is True)
        ad_data['Teve Alteração de Preço'] = is_true

    write_to_google_sheet(final_list, NOME_PLANILHA, NOME_ABA)

    # 8. Log and print summary
    summary_header = "\n--- Resumo da Execução Automatizada ---"
    summary_new = f"{total_new_ads} novos anúncios foram adicionados."
    summary_updated = f"{total_updated_ads} anúncios existentes foram atualizados."
    summary_price_change = f"{total_price_changes} anúncios tiveram o valor alterado."
    summary_removed = f"{total_removed_ads} anúncios foram marcados como removidos."
    summary_total = f"Total de anúncios no arquivo: {len(final_list)}."
    summary_file = f"Planilha '{NOME_PLANILHA}' foi atualizada com sucesso."

    print(summary_header)
    print(summary_new)
    print(summary_updated)
    print(summary_price_change)
    print(summary_removed)
    print(summary_total)
    print(summary_file)

    logging.info("--- RESUMO DA EXECUÇÃO ---")
    logging.info(summary_new)
    logging.info(summary_updated)
    logging.info(summary_price_change)
    logging.info(summary_removed)
    logging.info(summary_total)
    logging.info(summary_file)
    logging.info("--- FIM DA EXECUÇÃO AUTOMATIZADA ---")
