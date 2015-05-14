import httplib
import logging

from ARM import DatabaseProxyException
from Borg import Borg
from MySQLDatabaseProxy import MySQLDatabaseProxy
from CairisHTTPError import MissingParameterHTTPError, CairisHTTPError, ObjectNotFoundHTTPError

__author__ = 'Robin Quetin'


def check_required_keys(json_dict, required):
    if not all(reqKey in json_dict for reqKey in required):
        raise MissingParameterHTTPError(param_names=required)

def get_logger():
    b = Borg()
    log = logging.getLogger('cairisd')
    log.setLevel(logging.INFO)

    try:
        log = b.logger
    except AttributeError:
        pass

    return log

def get_session_id(session, request):
    # Look if HTTP session is being used
    if session is not None:
        session_id = session.get('session_id', -1)
    else:
        session_id = -1

    # Look if body contains session ID
    json = request.get_json(silent=True)
    if json is not False and json is not None:
        session_id = json.get('session_id', session_id)

    # Check if the session ID is provided by query parameters
    session_id = request.args.get('session_id', session_id)
    return session_id

def validate_proxy(session, id, request=None, conf=None):
    """
    Validates that the DB proxy object is properly set up
    :param session: The session object of the request
    :param id: The session ID provided by the user
    :param conf: A dictionary containing configuration settings for direct authenrication
    :return: The MySQLDatabaseProxy object associated to the session
    :rtype : MySQLDatabaseProxy
    :raise CairisHTTPError: Raises a CairisHTTPError when the database could not be properly set up
    """

    if session is not None:
        session_id = session.get('session_id', -1)
    else:
        session_id = -1

    if conf is not None:
        if isinstance(conf, dict):
            try:
                db_proxy = MySQLDatabaseProxy(host=conf['host'], port=conf['port'], user=conf['user'], passwd=conf['passwd'], db=conf['db'])
                if db_proxy is not None:
                    return db_proxy
                else:
                    raise CairisHTTPError(
                        status_code=httplib.CONFLICT,
                        message='The database connection could not be created.'
                    )
            except DatabaseProxyException:
                raise CairisHTTPError(
                    status_code=httplib.BAD_REQUEST,
                    message='The provided settings are invalid and cannot be used to create a database connection'
                )

    if not (session_id == -1 and id is None):
        if id is None:
            id = session_id
        b = Borg()
        db_proxy = b.get_dbproxy(id)

        if db_proxy is None:
            raise CairisHTTPError(
                status_code=httplib.CONFLICT,
                message='The database connection could not be created.'
            )
        elif isinstance(db_proxy, MySQLDatabaseProxy):
            return db_proxy
        else:
            raise CairisHTTPError(
                status_code=httplib.CONFLICT,
                message='The database connection was not properly set up. Please try to reset the connection.'
            )
    else:
        raise CairisHTTPError(
            status_code=httplib.BAD_REQUEST,
            message='The session is neither started or no session ID is provided with the request.'
        )

def validate_fonts(session, id):
    """
    Validates that the fonts to output the SVG models are properly set up
    :param session: The session object of the request
    :param id: The session ID provided by the user
    :return: The font name, font size and AP font name
    :rtype : str,str,str
    :raise CairisHTTPError: Raises a CairisHTTPError when the database could not be properly set up
    """

    if session is not None:
        session_id = session.get('session_id', -1)
    else:
        session_id = -1

    if not (session_id == -1 and id is None):
        if id is None:
            id = session_id

        b = Borg()
        settings = b.get_settings(id)
        fontName = settings.get('fontName', None)
        fontSize = settings.get('fontSize', None)
        apFontName = settings.get('apFontSize', None)

        if fontName is None or fontSize is None or apFontName is None:
            raise CairisHTTPError(
                status_code=httplib.BAD_REQUEST,
                message='The method is not callable without setting up the project settings.'
            )
        elif isinstance(fontName, str) and isinstance(fontSize, str) and isinstance(apFontName, str):
            return fontName, fontSize, apFontName
        else:
            raise CairisHTTPError(
                status_code=httplib.BAD_REQUEST,
                message='The database connection was not properly set up. Please try to reset the connection.'
            )
    else:
        raise CairisHTTPError(
            status_code=httplib.BAD_REQUEST,
            message='The method is not callable without setting up the project settings.'
        )

def check_environment(environment_name, session, session_id):
    db_proxy = validate_proxy(session, session_id)

    environment_names = db_proxy.getEnvironmentNames()
    if not environment_name in environment_names:
        raise ObjectNotFoundHTTPError('The specified environment')