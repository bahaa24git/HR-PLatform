import io
import json
import os
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from backend.ai_providers import build_request, response_text, provider_failure, request_json


class ProviderTest(unittest.TestCase):
    def payload(self):
        return {'model':'gemini-3.5-flash-lite','instructions':'Use authorized evidence.','input':'hello','text':{'format':{'schema':{'type':'object'}}},'max_output_tokens':100}

    def test_gemini_legacy_endpoint_and_structured_output(self):
        with patch.dict(os.environ,{'AI_PROVIDER':'auto','AI_MODEL':'gemini-3.5-flash-lite','AI_API_KEY':'private-test-key','AI_BASE_URL':'https://api.openai.com/v1'}):
            request,provider=build_request(self.payload())
        self.assertEqual(provider,'gemini')
        self.assertEqual(request.full_url,'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent')
        self.assertNotIn('private-test-key',request.full_url)
        self.assertEqual(request.get_header('X-goog-api-key'),'private-test-key')
        body=json.loads(request.data)
        self.assertEqual(body['generationConfig']['responseJsonSchema'],{'type':'object'})
        self.assertEqual(body['contents'][0]['parts'][0]['text'],'hello')
        self.assertEqual(response_text({'candidates':[{'content':{'parts':[{'text':'hidden','thought':True},{'text':'{"answer":"ok"}'}]}}]},provider),'{"answer":"ok"}')

    def test_openai_preserved(self):
        with patch.dict(os.environ,{'AI_PROVIDER':'openai','AI_API_KEY':'test-key','AI_BASE_URL':''}):
            request,provider=build_request(self.payload())
        self.assertEqual(provider,'openai')
        self.assertEqual(request.full_url,'https://api.openai.com/v1/responses')
        self.assertEqual(json.loads(request.data),self.payload())

    def test_gemini_preserves_types_without_expanding_nested_limits(self):
        from backend.report_schema import REPORT_SCHEMA
        payload=self.payload();payload['text']['format']['schema']=REPORT_SCHEMA
        with patch.dict(os.environ,{'AI_PROVIDER':'gemini','AI_API_KEY':'test','AI_BASE_URL':''}):
            request,_=build_request(payload)
        schema=json.loads(request.data)['generationConfig']['responseJsonSchema']
        self.assertNotIn('maxItems',json.dumps(schema));self.assertNotIn('maxLength',json.dumps(schema))
        self.assertEqual(REPORT_SCHEMA['required'],schema['required'])
        self.assertEqual(REPORT_SCHEMA['properties']['report_type'],schema['properties']['report_type'])
        self.assertIn('maxItems',json.dumps(REPORT_SCHEMA))

    def test_safe_provider_error(self):
        error=HTTPError('https://example.com',403,'Forbidden',{},io.BytesIO(b'{"error":{"message":"secret-key private input","status":"PERMISSION_DENIED"}}'))
        problem=provider_failure(error)
        self.assertNotIn('secret-key',str(problem))
        self.assertEqual(problem.details,{'provider_status':403,'provider_code':'PERMISSION_DENIED'})

    def test_transient_provider_failures_retry_with_bounded_attempts(self):
        from unittest.mock import MagicMock
        response=MagicMock();response.__enter__.return_value=response;response.read.return_value=b'{"ok":true}'
        failure=lambda status:HTTPError('https://example.com',status,'Unavailable',{},io.BytesIO(b'{}'))
        with patch('urllib.request.urlopen',side_effect=[failure(503),failure(429),response]) as transport,patch('backend.ai_providers.time.sleep') as sleep:
            self.assertEqual({'ok':True},request_json(object()))
            self.assertEqual(3,transport.call_count);self.assertEqual(2,sleep.call_count)
        for status in (400,401,403,404,503):
            with self.subTest(status=status),patch('urllib.request.urlopen',side_effect=lambda *args,**kwargs:(_ for _ in ()).throw(failure(status))) as transport,patch('backend.ai_providers.time.sleep'):
                with self.assertRaises(HTTPError):request_json(object())
                self.assertEqual(3 if status==503 else 1,transport.call_count)
