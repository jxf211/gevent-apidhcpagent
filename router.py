# -*- coding:utf-8 -*-

import routes
from oslo_log import log as logging
import routes.middleware
import webob.dec
import webob.exc
import six
import json
#from lxml import etree
from nspagent.dhcp.agent import DhcpAgent
import exception
import serializers
from const import HTTP_INTERNAL_SERVER_ERROR

log = logging.getLogger(__name__)

def render_response(body, status):
    """
    @body  :Response的body
    @status:Response的状态码
    """
    if not isinstance(body, str):
        body = str(body)
    # 获取body长度
    content_len = str(len(body))
    # 生成Response header
    headers = [('Content-type', 'application/json'),
               ('Content-length', content_len)]
    return webob.Response(body=body, status=status, headerlist=headers)


class DefaultMethodController(object):
    def option(self, req, allowed_methods, *args, **kwargs):
        raise webob.exc.HTTPNocontent(headers=[('Allow', allowed_methods)])

    def reject(self, req, allowed_methods, *args, **kwargs):
        raise webob.exc.HTTPMethodNotAllowed(headers=[('Allow', allowed_methods)])

def is_json_content_type(request):
    if request.method == 'GET':
        try:
            aws_content_type = request.params.get("ContentType")
        except Exception:
            aws_content_type = None
        # respect aws_content_type when both available
        content_type = aws_content_type or request.content_type
    else:
        content_type = request.content_type
    # bug #1887882
    # for back compatible for null or plain content type
    if not content_type or content_type.startswith('text/plain'):
        content_type = 'application/json'
    if (content_type in ('JSON', 'application/json')
            and request.body.startswith(b'{')):
        return True
    return False

class JSONRequestDeserializer(object):
    def has_body(self, request):
        if (int(request.content_length or 0) > 0 and
                is_json_content_type(request)):
            return True
        return False

    def from_json(selfm, datastring):
        try:
        #    if len(datastring) > 100000:
        #        raise exception.RequestLimitExceeded()
            return json.loads(datastring)
        except ValueError as ex:
            raise webob.exc.HTTPBadRequest(six, text_type(ex))

    def default (self, request):
        if self.has_body(request):
            return {'body': self.from_json(request.body)}
        else:
            return {}

class Request(webob.Request):
    """Add some API-specific logic to the base webob.Request."""
    def best_match_content_type(self):
        """Determine the requested response content-type."""
        supported = ('application/json',)
        bm = self.accept.best_match(supported)
        return bm or 'application/json'

    def get_content_type(self, allowed_content_types):
        """Determine content type of the request body."""
        if "Content-Type" not in self.headers:
            raise exception.InvalidContentType(content_type=None)

        content_type = self.content_type

        if content_type not in allowed_content_types:
            raise exception.InvalidContentType(content_type=content_type)
        else:
            return content_type

class Resource(object):
    def __init__(self, controller, deserializer, serializer=None):
        self.controller = controller
        self.deserializer = deserializer
        self.serializer = serializer

    @webob.dec.wsgify(RequestClass=Request)
    def __call__(self, request):
        """WSGI method that controls (de)serialization and method dispatch."""
        action_args = self.get_action_args(request.environ)
        action = action_args.pop('action', None)
        content_type = request.params.get("ContentType")

        try:
            deserialized_request = self.dispatch(self.deserializer,
                                                 action, request)
            action_args.update(deserialized_request)

            log.debug(('Calling %(controller)s : %(action)s'),
                      {'controller': self.controller, 'action': action})

            code, action_result = self.dispatch(self.controller, action,
                                               request, **action_args)
        except TypeError as err:
            log.error(('Exception handling resource: %s'), err)
            msg = ('The server could not comply with the request since '
                    'it is either malformed or otherwise incorrect.')
            raise webob.exc.HTTPBadRequest(msg)
        except webob.exc.HTTPException as err:
            if isinstance(err, webob.exc.HTTPError):
                raise
            if isinstance(err, exception.OsagentAPIException):
                raise
            if isinstance(err, webob.exc.HTTPServerError):
                log.error(("Returning %(code)s to user: %(explanation)s"),
                            {'code': err.code, 'explanation': err.explanation})
            raise
        except Exception as err:
            log.error(err)
            return render_response(err, HTTP_INTERNAL_SERVER_ERROR)

        try:
            serializer = self.serializer
            if serializer is None:
                if content_type == "JSON":
                    serializer = serializers.JSONResponseSerializer()
                else:
                    serializer = serializers.XMLResponseSerializer()
            response = webob.Response(request=request)
            self.dispatch(serializer, action, response, action_result,
                          status=code)
            return response
        except Exception as err:
            log.error(err)
            return render_response(err, HTTP_INTERNAL_SERVER_ERROR)

    def dispatch(self, obj, action, *args, **kwargs):
        """Find action-specific method on self and call it."""
        try:
            method = getattr(obj, action)
        except AttributeError:
            method = getattr(obj, 'default')
        return method(*args, **kwargs)

    def get_action_args(self, request_environment):
        """Parse dictionary created by routes library."""
        try:
            args = request_environment['wsgiorg.routing_args'][1].copy()
        except Exception:
            return {}

        try:
            del args['controller']
        except KeyError:
            pass

        try:
            del args['format']
        except KeyError:
            pass

        return args

class Router(object):
    def __init__(self, mapper):
        self.map = mapper
        self._router = routes.middleware.RoutesMiddleware(self._dispatch,
                                                           self.map)

    @webob.dec.wsgify
    def __call__(self, req):

        return self._router

    @staticmethod
    @webob.dec.wsgify
    def _dispatch(req):
        match = req.environ['wsgiorg.routing_args'][1]
        if not match:
            log.debug('router not found:404')
            return webob.exc.HTTPNotFound()

        app = match['controller']
        return app

class API(Router):
    def __init__ (self):
        mapper = routes.Mapper()
        default_resource = Resource(DefaultMethodController(),
                                    JSONRequestDeserializer())

        def connect(controller, path_prefix, routes):
            urls = {}
            for r in routes:
                url = path_prefix + r['url']
                methods = r['method']
                if isinstance(methods, six.string_types):
                    methods = [methods]
                methods_str = ','.join(methods)
                mapper.connect(r['name'], url, controller=controller,
                               action=r['action'],
                               conditions={'method':methods_str})
                if url not in urls:
                    urls[url] = methods
                else:
                    urls[url] += methods
            for url, methods in urls.items():
                all_methods = ['HEAD', 'GET', 'POST', 'PATCH', 'DELETE', 'PUT']
                missing_methods = [m for m in all_methods if m not in methods]
                allowed_methods_str = ','.join(methods)
                mapper.connect(url,
                               controller=default_resource,
                               action='reject',
                               allowed_methods=allowed_methods_str,
                               conditions={'method':missing_methods})
                if 'OPTIONS' not in methods:
                    mapper.connect(url,
                                   controller=default_resource,
                                   action='options',
                                   allowed_method=allowed_methods_str,
                                   conditions={'method', 'OPTIONS'})

        deserializer = JSONRequestDeserializer()
        serializer =  serializers.JSONResponseSerializer()
        dhcp_controller = Resource(DhcpAgent(), deserializer, serializer)
        connect(controller = dhcp_controller,
                path_prefix = '/v1',
                routes = [
                    {   'name':'network_create_end',
                        'url':'/dhcp_network/',
                        'action':'network_create_end',
                        'method':'POST'
                    },

                    {
                        'name':'network_update_end',
                        'url':'/dhcp_network/',
                        'action':'network_update_end',
                        'method':'PUT'
                    },

                    {
                        'name':'network_delete_end',
                        'url':'/dhcp_network/:network_id',
                        'action':'network_delete_end',
                        'method':'DELETE'
                    },
			
                    
		    {
                        'name':'subnet_create_end',
                        'url':'/dhcp_subnet/',
                        'action':'subnet_create_end',
                        'method':'POST'
                    },

 
		    {
                        'name':'subnet_update_end',
                        'url':'/dhcp_subnet/',
                        'action':'subnet_update_end',
                        'method':'PUT'
                    },

                    {
                        'name':'subnet_delete_end',
                        'url':'/dhcp_subnet/:subnet_id',
                        'action':'subnet_delete_end',
                        'method':'DELETE'
                    },

                    {
                        'name':'port_create_end',
                        'url':'/dhcp_port/',
                        'action':'port_update_end',
                        'method':'POST'
                    },
		
                    {
                        'name':'port_update_end',
                        'url':'/dhcp_port/',
                        'action':'port_update_end',
                        'method':'PUT'
                    },
					

                    {
                        'name':'port_delete_end',
                        'url':'/dhcp_port/:port_id',
                        'action':'port_delete_end',
                        'method':'DELETE'
                    },


                ]

                )
        super(API, self).__init__(mapper)
