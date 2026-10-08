import json
import os
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from app.config import settings

class StorageService:
    def __init__(self):
        self.use_firebase = settings.USE_FIREBASE
        self.local_upload_dir = settings.UPLOAD_DIR
        self.data_dir = settings.DATA_DIR
        self.data_file = self.data_dir / "firestore_mock_store.json"
        
        # Ensure directories
        self.local_upload_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self._firestore_client = None
        self._storage_bucket = None
        
        if self.use_firebase and settings.FIREBASE_CREDENTIALS_PATH:
            self._init_firebase()
        else:
            self._init_local_store()

    def _init_firebase(self):
        try:
            import firebase_admin
            from firebase_admin import credentials, firestore, storage
            
            if not firebase_admin._apps:
                cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
                firebase_admin.initialize_app(cred, {
                    'storageBucket': settings.FIREBASE_STORAGE_BUCKET
                })
            self._firestore_client = firestore.client()
            if settings.FIREBASE_STORAGE_BUCKET:
                self._storage_bucket = storage.bucket()
            print("Successfully initialized Firebase Admin SDK (Firestore & Storage)")
        except Exception as e:
            print(f"Failed to initialize Firebase Admin SDK: {e}. Falling back to local store.")
            self.use_firebase = False
            self._init_local_store()

    def _init_local_store(self):
        if not self.data_file.exists():
            initial_data = {
                "users": {
                    "faculty_demo_01": {
                        "uid": "faculty_demo_01",
                        "email": "faculty@pec.edu",
                        "name": "Dr. Faculty Reviewer",
                        "role": "faculty"
                    }
                },
                "rubrics": {},
                "sheets": {},
                "scores": {}
            }
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(initial_data, f, indent=2)

    def _read_local_data(self) -> Dict[str, Any]:
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"users": {}, "rubrics": {}, "sheets": {}, "scores": {}}

    def _write_local_data(self, data: Dict[str, Any]):
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    # ---------------- Image Storage ----------------
    def save_image(self, filename: str, file_bytes: bytes) -> str:
        """Saves file to Firebase Storage or local upload folder, returns accessible URL."""
        if self.use_firebase and self._storage_bucket:
            blob = self._storage_bucket.blob(f"sheets/{filename}")
            blob.upload_from_string(file_bytes, content_type="image/jpeg")
            blob.make_public()
            return blob.public_url
        else:
            dest_path = self.local_upload_dir / filename
            with open(dest_path, "wb") as f:
                f.write(file_bytes)
            # URL accessible via FastAPI static file route
            return f"/uploads/{filename}"

    # ---------------- Rubrics Collection ----------------
    def save_rubric(self, rubric_id: str, data: Dict[str, Any]) -> str:
        if self.use_firebase and self._firestore_client:
            self._firestore_client.collection("rubrics").document(rubric_id).set(data)
        else:
            store = self._read_local_data()
            store["rubrics"][rubric_id] = data
            self._write_local_data(store)
        return rubric_id

    def get_rubric(self, rubric_id: str) -> Optional[Dict[str, Any]]:
        if self.use_firebase and self._firestore_client:
            doc = self._firestore_client.collection("rubrics").document(rubric_id).get()
            return doc.to_dict() if doc.exists else None
        else:
            store = self._read_local_data()
            return store.get("rubrics", {}).get(rubric_id)

    def list_rubrics(self) -> List[Dict[str, Any]]:
        if self.use_firebase and self._firestore_client:
            docs = self._firestore_client.collection("rubrics").stream()
            return [doc.to_dict() for doc in docs]
        else:
            store = self._read_local_data()
            return list(store.get("rubrics", {}).values())

    # ---------------- Sheets Collection ----------------
    def save_sheet(self, sheet_id: str, data: Dict[str, Any]) -> str:
        if self.use_firebase and self._firestore_client:
            self._firestore_client.collection("sheets").document(sheet_id).set(data)
        else:
            store = self._read_local_data()
            store["sheets"][sheet_id] = data
            self._write_local_data(store)
        return sheet_id

    def update_sheet(self, sheet_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if self.use_firebase and self._firestore_client:
            self._firestore_client.collection("sheets").document(sheet_id).update(updates)
            return self.get_sheet(sheet_id)
        else:
            store = self._read_local_data()
            if sheet_id in store["sheets"]:
                store["sheets"][sheet_id].update(updates)
                self._write_local_data(store)
                return store["sheets"][sheet_id]
            return None

    def get_sheet(self, sheet_id: str) -> Optional[Dict[str, Any]]:
        if self.use_firebase and self._firestore_client:
            doc = self._firestore_client.collection("sheets").document(sheet_id).get()
            return doc.to_dict() if doc.exists else None
        else:
            store = self._read_local_data()
            return store.get("sheets", {}).get(sheet_id)

    def list_sheets(self, question_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if self.use_firebase and self._firestore_client:
            query = self._firestore_client.collection("sheets")
            if question_id:
                query = query.where("question_id", "==", question_id)
            return [doc.to_dict() for doc in query.stream()]
        else:
            store = self._read_local_data()
            sheets = list(store.get("sheets", {}).values())
            if question_id:
                sheets = [s for s in sheets if s.get("question_id") == question_id]
            return sheets

    # ---------------- Scores Collection ----------------
    def save_score(self, sheet_id: str, data: Dict[str, Any]) -> str:
        if self.use_firebase and self._firestore_client:
            self._firestore_client.collection("scores").document(sheet_id).set(data)
        else:
            store = self._read_local_data()
            store["scores"][sheet_id] = data
            # Also update sheet status to 'approved'
            if sheet_id in store["sheets"]:
                store["sheets"][sheet_id]["status"] = "approved"
            self._write_local_data(store)
        return sheet_id

    def get_score(self, sheet_id: str) -> Optional[Dict[str, Any]]:
        if self.use_firebase and self._firestore_client:
            doc = self._firestore_client.collection("scores").document(sheet_id).get()
            return doc.to_dict() if doc.exists else None
        else:
            store = self._read_local_data()
            return store.get("scores", {}).get(sheet_id)

    def list_scores(self, question_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if self.use_firebase and self._firestore_client:
            query = self._firestore_client.collection("scores")
            if question_id:
                query = query.where("question_id", "==", question_id)
            return [doc.to_dict() for doc in query.stream()]
        else:
            store = self._read_local_data()
            scores = list(store.get("scores", {}).values())
            if question_id:
                scores = [s for s in scores if s.get("question_id") == question_id]
            return scores

db_service = StorageService()
