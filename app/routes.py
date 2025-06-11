import os
import io
import zipfile
from datetime import datetime, timedelta, time, date
from collections import Counter, defaultdict, OrderedDict
from dateutil.relativedelta import relativedelta

from flask import (
    render_template, flash, redirect, url_for, request, session,
    jsonify, current_app, send_file, send_from_directory
)
from flask_login import (
    login_user, logout_user, current_user, login_required
)
from flask_wtf.csrf import validate_csrf, CSRFError
from flask_wtf import FlaskForm
from wtforms import SubmitField
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import asc, desc, nulls_last
from sqlalchemy.orm import joinedload
from app import db
from app.forms import (
    LoginForm, RegistrationForm, DocumentForm, RequestPasswordResetForm,
    ResetPasswordForm, ChangePasswordForm, UserProfileForm
)
from app.models import (
    User, Document, Appointment, SharedDocument, UserProfile
)
from app.blueprints import blueprint

# Dummy form for CSRF protection where needed
class DummyForm(FlaskForm):
    submit = SubmitField()

# Page 1 - Landing Page
@blueprint.route('/')
@blueprint.route('/index')
def index():
    # Automatically redirect member to dashboard if already logged in
    if session.get("role") == "member":
        return redirect(url_for("main.dashboard"))
    return render_template("page_1_LandingPage.html")

# Page 2 - Login Page
@blueprint.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    form = LoginForm()
    msg = ""

    if form.validate_on_submit():
        try:
            user = User.query.filter_by(email=form.email.data).first()

            # Check if user exists and password is correct
            if user and user.check_password(form.password.data):
                login_user(user, remember=form.remember_me.data)

                # Set up session data
                session['user_id'] = user.id
                session['first_name'] = user.first_name
                session['role'] = user.role
                session['notifications_viewed_at'] = (
                    user.notifications_viewed_at.isoformat()
                    if user.notifications_viewed_at else datetime.min.isoformat()
                )
                flash("Login successful", "success")

                # Redirect to 'next' parameter if it exists, otherwise to dashboard
                next_page = request.args.get('next')
                return redirect(next_page if next_page else url_for('main.dashboard'))
            else:
                if user:
                    print("Password check failed")
                msg = "Invalid email or password"
        except Exception as e:
            # Log any errors
            print(f"Login error: {str(e)}")
            msg = "An error occurred during login"

    return render_template("page_2_LoginPage.html", form=form, msg=msg)

@blueprint.route("/logout")
def logout():
    logout_user()
    session.clear()
    flash("You have been logged out", "info")
    return redirect(url_for("main.index"))

# Page 3 - Register Page
@blueprint.route("/register", methods=["GET", "POST"])
def register():
    # Redirect if user is already logged in
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = RegistrationForm()

    # Print form data for debugging
    if request.method == "POST":
        print(f"Register form submitted with data: {request.form}")

    if form.validate_on_submit():
        try:
            print("Form validation successful")

            # Create a new user object
            print(f"Creating user with email: {form.email.data}")
            hashed_pw = generate_password_hash(form.password.data)
            new_user = User(
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                email=form.email.data,
                password=hashed_pw,
                role="member"
            )

            # Add to database and commit
            db.session.add(new_user)
            db.session.commit()

            # Success message
            flash("Account created successfully! You can now login.", "success")

            # Important: Redirect to login page, don't render template
            print("Redirecting to login page")
            return redirect(url_for("main.login"))

        except Exception as e:
            # Roll back any changes and show error message
            db.session.rollback()
            print(f"ERROR in registration: {str(e)}")
            import traceback
            traceback.print_exc()  # Print full traceback for debugging
            flash(f"Registration failed: {str(e)}", "danger")

    # Print form errors if validation failed
    if form.errors:
        print(f"Form validation errors: {form.errors}")

    # Render registration form
    return render_template("page_3_RegisterPage.html", form=form)

# Page 4 - Dashboard Page
@blueprint.route("/dashboard")
@login_required
def dashboard():
    if session.get("role") != "member":
        return redirect(url_for("main.login"))

    today = datetime.today().date()

    upcoming_appointments = (
        Appointment.query
        .filter(
            Appointment.user_id == session["user_id"],
            Appointment.appointment_date >= today
        )
        .order_by(Appointment.appointment_date.asc())
        .limit(5)
        .all()
    )

    upcoming_data = []
    for appt in upcoming_appointments:
        days_away = (appt.appointment_date - today).days
        upcoming_data.append({
            "days_away": days_away,
            "date": appt.appointment_date.strftime("%b %d"),
            "practitioner": appt.practitioner_name,
            "type": appt.practitioner_type,
            "start_time": appt.starting_time.strftime("%I:%M%p").lower(),
            "end_time": appt.ending_time.strftime("%I:%M%p").lower()
        })

    # Expiring documents
    today = datetime.today().date()
    soon = today + timedelta(days=14)

    expiring_docs = (
        db.session.query(Document)
        .filter(
            Document.user_id == session["user_id"],
            Document.expiration_date != None,
            Document.expiration_date >= today,
            Document.expiration_date <= soon  # add this
        )
        .order_by(Document.expiration_date.asc())
        .limit(5)
        .all()
    )

    expiring_data = []
    for doc in expiring_docs:
        days_left = (doc.expiration_date - today).days
        expiring_data.append({
            "days_left": days_left,
            "document_type": doc.document_type,
            "practitioner_type": doc.practitioner_type,
            "expires_on": doc.expiration_date.strftime("%b %d")
        })

    return render_template(
        "page_4_dashboardPage.html",
        upcoming_appointments=upcoming_data,
        expiring_docs=expiring_data  # Include this line
    )

@blueprint.route("/notifications/read", methods=["POST"])
def mark_notifications_read():
    try:
        csrf_token = request.headers.get("X-CSRFToken")
        validate_csrf(csrf_token)
    except CSRFError:
        return "CSRF token invalid or missing", 400

    timestamp = datetime.utcnow()
    session["notifications_viewed_at"] = timestamp.isoformat()

    if current_user.is_authenticated:
        current_user.notifications_viewed_at = timestamp
        db.session.commit()

    session.modified = True
    return jsonify({"success": True})


@blueprint.context_processor
def inject_notifications():
    notifications = []
    n_not = 0

    if session.get("role") == "member" and "user_id" in session:
        user_id = session["user_id"]
        now = datetime.now()

        appointments = Appointment.query.filter(
            Appointment.user_id == user_id,
            Appointment.appointment_date >= now.date()
        ).all()

        reminder_options = {
            "2 hours before": timedelta(hours=2),
            "12 hours before": timedelta(hours=12),
            "1 day before": timedelta(days=1),
            "1 week before": timedelta(weeks=1),
        }

        for appt in appointments:
            appt_datetime = datetime.combine(appt.appointment_date, appt.starting_time)

            # Standard reminders
            reminder_list = appt.reminder.split(",") if appt.reminder else []
            for rem in reminder_list:
                rem = rem.strip()
                if rem in reminder_options:
                    reminder_time = appt_datetime - reminder_options[rem]
                    if reminder_time <= now:
                        notifications.append({
                            "title": "Upcoming Appointment",
                            "body": f"{appt.practitioner_name} ({appt.practitioner_type})",
                            "date": appt.appointment_date.strftime("%b %d"),  # Correct: appointment date
                            "reminder_info": f"{rem}",  # e.g. "1 day before"
                            "triggered_on": reminder_time.strftime("%b %d"),  # the day it popped up
                        })

            # Custom reminder
            if appt.custom_reminder:
                custom_reminder_time = datetime.combine(appt.custom_reminder, time.min)
                if custom_reminder_time <= now:
                    notifications.append({
                        "title": "Reminder",
                        "body": f"{appt.practitioner_name}",
                        "date": appt.appointment_date.strftime("%b %d"),
                        "reminder_info": "Custom reminder for",
                        "reminder_date": appt.custom_reminder.strftime("%b %d"),
                        "triggered_on": custom_reminder_time.strftime("%b %d"),
                        "timestamp": custom_reminder_time
                    })

        shared_docs = (
            db.session.query(SharedDocument)
            .join(User, SharedDocument.sender_id == User.id)
            .filter(SharedDocument.recipient_id == session["user_id"])
            .order_by(SharedDocument.shared_at.desc())
            .all()
        )

        for shared in shared_docs:
            # Only show if recent or unread (up to you)
            if shared.shared_at <= datetime.now():
                notifications.append({
                    "title": "Shared Document",
                    "first_name": shared.sender.first_name,
                    "body": f" has shared their document(s)",
                    "date": shared.shared_at.strftime("%d %b"),  # e.g., "16 May"
                    "time": shared.shared_at.strftime("%H:%M"),
                    "triggered_on": shared.shared_at.isoformat(),
                })

        n_not = len(notifications)  # badge will now show ALL relevant notifications

    notifications.sort(key=lambda x: x.get("triggered_on"), reverse=True)

    return dict(n_not=n_not, notifications=notifications)

# Page 5 - Appointments Manager Page
@blueprint.route("/appointments")
@login_required
def appointment_manager():
    if session.get("role") != "member":
        return redirect(url_for("main.login"))

    query = request.args.get('q', '').strip()
    practitioner = request.args.get('practitioner', '')
    date = request.args.get('date', '')
    appt_type = request.args.get('type', '')
    order = request.args.get('order', 'asc')

    appointments = Appointment.query.filter_by(user_id=session["user_id"])

    if query:
        appointments = appointments.filter(
            (Appointment.appointment_type.ilike(f'%{query}%')) |
            (Appointment.appointment_notes.ilike(f'%{query}%')) |
            (Appointment.practitioner_name.ilike(f'%{query}%')) 
        )
    if practitioner:
        appointments = appointments.filter(Appointment.practitioner_name.ilike(f'%{practitioner}%'))
    if date:
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
            appointments = appointments.filter(Appointment.appointment_date == date_obj)
        except ValueError:
            pass
    if appt_type:
        appointments = appointments.filter(Appointment.appointment_type.ilike(f'%{appt_type}%'))

    appointments = appointments.order_by(
        Appointment.appointment_date.asc() if order == 'asc' else Appointment.appointment_date.desc()
    ).all()

    # Add days_away and status dynamically
    now = datetime.now()
    for appt in appointments:
        appt_datetime = datetime.combine(appt.appointment_date, appt.starting_time)
        if appt.appointment_date and appt.starting_time:
            appt_datetime = datetime.combine(appt.appointment_date, appt.starting_time)
            appt.days_away = (appt_datetime.date() - now.date()).days
            if appt_datetime.date() == now.date():
                appt.status = "Today"
            elif appt_datetime > now:
                appt.status = "Upcoming"
            else:
                appt.status = "Completed"
        else:
            appt.status = "Unknown"
        appt.days_away = (appt_datetime.date() - now.date()).days
        if appt_datetime.date() == now.date():
            appt.status = "Today"
        elif appt_datetime > now:
            appt.status = "Upcoming"
        else:
            appt.status = "Completed"

    return render_template("page_5_AppointmentsManagerPage.html", appointments=appointments)



@blueprint.route("/appointment/add", methods=["GET", "POST"])
def add_appointment():
    if request.method == "POST":
        # Directly get start_time and end_time from the form
        start_time_str = request.form['starting_time']
        end_time_str = request.form['ending_time']

        # Parse them properly
        starting_time = datetime.strptime(start_time_str, "%H:%M").time()
        ending_time = datetime.strptime(end_time_str, "%H:%M").time()

        # Reminder handling
        reminder = ",".join(request.form.getlist("reminder"))
        reminder_custom_str = request.form.get("custom_reminder")
        custom_reminder = datetime.strptime(reminder_custom_str, "%Y-%m-%d").date() if reminder_custom_str else None

        # Create the appointment
        new_appointment = Appointment(
            user_id=session["user_id"],
            appointment_date=datetime.strptime(request.form['appointment_date'], "%Y-%m-%d").date(),
            starting_time=starting_time,
            ending_time=ending_time,
            practitioner_name=request.form['practitioner_name'],
            practitioner_type=request.form['practitioner_type'],
            location=request.form['location'],
            appointment_notes=request.form['appointment_notes'],
            appointment_type=request.form['appointment_type'],
            provider_number=request.form.get('provider_number'),
            reminder=reminder,
            custom_reminder=custom_reminder
        )

        # Save to DB
        db.session.add(new_appointment)
        db.session.commit()

        flash("Appointment successfully created", "success")
        return redirect(url_for("main.appointment_manager"))

    # GET method — show blank form
    return render_template("page_6_AddAppointmentPage.html", appt=None, is_edit=False)

@blueprint.route("/appointment/edit/<int:appointment_id>", methods=["GET", "POST"])
def edit_appointment(appointment_id):
    appt = Appointment.query.get_or_404(appointment_id)

    if session.get("role") != "member" or appt.user_id != session.get("user_id"):
        return redirect(url_for("main.login"))

    if request.method == "POST":
        # NEW: Fetch start_time and end_time separately (NO more time split)
        start_time_str = request.form["starting_time"]
        end_time_str = request.form["ending_time"]

        starting_time = datetime.strptime(start_time_str.strip(), "%H:%M").time()
        ending_time = datetime.strptime(end_time_str.strip(), "%H:%M").time()

        # Update appointment fields
        appt.appointment_date = datetime.strptime(request.form["appointment_date"], "%Y-%m-%d").date()
        appt.starting_time = starting_time
        appt.ending_time = ending_time
        appt.practitioner_name = request.form["practitioner_name"]
        appt.practitioner_type = request.form["practitioner_type"]
        appt.location = request.form["location"]
        appt.appointment_notes = request.form["appointment_notes"]
        appt.appointment_type = request.form["appointment_type"]
        appt.provider_number = request.form.get("provider_number")
        appt.reminder = ",".join(request.form.getlist("reminder"))

        reminder_custom_str = request.form.get("custom_reminder")
        appt.custom_reminder = datetime.strptime(reminder_custom_str, "%Y-%m-%d").date() if reminder_custom_str else None

        db.session.commit()
        flash("Appointment successfully updated", "success")
        return redirect(url_for("main.appointment_manager"))

    return render_template("page_6_AddAppointmentPage.html", appt=appt, is_edit=True)

@blueprint.route("/appointment/delete/<int:appointment_id>", methods=["POST"])
def delete_appointment(appointment_id):
    appt = Appointment.query.get_or_404(appointment_id)

    if session.get("role") != "member" or appt.user_id != session.get("user_id"):
        return jsonify({"error": "Unauthorized"}), 403

    db.session.delete(appt)
    db.session.commit()
    flash("Appointment successfully deleted", "success")
    return jsonify({"success": True})

# Page 7 - Calendar View Page
@blueprint.route("/calendar")
@login_required
def calendar():
    if session.get("role") != "member":
        return redirect(url_for("main.login"))

    appointments = Appointment.query.filter_by(user_id=session["user_id"]).all()
    documents = Document.query.filter_by(user_id=session["user_id"]).all()

    appt_data = [
        {
            "id": appt.id,
            "title": f"{appt.practitioner_name} ({appt.appointment_type})",
            "start": appt.appointment_date.strftime("%Y-%m-%d") + 'T' + appt.starting_time.strftime("%H:%M"),
            "end": appt.appointment_date.strftime("%Y-%m-%d") + 'T' + appt.ending_time.strftime("%H:%M"),
            "location": appt.location,
            "description": appt.appointment_notes,
            "type": appt.appointment_type
        }
        for appt in appointments
    ]

    doc_data = [
        {
            "id": doc.id,
            "title": f"{doc.document_type} ({doc.document_name})",
            "start": doc.upload_date.strftime("%Y-%m-%d") + 'T' + doc.upload_date.strftime("%H:%M"),
            "end": doc.expiration_date.strftime("%Y-%m-%d") + 'T' + doc.expiration_date.strftime("%H:%M") if doc.expiration_date else None,
            "type": doc.document_type,
            "description": f"Uploaded on {doc.upload_date.strftime('%Y-%m-%d')}",
            "expiration_date": doc.expiration_date.strftime("%Y-%m-%d") if doc.expiration_date else None
        }
        for doc in documents
    ]

    return render_template("page_7_CalendarViewPage.html", appt_data=appt_data, doc_data=doc_data)

# Page 8 - Medical Documents Manager Page
@blueprint.route("/medical_document")
@login_required
def medical_document():
    # Get all documents for the current user
    query = request.args.get('q', '').strip()  # Search query
    practitioner = request.args.get('practitioner', '')  # Filter by practitioner
    doc_type = request.args.get('type', '')  # Filter by document type
    expiration_date = request.args.get('expiration_date', '')  # Filter by expiration date
    sort_by = request.args.get('sort', 'upload-desc')  # Sort by upload date or expiration date

    # Start querying the documents
    documents = Document.query.filter_by(user_id=current_user.id)

    # Apply search filters if any
    if query:
        documents = documents.filter(
            (Document.document_name.ilike(f'%{query}%')) |
            (Document.document_notes.ilike(f'%{query}%')) |
            (Document.practitioner_name.ilike(f'%{query}%'))
        )

    # Filter by practitioner name
    if practitioner:
        documents = documents.filter(Document.practitioner_name.ilike(f'%{practitioner}%'))

    # Filter by document type
    if doc_type:
        documents = documents.filter(Document.document_type.ilike(f'%{doc_type}%'))

    # Filter by expiration date
    if expiration_date:
        try:
            expiration_date_obj = datetime.strptime(expiration_date, '%Y-%m-%d').date()
            documents = documents.filter(Document.expiration_date == expiration_date_obj)
        except ValueError:
            pass  # If the date format is incorrect, it will not filter by expiration date

    # Handle sorting
    if sort_by == 'upload-asc':
        documents = documents.order_by(Document.upload_date.asc())
    elif sort_by == 'upload-desc':
        documents = documents.order_by(Document.upload_date.desc())
    elif sort_by == 'expiry-asc':
        documents = documents.order_by(Document.expiration_date.asc())
    elif sort_by == 'expiry-desc':
        documents = documents.order_by(Document.expiration_date.desc())

    # Execute the query
    documents = documents.all()

    return render_template(
        "page_8_MedicalDocumentsManagerPage.html",
        documents=documents,
        sort_by=sort_by,
        query=query,
        practitioner=practitioner,
        doc_type=doc_type,
        expiration_date=expiration_date
    )

# search function for documents manager page
@blueprint.route('/documents/search', methods=['GET'])
@login_required
def search_documents():
    query = request.args.get('q', '').strip()
    doc_type = request.args.get('type', '')
    expiration = request.args.get('expiration', '')

    documents = Document.query.filter_by(user_id=current_user.id)

    if query:
        documents = documents.filter(
            (Document.document_name.ilike(f'%{query}%')) |
            (Document.document_notes.ilike(f'%{query}%'))
        )
    if doc_type:
        documents = documents.filter(Document.document_type.ilike(f'%{doc_type}%'))
    if expiration:
        try:
            expiration_obj = datetime.strptime(expiration, '%Y-%m-%d').date()
            documents = documents.filter(Document.expiration_date == expiration_obj)
        except ValueError:
            pass  # skip if date format is invalid

    documents = documents.all()
    return render_template('page_8_MedicalDocumentsManagerPage.html', documents=documents)


# View document route
@blueprint.route("/medical_document/view/<int:doc_id>")
@login_required
def view_document(doc_id):
    document = Document.query.get_or_404(doc_id)
    if document.user_id != current_user.id:
        flash("You don't have permission to view this document")
        return redirect(url_for('medical_document'))
    # for now return to the documents list with a message
    flash("Document viewing functionality will be implemented soon")
    return redirect(url_for('medical_document'))

# Download document route
@blueprint.route("/medical_document/download/<int:doc_id>")
@login_required
def download_document(doc_id):
    document = Document.query.get_or_404(doc_id)
     # Allow if user owns the doc or it's been shared with them
    is_owner = document.user_id == session["user_id"]
    is_shared_with_user = SharedDocument.query.filter_by(document_id=doc_id, recipient_id=session["user_id"]).first()

    if not (is_owner or is_shared_with_user):
        flash("You don't have permission to download this document")
        return redirect(url_for("document_manager"))

    return send_from_directory(current_app.config['UPLOAD_FOLDER'], document.file, as_attachment=True)

# Delete document route
@blueprint.route("/medical_document/delete/<int:doc_id>")
@login_required
def delete_document(doc_id):
    document = Document.query.get_or_404(doc_id)
    if document.user_id != current_user.id:
        flash("You don't have permission to delete this document")
        return redirect(url_for('medical_document'))
    db.session.delete(document)
    db.session.commit()

    flash(f"Document '{document.document_name}' has been deleted")
    return redirect(url_for('main.medical_document'))

# Page 9 - Upload New Document Page
@blueprint.route("/medical_document/upload_document", methods=["GET", "POST"])
@login_required
def upload_document():
    if request.method == "POST":
        if 'upload_document' not in request.files:
            flash("No file part", "danger")
            return redirect(request.url)

        file = request.files['upload_document']
        if file.filename == '':
            flash("No selected file", "danger")
            return redirect(request.url)

        filename = secure_filename(file.filename)
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(upload_path)

        # Parse form fields manually
        document_name = request.form['document_name']
        document_type = request.form['document_type']
        document_notes = request.form.get('document_notes', '')
        practitioner_name = request.form.get('practitioner_name', '')
        practitioner_type = request.form.get('practitioner_type', '')

        # Parse and validate date fields
        upload_date_str = request.form.get('upload_date')
        if not upload_date_str:
            flash("Upload date is required.", "danger")
            return redirect(request.url)

        try:
            upload_date = datetime.strptime(upload_date_str, "%Y-%m-%d")
        except ValueError:
            flash("Invalid upload date format. Use yyyy-mm-dd.", "danger")
            return redirect(request.url)

        expiration_date = None
        if request.form.get("expiration_enabled"):
            try:
                expiration_date = datetime.strptime(request.form['expiration_date'], "%Y-%m-%d")
            except ValueError:
                flash("Invalid expiration date format. Use yyyy-mm-dd.", "danger")
                return redirect(request.url)

        # Save document to DB
        print("DEBUG: Uploading", document_name, filename)  # <- Debug line
        new_doc = Document(
            user_id=current_user.id,
            document_name=document_name,
            document_type=document_type,
            document_notes=document_notes,
            practitioner_name=practitioner_name,
            practitioner_type=practitioner_type,
            upload_date=upload_date,
            expiration_date=expiration_date,
            file=filename
        )

        db.session.add(new_doc)
        db.session.commit()
        print("DEBUG: Upload succeeded")  # <-- Debug line

        flash("Document uploaded successfully!", "success")
        return redirect(url_for("main.medical_document"))

    return render_template("page_9_UploadNewDocumentPage.html")

# Page 10 - Select Documents to Share Page
@blueprint.route("/medical_document/share_document", methods=["GET", "POST"])
@login_required
def share_document():
    form = DummyForm()
    if form.validate_on_submit():
        recipient_email = request.form.get('recipient_email')
        document_ids    = request.form.getlist('document_ids')
        include_personal = bool(request.form.get('include_personal_summary'))

        if not recipient_email:
            flash("No email provided.", "warning")
        else:
            recipient = User.query.filter_by(email=recipient_email).first()
            if not recipient:
                flash("Recipient not found.", "danger")
            else:
                for doc_id in document_ids:
                    shared = SharedDocument(
                        document_id  = doc_id,
                        sender_id    = current_user.id,
                        recipient_id = recipient.id,
                        shared_at    = datetime.utcnow()
                    )
                    db.session.add(shared)
                db.session.commit()
                flash("Documents shared successfully!", "success")
        return redirect(url_for('main.share_document'))

    # on GET or invalid CSRF POST, fall through and re-render
    user_docs = Document.query.filter_by(user_id=current_user.id).all()
    shared_q = (
        db.session.query(
            SharedDocument, Document.document_name, Document.document_type,
            SharedDocument.shared_at, User.email.label("sender_email")
        )
        .join(Document, SharedDocument.document_id == Document.id)
        .join(User, SharedDocument.sender_id == User.id)
        .filter(SharedDocument.recipient_id == current_user.id)
        .all()
    )
    return render_template(
        "page_10_SelectDocumentsToSharePage.html",
        form             = form,
        documents        = user_docs,
        shared_documents = shared_q
    )

@blueprint.route('/documents/share/search', methods=['GET'])
@login_required
def search_documents_to_share():
    query = request.args.get('q', '').strip()
    doc_type = request.args.get('type', '')
    expiration = request.args.get('expiration', '')

    documents = Document.query.filter_by(user_id=current_user.id)

    if query:
        documents = documents.filter(
            (Document.document_name.ilike(f'%{query}%')) |
            (Document.document_notes.ilike(f'%{query}%'))
        )
    if doc_type:
        documents = documents.filter(Document.document_type.ilike(f'%{doc_type}%'))
    if expiration:
        try:
            expiration_obj = datetime.strptime(expiration, '%Y-%m-%d').date()
            documents = documents.filter(Document.expiration_date == expiration_obj)
        except ValueError:
            pass  # skip if date is invalid

    documents = documents.all()
    return render_template('page_10_SelectDocumentsToSharePage.html', documents=documents)

@blueprint.route('/documents/export', methods=['POST'])
@login_required
def export_documents():
    selected_ids = request.form.getlist('document_ids')
    include_personal_summary = request.form.get('include_personal_summary')

    if not selected_ids:
        flash('No documents selected for export.', 'danger')
        return redirect(url_for('share_document'))

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for doc_id in selected_ids:
            doc = Document.query.filter_by(id=doc_id, user_id=current_user.id).first()
            if not doc:
                continue

            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], doc.file)
            if os.path.exists(file_path):
                zipf.write(file_path, arcname=doc.file)
            else:
                current_app.logger.warning(f"File not found: {file_path}")

        if include_personal_summary:
            personal_details = generate_personal_summary(current_user)
            zipf.writestr('PersonalDetails.txt', personal_details)

    zip_buffer.seek(0)
    filename = f"{current_user.first_name}{current_user.last_name}_DocumentsToBeSent.zip"

    return send_file(
        zip_buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name=filename
    )

@blueprint.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

def generate_personal_summary(user):
    profile = user.profile

    summary = f"""
    Personal Details Summary
    ------------------------
    Name: {user.first_name} {user.last_name}
    Email: {user.email}
    Date of Birth: {profile.date_of_birth if profile else 'Not provided'}
    Contact Number: {profile.mobile_number if profile else 'Not provided'}
    Address: {profile.address if profile else 'Not provided'}
    Gender: {profile.gender if profile else 'Not provided'}
    Insurance Type: {profile.insurance_type if profile else 'Not provided'}
    Medical Summary: {getattr(user, 'medical_summary', 'Not provided')}

    Generated on: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"""
    return summary

# Page 11 - User Profile Settings Page
@blueprint.route("/user_profile", methods=["GET", "POST"])
@login_required
def user_profile():
    user = current_user
    form = UserProfileForm(obj=user)

    if form.validate_on_submit():
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        # user.email is read-only
        user.mobile_number = form.mobile_number.data
        user.insurance_type = form.insurance_type.data
        user.date_of_birth = form.dob.data
        user.address = form.address.data
        user.gender = form.gender.data

        # Optional password update
        if form.password.data:
            user.set_password(form.password.data)

        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for("main.user_profile"))

    return render_template("page_11_UserProfileSettingsPage.html", form=form, user=user)

# Page 13 - Edit Document Page
@blueprint.route("/medical_document/edit_document/<int:doc_id>", methods=["GET", "POST"])
@login_required
def edit_document(doc_id):
    document = Document.query.get_or_404(doc_id)

    form = DocumentForm(obj=document)

    if form.validate_on_submit():
        file_field = form.upload_document.data

        # Check if the user selected a new file
        if file_field:
            filename = secure_filename(file_field.filename)
            save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file_field.save(save_path)
            document.file = filename  # Update the file field with the new file
        else:
            # If no new file is selected, retain the existing file in the database
            document.file = document.file

        # Update other fields
        document.document_name = form.document_name.data
        document.upload_date = form.upload_date.data
        document.document_type = form.document_type.data
        document.document_notes = form.document_notes.data
        document.practitioner_name = form.practitioner_name.data
        document.expiration_date = form.expiration_date.data
        document.practitioner_type = form.practitioner_type.data

        db.session.commit()

        flash("Document edited successfully!", "success")
        return redirect(url_for("main.medical_document"))

    return render_template(
        "page_13_EditDocumentPage.html",
        form=form,
        document=document
    )

# Page 14 - Personal Insights
@blueprint.route("/insights")
@login_required
def insights():
    user_id = session.get("user_id")
    appointments = Appointment.query.filter_by(user_id=user_id).all()
    today = datetime.today().date()
    soon = today + timedelta(days=14)

    expiring_docs = (
        db.session.query(Document)
        .filter(
            Document.user_id == user_id,
            Document.expiration_date != None,
            Document.expiration_date.between(today, soon)
        )
        .all()
    )

    documents_expiring_soon = len(expiring_docs)

    total_documents = Document.query.filter_by(user_id=user_id).count()

    # Count most frequent appointment type
    type_counter = Counter([appt.appointment_type for appt in appointments])
    top_type = type_counter.most_common(1)
    top_appointment_type = f"{top_type[0][0]}" if top_type else "N/A"

    # Count most frequent practitioner
    practitioner_counter = Counter([appt.practitioner_type for appt in appointments if appt.practitioner_type])
    top_practitioner = practitioner_counter.most_common(1)

    practitioner_names = Counter([appt.practitioner_name for appt in appointments])
    most_frequent_practitioner = practitioner_names.most_common(1)[0][0] if practitioner_names else "TBD"

    # =====Bar chart ======

    top_practitioners = practitioner_names.most_common(6)
    bar_chart_labels = [pract[0] for pract in top_practitioners]
    bar_chart_values = [pract[1] for pract in top_practitioners]

    # ==== Pie chart data ====
    type_counts = Counter([appt.appointment_type for appt in appointments])
    labels = ["General", "Follow-up", "Checkup", "Consultation", "Test"]
    data = [type_counts.get(label, 0) for label in labels]

    # Define distinct colors (adjust or expand this list as needed)
    bar_chart_colors = ['#3B82F6', '#22C55E', '#EAB308', '#8B5CF6', '#EF4444', '#F97316']

    # ==== Line chart data ====

    latest_appointment_date = max((appt.appointment_date for appt in appointments), default=today)
    selected_range = "6months"  # or "3months", "year", etc.

    cutoff_months_map = {
        "year": 12,
        "6months": 6,
        "3months": 3,
        "month": 1
    }
    cutoff_months = cutoff_months_map.get(selected_range, 12)
    cutoff_date = latest_appointment_date - relativedelta(months=cutoff_months)

    # Filter appointments by date range
    filtered_appointments = [
        appt for appt in appointments
        if cutoff_date <= appt.appointment_date <= latest_appointment_date
    ]


    monthly_counts = defaultdict(lambda: defaultdict(int))  # {type: {YYYY-MM: count}}

    for appt in filtered_appointments:
        key = appt.appointment_date.strftime("%Y-%m")
        monthly_counts[appt.appointment_type][key] += 1

    all_months = sorted({appt.appointment_date.strftime("%Y-%m") for appt in filtered_appointments})

    # Convert to display format (e.g. "Jul 2024")
    display_labels = [datetime.strptime(m, "%Y-%m").strftime("%b %Y") for m in all_months]

    # Align each type's data to all_months
    line_chart_data = {
        t: [monthly_counts[t].get(m, 0) for m in all_months]
        for t in labels
    }

    color_map = {
        "General": "#3B82F6",
        "Follow-up": "#22C55E",
        "Checkup": "#EAB308",
        "Consultation": "#8B5CF6",
        "Test": "#EF4444"
    }

    # Build daily aggregation (for week view)
    daily_counts = defaultdict(lambda: defaultdict(int))  # {type: {date: count}}
    for appt in appointments:
        day_str = appt.appointment_date.strftime("%Y-%m-%d")
        daily_counts[appt.appointment_type][day_str] += 1

    # Extract sorted date labels (used for 'week' mode)
    all_days = sorted({appt.appointment_date.strftime("%Y-%m-%d") for appt in appointments})
    line_chart_days = {t: [daily_counts[t].get(day, 0) for day in all_days] for t in labels}
    latest_date_iso = latest_appointment_date.isoformat()
    latest_month_index = len(all_months) - 1

    return render_template("page_14_PersonalisedUserAnalytics.html",
                           total_appointments=len(appointments),
                           total_documents=total_documents,
                           documents_expiring_soon=documents_expiring_soon,
                           most_frequent_practitioner=most_frequent_practitioner,
                           top_appointment_type=top_appointment_type,
                           chart_labels=labels,
                           chart_data=data,
                           line_chart_data=line_chart_data,
                           line_chart_days=line_chart_days,
                           day_labels=all_days,
                           chart_month_keys=all_months,
                           chart_month_labels=display_labels,
                           latest_date=latest_date_iso,
                           latest_month_index=len(all_months) - 1,
                           bar_chart_labels=bar_chart_labels,
                           bar_chart_values=bar_chart_values,
                           bar_chart_colors=bar_chart_colors,
                           color_map=color_map)


# Page 15 - Password Reset Page
def send_reset_email(user):
    token = user.get_reset_token()
    # in real application, we would send an actual email but
    # for this project, we'll flash the reset link for demonstration
    reset_url = url_for('reset_token', token=token, _external=True)
    flash(f'Password reset link (for testing only): {reset_url}', 'info')

@blueprint.route("/reset_request", methods=["GET", "POST"])
def reset_request():
    # Redirect if user is already logged in
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = RequestPasswordResetForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        # Send password reset email
        # (In a real application, you would send an actual email here)
        token = user.get_reset_token()

        # For demonstration, we'll just show a direct link
        reset_url = url_for('main.reset_token', token=token, _external=True)
        print(f"Password reset link: {reset_url}")

        flash("A password reset link has been sent to your email.", "info")
        return redirect(url_for("main.login"))

    return render_template("page_15_PasswordResetRequest.html", form=form)

# Page 16 - Password Reset Page
# Password reset with token
@blueprint.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_token(token):
    # Redirect if user is already logged in
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    # Verify the token and get user
    user = User.verify_reset_token(token)

    if user is None:
        flash("That is an invalid or expired token", "warning")
        return redirect(url_for("main.reset_request"))

    form = ResetPasswordForm()

    if form.validate_on_submit():
        # Update the user's password
        user.set_password(form.password.data)
        db.session.commit()

        flash("Your password has been updated! You can now log in.", "success")
        return redirect(url_for("main.login"))

    return render_template("page_16_ResetToken.html", form=form)

# Page 17 - Change Password Page
# Change password (for logged-in users)
@blueprint.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()

    if form.validate_on_submit():
        # Verify current password
        if not current_user.check_password(form.current_password.data):
            flash("Current password is incorrect", "danger")
            return render_template("page_17_ChangePassword.html", form=form)

        # Set new password
        current_user.set_password(form.new_password.data)
        db.session.commit()

        flash("Your password has been changed successfully!", "success")
        return redirect(url_for("main.user_profile"))

    return render_template("page_17_ChangePassword.html", form=form)