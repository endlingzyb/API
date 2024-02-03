import os
from msgraph-sdk import auth, client

client_id = os.environ.get('CLIENT_ID')
client_secret = os.environ.get('CLIENT_SECRET')
user_id = os.environ.get('TENANT_ID')

credentials = auth.ClientCredentialProvider(
    client_id=client_id,
    client_secret=client_secret
)

graph_client = client.GraphClient(
    credentials, 
    scopes=['Notes.ReadWrite.All']
)

notebook = {
    "displayName": "add"
}

created_notebook = graph_client.me.onenote.notebooks.add(notebook)
print(created_notebook)
