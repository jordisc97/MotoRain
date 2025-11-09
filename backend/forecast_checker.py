import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json
from difflib import get_close_matches

class MeteoCatTemperatureScraper:
    """A scraper for meteo.cat to get weather forecast data for municipalities in Catalonia."""
    def __init__(self, municipalities_json_path='municipalities.json'):
        """Initializes the MeteoCatTemperatureScraper.

        Args:
            municipalities_json_path (str): The path to the JSON file containing
                municipalities data.
        """
        self.base_url = "https://www.meteo.cat/prediccio/municipal/"
        with open(municipalities_json_path, 'r', encoding='utf-8') as f:
            municipalities = json.load(f)
        
        self.municipalities_df = pd.DataFrame(municipalities)
        self.municipalities_df["nom_lower"] = self.municipalities_df["nom"].str.lower()

    def get_municipality_record(self, name: str) -> dict:
        """Finds a municipality record from the local JSON file.

        It uses fuzzy string matching to find the closest match for the given
        municipality name.

        Args:
            name: The name of the municipality to search for.

        Returns:
            A dictionary containing the municipality record, including codi, nom,
            coordenades, comarca, and slug.

        Raises:
            ValueError: If no municipality is found close to the given name.
        """
        name_lower = name.lower()
        matches = get_close_matches(name_lower, self.municipalities_df["nom_lower"], n=1, cutoff=0.6)
        if not matches:
            raise ValueError(f"No municipality found close to '{name}'")

        matched_name = matches[0]
        row = self.municipalities_df.loc[self.municipalities_df["nom_lower"] == matched_name].iloc[0]

        return {
            "codi": row["codi"],
            "nom": row["nom"],
            "coordenades": {
                "latitud": row["coordenades"]["latitud"],
                "longitud": row["coordenades"]["longitud"],
            },
            "comarca": {
                "codi": row["comarca"]["codi"],
                "nom": row["comarca"]["nom"],
            },
            "slug": row.get("slug"),
        }
    
    def scrape_weather_data_by_code(self, municipality_code: str) -> pd.DataFrame:
        """Scrapes weather data for a given municipality code from meteo.cat.

        It retrieves the forecast for today, tomorrow, and the day after tomorrow,
        parsing the HTML to extract temperature, precipitation, and wind data
        at different times of the day.

        Args:
            municipality_code: The official code of the municipality.

        Returns:
            A pandas DataFrame with the weather forecast for the next 3 days.
            The DataFrame includes columns for City, Day, Time, 
            'Temperatura (°C)', 'Precipitació acumulada (mm)', and 'Vent (km/h)'.
            Returns an empty DataFrame if no data can be scraped.
        """
        url = self.base_url + municipality_code
        today = datetime.now()

        day_map = {
            'Avui': today,
            'Demà': today + timedelta(days=1),
            'Demà passat': today + timedelta(days=2)
        }

        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        city_elem = soup.find('div', id='bit-1')
        city_h2 = city_elem.find('h2') if city_elem else None
        city_name = city_h2.get_text(strip=True) if city_h2 else ''

        weather_data = []

        for day_label, day_date in day_map.items():
            day_element = soup.find('strong', string=day_label)
            if not day_element:
                continue

            tables = []
            sibling = day_element.find_next_sibling()
            while sibling and sibling.name == "table":
                tables.append(sibling)
                sibling = sibling.find_next_sibling()
            if not tables:
                tables = day_element.find_all_next('table', limit=3)
            
            if not tables:
                continue

            header_cells = tables[0].find_all(['th', 'td'])
            times_raw = [cell.get_text(strip=True) for cell in header_cells[1:]]

            times = []
            for t in times_raw:
                if 'h' in t:
                    hr = t.replace('h', '').strip()
                    if hr.isdigit():
                        hour = int(hr)
                        if 0 <= hour <= 23:
                            times.append(f"{hour:02d}:00")

            day_dict = {
                'City': [], 'Day': [], 'Time': [], 'Temperatura (°C)': [],
                'Precipitació acumulada (mm)': [], 'Vent (km/h)': []
            }

            temperature_row, precipitation_row, wind_row = None, None, None

            for table in tables:
                for tr in table.find_all('tr'):
                    cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
                    if not cells:
                        continue
                    label, values = cells[0], cells[1:]
                    if label == 'Temperatura (°C)':
                        temperature_row = values
                    elif label == 'Precipitació acumulada (mm)':
                        precipitation_row = values
                    elif label.startswith('Vent'):
                        wind_row = values
                if all((temperature_row, precipitation_row, wind_row)):
                    break

            day_str = day_date.strftime("%d/%m/%y")

            for i in range(len(times)):
                day_dict['City'].append(city_name)
                day_dict['Day'].append(day_str)
                day_dict['Time'].append(times[i])
                day_dict['Temperatura (°C)'].append(temperature_row[i] if temperature_row and i < len(temperature_row) else '')
                day_dict['Precipitació acumulada (mm)'].append(precipitation_row[i] if precipitation_row and i < len(precipitation_row) else '')
                day_dict['Vent (km/h)'].append(wind_row[i] if wind_row and i < len(wind_row) else '')

            weather_data.append(pd.DataFrame(day_dict))

        if not weather_data:
            return pd.DataFrame()
            
        return pd.concat(weather_data, ignore_index=True)
    
    def get_weather_by_name(self, name: str) -> pd.DataFrame:
        """Gets weather data for a given municipality name.

        This is a convenience method that first finds the municipality record
        by name and then scrapes the weather data using its code.

        Args:
            name: The name of the municipality.

        Returns:
            A pandas DataFrame with the weather forecast.
        """
        record = self.get_municipality_record(name)
        return self.scrape_weather_data_by_code(record['codi'])

