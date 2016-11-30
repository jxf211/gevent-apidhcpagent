import json
import six
import logging
import datetime

log = logging.getLogger(__name__)

class JSONResponseSerializer(object):

    def to_json(self, data):
        def sanitizer(obj):
            if isinstance(obj, datetime.datetime):
                return obj.isoformat()
            return six.text_type(obj)

        response = json.dumps(data, default=sanitizer)
        log.debug("JSON response : %s" % response)
        return response

    def default(self, response, result, status=200):
        response.content_type = 'application/json'
        response.body = six.b(self.to_json(result))
        response.status = status
'''
class XMLResponseSerializer(object):

    def object_to_element(self, obj, element):
        if isinstance(obj, list):
            for item in obj:
                subelement = etree.SubElement(element, "member")
                self.object_to_element(item, subelement)
        elif isinstance(obj, dict):
            for key, value in obj.items():
                subelement = etree.SubElement(element, key)
                if key in JSON_ONLY_KEYS:
                    if value:
                        # Need to use json.dumps for the JSON inside XML
                        # otherwise quotes get mangled and json.loads breaks
                        try:
                            subelement.text = json.dumps(value)
                        except TypeError:
                            subelement.text = str(value)
                else:
                    self.object_to_element(value, subelement)
        else:
            element.text = six.text_type(obj)

    def to_xml(self, data):
        # Assumption : root node is dict with single key
        root = next(six.iterkeys(data))
        eltree = etree.Element(root)
        self.object_to_element(data.get(root), eltree)
        response = etree.tostring(eltree)
        return response

    def default(self, response, result, status=200):
        response.content_type = 'application/xml'
        response.body = self.to_xml(result)
        response.status = status
'''

