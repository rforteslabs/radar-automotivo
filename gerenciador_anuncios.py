#!/usr/bin/env python3
import requests
import csv
import json
import urllib3
import os
from datetime import date, datetime
import logging
import configparser

# --- LOGGING CONFIGURATION ---
logging.basicConfig(
    filename='anuncios.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- CONFIGURATION ---
config = configparser.ConfigParser()
config.read('config.ini')
BASE_URL = config['API']['BASE_URL']
# Desativar avisos de SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- FUNCTIONS ---

def get_existing_ads(filename):
    """Reads an existing CSV file and returns a dictionary of ads keyed by ID."""
    if not os.path.exists(filename):
        return {}
    
    existing_ads = {}
    try:
        with open(filename, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row.get('ID'):
                    existing_ads[row['ID']] = row
    except (IOError, csv.Error) as e:
        logging.error(f"Erro ao ler o arquivo CSV existente: {e}")
        return {}
    return existing_ads

def fetch_all_new_ads(search_term):
    """Fetches all ads from the API for a given search term."""
    all_vehicles = []
    try:
        initial_url = f"{BASE_URL}?q={search_term}&page=1"
        response = requests.get(initial_url, verify=False)
        response.raise_for_status() # Raise an exception for bad status codes
        initial_data = response.json()
        total_pages = initial_data.get('offers', {}).get('pages', 1)
        logging.info(f"Total de páginas a serem processadas: {total_pages}")
    except (requests.RequestException, json.JSONDecodeError) as e:
        logging.error(f"Erro ao obter o número total de páginas: {e}")
        return [] # Return empty list on failure

    for page in range(1, total_pages + 1):
        url = f"{BASE_URL}?q={search_term}&page={page}"
        try:
            response = requests.get(url, verify=False)
            response.raise_for_status()
            data = response.json()
            all_vehicles.extend(data.get('offers', {}).get('items', []))
            logging.info(f"Página {page} de {total_pages} processada.")
        except (requests.RequestException, json.JSONDecodeError) as e:
            logging.error(f"Erro ao processar a página {page}: {e}")
            continue
    return all_vehicles

def process_vehicle_data(vehicle, today_str):
    """Processes raw vehicle data from API into a structured dictionary."""
    owner_info = vehicle.get('owner', {})
    is_personal = owner_info.get('isPersonal', False)
    is_concessionaria = owner_info.get('isConcessionaria', False)
    
    if is_personal:
        seller_type = 'Particular'
    elif is_concessionaria:
        seller_type = 'Concessionária'
    else:
        seller_type = 'Revenda'

    # --- New Metric Calculations ---
    custo_por_km = "N/A"
    km_anual = "N/A"
    try:
        price_numeric = float(vehicle.get('priceCurrency', '').replace("R$ ", "").replace(".", "").replace(",", "."))
        km_numeric = int(vehicle.get('km', ''))
        year_numeric = int(vehicle.get('year', ''))

        # Calculate Custo por KM
        if km_numeric > 0:
            custo_por_km = round(price_numeric / km_numeric, 2)
        
        # Calculate KM Anual
        current_year = date.today().year
        age = current_year - year_numeric
        if age > 0:
            km_anual = int(km_numeric / age)
        elif age == 0:
            km_anual = km_numeric
            
    except (ValueError, TypeError, ZeroDivisionError):
        pass # Values will remain "N/A"

    return {
        'ID': str(vehicle.get('offerId', '')),
        'Marca': vehicle.get('brand', ''),
        'Modelo': f"{vehicle.get('brand', '')} {vehicle.get('model', '')}",
        'Veículo': f"{vehicle.get('brand', '')} {vehicle.get('model', '')} {vehicle.get('version', '')}",
        'Ano': vehicle.get('year', ''),
        'Preço': vehicle.get('priceCurrency', ''),
        'KM': vehicle.get('km', ''),
        'Câmbio': vehicle.get('gear', ''),
        'Combustível': vehicle.get('fuel', ''),
        'Cor': vehicle.get('color', ''),
        'Vendedor': owner_info.get('name', ''),
        'Tipo de Vendedor': seller_type,
        'Localização': f"{owner_info.get('address', {}).get('city', '')}/{owner_info.get('address', {}).get('country', '')}",
        'Link': vehicle.get('link', ''),
        'Data da Coleta': today_str,
        'Last Check': today_str,
        'Anúncio Removido em': 'Anúncio ativo',
        'Vendido em x dias': '',
        'Dias Anunciado': 0,
        'Faixa de Preço': get_price_range(vehicle.get('priceCurrency', '')),
        'Histórico de Preço': '',
        'Custo por KM': custo_por_km,
        'KM Anual': km_anual
    }

def get_price_range(price_str):
    """Converts a price string to a number and returns its price range category."""
    try:
        price_numeric = float(price_str.replace("R$ ", "").replace(".", "").replace(",", "."))
    except (ValueError, AttributeError):
        return "Preço inválido"

    if price_numeric <= 30000:
        return "ATÉ 30 MIL"
    elif price_numeric <= 40000:
        return "DE 30 MIL A 40 MIL"
    elif price_numeric <= 50000:
        return "DE 40 MIL A 50 MIL"
    elif price_numeric <= 60000:
        return "DE 50 MIL A 60 MIL"
    elif price_numeric <= 70000:
        return "DE 60 MIL A 70 MIL"
    elif price_numeric <= 80000:
        return "DE 70 MIL A 80 MIL"
    elif price_numeric <= 90000:
        return "DE 80 MIL A 90 MIL"
    elif price_numeric <= 100000:
        return "DE 90 MIL A 100 MIL"
    else:
        return "MAIS DE 100 MIL"

def write_csv(filename, all_data):
    """Writes the final list of ads to the CSV file."""
    if not all_data:
        logging.warning("Nenhum dado para escrever.")
        return

    headers = [
        'ID', 'Marca', 'Modelo', 'Veículo', 'Ano', 'Preço', 'KM', 'Câmbio', 'Combustível', 'Cor', 
        'Vendedor', 'Tipo de Vendedor', 'Localização', 'Link', 'Data da Coleta', 
        'Last Check', 'Anúncio Removido em', 'Vendido em x dias', 'Dias Anunciado', 'Faixa de Preço', 'Histórico de Preço', 'Custo por KM', 'KM Anual'
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
    search_term = input("Digite o modelo do veículo a ser buscado: ")
    output_filename = f'{search_term.lower().replace(" ", "_")}.csv'
    today_str = date.today().strftime('%Y-%m-%d')

    logging.info(f"--- INICIANDO BUSCA PARA: {search_term.upper()} ---")

    # 1. Read existing data
    existing_ads = get_existing_ads(output_filename)
    logging.info(f"Encontrados {len(existing_ads)} anúncios no arquivo {output_filename}.")

    # 2. Fetch new data
    newly_fetched_ads_raw = fetch_all_new_ads(search_term)
    
    newly_fetched_ids = {
        str(ad.get('offerId')) for ad in newly_fetched_ads_raw if ad.get('offerId')
    }
    logging.info(f"Encontrados {len(newly_fetched_ids)} anúncios na API.")

    final_data = []
    new_ads_count = 0
    updated_ads_count = 0
    removed_ads_count = 0
    price_change_count = 0

    # 3. Compare and merge
    # Handle new and updated ads
    for ad_raw in newly_fetched_ads_raw:
        ad_id = str(ad_raw.get('offerId'))
        if not ad_id:
            continue

        if ad_id in existing_ads:
            # It's an existing ad.
            original_ad_data = existing_ads[ad_id]
            
            # Process the new data to get all fresh fields
            updated_ad = process_vehicle_data(ad_raw, today_str)
            
            # --- PRICE CHANGE LOGIC ---
            old_price_str = original_ad_data.get('Preço', '')
            new_price_str = updated_ad.get('Preço', '')
            
            # Check if price has changed
            if old_price_str and new_price_str and old_price_str != new_price_str:
                # Price has changed, create the history string with today's date
                history_string = f"de {old_price_str} para {new_price_str} em {today_str}"
                updated_ad['Histórico de Preço'] = history_string
                price_change_count += 1
            else:
                # Price is the same, carry over old history if it exists
                updated_ad['Histórico de Preço'] = original_ad_data.get('Histórico de Preço', '')
            # --- END PRICE CHANGE LOGIC ---

            # Preserve historical data
            updated_ad['Data da Coleta'] = original_ad_data.get('Data da Coleta', today_str)
            updated_ad['Vendido em x dias'] = original_ad_data.get('Vendido em x dias', '')

            # Recalculate active days
            try:
                data_coleta = datetime.strptime(updated_ad['Data da Coleta'], '%Y-%m-%d').date()
                data_atual = date.today()
                delta = data_atual - data_coleta
                updated_ad['Dias Anunciado'] = delta.days
            except (ValueError, KeyError):
                updated_ad['Dias Anunciado'] = 'Erro no cálculo'

            final_data.append(updated_ad)
            updated_ads_count += 1
        else:
            # It's a new ad
            new_ad = process_vehicle_data(ad_raw, today_str)
            final_data.append(new_ad)
            new_ads_count += 1

    # Handle removed ads
    for ad_id, ad_data in existing_ads.items():
        if ad_id not in newly_fetched_ids:
            # This ad was removed
            removed_ad = ad_data
            if removed_ad.get('Anúncio Removido em') == 'Anúncio ativo':
                removed_ad['Anúncio Removido em'] = today_str
                try:
                    data_coleta = datetime.strptime(removed_ad['Data da Coleta'], '%Y-%m-%d').date()
                    data_remocao = date.today()
                    delta = data_remocao - data_coleta
                    removed_ad['Vendido em x dias'] = delta.days
                except (ValueError, KeyError):
                    removed_ad['Vendido em x dias'] = 'Erro no cálculo'
                removed_ads_count += 1
            final_data.append(removed_ad)

    # 4. Write back to CSV
    write_csv(output_filename, final_data)

    # --- Log and print summary ---
    summary_header = "\n--- Resumo da Execução ---"
    summary_new = f"{new_ads_count} novos anúncios foram adicionados."
    summary_updated = f"{updated_ads_count} anúncios existentes foram atualizados."
    summary_price_change = f"{price_change_count} anúncios tiveram o valor alterado."
    summary_removed = f"{removed_ads_count} anúncios foram marcados como removidos."
    summary_total = f"Total de anúncios no arquivo: {len(final_data)}."
    summary_file = f"Arquivo '{output_filename}' foi atualizado com sucesso."

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
    logging.info("--- FIM DA BUSCA ---")
