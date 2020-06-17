#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# @package    
# @brief      
#
# @version    $Revision: $
# @author     Sergey Green
# @note       
# @note       $Date:     $
# @note       $self.url:      $
#
# @requires https://pypi.org/project/requests/2.7.0/#files
# Revisions
# 2020-06-02 - added function to check the ansible flag file
# 2020-05-29 - Ambili Balan - added health checks for FILENET(ISRA))

import sys
import os
import re
import json
import logging
import socket
import requests
import collections
import inspect
import threading
import io
import glob
from xml.dom import minidom
from argparse import ArgumentParser, RawTextHelpFormatter
import potato.services

formatter = logging.Formatter('%(message)s')

console = logging.StreamHandler()
console.setFormatter(formatter)

LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(console)
LOGGER.setLevel(2)

#
# TODO:
# - docstrings
#
# NOTE:
# - Do not remove show_trace() method!
#

os.environ['REQUESTS_CA_BUNDLE'] = '/etc/ssl/certs/ca-bundle.crt' 

class Check_Alive:
    '''
        * Checks which services should be expected to run on a given host
          --option discovery
          
        * Checks if the indicated by the URL service is alive
          --option get_data
    '''
    def __init__(self):
        
        self.hostname  = socket.getfqdn().lower()
        self.maintenance = None

    def collect_args(self):
        
        parser = ArgumentParser(
            description='',
            formatter_class=RawTextHelpFormatter
        )
        parser.add_argument('--option',
            choices=['discovery', 'get_data'],
            required=True,
            help='Operation selector (discovery | get_data),\ndefault: %(default)s',
            metavar='OPTION'
        )
        parser.add_argument(
            '--fqdn',
            default=socket.getfqdn(),
            help='Fully qualified domain name,\ndefault = {}'.format(
                socket.getfqdn()
                ),
        )
        parser.add_argument(
            '--config',
            default='/etc/opt/allianz/allianz.server.conf',
            help='Configuration file defining the services on the given host,\ndefault = {}'.format(
                '/etc/opt/allianz/allianz.server.conf'
            ),
        )
        parser.add_argument(
            '--url',
            default=None,
            help='URL (See discovered items),\ndefault: %(default)s'
        )
        parser.add_argument(
            '--gfbid',
            default='15388493-61d3-11e9-a6cf-00505686183e',
            help='Enter the GFB_ID of the document to be checked for filenet health check,\ndefault: %(default)s'
        )  
        parser.add_argument(
            '--profile',
            default=None,
            help='Profile name (Used for discovering maintenance mode),\ndefault: %(default)s'
        )
        parser.add_argument(
            '--notation',
            default=None,
            help='Notation ( HTTP_HEADER | REST | REST_ADAPTER | SOAP | TEXT | XML ) \nthe returned data to be read from,\ndefault: %(default)s',
            metavar='NOTATION'
        )
        parser.add_argument(
            '--timeout',
            default=6,
            help='Timeout\ndefault: %(default)s seconds',
            metavar='SECONDS'
        )
        parser.add_argument('--trace', 
            default=False, 
            action='store_true',
            help='See where the execution of the script is,\ndefault: %(default)s'
        )
       
        self.args = parser.parse_args()
    
    def verify_args(self):
        
        self.show_trace()
        
        if self.args.url == 'na' or self.args.url == 'na':
            self.end_check()
        if self.args.option == 'get_data' and not self.args.url:
            self.print_error('URL is required ..')
        if self.args.option == 'get_data' and not self.args.notation:
            self.print_error('Notaion (SOAP, REST, HTTP_HEADER, TEXT) is required ..')
            
    def select_option(self):
        
        self.show_trace()
        options = {
            'discovery' : self.do_discovery,
            'get_data' : self.get_data
        }
        
        options[self.args.option]()
        
    def do_discovery(self):
        
        self.show_trace()
        discovered = []
        
        for profile in self.get_profiles():
            url = self.make_url(profile.port, profile.url)
            data = {
                "{#BASEURL}": url,
                "{#ITEMNAME}": profile.application,
                "{#PROFILE}": profile.profile,
                "{#NOTATION}": profile.notation
            }
            discovered.append(data)
            
        self.format_discovery(discovered)
        
    def get_profiles(self):
        
        self.show_trace()
        profiles = []
        Profile = collections.namedtuple("Profile","application profile port url notation")
        asc = potato.services.Services (self.args.config)
        asc.if_exists()
        
        for profile in asc.get_profiles():
            if 'jolokia' in profile[3]:
                continue
            
            profile = Profile(profile[0], profile[1], profile[2], profile[3], profile[4])
            profiles.append(profile)
            
        return profiles

    def format_discovery(self, discovered):
        
        self.show_trace()

        load = {}
        load['data'] = discovered
        LOGGER.info (json.dumps(load,indent=4))
        
        self.end_timeout()
        
    def make_url(self, port, url):

        self.show_trace()
        replacements = {
            '%HOSTNAME%':self.args.fqdn,
            '%PORT%':port}
        
        for old, new in replacements.items():
            url = url.replace(old,new)
            
        return url
    
    def get_data(self):
        
        self.show_trace()
        
        self.check_ansiblemaintenance()
        
        self.attest_maintenance()
        
        notation = {
            'REST' : self.do_rest,
            'REST_ADAPTER' : self.do_rest_adapter,
            'SOAP' : self.do_soap,
            'XML' : self.do_xml,
            'HTTP_HEADER' : self.do_http_header,
            'TEXT' : self.do_text,
            'INFO': self.do_info
        }
        notation[self.args.notation]()
        
    def attest_maintenance(self):
        
        self.show_trace()
        
        for maintenance_flag in [
            '{}.{}'.format(p, self.args.profile) for p in 'maintenance-svc maintenance-cmon'.split()
            ]:
            if os.path.isfile(os.path.join('/tmp/',maintenance_flag)):
                self.maintenance = maintenance_flag

    def do_rest(self):   
        
        self.show_trace()
        self.create_rest_session()
        self.lookup_rest()   
        
    def do_rest_adapter(self):
        
        self.show_trace()
        self.create_rest_session()
        self.lookup_rest_adapter()
          
    def do_soap(self):
        
        self.show_trace()
        self.create_soap_session()
        self.lookup_soap()
        
    def do_xml(self):
        
        self.show_trace()
        self.create_soap_session()
        self.lookup_xml()
        
    def do_http_header(self):
        
        self.show_trace()
        self.create_rest_session()
        self.lookup_http_header()
        
    def do_text(self):
        
        self.show_trace()
        self.create_rest_session()
        self.lookup_text()
        
    def do_info(self):
        
        self.show_trace()
        self.create_rest_session()
        self.lookup_info()
        
    def create_soap_session(self):
        
        self.show_trace()
        self.session = requests.Session()
        self.session.headers = {
            'Content-type': 'application/soap+xml',
            'SOAPAction': 'http://gfb.allianz.at/mag/vertrag/isalive/ws'
        }
        
    def create_rest_session(self):
        
        self.show_trace()
        self.session = requests.Session()
        self.session.headers = {
            'Connection' : 'keep-alive',
            'Content-Type' : 'application/json',
        }

    def session_call(self):
        
        self.show_trace()
                
        try:
            r = self.session.get(self.args.url)
        except Exception as e:
            self.print_error(e)
            
        if r.status_code == 200:
            return r
        
        LOGGER.info(1)
        self.end_timeout()
        sys.exit(1)
        
    def session_call_rest_adapter(self):
        
        self.show_trace()

        try:
            r = self.session.get(self.args.url)
        except Exception as e:
            self.print_error(e)
            
        if r.status_code == 200:
            return r
        
        LOGGER.info(1)
        self.end_timeout()
        sys.exit(1)
        
    def session_call_soap(self):
        
        self.show_trace()
        xml=('''<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">
           <soap:Header/>
           <soap:Body/>
        </soap:Envelope>''')
        
        try:
            r = self.session.post(self.args.url, data=xml)
        except Exception as e:
            self.print_error(e)
        
        if r.status_code == 200:
            return r
        
        LOGGER.info(1)
        self.end_timeout()
        sys.exit(1)
        
    def session_call_http_header(self):
        
        self.show_trace()
        
        try:
            r = self.session.post(self.args.url)
        except requests.exceptions.ConnectionError as e:
            self.print_error(e)

        if r.status_code == 200:
            return r
        
        LOGGER.info(1)
        self.end_timeout()
        sys.exit(1)
        
    def lookup_rest(self):
        
        self.show_trace()
        resp = self.session_call() 
        self.format_rest(resp)
        
    def lookup_soap(self):
        
        self.show_trace()
        resp = self.session_call_soap() 
        self.format_soap(resp)
        
    def lookup_xml(self):
        
        self.show_trace()
        resp = self.session_call() 
        self.format_xml(resp)
        
    def lookup_rest_adapter(self):
        
        self.show_trace()
        resp = self.session_call_rest_adapter() 
        self.format_rest_adapter(resp)
        
    def lookup_http_header(self):
        
        self.show_trace()
        resp = self.session_call_http_header() 
        self.format_http_headers(resp)
        
    def lookup_text(self):
        
        self.show_trace()
        for profile in self.get_profiles():
            if profile.application == 'FILENET': 
                resp=self.session_call_filenet()
                LOGGER.info(0) if resp else LOGGER.info(1)
                self.end_timeout()
            else:
                resp = self.session_call() 
                self.format_text(resp)
                
    def session_call_filenet(self):
        
        self.show_trace()
        url='{}/{}'.format(self.args.url,self.args.gfbid)    
        try:
            r = self.session.get(url)
        except Exception as e:
            self.print_error(e)
        if r.status_code == 200:
            return r
        LOGGER.info(1)
        self.end_timeout()
        sys.exit(1) 
        
    def lookup_info(self):
        
        self.show_trace()
        resp = self.session_call() 
        self.format_info(resp)
        
    def format_rest(self, resp):
        #
        # TODO
        # * tst with bad status
        #
        self.show_trace()
        try:
            status = 0 if json.loads(resp.text)['status'] == 'UP' else 1
           
        except Exception as e:
            self.print_error('Bad format: {} - {}'.format(self.args.notation, e))
         
        self.print_finding(status)   
        
    def format_rest_adapter(self, resp):
       
        self.show_trace()
        try:
            status = json.loads(resp.text)['items'][0]['statusCode']
            
        except Exception as e:
            self.print_error('Bad format: {} - {}'.format(self.args.notation, e))
        
        self.print_finding(status)    
       
    def format_soap(self, resp):
        #
        # TODO
        # * test with bad status
        #
        self.show_trace()
        try:
            doc = minidom.parseString(resp.text)
            check_response = doc.getElementsByTagName('checkResponse')[0]
            status = 1

            if check_response.firstChild.nodeValue == '1':
                status = 0
           
        except Exception as e:
            self.print_error('Bad format: {} - {}'.format(self.args.notation, e))
         
        self.print_finding(status)    
      
    def format_xml(self, resp):
        #
        # TODO
        # * test with failed deployments (how it is to be printed)
        #
        self.show_trace()
        
        doc = minidom.parseString(resp.text)
        
        deployments = doc.getElementsByTagName('ns2:deployment')
        
        bads = []
        
        for deployment in deployments:
            if not deployment.getElementsByTagName('status')[0].firstChild.nodeValue == 'OK':
                bads.append (deployment.getElementsByTagName('deploymentName')[0].firstChild.nodeValue)
                
        if bads:
            status = 'FAILED Deployment|s: {}'.format(bads)
        elif not doc.getElementsByTagName('ns2:deployment').length:
            status = 2
        else:
            status = 0
         
        self.print_finding(status)    
        
    def format_http_headers(self, resp):
        #
        # TODO
        # * maintenance is not checked
        #
        self.show_trace
        
        try:
            content = [line.strip() for line in io.StringIO(resp.text) ]

            for line in content:
                if 'bordered label' in line:
                    result = re.search('<div><span class="bordered label">(.*)</span>', line)
                    if result:
                        LOGGER.info(result.group(1))
        
        except Exception as e:
            self.print_error('Bad format: {} - {}'.format(self.args.notation, e))
        
        self.end_timeout()
                    
    def format_text(self, resp):
        #
        # TODO
        #
        self.show_trace()
        
        try:
            if self.maintenance:
                LOGGER.info(3)
            else:
                LOGGER.info (resp.text.replace('<br/>','\n'))       
        except Exception as e:
            self.print_error('Bad format: {} - {}'.format(self.args.notation, e))
        
        self.end_timeout()    
        
    def format_info(self, resp):
       
        self.print_finding(0)
            
    def print_finding(self, status):
        
        if not status and not self.maintenance:
            LOGGER.info(0)
        elif status and not self.maintenance:
            LOGGER.info(1)
        elif status and self.maintenance:
            LOGGER.info(2)
        elif not status and self.maintenance:
            LOGGER.info(3)
            
        self.end_timeout()
                         
    def print_error(self, text):
        
        self.show_trace()
        LOGGER.info('{}'.format(text))
        self.end_timeout()
        sys.exit(1)
        
    def start_timeout(self):
       
        self.show_trace()
        self.timeout = threading.Timer(int(self.args.timeout), self.print_timeout)
        self.timeout.start()
        
    def end_timeout(self):
        
        self.show_trace()
        self.timeout.cancel()
    
    def print_timeout(self, t=None):
    
        self.show_trace()
        LOGGER.info(4)
        os._exit(1)
            
    def show_trace(self):
        
        if self.args.trace:
            LOGGER.info('{:03d}: {:17}-> {}'.format(
                inspect.currentframe().f_back.f_lineno,
                sys._getframe(2).f_code.co_name,
                sys._getframe(1).f_code.co_name
                )
            )
            
    def end_check(self):
        
        self.show_trace()
        
        LOGGER.info(2)
        self.end_timeout()
        sys.exit()
        
    def check_ansiblemaintenance(self):
        self.show_trace()
        if glob.glob("/tmp/maintenance-deployment-running.*"):
            LOGGER.info(7)
            self.end_timeout()
            exit()
        
def main():
    ca = Check_Alive()
    ca.collect_args()
    ca.start_timeout()
    ca.verify_args()
    ca.select_option()

if __name__ == '__main__':
    main()
