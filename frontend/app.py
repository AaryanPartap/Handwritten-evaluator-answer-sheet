import csv
import io
import requests
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response
from frontend.config import frontend_config

app = Flask(__name__)
app.secret_key = frontend_config.SECRET_KEY
BACKEND_URL = frontend_config.BACKEND_URL

def get_auth_headers():
    token = session.get("token")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "token" not in session:
            flash("Please sign in to access the evaluator dashboard.", "info")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_globals():
    return {
        "current_user": session.get("user"),
        "backend_url": BACKEND_URL
    }

@app.route("/")
def index():
    if "token" in session:
        return redirect(url_for("rubrics_list"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        client_token = request.form.get("firebase_token", "").strip()

        try:
            if client_token:
                # Direct Firebase ID Token verification
                resp = requests.post(
                    f"{BACKEND_URL}/auth/verify",
                    json={"token": client_token},
                    timeout=10
                )
            else:
                # Dev / Local login
                resp = requests.post(
                    f"{BACKEND_URL}/auth/login",
                    json={"email": email, "password": password},
                    timeout=10
                )

            if resp.status_code == 200:
                data = resp.json()
                session["token"] = data.get("access_token", client_token or "demo_faculty_token")
                session["user"] = data.get("user") or {"email": email, "name": "Faculty Member", "role": "faculty"}
                flash("Signed in successfully. Welcome to the Evaluation Dashboard!", "success")
                return redirect(url_for("rubrics_list"))
            else:
                flash(f"Sign-in failed: {resp.text}", "danger")
        except Exception as e:
            flash(f"Could not connect to FastAPI Backend at {BACKEND_URL}: {str(e)}", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for("login"))

# ---------------- Rubrics Routes ----------------
@app.route("/rubrics", methods=["GET"])
@login_required
def rubrics_list():
    try:
        resp = requests.get(f"{BACKEND_URL}/rubrics", headers=get_auth_headers(), timeout=10)
        rubrics = resp.json() if resp.status_code == 200 else []
    except Exception as e:
        flash(f"Error fetching rubrics: {str(e)}", "warning")
        rubrics = []
    return render_template("rubrics_list.html", rubrics=rubrics)

@app.route("/rubrics/new", methods=["GET", "POST"])
@login_required
def rubric_new():
    if request.method == "POST":
        question_text = request.form.get("question_text", "").strip()
        model_answer = request.form.get("model_answer", "").strip()
        max_marks = float(request.form.get("max_marks", 10.0))
        subject = request.form.get("subject", "Computer Science").strip()

        # Extract dynamic rubric checklist items
        point_texts = request.form.getlist("point_text[]")
        point_marks = request.form.getlist("point_marks[]")
        
        rubric_points = []
        for i, (p_text, p_marks) in enumerate(zip(point_texts, point_marks)):
            if p_text.strip():
                rubric_points.append({
                    "id": f"pt_{i+1}",
                    "text": p_text.strip(),
                    "marks": float(p_marks or 1.0)
                })

        payload = {
            "question_text": question_text,
            "model_answer": model_answer,
            "max_marks": max_marks,
            "subject": subject,
            "rubric_points": rubric_points
        }

        try:
            resp = requests.post(f"{BACKEND_URL}/rubrics", json=payload, headers=get_auth_headers(), timeout=10)
            if resp.status_code == 201:
                flash("Rubric created and saved successfully!", "success")
                return redirect(url_for("rubrics_list"))
            else:
                flash(f"Failed to create rubric: {resp.text}", "danger")
        except Exception as e:
            flash(f"Error communicating with backend: {str(e)}", "danger")

    return render_template("rubric_new.html")

# ---------------- Upload Sheet Route ----------------
@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    # Fetch available rubrics to populate selector
    rubrics = []
    try:
        r_resp = requests.get(f"{BACKEND_URL}/rubrics", headers=get_auth_headers(), timeout=10)
        if r_resp.status_code == 200:
            rubrics = r_resp.json()
    except Exception:
        rubrics = []

    if request.method == "POST":
        if "sheet_image" not in request.files:
            flash("No file was uploaded", "danger")
            return redirect(request.url)

        file = request.files["sheet_image"]
        if file.filename == "":
            flash("Please choose an image file to upload", "danger")
            return redirect(request.url)

        roll_no = request.form.get("roll_no", "").strip()
        question_id = request.form.get("question_id", "Q1").strip()
        subject = request.form.get("subject", "Computer Science").strip()
        rubric_id = request.form.get("rubric_id", "").strip()

        files = {"image": (file.filename, file.read(), file.content_type)}
        data = {
            "roll_no": roll_no,
            "question_id": question_id,
            "subject": subject,
            "rubric_id": rubric_id
        }

        try:
            upload_resp = requests.post(
                f"{BACKEND_URL}/sheets/upload",
                files=files,
                data=data,
                headers=get_auth_headers(),
                timeout=15
            )
            if upload_resp.status_code == 201:
                sheet_data = upload_resp.json()
                sheet_id = sheet_data["sheet_id"]

                # Automatically trigger OCR immediately
                ocr_resp = requests.post(
                    f"{BACKEND_URL}/ocr/{sheet_id}",
                    headers=get_auth_headers(),
                    timeout=20
                )
                
                flash(f"Answer sheet for Roll No. {roll_no} uploaded and OCR extracted!", "success")
                return redirect(url_for("review", sheet_id=sheet_id))
            else:
                flash(f"Upload failed: {upload_resp.text}", "danger")
        except Exception as e:
            flash(f"Error during upload or OCR: {str(e)}", "danger")

    return render_template("upload.html", rubrics=rubrics)

# ---------------- Review & Side-by-Side Dashboard ----------------
@app.route("/review/<sheet_id>", methods=["GET"])
@login_required
def review(sheet_id):
    try:
        s_resp = requests.get(f"{BACKEND_URL}/sheets/{sheet_id}", headers=get_auth_headers(), timeout=10)
        if s_resp.status_code != 200:
            flash(f"Sheet '{sheet_id}' not found.", "warning")
            return redirect(url_for("rubrics_list"))
        sheet = s_resp.json()

        # Load rubric
        rubric = None
        rubric_id = sheet.get("rubric_id")
        if rubric_id:
            r_resp = requests.get(f"{BACKEND_URL}/rubrics/{rubric_id}", headers=get_auth_headers(), timeout=10)
            if r_resp.status_code == 200:
                rubric = r_resp.json()

        # Fetch all rubrics in case user wants to change rubric
        all_rubrics = []
        try:
            ar_resp = requests.get(f"{BACKEND_URL}/rubrics", headers=get_auth_headers(), timeout=10)
            if ar_resp.status_code == 200:
                all_rubrics = ar_resp.json()
        except Exception:
            all_rubrics = []

        # Check existing score
        score = None
        score_resp = requests.get(f"{BACKEND_URL}/scores/{sheet_id}", headers=get_auth_headers(), timeout=10)
        if score_resp.status_code == 200:
            score = score_resp.json()

        # Formulate full image URL
        raw_img_url = sheet.get("image_url", "")
        if raw_img_url.startswith("/uploads/"):
            full_img_url = f"{BACKEND_URL}{raw_img_url}"
        else:
            full_img_url = raw_img_url

        return render_template(
            "review.html",
            sheet=sheet,
            rubric=rubric,
            all_rubrics=all_rubrics,
            score=score,
            image_url=full_img_url
        )
    except Exception as e:
        flash(f"Error loading review page: {str(e)}", "danger")
        return redirect(url_for("rubrics_list"))

# ---------------- Results Table & CSV Export ----------------
@app.route("/results", methods=["GET"])
@login_required
def results():
    q_filter = request.args.get("question_id", "").strip()
    params = {"question_id": q_filter} if q_filter else {}
    
    results_list = []
    rubrics = []
    try:
        r_resp = requests.get(f"{BACKEND_URL}/results", params=params, headers=get_auth_headers(), timeout=10)
        if r_resp.status_code == 200:
            results_list = r_resp.json()
            
        rub_resp = requests.get(f"{BACKEND_URL}/rubrics", headers=get_auth_headers(), timeout=10)
        if rub_resp.status_code == 200:
            rubrics = rub_resp.json()
    except Exception as e:
        flash(f"Error loading results: {str(e)}", "warning")

    # Compute high-level metrics for dashboard cards
    total_count = len(results_list)
    avg_score = (sum(r.get("final_marks", 0) for r in results_list) / total_count) if total_count > 0 else 0.0
    overridden_count = sum(1 for r in results_list if r.get("edited_flag"))
    agreement_rate = ((total_count - overridden_count) / total_count * 100) if total_count > 0 else 100.0

    return render_template(
        "results.html",
        results=results_list,
        rubrics=rubrics,
        selected_question=q_filter,
        metrics={
            "total_count": total_count,
            "avg_score": round(avg_score, 2),
            "overridden_count": overridden_count,
            "agreement_rate": round(agreement_rate, 1)
        }
    )

@app.route("/results/export-csv")
@login_required
def export_csv():
    q_filter = request.args.get("question_id", "").strip()
    params = {"question_id": q_filter} if q_filter else {}
    try:
        resp = requests.get(f"{BACKEND_URL}/results", params=params, headers=get_auth_headers(), timeout=10)
        results_data = resp.json() if resp.status_code == 200 else []
    except Exception:
        results_data = []

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Roll No", "Question ID", "Rubric ID", "Suggested Marks",
        "Final Marks", "Max Marks", "Faculty Overridden", "Confidence", "Approved At"
    ])

    for row in results_data:
        writer.writerow([
            row.get("roll_no"),
            row.get("question_id"),
            row.get("rubric_id"),
            row.get("suggested_marks"),
            row.get("final_marks"),
            row.get("max_marks"),
            "Yes" if row.get("edited_flag") else "No",
            row.get("confidence"),
            row.get("approved_at")
        ])

    csv_data = output.getvalue()
    filename = f"evaluator_results_{q_filter or 'all'}.csv"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )

# ---------------- AJAX Proxy Endpoints for Seamless UI ----------------
@app.route("/api/ocr/<sheet_id>", methods=["PATCH"])
@login_required
def proxy_patch_ocr(sheet_id):
    data = request.get_json()
    resp = requests.patch(
        f"{BACKEND_URL}/ocr/{sheet_id}",
        json=data,
        headers=get_auth_headers(),
        timeout=10
    )
    return jsonify(resp.json()), resp.status_code

@app.route("/api/evaluate/<sheet_id>", methods=["POST"])
@login_required
def proxy_evaluate(sheet_id):
    data = request.get_json()
    resp = requests.post(
        f"{BACKEND_URL}/evaluate/{sheet_id}",
        json=data,
        headers=get_auth_headers(),
        timeout=25
    )
    return jsonify(resp.json()), resp.status_code

@app.route("/api/scores/<sheet_id>/approve", methods=["POST"])
@login_required
def proxy_approve_score(sheet_id):
    data = request.get_json()
    resp = requests.post(
        f"{BACKEND_URL}/scores/{sheet_id}/approve",
        json=data,
        headers=get_auth_headers(),
        timeout=15
    )
    return jsonify(resp.json()), resp.status_code
