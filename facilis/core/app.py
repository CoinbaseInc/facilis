#!/usr/bin/python
# -*- coding: utf-8 -*-

#  Facilis
#  João Moreno <http://www.joaomoreno.com/>
#  GPLv3

import os, yaml, sys, clipboard
from urllib2 import urlopen, HTTPError
from re import search
from web import ServerHandler
from db import FilesDatabase
from misc import PortInUse
from threading import Event, Thread

class FacilisApp(object):
    def __init__(self):
        """Load options and start app."""
        
        # Load configuration stuff
        self.configFile = self.__configFile()
        self.__loadConfig()
        
        self.updateIP()
        self.ip_monitor = IPMonitor(self, 5 * 60)
        self.ip_monitor.start()
        
        self.db = FilesDatabase()
        # Load server
        self.server = ServerHandler(self, self.config['port'])
    
    def updateIP(self):
        """Stores the outer IP of this network / machine."""
        try:
            ip = urlopen('http://checkip.dyndns.org/').read()
            self.ip = search(r'(\d+.\d+.\d+.\d+)', ip).group()
        except HTTPError:
            import socket
            self.ip = socket.gethostbyname(socket.gethostname())
    
    def start(self):
        """Starts the application."""
        
        # Start the server (threaded)
        self.server.start()
        self.server.join(0.5)
        if not self.server.isAlive():
            raise PortInUse, self.config['port']
    
    def kill(self):
        """Called by the interface to kill the application."""
        self.ip_monitor.kill()
        exit(0)
    
    def __loadConfig(self):
        """Loads the config file and stores it in self.config."""
        try:
            f = file(self.configFile, 'r')
            self.config = yaml.load(f)
            f.close()
        except:
            # Default Configuration
            self.config = {
                'port': 4242,
                'domain': None,
                'use_domain': False
            }
            self.__saveConfig()
    
    def __saveConfig(self):
        """Saves the config in self.config to the config file."""
        f = file(self.configFile, 'w')
        yaml.dump(self.config, f)
        f.close()
    
    def __configFile(self):
        """Returns the configuration filename."""
        d = self.__userDir()
        if not os.path.exists(d):
            os.mkdir(d)
        return d + os.sep + "config.yml"
    
    def __userDir(self):
        """Returns the user configuration directory. Adapted from http://tinyurl.com/6hk5vz."""
        try:
            from win32com.shell import shell, shellcon
        except ImportError:
            shell = None
        try:
            import _winreg
        except ImportError:
            _winreg = None
        
        if shell:
            return shell.SHGetFolderPath(0, shellcon.CSIDL_APPDATA, 0, 0) + os.sep + "Facilis"
        if _winreg:
            k = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER,r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
            try:
                return _winreg.QueryValueEx( k, "AppData" )[0] + os.sep + "Facilis"
            finally:
                _winreg.CloseKey( k )
        
        for name in ['appdata', 'home']:
            if os.environ.has_key( name ):
                return os.environ[name] + os.sep + ".facilis"
        
        possible = os.path.abspath(os.path.expanduser( '~/' ))
        if os.path.exists( possible ):
            return possible + os.sep + ".facilis"
        
        raise OSError( "Unable to determine user's application-data directory")
    
    def setPort(self,p):
        self.config['port'] = p
        self.__saveConfig()
    
    def setDomain(self,d):
        self.config['domain'] = d
        self.__saveConfig()
    
    def useDomain(self,u):
        self.config['use_domain'] = u
        self.__saveConfig()
    
    def addFile(self, fname):
        """Add a file to share. Trows IOError in case file does not exist or is unreadable."""
        h = self.db.addFile(fname)
        url = self.getUrl(h)
        clipboard.copy(url)
        return url
    
    def getFile(self, url):
        return self.db.getFile(url)
    
    def getUrl(self, hash=''):
        return "http://%s:%i/%s\n" % (self.config['domain'] if self.config['use_domain'] else self.ip, self.config['port'], hash)

class IPMonitor(object):
    def __init__(self, app, interval):
        self.app = app
        self.e = Event()
        self.t = Thread(target=self.__repeat)
        self.i = interval

    def start(self):
        self.t.start()
    
    def kill(self):
        self.e.set()
        self.t.join()
    
    def __repeat(self):
        while True:
            self.e.wait(self.i)
            if self.e.isSet():
                break
            self.app.updateIP()
