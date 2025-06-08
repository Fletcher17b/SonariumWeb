import time,datetime,os


def event_logger(string):
    if not os.path.exists('logs'):
        os.makedirs('logs')
    if not os.path.exists('logs/logs.txt'):
        os.makedirs('logs/logs.txt')
        
    rn = datetime.now()

    logstring = rn + ": " + string
