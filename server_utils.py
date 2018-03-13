#utility functions that help define server properties
import re
import logging
import sys

GOOGLE_PLACES_API_KEY = 'AIzaSyAz2QNbrKwKrPqaFhf1hvlHDGVzadjxiT8'

def getPort(serverName):
    return {
      'Goloman': 16590,
      'Hands': 16591,
      'Holiday': 16592,
      'Welsh': 16593,
      'Wilkes': 16594
    }.get(serverName, -1)

def getNeighbors(serverName):
    return {
      'Goloman': ['Hands', 'Holiday', 'Wilkes'],
      'Hands': ['Wilkes', 'Goloman'],
      'Holiday': ['Welsh', 'Wilkes', 'Goloman'],
      'Wilkes': ['Goloman', 'Hands', 'Holiday'],
      'Welsh': ['Holiday']
    }.get(serverName, -1)


def isWellFormed(message, type):
    message_split = message.split(' ')

    # Three types of messages: IAMAT, AT, WHATSAT
    #IAMAT
    if type == 'IAMAT':
      if len(message_split) != 4:
        return False

      client_ID = message_split[1]
      client_lat_long = message_split[2]
      client_time_sent = message_split[3]
      
      # Run a series of regex checks
      t1 = re.match(r'\S+', client_ID)
      t2 = re.match(r'[\+\-]\d+\.\d+[\+\-]\d+\.\d+', client_lat_long)
      t3 = re.match(r'\d+\.\d+', client_time_sent)
      if (t1 == None) or (t2 == None) or (t3 == None):
        return False

    #WHATSAT
    elif type == 'WHATSAT':
      if len(message_split) != 4:
        return False

      client_ID = message_split[1]
      client_radius = message_split[2]
      client_upper_bound = message_split[3]

      # Run a series of regex checks
      t1 = re.match(r'\S+', client_ID)
      t2 = re.match(r'\b\d{1,2}\b', client_radius)
      t3 = re.match(r'\b\d{1,2}\b', client_upper_bound)
      if (t1 == None) or (t2 == None) or (t3 == None):
        return False
      
      # Client radius 0-50
      if (int(client_radius) < 0) or (int(client_radius) > 50):
        return False
      # Client upper bound 0-20
      if (int(client_upper_bound) < 0) or (int(client_upper_bound) > 20):
        return False

    #AT
    elif type == 'AT':
      if len(message_split) != 7:
        return False

      server_ID = message_split[1] 
      clock_skew = message_split[2]
      client_ID = message_split[3]
      client_lat_long = message_split[4]
      client_time_sent = message_split[5]
      from_server = message_split[6]

      # Run a series of regex checks
      t1 = re.match(r'[a-zA-Z]+', server_ID)
      t2 = re.match(r'[\+\-]\d+\.\d+', clock_skew)
      t3 = re.match(r'\S+', client_ID)
      t4 = re.match(r'[\+\-]\d+\.\d+[\+\-]\d+\.\d+', client_lat_long)
      t5 = re.match(r'\d+\.\d+', client_time_sent)
      t6 = re.match(r'[a-zA-Z]+', from_server)
      if (t1 == None) or (t2 == None) or (t3 == None) or (t4 == None) or (t5 == None) or (t6 == None):
        return False

    # The message passed all the checks
    return True

class Client:
    def __init__(self, ID, location, time):
        self.ID = ID
        self.location = location
        self.time = time