import os
from msgraph import auth, client

from azure.identity.aio import ClientSecretCredential

credential = ClientSecretCredential(
    tenant_id=os.environ.get('TENANT_ID'),
    client_id=os.environ.get('CLIENT_ID'),
    client_secret=os.environ.get('CLIENT_SECRET'),
)

graph_client = client.GraphClient(
    credential, 
    scopes=['Notes.ReadWrite.All']
)

notebook = {
    "displayName": "add"
}

created_notebook = graph_client.me.onenote.notebooks.add(notebook)
print(created_notebook)
