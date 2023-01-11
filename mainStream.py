#!/usr/bin/env python3

# --------------------------------------------
# @required Python 3.8
#
# Python script for root of node management
#
# (C) 2022 Proflujo Technology Pvt. Ltd.
# --------------------------------------------

# import python modules
import os, sys, glob, time, requests, json
import logging, sched, argparse, atexit
import subprocess, threading
# , yaml
from datetime import datetime
from datetime import timedelta
from datetime import date
import configparser, base64
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import ThreadPoolExecutor
from concurrent import futures

# import mysql.connector

class MainStream:

  """docstring for ClassName"""
  def __init__(self, log = True, logDir = ''):
    self.config  = configparser.ConfigParser()
    self.configfile = "config.ini"
    self.propertyfile = "env.yaml"
    self.showLog = log
    self.logDir = 'node-logs' if not logDir else logDir

    self.logger = self.configLogger()

    self.configColors()

  #---------------------------------------
  # Execute the command in server
  #---------------------------------------
  def onExecuteSSH( self, command, node, stfp = False ):
    
    if stfp:
      cmd = f"sshpass -p '{node.get('password')}' sftp -P {node.get('port')} {node.get('user')}@{node.get('host')} <<CMD \n{command} \nCMD"
    else:
      cmd = f"sshpass -p '{node.get('password')}' ssh -p {node.get('port')} {node.get('user')}@{node.get('host')} -To StrictHostKeyChecking=no 2>&1 -q <<CMD \n{command} \nCMD"
    
    result = subprocess.run( cmd, shell=True, capture_output=True, text=True )
    
    code    = result.returncode
    message = None

    output = result.stdout.strip()
    if output:
      message = output

    if code != 0:
      self.logger.debug(f"Error:Node {node.get('host')} \nwhile run following command: '{command}'\nerror: '{result.stderr}'\noutput:'{result.stdout}'")
    else:
      self.logger.debug(f"Success:Node : {node.get('host')}\ncommand:'{command}'\noutput: '{result.stdout}'")

    return { "code":code, "message":message }

  #---------------------------------------
  # Write log in custom file
  #---------------------------------------
  def writeLog(self, file, message, namedir = "", mode = "a"):
    loc = os.path.dirname(os.path.realpath(__file__))

    logDir = self.logDir
    if namedir != "":
      logDir = f"{self.logDir}/{namedir}"

    if not os.path.exists( logDir ):
       os.makedirs( logDir )
    
    # creating/opening a file
    f = open(f"{logDir}/{file}", mode)
    f.write(message)
    f.write("\n")
    f.close()

  #---------------------------------------
  # get config values from config file
  #---------------------------------------
  def getConfig(self, section, key):
    try:
        self.config.read(self.configfile)

        value = self.config.get( section, key )
        
        if value:
          return value
        else:
          return ""

    except Exception as e:
        self.logger.error("Sorry! Unable to find out the configuration...")

    return None
        
  #---------------------------------------
  # Write config in config file
  #---------------------------------------
  def setConfig(self, section, key, value):
    try:
        if os.path.exists(self.configfile):
            self.config.read(self.configfile)

        if not self.config.has_section(section):    
          self.config.add_section(section)

        self.config.set( section, key, value )

        with open(self.configfile, 'w') as configfile:
            self.config.write(configfile)
    except Exception as e:
        self.logger.error("Sorry! Configuration failed...")
  
  #---------------------------------------
  # Encrypt content 
  #---------------------------------------
  def encryptCon( self, token ):
    messageBytes = token.encode('ascii')
    base64Bytes = base64.b64encode(messageBytes)
    base64Message = base64Bytes.decode('ascii')
    
    return base64Message

  #---------------------------------------
  # Decrypt content 
  #---------------------------------------
  def decryptCon(self, token ):
    base64Bytes = token.encode('ascii')
    messageBytes = base64.b64decode(base64Bytes)
    message = messageBytes.decode('ascii')

    return message

  # --------------------------------------------
  # Configure colors for logs
  # --------------------------------------------
  def configColors(self):
    self.colors = {
                    'white': "\033[137m",
                    'yellow': "\033[133m",
                    'green': "\033[132m",
                    'blue': "\033[134m",
                    'cyan': "\033[136m",
                    'red': "\033[131m",
                    'magenta': "\033[135m",
                    'black': "\033[130m",
                    'darkwhite': "\033[037m",
                    'darkyellow': "\033[033m",
                    'darkgreen': "\033[032m",
                    'darkblue': "\033[034m",
                    'darkcyan': "\033[036m",
                    'darkred': "\033[031m",
                    'darkmagenta':"\033[035m",
                    'darkblack': "\033[030m",
                    'error': "\033[91m",
                    'success': "\033[92m",
                    'warning': "\033[93m",
                    'info': "\033[94m",
                    'bold': "\033[1m",
                    'underline': "\033[4m",
                    'off': "\033[0m"
                  }
    return

  # --------------------------------------------
  # Configure logger for level logs
  # --------------------------------------------
  def configLogger(self):
    if not os.path.exists(self.logDir):
          os.makedirs(self.logDir)
    
    logger = logging.getLogger("nodemanager")
    logger.setLevel(logging.DEBUG)

    logname = f"{self.logDir}/{date.today().strftime('%Y%m%d')}-output"

    if self.showLog:
      # Create handlers, formatters and add it to handlers
      # CLI logger
      chandler = logging.StreamHandler()
      chandler.setLevel(logging.INFO)
      cformat = logging.Formatter('[%(levelname)s] %(asctime)s: %(message)s', datefmt="%d-%m-%Y %H:%M:%S")
      chandler.setFormatter(cformat)
      logger.addHandler(chandler)

    # file logger
    fhandler = logging.FileHandler(f'{logname}.log')
    fhandler.setLevel(logging.DEBUG)
    fformat = logging.Formatter('[%(name)s] %(asctime)s - %(levelname)s: %(message)s', datefmt="%d-%m-%Y %H:%M:%S")
    fhandler.setFormatter(fformat)
    logger.addHandler(fhandler)

    return logger

  def properties(self):
    with open(self.propertyfile) as f:
      envDict = yaml.safe_load(f)

  def parseJson(self, data):
    try:
      jsonData = json.loads(data)
      return jsonData
    except ValueError as e:
      return False

  def configParser( self, parser ):
    try:
      parser.add_argument('-config', '--config', type=str, help='Give a section from ini file')
      parser.add_argument('-key', '--key', type=str, help='Give the configuration key')
      parser.add_argument('-value', '--value', type=str, help='Give the configuration value')
      parser.add_argument('-v', '--version', action='version')
      parser.add_argument('-o', '--output', default='on', help='Show detailed output, options: on, off')
    except Exception as e:
      pass

    return parser

  def argProcess( self, arg ):
    try:
      self.showLog = True
      if arg.output == 'off':
        self.showLog = False

      if arg.config:
        if arg.key and arg.value:

          value = arg.value
          if arg.key == "password":
              value = self.encryptCon(value)

          self.setConfig( arg.config, arg.key, value )

          self.logger.info("Configration saved successfully.")
        else:
          self.logger.warning("If you choose configuration, please must provide the key & value")
          self.showLog = False

        return True
    except Exception as e:
      self.logger.error(e.str)
    
    return False

focal = MainStream()
