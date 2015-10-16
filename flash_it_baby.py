#!/usr/bin/env python3

import importlib

def checkForModule(module):
    if importlib.find_loader(module) is None:
        print('missing "' + module + '" module')
        exit()


[ checkForModule(m) for m in ['requests', 'paramiko'] ]

import requests
import re
import paramiko
import time
import sys
import csv
import traceback
from os import listdir
from os.path import isfile, join


class MyPolicy:
    def missing_host_key(client, hostname, key):
        return



def httpHostIsUp(ipv4):
    try:
        result = requests.get('http://' + ipv4 + '/', timeout=0.01)
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
        return False
    except Exception as e:
        print(e)
        print(type(e))
        return False

    return True


def uploadImage(imageName):
    LOGIN_URL = 'http://192.168.0.1/userRpm/LoginRpm.htm?Save=Save'
    REFERER_URL = 'http://192.168.0.1/{0}/userRpm/SoftwareUpgradeRpm.htm'
    FIRMWARE_URL = 'http://192.168.0.1/{0}/incoming/Firmware.htm'

    print('Uploading custom image...')

    cookies = { 'Authorization': 'Basic%20YWRtaW46MjEyMzJmMjk3YTU3YTVhNzQzODk0YTBlNGE4MDFmYzM%3D', 'path': '/' }

    login = requests.get(LOGIN_URL, cookies=cookies, timeout=0.1)

    sessionKey = re.search('1/([^/]+)/', login.text).group(1)

    headers = { 'Referer': REFERER_URL.format(sessionKey) }

    form = { 'Upgrade': 'Upgrade' }
    files = { 'Filename': open(imageName, 'rb') }

    upload = requests.post(FIRMWARE_URL.format(sessionKey),
                            cookies=cookies,
                            headers=headers,
                            files=files,
                            data=form,
                            timeout=10)

    # print(upload.text)


def waitForHttpHostUp(ipv4, message=None):
    DOTS_COUNT = 3
    iteration = 0
    first = True

    if message is None:
        message = 'Waiting for ' + ipv4

    while not httpHostIsUp(ipv4):
        first = False
        print('\r' + message, end='')
        iteration = (iteration + 1) % (DOTS_COUNT + 1)
        print('.' * iteration + ' ' * (DOTS_COUNT - iteration), end='')
        time.sleep(1)

    if not first:
        print()


def connectToSSH(host, password):

    print('Testing SSH connection... ', end='')

    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(MyPolicy)

        while True:
            try:
                client.connect(host, username='root', password=password)
                stdin, stdout, stderr = client.exec_command('df -h')
                break
            except ConnectionRefusedError:
                pass

    except paramiko.ssh_exception.AuthenticationException:
        return False
    except Exception as e:
        print(e)
        print(type(e))
        traceback.print_exc(file=sys.stdout)
        return False

    return True


def findImage(number):
    result = [ f for f in listdir('./') if number in f and 'sysupgrade' not in f ]
    if len(result) == 1:
        if len(result[0]) > 30:
            print('image for "' + result[0] + '" not found')
            return None

        return result[0]
    else:
        return None


def getRouterData(imageNr):
    result = [ f for f in listdir('./') if f.endswith('.csv') ]
    if len(result) == 1:
        with open(result[0], 'r') as f:
            reader = csv.reader(f)
            data = [ d for d in list(reader) if d[0] == imageNr ]
            if len(data) == 1:
                imageName = findImage(imageNr)
                if imageName is None:
                    return None

                return {
                    'nr': imageNr,
                    'imageName': imageName,
                    'SSID': data[0][1],
                    'wifiPwd': data[0][2],
                    'rootPwd': data[0][3]
                }
            elif len(data) == 0:
                print('image data for "' + imageNr + '" not found!')
                return None
            else:
                print('imageNr not unique!')
                return None
    elif len(result) == 0:
        print('.csv with image data not found!')
        return None

    print('.csv file not unique!')
    return None


def flashRouter(imageNr):

    data = getRouterData(imageNr)
    if data is None:
        return

    waitForHttpHostUp('192.168.0.1', 'Waiting for unflashed router')
    uploadImage(data['imageName'])
    waitForHttpHostUp('192.168.1.1', 'Flashing')
    if connectToSSH('192.168.1.1', data['rootPwd']):
        print('Success!')
    else:
        print('Failure?!')


def main():
    if len(sys.argv) == 2:
        flashRouter(sys.argv[1])
        return

    while True:
        image = 'exit'
        try:
            image = input('Image number? ')
        except EOFError:
            return

        if image == 'exit':
            return
        else:
            flashRouter(image)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        print(e)
