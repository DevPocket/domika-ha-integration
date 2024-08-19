from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/androidpublisher']
SERVICE_ACCOUNT_FILE = 'domika.json'

credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)

service = build('androidpublisher', 'v3', credentials=credentials)
request = service.purchases().subscriptionsv2().get(
    packageName='com.devpocket.domika.android',
    token="egbghhogldklonpnlndpnhkl.AO-J1OwsvuuO4ehygO9u6z77QLFQH-ye3edvO7qpCNbUjE_1svzLYSS9sv1irpVnKSJr1A8ca67f0c50mo970vd-L2qOJT3SSla53UYS-mr-oF0I8vvjAEk"
)
response = request.execute()
print(response)
