from oauth2client.client import OAuth2WebServerFlow
import webbrowser
from oauth2client.file import Storage
import httplib2

flow = OAuth2WebServerFlow(
    client_id='.com',
    client_secret='',
    redirect_uri='http://iot.duality.co.nz/oauth2callback',
    scope='email',
    user_agent='my-sample/1.0')


authorize_url = flow.step1_get_authorize_url()
webbrowser.open(authorize_url, new=2)

credentials = flow.step2_exchange(raw_input("code: "))
storage = Storage('credentials')
storage.put(credentials)

credentials = storage.get()

http = httplib2.Http()
http = credentials.authorize(http)

print http