import httplib

from flask import session, request, make_response
from flask.ext.restful_swagger import swagger
from flask_restful import Resource

import ARM
from Borg import Borg
from CairisHTTPError import ARMHTTPError, CairisHTTPError, ObjectNotFoundHTTPError
from CairisHTTPError import MalformedJSONHTTPError
from Goal import Goal
from GoalParameters import GoalParameters
from KaosModel import KaosModel
from tools.JsonConverter import json_serialize, json_deserialize
from tools.MessageDefinitions import GoalMessage
from tools.ModelDefinitions import GoalModel as SwaggerGoalModel
from tools.SessionValidator import validate_proxy, validate_fonts, check_environment


__author__ = 'Robin Quetin'


class GoalsAPI(Resource):
    #region Swagger Doc
    @swagger.operation(
        notes='Get all goals.',
        responseClass=SwaggerGoalModel.__name__,
        nickname='goals-get',
        parameters=[
            {
                "name": "session_id",
                "description": "The ID of the user's session",
                "required": False,
                "allowMultiple": False,
                "dataType": str.__name__,
                "paramType": "query"
            }
        ],
        responseMessages=[
            {
                "code": httplib.BAD_REQUEST,
                "message": "The database connection was not properly set up"
            }
        ]
    )
    #endregion
    def get(self):
        session_id = request.args.get('session_id', None)
        db_proxy = validate_proxy(session, session_id)
        goals = db_proxy.getGoals()

        assert isinstance(goals, dict)
        for key in goals:
            goal = goals[key]
            goal.theEnvironmentDictionary = {}
            goals[key] = goal

        resp = make_response(json_serialize(goals, session_id=session_id))
        resp.headers['Content-Type'] = "application/json"
        return resp

    #region Swagger Doc
    @swagger.operation(
        notes='Creates a new goal',
        nickname='goal-post',
        parameters=[
            {
                "name": "body",
                "description": "The serialized version of the new goal to be added",
                "required": True,
                "allowMultiple": False,
                "type": GoalMessage.__name__,
                "paramType": "body"
            },
            {
                "name": "session_id",
                "description": "The ID of the user's session",
                "required": False,
                "allowMultiple": False,
                "dataType": str.__name__,
                "paramType": "query"
            }
        ],
        responseMessages=[
            {
                'code': httplib.BAD_REQUEST,
                'message': 'One or more attributes are missing'
            },
            {
                'code': httplib.CONFLICT,
                'message': 'Some problems were found during the name check'
            },
            {
                'code': httplib.CONFLICT,
                'message': 'A database error has occurred'
            }
        ]
    )
    #endregion
    def post(self):
        session_id = request.args.get('session_id', None)
        new_json_goal = request.get_json(silent=True)
        if new_json_goal is False or new_json_goal is None:
            raise MalformedJSONHTTPError(data=request.get_data())

        session_id = new_json_goal.get('session_id', session_id)
        db_proxy = validate_proxy(session, session_id)
        goal = json_deserialize(new_json_goal['object'], 'goal')

        try:
            db_proxy.nameCheck(goal.theName, 'goal')
        except ARM.ARMException as ex:
            raise ARMHTTPError(ex)

        goalParams = GoalParameters(
            goalName=goal.theName,
            goalOrig=goal.originator(),
            tags=goal.tags(),
            properties=goal.environmentProperties()
        )

        try:
            resp_dict = dict()
            resp_dict['goal_id'] = db_proxy.addGoal(goalParams)
            resp = make_response(json_serialize(resp_dict), httplib.OK)
            resp.contenttype = 'application/json'
            return resp
        except ARM.ARMException as ex:
            raise ARMHTTPError(ex)

class ColouredGoalsAPI(Resource):
    #region Swagger Doc
    @swagger.operation(
        notes='Get all goals with associated goals',
        responseClass=SwaggerGoalModel.__name__,
        nickname='goals-coloured-get',
        parameters=[
            {
                "name": "session_id",
                "description": "The ID of the user's session",
                "required": False,
                "allowMultiple": False,
                "dataType": str.__name__,
                "paramType": "query"
            }
        ],
        responseMessages=[
            {
                "code": httplib.BAD_REQUEST,
                "message": "The database connection was not properly set up"
            }
        ]
    )
    #endregion
    def get(self):
        session_id = request.args.get('session_id', None)
        db_proxy = validate_proxy(session, session_id)
        goals = db_proxy.getColouredGoals()

        assert isinstance(goals, dict)
        for key in goals:
            goal = goals[key]
            goal.theEnvironmentProperties = []
            goals[key] = goal

        resp = make_response(json_serialize(goals, session_id=session_id))
        resp.headers['Content-Type'] = "application/json"
        return resp

class GoalByIdAPI(Resource):
    # region Swagger Doc
    @swagger.operation(
        notes='Get a goal by ID',
        responseClass=SwaggerGoalModel.__name__,
        nickname='goal-by-id-get',
        parameters=[
            {
                "name": "session_id",
                "description": "The ID of the user's session",
                "required": False,
                "allowMultiple": False,
                "dataType": str.__name__,
                "paramType": "query"
            }
        ],
        responseMessages=[
            {
                "code": httplib.BAD_REQUEST,
                "message": "The database connection was not properly set up"
            }
        ]
    )
    # endregion
    def get(self, id):
        session_id = request.args.get('session_id', None)
        db_proxy = validate_proxy(session, session_id)
        goals = db_proxy.getGoals()

        found_goal = None
        idx = 0
        while found_goal is None and idx < len(goals):
            if goals.values()[idx].theId == id:
                found_goal = goals.values()[idx]
                found_goal.theEnvironmentDictionary = {}
            idx += 1

        resp = make_response(json_serialize(found_goal, session_id=session_id))
        resp.headers['Content-Type'] = "application/json"
        return resp

    #region Swagger Doc
    @swagger.operation(
        notes='Updates an existing goal',
        nickname='goal-put',
        parameters=[
            {
                "name": "body",
                "description": "The serialized version of the goal to be updated",
                "required": True,
                "allowMultiple": False,
                "type": GoalMessage.__name__,
                "paramType": "body"
            },
            {
                "name": "session_id",
                "description": "The ID of the user's session",
                "required": False,
                "allowMultiple": False,
                "dataType": str.__name__,
                "paramType": "query"
            }
        ],
        responseMessages=[
            {
                'code': httplib.BAD_REQUEST,
                'message': 'One or more attributes are missing'
            },
            {
                'code': httplib.CONFLICT,
                'message': 'Some problems were found during the name check'
            },
            {
                'code': httplib.CONFLICT,
                'message': 'A database error has occurred'
            }
        ]
    )
    #endregion
    def put(self, id):
        session_id = request.args.get('session_id', None)
        new_json_goal = request.get_json(silent=True)

        if new_json_goal is False or new_json_goal is None:
            raise MalformedJSONHTTPError(data=request.get_data())

        session_id = new_json_goal.get('session_id', session_id)
        db_proxy = validate_proxy(session, session_id)
        goal = json_deserialize(new_json_goal['object'])

        try:
            db_proxy.nameCheck(goal.theName, 'goal')
            raise ObjectNotFoundHTTPError('The provided goal name')
        except ARM.ARMException as ex:
            if str(ex.value).find(' already exists') < 0:
                raise ARMHTTPError(ex)

        goalParams = GoalParameters(
            goalName=goal.theName,
            goalOrig=goal.originator(),
            tags=goal.tags(),
            properties=goal.environmentProperties()
        )
        goalParams.setId(id)

        try:
            db_proxy.updateGoal(goalParams)
            resp = make_response('Update successful', httplib.OK)
            resp.contenttype = 'text/plain'
            return resp
        except ARM.ARMException as ex:
            raise ARMHTTPError(ex)

    #region Swagger Doc
    @swagger.operation(
        notes='Deletes an existing goal',
        nickname='goal-by-id-delete',
        parameters=[
            {
                "name": "body",
                "description": "The serialized version of the goal to be updated",
                "required": True,
                "allowMultiple": False,
                "type": GoalMessage.__name__,
                "paramType": "body"
            },
            {
                "name": "session_id",
                "description": "The ID of the user's session",
                "required": False,
                "allowMultiple": False,
                "dataType": str.__name__,
                "paramType": "query"
            }
        ],
        responseMessages=[
            {
                'code': httplib.BAD_REQUEST,
                'message': 'One or more attributes are missing'
            },
            {
                'code': httplib.CONFLICT,
                'message': 'Some problems were found during the name check'
            },
            {
                'code': httplib.CONFLICT,
                'message': 'A database error has occurred'
            }
        ]
    )
    #endregion
    def delete(self, id):
        session_id = request.args.get('session_id', None)
        db_proxy = validate_proxy(session, session_id)

        goals = db_proxy.getGoals()
        if goals is None:
            raise ObjectNotFoundHTTPError('A full list of goals')

        found_goal = None
        idx = 0
        while found_goal is None and idx < len(goals.values()):
            goal = goals.values()[idx]
            if goal.theId == id:
                found_goal = goal
            idx+=1

        if found_goal is None or not isinstance(found_goal, Goal):
            raise ObjectNotFoundHTTPError('The provided goal ID')

        try:
            db_proxy.deleteGoal(found_goal.theId)
            resp = make_response('Delete successful', httplib.OK)
            resp.contenttype = 'text/plain'
            return resp
        except ARM.ARMException as ex:
            raise ARMHTTPError(ex)

class GoalByNameAPI(Resource):
    # region Swagger Doc
    @swagger.operation(
        notes='Get a goal by name',
        responseClass=SwaggerGoalModel.__name__,
        nickname='goal-by-name-get',
        parameters=[
            {
                "name": "session_id",
                "description": "The ID of the user's session",
                "required": False,
                "allowMultiple": False,
                "dataType": str.__name__,
                "paramType": "query"
            }
        ],
        responseMessages=[
            {
                "code": httplib.BAD_REQUEST,
                "message": "The database connection was not properly set up"
            }
        ]
    )
    # endregion
    def get(self, name):
        session_id = request.args.get('session_id', None)
        db_proxy = validate_proxy(session, session_id)
        goals = db_proxy.getGoals()

        found_goal = None
        if goals is not None:
            found_goal = goals.get(name, None)

        if found_goal is None:
            raise ObjectNotFoundHTTPError('The provided goal name')

        resp = make_response(json_serialize(found_goal, session_id=session_id))
        resp.headers['Content-Type'] = "application/json"
        return resp

    #region Swagger Doc
    @swagger.operation(
        notes='Updates an existing goal',
        nickname='goal-put',
        parameters=[
            {
                "name": "body",
                "description": "The serialized version of the goal to be updated",
                "required": True,
                "allowMultiple": False,
                "type": GoalMessage.__name__,
                "paramType": "body"
            },
            {
                "name": "session_id",
                "description": "The ID of the user's session",
                "required": False,
                "allowMultiple": False,
                "dataType": str.__name__,
                "paramType": "query"
            }
        ],
        responseMessages=[
            {
                'code': httplib.BAD_REQUEST,
                'message': 'One or more attributes are missing'
            },
            {
                'code': httplib.CONFLICT,
                'message': 'Some problems were found during the name check'
            },
            {
                'code': httplib.CONFLICT,
                'message': 'A database error has occurred'
            }
        ]
    )
    #endregion
    def put(self, name):
        session_id = request.args.get('session_id', None)
        new_json_goal = request.get_json(silent=True)

        if new_json_goal is False or new_json_goal is None:
            raise MalformedJSONHTTPError(data=request.get_data())

        session_id = new_json_goal.get('session_id', session_id)
        db_proxy = validate_proxy(session, session_id)
        goal = json_deserialize(new_json_goal['object'])

        try:
            db_proxy.nameCheck(name, 'goal')
            raise ObjectNotFoundHTTPError('The provided goal name')
        except ARM.ARMException as ex:
            if str(ex.value).find(' already exists') < 0:
                raise ARMHTTPError(ex)

        goalParams = GoalParameters(
            goalName=goal.theName,
            goalOrig=goal.originator(),
            tags=goal.tags(),
            properties=goal.environmentProperties()
        )
        goalParams.setId(goal.theId)

        try:
            db_proxy.updateGoal(goalParams)
            resp = make_response('Update successful', httplib.OK)
            resp.contenttype = 'text/plain'
            return resp
        except ARM.ARMException as ex:
            raise ARMHTTPError(ex)

    #region Swagger Doc
    @swagger.operation(
        notes='Deletes an existing goal',
        nickname='goal-by-id-delete',
        parameters=[
            {
                "name": "body",
                "description": "The serialized version of the goal to be updated",
                "required": True,
                "allowMultiple": False,
                "type": GoalMessage.__name__,
                "paramType": "body"
            },
            {
                "name": "session_id",
                "description": "The ID of the user's session",
                "required": False,
                "allowMultiple": False,
                "dataType": str.__name__,
                "paramType": "query"
            }
        ],
        responseMessages=[
            {
                'code': httplib.BAD_REQUEST,
                'message': 'One or more attributes are missing'
            },
            {
                'code': httplib.CONFLICT,
                'message': 'Some problems were found during the name check'
            },
            {
                'code': httplib.CONFLICT,
                'message': 'A database error has occurred'
            }
        ]
    )
    #endregion
    def delete(self, name):
        session_id = request.args.get('session_id', None)
        db_proxy = validate_proxy(session, session_id)

        goals = db_proxy.getGoals()
        if goals is None:
            raise ObjectNotFoundHTTPError('A full list of goals')

        found_goal = goals.get(name)

        if found_goal is None or not isinstance(found_goal, Goal):
            raise ObjectNotFoundHTTPError('The provided goal ID')

        try:
            db_proxy.deleteGoal(found_goal.theId)
            resp = make_response('Delete successful', httplib.OK)
            resp.contenttype = 'text/plain'
            return resp
        except ARM.ARMException as ex:
            raise ARMHTTPError(ex)


class GoalModelAPI(Resource):
    # region Swagger Doc
    @swagger.operation(
        notes='Get the goal model for a specific environment',
        responseClass=SwaggerGoalModel.__name__,
        nickname='goal-by-name-get',
        parameters=[
            {
                "name": "environment",
                "description": "The environment to be used for the asset model",
                "required": True,
                "allowMultiple": False,
                "dataType": str.__name__,
                "paramType": "query"
            },
            {
                "name": "session_id",
                "description": "The ID of the user's session",
                "required": False,
                "allowMultiple": False,
                "dataType": str.__name__,
                "paramType": "query"
            }
        ],
        responseMessages=[
            {
                "code": httplib.BAD_REQUEST,
                "message": "The database connection was not properly set up"
            },
            {
                "code": httplib.NOT_FOUND,
                "message": "Environment not found"
            },
            {
                "code": httplib.BAD_REQUEST,
                "message": "Environment not defined"
            }
        ]
    )
    # endregion
    def get(self):
        b = Borg()
        model_generator = b.model_generator

        session_id = request.args.get('session_id', None)
        environment = request.args.get('environment', None)

        if environment is None:
            raise CairisHTTPError(
                status_code=httplib.BAD_REQUEST,
                message='''The 'environment' query parameter was not provided to the API call.''',
                status='Environment not defined'
            )

        check_environment(environment, session, session_id)

        db_proxy = validate_proxy(session, session_id)
        fontName, fontSize, apFontName = validate_fonts(session, session_id)
        try:
            associationDictionary = db_proxy.goalModel(environment)
            associations = KaosModel(associationDictionary.values(), environment, db_proxy=db_proxy, font_name=fontName,
                font_size=fontSize)
            dot_code = associations.graph()
        except ARM.DatabaseProxyException as ex:
            raise ARMHTTPError(ex)

        resp = make_response(model_generator.generate(dot_code), httplib.OK)
        accept_header = request.headers.get('Accept', 'image/svg+xml')
        if accept_header.find('text/plain') > -1:
            resp.headers['Content-type'] = 'text/plain'
        else:
            resp.headers['Content-type'] = 'image/svg+xml'

        return resp