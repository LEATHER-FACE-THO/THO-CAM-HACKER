import sys
import re
import urllib.request
import urllib.error
import json
import html
from time import sleep
from concurrent.futures import ThreadPoolExecutor
import platform
import requests
from datetime import datetime
import os  
import shodan  
from bs4 import BeautifulSoup
from tqdm import tqdm
import ipaddress
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

LIME = '\033[38;2;0;255;0m'
GOLD = '\033[38;2;255;215;0m'
RED = '\033[31m'
RESET = '\033[0m'

APIS = {
    'insecam': {
        'base_url': "http://www.insecam.org/en/jsoncountries/",
        'country_url': "http://www.insecam.org/en/bycountry/",
        'need_key': False
    },
    'earthcam': {
        'base_url': "https://www.earthcam.com/",
        'country_url': "https://www.earthcam.com/search/ft_search.php?term={country}",
        'need_key': False
    },
    'webcamgalore': {
        'base_url': "https://www.webcamgalore.com/",
        'country_url': "https://www.webcamgalore.com/EN/{country}/",
        'need_key': False
    },
    'webcamhopper': {
        'base_url': "https://www.webcamhopper.com/",
        'country_url': "https://www.webcamhopper.com/country/{country}",
        'need_key': False
    },
    'opentopia': {
        'base_url': "http://www.opentopia.com/",
        'country_url': "http://www.opentopia.com/browsecountry?country={country}",
        'need_key': False
    },
    'meteocam': {
        'base_url': "https://www.meteocam.gr/",
        'country_url': "https://www.meteocam.gr/{country}/",
        'need_key': False
    },
    'skylinewebcams': {
        'base_url': "https://www.skylinewebcams.com/",
        'country_url': "https://www.skylinewebcams.com/webcam/{country}.html",
        'need_key': False
    },
    'lookr': {
        'base_url': "https://www.lookr.com/",
        'country_url': "https://lookr.com/explore#{country}",
        'need_key': False
    }
}

def get_platform():
    system = platform.system().lower()
    if "windows" in system:
        return "windows"
    elif "linux" in system:
        if os.path.exists("/data/data/com.termux"):
            return "termux"
        return "linux"
    return "unknown"

def get_data(url):
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
                  "image/avif,image/webp,image/apng,*/*;q=0.8,"
                  "application/signed-exchange;v=b3;q=0.7",
        "Cache-Control": "max-age=0",
        "Connection": "keep-alive",
        "Host": "www.insecam.org",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/110.0.0.0 Safari/537.36"
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode('utf-8')


def save_ips_to_file(country_f, country_name, ips, cities, cameras_found):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f'cameras_{country_f}_{timestamp}.txt'
    
    found_count = 0
    with open(filename, 'a', encoding="utf-8") as f:
        f.write(f"=== CÁMARAS ENCONTRADAS - {country_name} ===\n")
        f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("-" * 50 + "\n\n")
        
        for ip, city in zip(ips, cities):
            if verify_camera(ip):  
                print(f"\n{LIME}[+] Cámara activa:{RESET} {GOLD}{ip}{RESET}")
                print(f"{LIME}[+] Ubicación:{RESET} {GOLD}{city}{RESET}")
                f.write(f'IP: {ip}\nUbicación: {city}\nEstado: ACTIVA\n')
                f.write("-" * 30 + "\n")
                cameras_found.append({
                    'ip': ip,
                    'city': city,
                    'tipo': 'insecam',
                    'url': ip
                })
                found_count += 1
            else:
                print(f"\n{RED}[-] Cámara inactiva:{RESET} {ip}")
    
    return found_count

def verify_camera(url):
    try:
        response = requests.head(url, timeout=5, allow_redirects=True)
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '').lower()
            if any(t in content_type for t in ['image', 'stream', 'video', 'mjpeg', 'multipart']):
                return True
            try:
                response = requests.get(url, timeout=5, stream=True)
                for chunk in response.iter_content(chunk_size=1024):
                    if b'JFIF' in chunk or b'MJPG' in chunk or b'JPEG' in chunk:
                        return True
                    break
            except:
                pass
        return False
    except:
        try:
            urllib.request.urlopen(url, timeout=5)
            return True
        except:
            return False

def save_results(country_code, cameras):
    filename = f'camaras_{country_code}_{len(cameras)}.txt'
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("=== REGISTRO DE CÁMARAS ENCONTRADAS ===\n\n")
        for camera in cameras:
            f.write(f"Tipo: {camera['tipo']}\n")
            f.write(f"URL: {camera['url']}\n")
            f.write(f"Ubicación: {camera['ubicacion']}\n")
            f.write("-" * 50 + "\n")
        print(f"{LIME}[✓] Archivo guardado:{RESET} {GOLD}{filename}{RESET}")


def banner():
    print(f"""{RED}
    ██╗     ███████╗ █████╗ ████████╗██╗  ██╗███████╗██████╗     ███████╗ █████╗  ██████╗███████╗
    ██║     ██╔════╝██╔══██╗╚══██╔══╝██║  ██║██╔════╝██╔══██╗    ██╔════╝██╔══██╗██╔════╝██╔════╝
    ██║     █████╗  ███████║   ██║   ███████║█████╗  ██████╔╝    █████╗  ███████║██║     █████╗  
    ██║     ██╔══╝  ██╔══██║   ██║   ██╔══██║██╔══╝  ██╔══██╗    ██╔══╝  ██╔══██║██║     ██╔══╝  
    ███████╗███████╗██║  ██║   ██║   ██║  ██║███████╗██║  ██║    ██║     ██║  ██║╚██████╗███████╗
    ╚══════╝╚══════╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝    ╚═╝     ╚═╝  ╚═╝ ╚═════╝╚══════╝
    {GOLD}╔════════════════════════════════════════════════════════════════════════════╗
    ║  OBSERVE THE WORLD FROM ANYWHERE                                           ║
    ║  Created by: LEATHER FACE                                                  ║
    ║  Discord  : https://discord.com/invite/Zcq7GD3FFH                          ║
    ║  Instagram: https://www.instagram.com/leather_face_tho                     ║
    ║  GitHub   : https://github.com/LEATHER-FACE-THO                            ║
    ╚════════════════════════════════════════════════════════════════════════════╝{RESET}""")


def get_data_with_key(url, api_key):
    headers = {
        'Authorization': f'Bearer {api_key}',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode('utf-8')


def parse_earthcam_data(data):
    cameras = []
    try:
        soup = BeautifulSoup(data, 'html.parser')
        for cam in soup.find_all('div', class_='webcam-entry'):
            url = cam.find('a')['href']
            location = cam.find('h3').text.strip()
            if verify_camera(url):
                cameras.append({
                    'url': url,
                    'ubicacion': location,
                    'tipo': 'earthcam'
                })
    except Exception as e:
        print(f"{RED}[!] Error al procesar EarthCam: {str(e)}{RESET}")
    return cameras


def parse_surveillance_data(data):
    cameras = []
    try:
        json_data = json.loads(data)
        for cam in json_data.get('results', []):
            cameras.append({
                'url': cam.get('stream_url'),
                'ubicacion': cam.get('location'),
                'tipo': 'surveillance'
            })
    except json.JSONDecodeError:
        print(f"{RED}[!] Error al procesar datos de Surveillance{RESET}")
    return cameras


def parse_webcam_data(data):
    cameras = []
    try:
        json_data = json.loads(data)
        for cam in json_data.get('cameras', []):
            cameras.append({
                'url': cam.get('url'),
                'ubicacion': cam.get('city'),
                'tipo': 'webcam'
            })
    except json.JSONDecodeError:
        print(f"{RED}[!] Error al procesar datos de Webcam{RESET}")
    return cameras


def parse_worldcams_data(data):
    cameras = []
    try:
        json_data = json.loads(data)
        for cam in json_data.get('cameras', []):
            cameras.append({
                'url': cam.get('url'),
                'ubicacion': cam.get('location'),
                'tipo': 'worldcams'
            })
    except json.JSONDecodeError:
        print(f"{RED}[!] Error al procesar datos de Worldcams{RESET}")
    return cameras


def parse_winkcam_data(data):
    cameras = []
    try:
        json_data = json.loads(data)
        for cam in json_data.get('cameras', []):
            cameras.append({
                'url': cam.get('url'),
                'ubicacion': cam.get('country'),
                'tipo': 'winkcam'
            })
    except json.JSONDecodeError:
        print(f"{RED}[!] Error al procesar datos de Winkcam{RESET}")
    return cameras


def parse_webcamtaxi_data(data):
    cameras = []
    try:
        ip_pattern = r'http[s]?://(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?::[0-9]+)?'
        urls = re.findall(ip_pattern, data)
        locations = re.findall(r'<h3 class="title">(.*?)</h3>', data)
        
        for url, location in zip(urls, locations):
            if verify_camera(url):
                cameras.append({
                    'url': url,
                    'ubicacion': location.strip(),
                    'tipo': 'webcamtaxi'
                })
    except Exception as e:
        print(f"{RED}[!] Error al procesar WebcamTaxi: {str(e)}{RESET}")
    return cameras


def parse_opentopia_data(data):
    cameras = []
    try:
        soup = BeautifulSoup(data, 'html.parser')
        for cam in soup.find_all('div', class_='webcam-listing'):
            try:
                url = cam.find('a', class_='stream-link')['href']
                location = cam.find('div', class_='location-info').text.strip()
                if verify_camera(url):
                    cameras.append({
                        'url': url,
                        'ubicacion': location,
                        'tipo': 'opentopia'
                    })
            except Exception as e:
                continue
    except Exception as e:
        print(f"{RED}[!] Error al procesar Opentopia: {str(e)}{RESET}")
    return cameras

def parse_meteocam_data(data):
    cameras = []
    try:
        soup = BeautifulSoup(data, 'html.parser')
        for cam in soup.find_all('div', class_='webcam-container'):
            try:
                url = cam.find('img', class_='webcam-image')['src']
                location = cam.find('h4', class_='location').text.strip()
                if verify_camera(url):
                    cameras.append({
                        'url': url,
                        'ubicacion': location,
                        'tipo': 'meteocam'
                    })
            except Exception as e:
                continue
    except Exception as e:
        print(f"{RED}[!] Error al procesar Meteocam: {str(e)}{RESET}")
    return cameras

def parse_skylinewebcams_data(data):
    cameras = []
    try:
        soup = BeautifulSoup(data, 'html.parser')
        for cam in soup.find_all('div', class_='webcam-box'):
            try:
                url = cam.find('a', class_='webcam-link')['href']
                location = cam.find('div', class_='webcam-title').text.strip()
                if verify_camera(url):
                    cameras.append({
                        'url': url,
                        'ubicacion': location,
                        'tipo': 'skylinewebcams'
                    })
            except Exception as e:
                continue
    except Exception as e:
        print(f"{RED}[!] Error al procesar Skylinewebcams: {str(e)}{RESET}")
    return cameras

class CameraCounter:
    def __init__(self):
        self.total = 0
        self.active = 0
        self.by_source = {}

    def add_source(self, source, total, active):
        self.total += total
        self.active += active
        self.by_source[source] = {'total': total, 'active': active}

    def print_stats(self):
        print(f"\n{LIME}[*] Estadísticas de búsqueda:{RESET}")
        for source, stats in self.by_source.items():
            print(f"{GOLD}[{source}]{RESET} Total: {stats['total']} | Activas: {stats['active']}")
        print(f"\n{LIME}[✓] Total global de cámaras: {GOLD}{self.total}{RESET}")
        print(f"{LIME}[✓] Total de cámaras activas: {GOLD}{self.active}{RESET}")

def print_found_cameras(cameras):
    if cameras:
        print(f"\n{LIME}[✓] Cámaras encontradas:{RESET}")
        print("-" * 60)
        for i, cam in enumerate(cameras, 1):
            print(f"{GOLD}[{i}]{RESET} {cam['url']}")
            print(f"    Ubicación: {cam['ubicacion']}")
            print(f"    Tipo: {cam['tipo']}")
            print("-" * 60)
    return len(cameras)

def get_cameras_from_api(api_name, country_code, counter):

    cameras = []
    total_found = 0
    active_found = 0
    
    try:
        if api_name == 'insecam':
            rsp = get_data(APIS['insecam']['base_url'])
            data = json.loads(rsp)
            countries = data['countries']

            if country_code in countries:
                total_found = countries[country_code]['count']
                country_name = countries[country_code]['country']
                print(f"\n{LIME}[*] Buscando en {country_name}: {GOLD}{total_found}{RESET} cámaras registradas")
                
                res = get_data(f"{APIS['insecam']['country_url']}{country_code}")
                last_page = re.findall(r'pagenavigator\("\?page=", (\d+)', res)[0]
                
                for page in range(int(last_page)):
                    print(f"{LIME}[*] Buscando página {GOLD}{page + 1}/{last_page}{RESET}", end='\r')
                    res = get_data(f"{APIS['insecam']['country_url']}{country_code}/?page={page}")
                    find_ip = re.findall(r"http://\d+.\d+.\d+.\d+:\d+", res)
                    find_c_r = re.findall(r'title="[^"]*?\bin\s+([^,"]+)', res)[1::2]
                    find_city = [html.unescape(i) for i in find_c_r]
                    
                    for ip, city in zip(find_ip, find_city):
                        if verify_camera(ip):
                            active_found += 1
                            cameras.append({
                                'url': ip,
                                'ubicacion': city,
                                'tipo': 'insecam'
                            })
                    sleep(0.1)

        else:
            url = APIS[api_name]['country_url'].format(country=country_code.lower())
            try:
                response = requests.get(url, timeout=15)
                if response.status_code == 200:
                    parsers = {
                        'webcamtaxi': parse_webcamtaxi_data,
                        'earthcam': parse_earthcam_data,
                        'opentopia': parse_opentopia_data,
                        'meteocam': parse_meteocam_data,
                        'skylinewebcams': parse_skylinewebcams_data
                    }
                    
                    if api_name in parsers:
                        new_cameras = parsers[api_name](response.text)
                        total_found = len(new_cameras)
                        active_found = len([c for c in new_cameras if verify_camera(c['url'])])
                        cameras.extend(new_cameras)
                        print(f"{LIME}[+] {api_name.capitalize()}: {GOLD}{total_found}{RESET} cámaras encontradas, {GOLD}{active_found}{RESET} activas")
                    
            except requests.exceptions.RequestException:
                pass
                
    except Exception:
        pass
    
    counter.add_source(api_name, total_found, active_found)
    return cameras

def check_dependencies():
    try:
        import requests
        from concurrent.futures import ThreadPoolExecutor
        return True
    except ImportError:
        print(f"{RED}[!] Faltan dependencias. Ejecute: ./install.sh{RESET}")
        return False

def scan_all_cameras(country_code, country_name):
    cameras_found = []
    total_progress = 100
    
    try:
        if country_code not in ['US', 'GB', 'DE', 'FR', 'ES', 'IT']:
            print(f"\n{LIME}[*] Buscando IPs de {country_name}...{RESET}")
            
            country_ranges = {
                'RD': [
                    "152.166.0.0/24", "152.167.0.0/24",
                    "186.120.0.0/24", "186.121.0.0/24",
                    "190.80.0.0/24", "190.81.0.0/24"
                ],
                'CO': [
                    "181.49.0.0/24", "181.50.0.0/24",
                    "186.80.0.0/24", "186.81.0.0/24",
                    "190.60.0.0/24", "190.61.0.0/24"
                ]
            }
            
            if country_code not in country_ranges:
                base_ranges = [
                    ("186", 4),
                    ("190", 4),
                    ("200", 4)
                ]
                country_ranges[country_code] = []
                for base, count in base_ranges:
                    for i in range(count):
                        country_ranges[country_code].append(f"{base}.{i}.0.0/24")
            
            ip_ranges = country_ranges[country_code][:4]  
            
            with tqdm(total=len(ip_ranges), desc=f"{LIME}Buscando{RESET}", 
                     bar_format="{l_bar}%s{bar}%s{r_bar}" % (GOLD, RESET)) as pbar:
                
                for ip_range in ip_ranges:
                    try:
                        network = ipaddress.ip_network(ip_range)
                        for ip in network:
                            ip_str = str(ip)
                            for port in [80, 8080, 554, 81]:
                                url = f"http://{ip_str}:{port}"
                                try:
                                    if verify_camera(url):
                                        location = get_ip_location(ip_str)
                                        cameras_found.append({
                                            'url': url,
                                            'ubicacion': location,
                                            'tipo': 'ip_scan',
                                            'estado': 'verificando'
                                        })
                                        print(f"\n{LIME}[+] Cámara encontrada: {GOLD}{url}{RESET}")
                                except:
                                    continue
                    except:
                        continue
                    pbar.update(1)
            
            return cameras_found
                    
        with tqdm(total=total_progress, desc=f"{LIME}Buscando cámaras{RESET}", 
                 bar_format="{l_bar}%s{bar}%s{r_bar}" % (GOLD, RESET)) as pbar:
            
            try:
                for api_name, api_info in APIS.items():
                    try:
                        url = api_info['country_url'].format(country=country_code.lower())
                        response = requests.get(url, timeout=15)
                        if response.status_code == 200:
                            if api_name == 'insecam':
                                res = response.text
                                find_ip = re.findall(r"http://\d+.\d+.\d+.\d+:\d+", res)
                                find_city = re.findall(r'title="[^"]*?\bin\s+([^,"]+)', res)[1::2]
                                
                                for ip, city in zip(find_ip, find_city):
                                    cameras_found.append({
                                        'url': ip,
                                        'ubicacion': html.unescape(city),
                                        'tipo': 'insecam',
                                        'estado': 'verificando'
                                    })
                            else:
                                if api_name in ['earthcam', 'meteocam', 'skylinewebcams']:
                                    parser_func = globals()[f'parse_{api_name}_data']
                                    cameras_found.extend(parser_func(response.text))
                    except:
                        continue
                    pbar.update(50 // len(APIS))
                    
            except Exception as e:
                print(f"\n{RED}[!] Error en la búsqueda: {str(e)}{RESET}")
                
    except Exception as e:
        print(f"\n{RED}[!] Error general: {str(e)}{RESET}")
        
    return cameras_found

def verify_and_save_cameras(cameras, country_code):
    active_cameras = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f'camaras_{country_code}_{timestamp}.txt'
    
    print(f"\n{LIME}[*] Verificando {len(cameras)} cámaras encontradas...{RESET}")
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"=== REGISTRO DE CÁMARAS ENCONTRADAS ===\n")
        f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 50 + "\n\n")
        
        for i, cam in enumerate(cameras, 1):
            is_active = verify_camera(cam['url'])
            status = f"{LIME}ACTIVA{RESET}" if is_active else f"{RED}INACTIVA{RESET}"
            
            print(f"\n{GOLD}[{i}/{len(cameras)}]{RESET} Cámara encontrada:")
            print(f"  URL: {cam['url']}")
            print(f"  Ubicación: {cam['ubicacion']}")
            print(f"  Estado: {status}")
            
            f.write(f"Cámara #{i}\n")
            f.write(f"URL: {cam['url']}\n")
            f.write(f"Ubicación: {cam['ubicacion']}\n")
            f.write(f"Tipo: {cam['tipo']}\n")
            f.write(f"Estado: {'ACTIVA' if is_active else 'INACTIVA'}\n")
            f.write("-" * 50 + "\n")
            
            if is_active:
                active_cameras.append(cam)
    
    print(f"\n{LIME}[✓] Se encontraron {len(active_cameras)}/{len(cameras)} cámaras activas{RESET}")
    print(f"{LIME}[✓] Resultados guardados en:{RESET} {GOLD}{filename}{RESET}")
    return active_cameras

def search_cameras(country_code, country_name):
    all_cameras = []
    active_cameras = []
    
    print(f"\n{LIME}[*] Buscando cámaras en {country_name}{RESET}")
    
    with tqdm(total=100, desc="Progreso", bar_format="{l_bar}%s{bar}%s{r_bar}" % (GOLD, RESET)) as pbar:
        try:
            res = get_data(f"{APIS['insecam']['country_url']}{country_code}")
            last_page = re.findall(r'pagenavigator\("\?page=", (\d+)', res)
            if last_page:
                pages = int(last_page[0])
                for page in range(pages):
                    res = get_data(f"{APIS['insecam']['country_url']}{country_code}/?page={page}")
                    find_ip = re.findall(r"http://\d+.\d+.\d+.\d+:\d+", res)
                    find_c_r = re.findall(r'title="[^"]*?\bin\s+([^,"]+)', res)[1::2]
                    
                    for ip, city in zip(find_ip, find_c_r):
                        all_cameras.append({
                            'url': ip,
                            'ubicacion': html.unescape(city),
                            'tipo': 'insecam'
                        })
                    pbar.update(50 // (pages or 1))
            
            for api_name in ['earthcam', 'meteocam', 'skylinewebcams']:
                try:
                    url = APIS[api_name]['country_url'].format(country=country_code.lower())
                    response = requests.get(url, timeout=15)
                    if response.status_code == 200:
                        if api_name == 'earthcam':
                            new_cams = parse_earthcam_data(response.text)
                        elif api_name == 'meteocam':
                            new_cams = parse_meteocam_data(response.text)
                        elif api_name == 'skylinewebcams':
                            new_cams = parse_skylinewebcams_data(response.text)
                        all_cameras.extend(new_cams)
                except:
                    continue
                pbar.update(10)
            
            pbar.update(100 - pbar.n)  

            print(f"\n{LIME}[*] Total de IPs encontradas: {len(all_cameras)}{RESET}")
            for i, cam in enumerate(all_cameras, 1):
                print(f"{GOLD}[{i}]{RESET} {cam['url']} - {cam['ubicacion']}")

            print(f"\n{LIME}[*] Verificando cámaras activas...{RESET}")
            
            with tqdm(total=len(all_cameras), desc="Verificando", 
                     bar_format="{l_bar}%s{bar}%s{r_bar}" % (GOLD, RESET)) as pbar:
                for cam in all_cameras:
                    if verify_camera(cam['url']):
                        active_cameras.append(cam)
                    pbar.update(1)
            
            print(f"\n{LIME}[*] Resumen de la búsqueda:{RESET}")
            print(f"{GOLD}[+] Total IPs encontradas: {len(all_cameras)}{RESET}")
            print(f"{GOLD}[+] Cámaras activas: {len(active_cameras)}{RESET}")
                    
            return active_cameras
            
        except Exception as e:
            print(f"{RED}[!] Error: {str(e)}{RESET}")
            return []
            
            if all_cameras:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f'camaras_{country_code}_{timestamp}.txt'
                
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"=== CÁMARAS ENCONTRADAS EN {country_name.upper()} ===\n")
                    f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Total de cámaras: {len(all_cameras)}\n")
                    f.write("-" * 50 + "\n\n")
                    
                    for i, cam in enumerate(cameras, 1):
                        f.write(f"Cámara #{i}\n")
                        f.write(f"URL: {cam['url']}\n")
                        f.write(f"Ubicación: {cam['ubicacion']}\n")
                        f.write(f"Tipo: {cam['tipo']}\n")
                        f.write("-" * 50 + "\n")
                
                print(f"\n{LIME}[✓] Total de cámaras encontradas: {GOLD}{len(all_cameras)}{RESET}")
                print(f"{LIME}[✓] IPs guardadas en: {GOLD}{filename}{RESET}")
            
            pbar.update(100 - pbar.n)  

            active_cameras = []
            print(f"\n{LIME}[*] Verificando {len(all_cameras)} cámaras...{RESET}")
            
            for cam in all_cameras:
                if verify_camera(cam['url']):
                    active_cameras.append(cam)
            
            return active_cameras
            
        except Exception as e:
            print(f"{RED}[!] Error: {str(e)}{RESET}")
            return []

def get_public_camera_links():

    public_links = {
        "Cámaras de tráfico mundiales": "https://www.earthcam.com/network/index.php?country=all",
        "Webcams de aeropuertos": "https://airportwebcams.net/",
        "Cámaras en vivo mundiales": "https://www.skylinewebcams.com/",
        "Webcams de playas": "https://www.surfline.com/surf-report",
        "Cámaras meteorológicas": "https://www.windy.com/webcams",
        "Webcams de naturaleza": "https://explore.org/livecams",
        "Cámaras de ciudades": "https://www.webcamtaxi.com/en/",
        "Webcams turísticas": "https://www.lookr.com/",
    }
    return public_links

def deep_search_cameras(country_code, country_name):
    print(f"\n{LIME}[*] Iniciando búsqueda profunda en {country_name}...{RESET}")
    deep_cameras = []
    
    country_ranges = {
        'CO': [  
            "181.49.0.0/24", "181.50.0.0/24",
            "186.80.0.0/24", "186.81.0.0/24",
            "190.60.0.0/24", "190.61.0.0/24",
        ],
        'RD': [  
            "152.166.0.0/24", "152.167.0.0/24",
            "186.120.0.0/24", "186.121.0.0/24",
            "190.80.0.0/24", "190.81.0.0/24",
        ]

    }

    if country_code not in country_ranges:
        country_ranges[country_code] = [
            f"186.{i}.0.0/24" for i in range(4)
        ] + [
            f"190.{i}.0.0/24" for i in range(4)
        ]

    ip_ranges = country_ranges.get(country_code, [])[:4]  
    print(f"{LIME}[*] Buscando {len(ip_ranges)} rangos de IP...{RESET}")
    
    common_ports = [80, 8080, 554, 88, 81, 82, 8081, 8082]
    
    common_paths = [
        '/video.mjpg',
        '/cam/1',
        '/live',
        '/live.jpg',
        '/mjpg/video.mjpg',
        '/cgi-bin/camera',
        '/snap.jpg'
    ]

    def check_ip_fast(ip):
        for port in common_ports:
            for path in common_paths:
                url = f"http://{str(ip)}:{port}{path}"
                try:
                    response = requests.get(url, timeout=1, verify=False, stream=True)
                    if response.status_code == 200:
                        content_type = response.headers.get('content-type', '').lower()
                        if any(t in content_type for t in ['image', 'stream', 'video', 'mjpeg']):
                            location = get_ip_location(str(ip))
                            deep_cameras.append({
                                'url': url,
                                'ubicacion': location,
                                'tipo': 'deep_search',
                                'estado': 'ACTIVA'
                            })
                            print(f"\n{LIME}[+] Cámara encontrada:{RESET} {GOLD}{url}{RESET}")
                            print(f"{LIME}[+] Ubicación:{RESET} {GOLD}{location}{RESET}")
                            return True
                except:
                    continue
        return False

    total_ips = sum(len(list(ipaddress.ip_network(r))) for r in ip_ranges)
    print(f"{LIME}[*] Total IPs a escanear: {total_ips}{RESET}")
    
    with ThreadPoolExecutor(max_workers=100) as executor:
        with tqdm(total=len(ip_ranges), desc="Progreso", bar_format="{l_bar}%s{bar}%s{r_bar}" % (GOLD, RESET)) as pbar:
            for ip_range in ip_ranges:
                try:
                    network = ipaddress.ip_network(ip_range.strip())
                    futures = []
                    for ip in network:
                        futures.append(executor.submit(check_ip_fast, str(ip)))
                        
                    for i, future in enumerate(futures):
                        if i % 100 == 0:
                            try:
                                future.result(timeout=1)
                            except:
                                continue
                except:
                    continue
                pbar.update(1)
    
    return deep_cameras

def get_ip_location(ip):
    services = [
        f"http://ip-api.com/json/{ip}",
        f"https://ipapi.co/{ip}/json/",
        f"https://freegeoip.app/json/{ip}"
    ]
    
    for service in services:
        try:
            response = requests.get(service, timeout=3)
            if response.status_code == 200:
                data = response.json()
                city = data.get('city', data.get('location', {}).get('city', 'Unknown'))
                country = data.get('country', data.get('location', {}).get('country', 'Unknown'))
                return f"{city}, {country}"
        except:
            continue
    return "Unknown Location"

def check_camera_url(url):
    try:
        response = requests.head(url, timeout=2, verify=False, allow_redirects=True)
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '').lower()
            if any(t in content_type for t in ['image', 'stream', 'video', 'mjpeg', 'multipart']):
                return (url, True)
        return (url, False)
    except:
        return (url, False)

def main():
    while True:
        if not check_dependencies():
            sys.exit(1)
        
        platform_type = get_platform()
        print(f"{LIME}[*] Plataforma detectada: {platform_type}{RESET}")
        
        banner()
        
        print(f"\n{LIME}[*] Enlaces útiles de cámaras públicas:{RESET}")
        for desc, link in get_public_camera_links().items():
            print(f"{GOLD}[+] {desc}:{RESET} {link}")
        print("-" * 60)
        
        try:
            rsp = get_data(APIS['insecam']['base_url'])
            data = json.loads(rsp)
            countries = data['countries']
            
            print(f"\n{LIME}[*] Países disponibles:{RESET}")
            for key, value in countries.items():
                print(f"{GOLD}[{key}]{RESET} {value['country']} - {LIME}{value['count']}{RESET} cámaras")
            
            print(f"\n{GOLD}[99]{RESET} Buscar en otro país | Pronto esta en desarrollo...")
            
            country = input(f"\n{LIME}[?] Ingrese el Código del País:{RESET} ").upper()
            
            if country == "99":
                country = input(f"{LIME}[?] Ingrese el código de país (2 letras, ej: RD):{RESET} ").upper()
                country_name = input(f"{LIME}[?] Ingrese el nombre del país:{RESET} ")
                countries[country] = {
                    'country': country_name,
                    'count': 0,
                    'custom': True  
                }
                print(f"\n{LIME}[*] Buscando cámaras en {country_name} usando rangos de IP...{RESET}")
        
            elif country not in countries:
                print(f"\n{RED}[!] El país {country} no está en la lista{RESET}")
                print(f"{GOLD}[*] Volviendo al menú principal en 4 segundos...{RESET}")
                sleep(4)
                continue

            print(f"\n{LIME}[*] Iniciando búsqueda exhaustiva de cámaras...{RESET}")
            found_cameras = scan_all_cameras(country, countries[country]['country'])
            active_cameras = verify_and_save_cameras(found_cameras, country)
            
            print(f"\n{LIME}[*] Resumen de la búsqueda:{RESET}")
            print(f"{GOLD}[+] Total IPs encontradas: {len(found_cameras)}{RESET}")
            print(f"{GOLD}[+] Cámaras activas: {len(active_cameras)}{RESET}")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f'camaras_{country}_{timestamp}.txt'
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"=== CÁMARAS ENCONTRADAS EN {countries[country]['country'].upper()} ===\n")
                f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total de IPs encontradas: {len(found_cameras)}\n")
                f.write(f"Total cámaras activas: {len(active_cameras)}\n")
                f.write("-" * 50 + "\n\n")
                
                for i, cam in enumerate(active_cameras, 1):
                    f.write(f"Cámara #{i}\n")
                    f.write(f"URL: {cam['url']}\n")
                    f.write(f"Ubicación: {cam['ubicacion']}\n")
                    f.write(f"Tipo: {cam['tipo']}\n")
                    f.write("-" * 50 + "\n")
            
            if active_cameras:
                print(f"\n{LIME}[✓] Se encontraron {GOLD}{len(active_cameras)}{RESET} cámaras activas")
                print(f"{LIME}[✓] Resultados guardados en: {GOLD}{filename}{RESET}")
            else:
                print(f"\n{RED}[!] No se encontraron cámaras activas en {countries[country]['country']}{RESET}")

            print(f"\n{LIME}[*] Opciones disponibles:{RESET}")
            print(f"{GOLD}[1]{RESET} Realizar búsqueda profunda")
            print(f"{GOLD}[2]{RESET} Volver al menú principal")
            
            opcion = input(f"\n{LIME}[?] Seleccione una opción:{RESET} ")
            
            if opcion == "1":
                print(f"\n{GOLD}[!] Advertencia: La búsqueda profunda puede tardar varios minutos{RESET}")
                print(f"{GOLD}[!] Esta búsqueda intentará encontrar cámaras ocultas y no listadas{RESET}")
                confirmar = input(f"{LIME}[?] ¿Desea continuar? (s/n):{RESET} ").lower()
                
                if confirmar == 's':
                    deep_cameras = deep_search_cameras(country, countries[country]['country'])
                    
                    if deep_cameras:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f'camaras_deep_{country}_{timestamp}.txt'
                        
                        with open(filename, 'w', encoding='utf-8') as f:
                            f.write(f"=== BÚSQUEDA PROFUNDA EN {countries[country]['country'].upper()} ===\n")
                            f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                            f.write(f"Total cámaras encontradas: {len(deep_cameras)}\n")
                            f.write("-" * 50 + "\n\n")
                            
                            for i, cam in enumerate(deep_cameras, 1):
                                f.write(f"Cámara #{i}\n")
                                f.write(f"URL: {cam['url']}\n")
                                f.write(f"Ubicación: {cam['ubicacion']}\n")
                                f.write(f"Tipo: {cam['tipo']}\n")
                                f.write("-" * 50 + "\n")
                        
                        print(f"\n{LIME}[✓] Búsqueda profunda completada{RESET}")
                        print(f"{LIME}[✓] Se encontraron {GOLD}{len(deep_cameras)}{RESET} cámaras adicionales")
                        print(f"{LIME}[✓] Resultados guardados en: {GOLD}{filename}{RESET}")
                    else:
                        print(f"\n{RED}[!] No se encontraron cámaras adicionales{RESET}")

            continuar = input(f"\n{LIME}[?] ¿Desea buscar en otro país? (s/n):{RESET} ").lower()
            if continuar != 's':
                print(f"\n{GOLD}[*] ¡Gracias por usar la herramienta!{RESET}")
                break

        except KeyboardInterrupt:
            print(f"\n{LIME}[!] Operación cancelada por el usuario{RESET}")
            break
        except Exception as e:
            print(f"\n{RED}[!] Error: {str(e)}{RESET}")
            continuar = input(f"\n{LIME}[?] ¿Desea intentar de nuevo? (s/n):{RESET} ").lower()
            if continuar != 's':
                break

        while True:
            print(f"\n{LIME}[*] Opciones disponibles:{RESET}")
            print(f"{GOLD}[1]{RESET} Realizar búsqueda profunda")
            print(f"{GOLD}[2]{RESET} Volver al menú principal")
            
            opcion = input(f"\n{LIME}[?] Seleccione una opción:{RESET} ")
            
            if opcion == "1":
                print(f"\n{GOLD}[!] Advertencia: La búsqueda profunda puede tardar varios minutos{RESET}")
                print(f"{GOLD}[!] Esta búsqueda intentará encontrar cámaras ocultas y no listadas{RESET}")
                confirmar = input(f"{LIME}[?] ¿Desea continuar? (s/n):{RESET} ").lower()
                
                if confirmar == 's':
                    deep_cameras = deep_search_cameras(country, countries[country]['country'])
                    
                    if deep_cameras:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f'camaras_deep_{country}_{timestamp}.txt'
                        
                        with open(filename, 'w', encoding='utf-8') as f:
                            f.write(f"=== BÚSQUEDA PROFUNDA EN {countries[country]['country'].upper()} ===\n")
                            f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                            f.write(f"Total cámaras encontradas: {len(deep_cameras)}\n")
                            f.write("-" * 50 + "\n\n")
                            
                            for i, cam in enumerate(deep_cameras, 1):
                                f.write(f"Cámara #{i}\n")
                                f.write(f"URL: {cam['url']}\n")
                                f.write(f"Ubicación: {cam['ubicacion']}\n")
                                f.write(f"Tipo: {cam['tipo']}\n")
                                f.write("-" * 50 + "\n")
                        
                        print(f"\n{LIME}[✓] Búsqueda profunda completada{RESET}")
                        print(f"{LIME}[✓] Se encontraron {GOLD}{len(deep_cameras)}{RESET} cámaras adicionales")
                        print(f"{LIME}[✓] Resultados guardados en: {GOLD}{filename}{RESET}")
                    else:
                        print(f"\n{RED}[!] No se encontraron cámaras adicionales{RESET}")

            elif opcion == "2":
                break
            
            else:
                print(f"\n{RED}[!] Opción no válida{RESET}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{RED}[!] Programa interrumpido por el usuario{RESET}")
        sys.exit(0)

