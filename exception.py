import sys
import six
import logging
from six import reraise as raise_
import webob.exc 
import serializers

log = logging.getLogger(__name__)

class OsagentAPIException(webob.exc.HTTPError):

    """webob HTTPError subclass that creates a serialized body.

    Subclass webob HTTPError so we can correctly serialize the wsgi response
    into the http response body, using the format specified by the request.
    Note this should not be used directly, instead use the subclasses
    defined below which map to AWS API errors.
    """

    code = 400
    title = "AgentAPIException"
    explanation = ("Generic AgentAPIException, please use specific "
                    "subclasses!")
    err_type = "Sender"

    def __init__(self, detail=None):
        """Overload HTTPError constructor to create a default serialized body.

        This is required because not all error responses are processed
        by the wsgi controller (such as auth errors), which are further up the
        paste pipeline.  We serialize in XML by default (as AWS does).
        """
        webob.exc.HTTPError.__init__(self, detail=detail)
        serializer = serializers.JSONResponseSerializer()
        serializer.default(self, self.get_unserialized_body(), status=self.code)

    def get_unserialized_body(self):
        """Return a dict suitable for serialization in the wsgi controller.

        This wraps the exception details in a format which maps to the
        expected format for the AWS API.
        """
        # Note the aws response format specifies a "Code" element which is not
        # the html response code, but the AWS API error code, e.g self.title
        if self.detail:
            message = ":".join([self.explanation, self.detail])
        else:
            message = self.explanation
        return {'ErrorResponse': {'Error': {'Type': self.err_type,
                'Code': self.title, 'Message': message}}}

class RequestLimitExceeded(OsagentAPIException):
    code = 500
    title = "Request limit exceeded "
    explanation = 'Request json body limit exceeded  100000'

class SIGHUPInterrupt(Exception):
    message = "SIGHUPInterrupt"
    error_code = None
