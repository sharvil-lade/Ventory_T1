from firebase_admin import credentials, firestore, storage, initialize_app

cred = credentials.Certificate("config/firebase-adminsdk.json")
initialize_app(cred, {
    'projectId': 'certificate-management-s-54960',
    'storageBucket': 'certificate-management-s.appspot.com',
})

db = firestore.client()
bucket = storage.bucket()