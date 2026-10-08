import requests

BASE_API = "http://127.0.0.1:8000"

def test_full_pipeline():
    print("1. Authenticating faculty...")
    auth_resp = requests.post(f"{BASE_API}/auth/login", json={"email": "faculty@pec.edu", "password": "demo"})
    assert auth_resp.status_code == 200, f"Auth failed: {auth_resp.text}"
    token = auth_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("   -> Success. Token obtained.")

    print("2. Creating a test rubric...")
    rubric_payload = {
        "question_text": "Explain QuickSort partition procedure and worst-case complexity.",
        "model_answer": "QuickSort chooses a pivot and partitions the array such that elements smaller than pivot are on the left and larger on the right. Worst-case is O(n^2) when array is already sorted.",
        "max_marks": 5.0,
        "subject": "Data Structures & Algorithms",
        "rubric_points": [
            {"id": "pt_1", "text": "Describes pivot selection and partitioning into two subarrays", "marks": 3.0},
            {"id": "pt_2", "text": "States worst-case time complexity as O(n^2)", "marks": 2.0}
        ]
    }
    r_resp = requests.post(f"{BASE_API}/rubrics", json=rubric_payload, headers=headers)
    assert r_resp.status_code == 201, f"Rubric creation failed: {r_resp.text}"
    rubric_id = r_resp.json()["rubric_id"]
    print(f"   -> Success. Rubric ID: {rubric_id}")

    print("3. Uploading answer sheet...")
    with open("uploads/sample_bfs_answer.jpg", "rb") as f:
        files = {"image": ("sample.jpg", f, "image/jpeg")}
        data = {
            "roll_no": "21103099",
            "question_id": "Q2",
            "subject": "Data Structures & Algorithms",
            "rubric_id": rubric_id
        }
        up_resp = requests.post(f"{BASE_API}/sheets/upload", files=files, data=data, headers=headers)
    assert up_resp.status_code == 201, f"Upload failed: {up_resp.text}"
    sheet_id = up_resp.json()["sheet_id"]
    print(f"   -> Success. Sheet ID: {sheet_id}")

    print("4. Running OCR pipeline with OpenCV preprocessing...")
    ocr_resp = requests.post(f"{BASE_API}/ocr/{sheet_id}", headers=headers)
    assert ocr_resp.status_code == 200, f"OCR failed: {ocr_resp.text}"
    ocr_data = ocr_resp.json()
    print(f"   -> Success. Extracted text sample: {ocr_data['raw_text'][:50]}... (Confidence: {ocr_data['confidence']})")

    print("5. Patching / correcting OCR text...")
    patch_resp = requests.patch(
        f"{BASE_API}/ocr/{sheet_id}",
        json={"corrected_text": "QuickSort picks a pivot element and partitions the array into elements less than and greater than the pivot. In the worst case when the pivot is the smallest or largest element, its time complexity degrades to O(n^2)."},
        headers=headers
    )
    assert patch_resp.status_code == 200, f"Patch failed: {patch_resp.text}"
    print("   -> Success. OCR text corrected.")

    print("6. Requesting LLM Evaluation against rubric...")
    eval_resp = requests.post(
        f"{BASE_API}/evaluate/{sheet_id}",
        json={"rubric_id": rubric_id},
        headers=headers
    )
    assert eval_resp.status_code == 200, f"Evaluation failed: {eval_resp.text}"
    eval_data = eval_resp.json()
    print(f"   -> Success. Suggested Mark: {eval_data['suggested_marks']} / {eval_data['max_marks']}")
    print(f"      Matched Points: {len(eval_data['matched_points'])}")
    print(f"      Missing Points: {len(eval_data['missing_points'])}")
    print(f"      Confidence: {eval_data['confidence']}")

    print("7. Faculty approves and finalizes score...")
    approve_resp = requests.post(
        f"{BASE_API}/scores/{sheet_id}/approve",
        json={"final_marks": eval_data["suggested_marks"], "edited_flag": False},
        headers=headers
    )
    assert approve_resp.status_code == 200, f"Approve failed: {approve_resp.text}"
    print("   -> Success. Grade finalized and saved.")

    print("8. Fetching results table...")
    res_resp = requests.get(f"{BASE_API}/results", headers=headers)
    assert res_resp.status_code == 200, f"Results fetch failed: {res_resp.text}"
    results = res_resp.json()
    print(f"   -> Total scored answer sheets in system: {len(results)}")
    print("\nALL MVP USER JOURNEY STEPS PASSED SUCCESSFULLY! 🚀")

if __name__ == "__main__":
    test_full_pipeline()
