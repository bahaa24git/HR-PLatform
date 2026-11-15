import io
import json
import os
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from backend.ai_providers import build_request, response_text, provider_failure


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

    def test_safe_provider_error(self):
        error=HTTPError('https://example.com',403,'Forbidden',{},io.BytesIO(b'{"error":{"message":"secret-key private input","status":"PERMISSION_DENIED"}}'))
        problem=provider_failure(error)
        self.assertNotIn('secret-key',str(problem))
        self.assertEqual(problem.details,{'provider_status':403,'provider_code':'PERMISSION_DENIED'})
