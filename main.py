import time
import json
import requests
from google.oauth2 import service_account
import google.auth.transport.requests

# Caminho para o Secret File seguro no Render
SERVICE_ACCOUNT_FILE = "/etc/secrets/serviceAccount.json"

# Autentica com as credenciais do Firebase
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=["https://www.googleapis.com/auth/firebase.messaging"]
)

def get_access_token():
    request = google.auth.transport.requests.Request()
    credentials.refresh(request)
    return credentials.token

def send_push_notification(title, body):
    access_token = get_access_token()
    url = "https://fcm.googleapis.com/v1/projects/cryptojaspion/messages:send"

    message = {
        "message": {
            "topic": "all",
            "notification": {
                "title": title,
                "body": body
            }
        }
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; UTF-8",
    }

    response = requests.post(url, headers=headers, data=json.dumps(message))
    print(f"Status: {response.status_code}, Response: {response.text}")

if __name__ == "__main__":
    while True:
        print("Enviando alerta...")  # Log de teste
        send_push_notification("Alerta Crypto", "Bitcoin está perto do ATH!")
        time.sleep(600)  # Espera 10 minutos antes de enviar o próximo alerta
