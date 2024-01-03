import os
import sys
import json
from matplotlib.ticker import EngFormatter
import requests as req
from bs4 import BeautifulSoup as bs
from selenium.webdriver import Edge, EdgeOptions
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.common.exceptions import WebDriverException
from threading import Thread
import traceback


def sum_bytes(sizes_list):

    multipliers = {
                    'B': 1,
                    'KB': 1024,
                    'MB': 1024**2,
                    'GB': 1024**3,
                }

    bytes_sum=sum(float(size_str.split()[0]) * multipliers.get(size_str.split()[-1], 1) for size_str in sizes_list if size_str)

    return bytes_sum


def convert_bytes(bytes):

    return EngFormatter('B', 2)(bytes)


def verif_listdir(arch, path):
    
    return os.path.splitext(arch)[0] in [os.path.splitext(file)[0] for file in os.listdir(path)]


def get_info(url, webdriver=False, download_path=None):
    
    if webdriver:

        options = EdgeOptions()
        options.add_argument('--enable-chrome-browser-cloud-management')
        options.add_argument("--headless=new")
        options.add_argument('--disable-gpu')
        ######
        # options.add_argument("--headless")
        # options.add_argument('--ignore-certificate-errors')
        # options.add_argument("--disable-features=msEdgeEnableNurturingFramework")
        # options.add_argument('--ignore-certificate-errors-spki-list')
        # options.add_argument('--disable-notifications')
        # options.add_argument('--log-level=3')
        # options.add_experimental_option('excludeSwitches', ['enable-logging'])
        # options.add_argument('--start-maximized')
        ######
        options.add_experimental_option("detach", True)
        options.add_experimental_option("prefs",{
                                                "download.default_directory": download_path,
                                                "download.prompt_for_download": False,
                                                "download.directory_upgrade": True,
                                                "safebrowsing.enabled": False
                                                })
        
        msedgedriver=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedgedriver.exe"
        if not os.path.exists(msedgedriver):
            msedgedriver=EdgeChromiumDriverManager(log_level=0, print_first_line=False).install()

        driver = Edge(service=Service(msedgedriver), options = options)
        driver.get(url)
    else:

        driver=req.get(url)

    return driver


class Roms_Dl(Thread):

    def __init__(self, master=None, main_path=os.getcwd(), choosed_systems=[], systems=[], progress=None):

        Thread.__init__(self)
        self.main_site='https://vimm.net'
        self.page_filter='/{}?p=list&action=filters&countries_all=1&hacked=1&translated=1&prototype=1&demo=1&unlicensed=1&bonus=1&version=all&discs=all'
        self.master = master
        self.progress = None
        if self.master:
            self.progress = master
        elif progress:
            self.progress = progress
        self.main_path = main_path
        self.systems=systems
        self.choosed_systems=choosed_systems
        self.stop_event=False

        
    def main(self):

        for item in bs(get_info(self.main_site+'/vault').text, features="html.parser").find_all('tr'):
            item=item.find('td').find('a')
            if item:
                self.systems.append({'Name': item.get_text(), 'URL': self.main_site+item.get('href')})
       
        return self.systems
    

    def run(self):

        try:
            assert os.path.isdir(self.main_path), "The given directory does not exist!"
            assert self.choosed_systems, "No system given!"
            
            roms=self.get_roms()
            if self.progress:
                roms=list(roms)
                self.progress.progress_set_maximum(len(roms))
                self.progress.progress_set_value(0)
            
            for progress, rom in enumerate(roms, 1):
                self.download_rom(rom)
                print('\nROMs analisadas: {}.'.format(progress))

                if self.progress:
                    self.progress.progress_set_value(progress)
                    
         
            if self.master is None:

                print('\nTodos os processos foram concluídos.')

            else:

                self.master.generic_queue.put(lambda: self.master.stop(1))

        except Exception as e:

            if not isinstance(e, StopException):

                if self.master is not None:
                    message="The following error was thrown:\n{}".format(e)
                    self.master.generic_queue.put(lambda: self.master.showerror("Error encountered", message))

                else:

                    print("Error encountered:", file=sys.stderr)
                    traceback.print_exc()


    def get_roms(self):
        for index in self.choosed_systems:
            system_roms=[]
            system=self.systems[index]
            system_path=os.path.join(self.main_path, system.get('Name'))
            os.makedirs(system_path, exist_ok=True)
            error_file=os.path.join(system_path, 'ROMs_errors.txt')
            if os.path.exists(error_file):
                os.remove(error_file)
            system_url=system.get('URL')
            for filter in bs(get_info(system_url).text, features="html.parser").find(id='vaultMenu').find_all('a'):
                filter_code=filter.get_text()
                if filter_code=='#':
                    filter_code='number'
                for item in bs(get_info(system_url+self.page_filter.format(filter_code)).text, features="html.parser").find_all('tr'):
                    item=item.find('td').find('a')
                    if item:
                        rom={'Name': item.get_text(), 'URL': self.main_site+item.get('href'), 'system_path':system_path, 'Error': False}
                        system_roms.append(rom)
                        self.check_is_stopped()

                        yield rom


    def download_rom(self, rom):
    
        url=rom.get('URL')
        system_path=rom.get('system_path')
        while True:
            soup=bs(get_info(url).text, features="html.parser")
            versions=soup.find(id='download_version').find_all('option')
            if len(versions)>1:
                try:
                    driver=get_info(url, webdriver=True, download_path=system_path)
                    file_name=driver.find_element(By.ID, 'data-good-title').text
                    download_size=driver.find_element(By.ID, 'download_size').text
                except WebDriverException as e:
                    print(str(e))
                    continue
            else:
                driver=None
                file_name=soup.find(id='data-good-title').get_text()
                download_size=soup.find(id='download_size').get_text()
            rom.update({'file_name':file_name, 'download_size':download_size})
            if len(file_name)==0 or sum_bytes([download_size])==0 or self.check_download(rom, driver)==False:
                rom.update({'Error': True})
                error_file=os.path.join(system_path, 'ROMs_errors.txt')
                with open(error_file, 'w') as file:
                    json.dump(rom, fp=file, ensure_ascii=False, indent=2, sort_keys=True)
            self.check_is_stopped()
            break


    def check_download(self, rom, driver=None):

        file_name=rom.get('file_name')
        path=rom.get('system_path')
        if verif_listdir(file_name, path)==False:
            print('\nBaixando "{}".'.format(file_name))
            while True:
                try:
                    if not driver:
                        driver=get_info(rom.get('URL'), webdriver=True, download_path=path)
                    button=WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'download_form')))
                    if not button:
                        return False
                    button.click()
                    while verif_listdir(file_name, path)==False:
                        continue    
                    driver.quit()
                except WebDriverException as e:
                    print(str(e))

                    continue
                break
            print('Download feito.')

        return True
      

    def stop(self):
        self.stop_event = True

    def check_is_stopped(self):
        if self.stop_event:
            raise StopException()
        
class StopException(Exception):
    def __str__(self):
        return "The ePub creator has been stopped!"
