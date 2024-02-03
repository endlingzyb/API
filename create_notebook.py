import requests
import os

def get_access_token():
    tenant_id = os.environ.get('TENANT_ID')
    client_id = os.environ.get('CLIENT_ID')
    client_secret = os.environ.get('CLIENT_SECRET')
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': 'https://graph.microsoft.com/.default'
    }
    response = requests.post(token_url, data=data)
    return response.json().get('access_token')

def create_notebook(access_token):
    endpoint = "https://graph.microsoft.com/v1.0/me/onenote/notebooks"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "displayName": "new"
    }
    response = requests.post(endpoint, headers=headers, json=payload)
    return response.json()

def main():
    access_token = get_access_token()
    notebook = create_notebook(access_token)
    print(notebook)

if __name__ == "__main__":
    main()
