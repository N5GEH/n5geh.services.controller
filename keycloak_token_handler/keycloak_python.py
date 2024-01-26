import requests
import os
from dotenv import load_dotenv
from datetime import datetime,timedelta,timezone

class KeycloakPython:
    def __init__(self, keycloak_host=None, client_id=None, client_secret=None):
        """
        - Initialze the Keycloak Host , Client ID and Client secret.
        - If no parameters are passed .env file is used
        - Priority : function parameters > Class Instatiation > .env file
        """
        load_dotenv()
        self.keycloak_host = os.getenv('KEYCLOAK_HOST') if keycloak_host == None else keycloak_host
        self.client_id = os.getenv('CLIENT_ID') if client_id == None else client_id
        self.client_secret = os.getenv('CLIENT_SECRET') if client_secret ==None else client_secret
        self.access_token = None
        self.expires_in = None

    def get_access_token(self,keycloak_host=None, client_id=None, client_secret=None):
        """
        - Get access token for a given client id and client secret.
        """        
        self.keycloak_host = keycloak_host if keycloak_host != None else self.keycloak_host
        self.client_id = client_id if client_id !=None else self.client_id
        self.client_secret = client_secret if client_secret !=None else self.client_secret

        self.data = {'client_id':self.client_id, 
                    'client_secret':self.client_secret,
                    'scope':'email',
                    'grant_type':'client_credentials'}
        try:
            if self.keycloak_host and self.client_id and self.client_secret:
                headers = {"content-type": "application/x-www-form-urlencoded"}
                access_data = requests.post(self.keycloak_host, data=self.data, headers=headers, verify=False)
                if access_data.ok:
                    current_time = datetime.now(timezone.utc)
                    self.expires_in = current_time + timedelta(seconds=int(access_data.json()['expires_in']))
                    self.access_token = access_data.json()['access_token']
                else:
                    raise Exception('HTTP Status Code: '+ str(access_data.status_code), access_data.text)
            return self.access_token, self.expires_in
        except requests.exceptions.RequestException as err:
            print(err)
            raise KeycloakPythonException(err.args[0])
        
    def check_update_token_validity(self, input_token, min_valid_time=60):
        # min_valid_time = the time the token must still be valid at the IDM before a new token is requested.
        
        if all(input_token):
            if (datetime.now(timezone.utc) + timedelta(seconds=min_valid_time)) > input_token[1]:
                return self.get_access_token()
            else:
                return input_token #, self.expires_in
        else:
            pass

class KeycloakPythonException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)
