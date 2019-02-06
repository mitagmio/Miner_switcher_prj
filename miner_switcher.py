import os
import subprocess
import time
import copy
import requests
import configparser
from datetime import datetime
import sys
import psutil

def get_pid(name_proc):
    process = filter(lambda p: p.name() == name_proc, psutil.process_iter())
    for i in process:
        return i.pid

def config_read ():
    config = configparser.ConfigParser()
    config.sections()
    config.read('config.ini')
    print(str(datetime.now()) + ' - Config have been read successfully')
    return config


def start_miner(info, config):
    curdir = os.path.dirname(os.path.abspath(__file__))
    #print(curdir)
    if info['currency'].split('-')[0].upper() == 'NICEHASH':
        subprocess.Popen(curdir + '\\' + config['Currency'][info['currency']], cwd=curdir,
                         creationflags=subprocess.CREATE_NEW_CONSOLE, shell=True)
    elif info['currency'] != 'NICEHASH' and info['currency'] != '':
        subprocess.Popen(curdir + '\\' + config['Currency'][info['currency']], cwd=curdir,
                         creationflags=subprocess.CREATE_NEW_CONSOLE, shell=True)
    else:
        print("Miner bat file not found. Check config. You didn't select currency with miner bat file. Closing Switcher in 10 sec")
        time.sleep(10)
        sys.exit()
    return info


def stop_miner(config):
    os.system("taskkill /f /t /im " + str(config['Path']['proc_miner']))


def request_coins(config):
    coins = None
    while coins is None:
        print(str(datetime.now()) + " - Requesting coins info for WhattoMine.com!")
        url = str(config['UrlPath']['url']) + str(config['UrlPath']['userrates'])
        try:
            coins = (requests.get(url=url, timeout=3))
        except:
            print(str(datetime.now()) + " - Site didn't respond. Reconnecting in 10 sec!")
            time.sleep(10)
    if coins is not None and coins.status_code == 200:
            coins = coins.json()['coins']
    else:
        print(str(datetime.now()) + " - WhattoMine.com Server Response isn't OK . Switcher will close in 10 sec")
        time.sleep(10)
        sys.exit()
    if not coins:
        print(str(datetime.now()) + " - You setup wrong UserRates in config file closing in 10 sec")
        time.sleep(10)
        sys.exit()
    else:
        print(str(datetime.now()) + ' - Coins info received successfully')
    return coins


def user_coins_request(config,coins):
    user_coins = {}
    for key, value in config['Currency'].items():
            if value != '':
                if key.split('-')[0].upper() == 'NICEHASH':
                    tag = key.split('-')[0].upper()
                    alg_low = key.split('-')[1]
                    alg = alg_low[0].upper() + alg_low[1:]
                else:
                    tag = key.upper()
                    alg = ''
                for key_coin, value_coin in coins.items():
                    if value_coin['tag'] == 'NICEHASH' and value_coin['algorithm'] == alg:
                        user_coins[key_coin] = value_coin
                    if value_coin['tag'] == tag and value_coin['tag'] != 'NICEHASH':
                        user_coins[key_coin] = value_coin
    return user_coins


def update_profit_info(info, user_coins):
    for key, value in user_coins.items():
        if value['tag'] == info['temp_currency']:
            info['temp_profit'] = value['btc_revenue']
        if value['tag'] == info['currency']:
            info['profit'] = value['btc_revenue']
            info['profitability'] = value['profitability']
    return info


def choosing_currency(user_coins):
    most_profit_currency = {'profit': 0, 'currency': None, 'algorithm': None, 'profitability': None}
    for key, value in user_coins.items():
        if float(value['btc_revenue']) > float(most_profit_currency['profit']):
            most_profit_currency['profit'] = value['btc_revenue']
            if value['tag'] == 'NICEHASH':
                most_profit_currency['currency'] = key
            else:
                most_profit_currency['currency'] = value['tag']
            most_profit_currency['algorithm'] = value['algorithm']
            most_profit_currency['profitability'] = value['profitability']
    print(str(datetime.now()) + ' - Most profitable Currency was chosen')
    return most_profit_currency


def miner_chose(config, info):
    coins = request_coins(config)
    user_coins = user_coins_request(config, coins)
    info = update_profit_info(info, user_coins)
    most_profit_currency = choosing_currency(user_coins)
    if float(most_profit_currency['profit']) > float(info['profit']) * \
            (float(config['CheckOptions']['profitprocent'])+ 100) / 100:
        if most_profit_currency['currency'] != info['currency'] and int(info['check_times']) < \
                int(config['CheckOptions']['times']):
            if info['temp_currency'] != most_profit_currency['currency']:
                info['temp_currency'] = most_profit_currency['currency']
                info['check_times'] = 0
                info['profitability'] = most_profit_currency['profitability']
            info['check_times'] += 1
            info['temp_profit'] = most_profit_currency['profit']
        if most_profit_currency['currency'] != info['currency'] and int(info['check_times']) >= \
                int(config['CheckOptions']['times']):
            info['profit'] = most_profit_currency['profit']
            info['currency'] = most_profit_currency['currency']
            info['algorithm'] = most_profit_currency['algorithm']
            info['profitability'] = most_profit_currency['profitability']
            info['check_times'] = 0
    return info

def start_proc(info, config):
	stop_miner(config)
	start_miner(info, config)

def start(config):
    check_times = int(config['CheckOptions']['times']) + 1
    info = {'profit': 0, 'check_times': check_times, 'currency': None, 'temp_profit': 0, 'temp_currency': None}
    while True:
        if info['profit'] != 0:
            old_info = copy.deepcopy(info)
            #print(old_info)
            info = miner_chose(config, info)
            print(
                str(datetime.now()) + ' - Checking profit. Current currency: ' + info['currency'] + '. Profit: ' +
                    str(info['profitability']) + '%' + ' - ' + info['profit'] + ' BTC/Day.')
            #print(info)
            if info['currency'] != old_info['currency']:
                print('!!!!!!Changing miner!!!!!!!!. Currency ' + info['currency'] + '. Profit: ' +
                    str(info['profitability']) + '%' + ' - ' + info['profit'] + ' BTC/Day.')
                start_proc(info, config)
            elif info['currency'] == old_info['currency']:
                try:
                    pid = int(get_pid(str(config['Path']['proc_miner'])))
                    if pid > 0:
                        print('Process PID: ' + str(pid) + ' Continue mining:' + ' ' + info['currency'])
                except TypeError:
                    print('Restart miner and mining:' + ' ' + info['currency'])
                    start_proc(info, config)
            time.sleep(int(config['CheckOptions']['period']) * 60)
        else:
            info = miner_chose(config,info)
            print(str(datetime.now()) + " - Starting miner first time. Currency: " + info['currency'] + '. Profit: ' +
                  str(info['profitability']) + '%' + ' - ' + info['profit'] + ' BTC/Day.')
            start_miner(info, config)
            time.sleep(5)
            try:
                pid = int(get_pid(str(config['Path']['proc_miner'])))
                if pid > 0:
                    print('Miner was started on process PID: ' + str(pid))
            except TypeError:
                print("!!!!Can't starting miner!!!! Fix your bat file of miner")
                time.sleep(10)
                sys.exit()
            time.sleep(int(config['CheckOptions']['period']) * 60)


def main():
    config = config_read()
    stop_miner(config)
    start(config)


if __name__ == '__main__':
    main()



