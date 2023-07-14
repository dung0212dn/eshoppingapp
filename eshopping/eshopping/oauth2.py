from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://mail.google.com/']

def get_gmail_credentials():
    flow = InstalledAppFlow.from_client_secrets_file(
        'eshopping/client_secret.json', SCOPES)
    credentials = flow.run_local_server(port=0)
    return credentials