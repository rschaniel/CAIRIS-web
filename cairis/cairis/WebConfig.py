import logging
import os

from Borg import Borg
import BorgFactory


__author__ = 'Robin Quetin'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('cairisd')

def config(settings):
    logger.info('Starting CAIRIS as web daemon')

    if settings.has_key('configFile'):
        loadSettingsFromFile(settings['configFile'])
    else:
        loadSettingsFromFile()
    if settings.has_key('staticDir'):
        setStaticDir(settings['staticDir'])
    if settings.has_key('port'):
        setPort(int(settings['port']))
    if settings.has_key('loggingLevel'):
        setLoglevel(settings['loggingLevel'])

    logParams()

def loadSettingsFromFile(config_file=''):
    logger.info('Loading settings from file...')
    BorgFactory.dInitialise(config_file)

def setLoglevel(log_level):
    b = Borg()
    logger.info('Applying log level...')

    log_level = log_level.lower()
    if log_level == 'verbose':
        realLevel = logging.INFO
    elif log_level == 'debug':
        realLevel = logging.DEBUG
    else:
        realLevel = logging.WARNING

    b.logLevel = realLevel

def setPort(port):
    logger.info('Applying web port...')
    b = Borg()
    if port == 0:
        if not hasattr(b, 'webPort'):
            b.webPort = 7071
    else:
        b.webPort = port

def logParams():
    b = Borg()
    logger.info('Config: %s/cairis.cnf', b.configDir)
    if b.logLevel == logging.INFO:
        logger.info('Log level: INFO')
    elif b.logLevel == logging.DEBUG:
        logger.info('Log level: DEBUG')
    elif b.logLevel == logging.WARNING:
        logger.info('Log level: WARNING')

    logger.info('Port: %d', b.webPort)

def setStaticDir(self, static_dir):
    self.logger.info('Applying web port...')
    b = Borg()
    try:
        os.listdir(static_dir)
    except EnvironmentError as ex:
        self.logger.warning('The directory for static web content is not readable: %s' % ex.strerror)
        self.logger.warning('Static content may not be available')

    b.staticDir = os.path.abspath(static_dir)