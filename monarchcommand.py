# *********************************************************
# *   monarchcommand.py                                   *
# *                                                       *
# *   Author: Joshua Morris, josh.morris@monash.edu       *
# *                                                       *
# *   Python library to interface and send a few simple   *
# *   simple commands to the Matrox Monarch HD encoder.   *
# *                                                       *
# *********************************************************

import time
import requests
# import numpy as np

# TODO deal with return results from commands sent


class MonarchHD(object):

    def __init__(self, IP, username='admin', password='admin'):

        # set control properties
        self.ip = IP
        self.usr = username
        self.pwd = password

        # set base URL
        self.url = 'http://%s/Monarch/syncconnect/sdk.aspx?command=%s'

    # send command to Monarch
    def monCommand(self, command):
        return requests.get(self.url % (self.ip, command), auth=(self.usr, self.pwd), timeout=5)

    # get device status
    def GetStatus(self):
        result = self.monCommand('GetStatus')
        return result
        
    # start streaming
    def StartStream(self):
        result = self.monCommand('StartStreaming')

    # start recording
    def StartRecord(self):
        result = self.monCommand('StartRecording')

    # start streaming and recording
    def StartStrRec(self):
        result = self.monCommand('StartStreamingAndRecording')

    # stop streaming
    def StopStream(self):
        result = self.monCommand('StopStreaming')

    # stop recording
    def StopRecord(self):
        result = self.monCommand('StopRecording')

    # stop streaming and recording
    def StopStrRec(self):
        result = self.monCommand('StopStreamingAndRecording')

if __name__ == '__main__':

    #-----------------
    # User parameters
    #-----------------
    # ip address of the monarch
    target_ip = '130.194.171.212'

    # username and password (default is admin/admin)
    usr = 'admin'
    pwd = 'admin'

    monarch = MonarchHD(target_ip, username=usr, password=pwd)
    status = monarch.GetStatus()