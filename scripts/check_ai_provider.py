"""Safe provider connectivity probe: no keys, raw bodies or company data printed."""
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from backend.db import load_env

model=os.getenv('AI_MODEL','').strip().removeprefix('models/')
key=os.getenv('AI_API_KEY','').strip()
if not key or not model:sys.exit('Provider key/model is not configured.')
generate='--generate' in sys.argv
if generate:
    from backend.ai_providers import build_request, response_text, provider_failure
    from backend.ai import validate_output
    schema={'type':'object','properties':{'answer':{'type':'string'},'recommendations':{'type':'array','items':{'type':'string'}},'evidence':{'type':'array','items':{'type':'string'}},'caution':{'type':'string'}},'required':['answer','recommendations','evidence','caution'],'additionalProperties':False}
    request,provider=build_request({'model':model,'instructions':'Return a short JSON answer. No company data is available.','input':'Say hello. Use empty arrays for recommendations and evidence, and an empty caution.','text':{'format':{'type':'json_schema','name':'probe','schema':schema,'strict':True}},'max_output_tokens':2400})
else:
    endpoint='https://generativelanguage.googleapis.com/v1beta/models/'+quote(model,safe='-._')
    request=urllib.request.Request(endpoint,headers={'x-goog-api-key':key})
try:
    with urllib.request.urlopen(request,timeout=20) as response:
        value=json.loads(response.read(100000))
        if generate:
            validate_output(json.loads(response_text(value,provider)))
            print(json.dumps({'status':response.status,'provider':provider,'structured_response_valid':True}))
        else:print(json.dumps({'status':response.status,'model':value.get('name'),'generation_supported':'generateContent' in value.get('supportedGenerationMethods',[])}))
except urllib.error.HTTPError as ex:
    try:error=json.loads(ex.read(100000)).get('error',{})
    except ValueError:error={}
    reason=next((detail.get('reason') for detail in error.get('details',[]) if isinstance(detail,dict) and detail.get('reason')),None)
    print(json.dumps({'status':ex.code,'provider_status':error.get('status'),'reason':reason}))
    sys.exit(1)
except urllib.error.URLError:
    sys.exit('Network connection to the provider is unavailable.')
