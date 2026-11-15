"""Provider-specific transport; credentials stay in request headers."""
import json
import os
import re
import urllib.request
from urllib.parse import quote, urlsplit
from .service import Problem, require


def provider_name():
    provider=os.getenv('AI_PROVIDER','auto').strip().lower() or 'auto'
    require(provider in ('auto','openai','gemini'),'AI_PROVIDER must be auto, openai or gemini.',503)
    if provider=='auto':
        return 'gemini' if os.getenv('AI_MODEL','').removeprefix('models/').startswith('gemini-') or urlsplit(os.getenv('AI_BASE_URL','')).hostname=='generativelanguage.googleapis.com' else 'openai'
    return provider


def build_request(payload):
    provider=provider_name()
    base=os.getenv('AI_BASE_URL','').strip().rstrip('/')
    key=os.environ['AI_API_KEY'].strip()
    if provider=='gemini':
        if not base or urlsplit(base).hostname=='api.openai.com':base='https://generativelanguage.googleapis.com/v1beta'
        model=payload['model'].strip().removeprefix('models/')
        require(bool(re.fullmatch(r'[A-Za-z0-9._-]+',model)),'Invalid Gemini model identifier.',503)
        endpoint=base+'/models/'+quote(model,safe='-._')+':generateContent'
        body={'systemInstruction':{'parts':[{'text':payload['instructions']}]},'contents':[{'role':'user','parts':[{'text':payload['input']}]}],'generationConfig':{'responseMimeType':'application/json','responseJsonSchema':payload['text']['format']['schema'],'maxOutputTokens':payload['max_output_tokens']}}
        headers={'Content-Type':'application/json','x-goog-api-key':key}
    else:
        endpoint=(base or 'https://api.openai.com/v1')+'/responses'
        body=payload
        headers={'Content-Type':'application/json','Authorization':'Bearer '+key}
    parsed=urlsplit(endpoint)
    require((parsed.scheme=='https' or parsed.scheme=='http' and parsed.hostname in ('127.0.0.1','localhost','::1')) and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment,'AI provider URL must use HTTPS (loopback providers may use HTTP), without embedded credentials.',503)
    return urllib.request.Request(endpoint,data=json.dumps(body).encode(),headers=headers),provider


def response_text(body,provider):
    if provider=='gemini':
        return ''.join(part.get('text','') for part in body['candidates'][0]['content']['parts'] if not part.get('thought'))
    return ''.join(c.get('text','') for item in body.get('output',[]) for c in item.get('content',[]) if c.get('type')=='output_text')


def provider_failure(error):
    # Never expose the provider body: it may echo credentials or private input.
    try:
        body=json.loads(error.read(100000)).get('error',{})
        reason=next((d.get('reason') for d in body.get('details',[]) if isinstance(d,dict) and d.get('reason')),body.get('code') or body.get('status'))
    except (ValueError,TypeError,AttributeError):reason=None
    message={400:'The AI provider rejected the request format or model configuration.',401:'The AI provider rejected the API key. Check the server credential.',403:'The AI provider denied access. Check API enablement, key restrictions and account permissions.',404:'The configured AI model or endpoint was not found.',429:'The AI provider quota or rate limit was reached. Check the account quota and retry later.'}.get(error.code,'The AI provider is temporarily unavailable. Please retry.')
    problem=Problem(message,503 if error.code==429 or error.code>=500 else 502)
    problem.details={'provider_status':error.code}
    if reason and re.fullmatch(r'[A-Za-z0-9_]{1,70}',str(reason)):problem.details['provider_code']=str(reason)
    return problem
