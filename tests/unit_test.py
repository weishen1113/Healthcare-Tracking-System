import os
import sys
import unittest
import warnings
from flask import session
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta, date, time
import random
import string

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import from app
from app import db, create_app
from app.models import User, Appointment, Document

# Suppress noisy test resource warnings
warnings.filterwarnings("ignore", category=ResourceWarning)

class UnitTests(unittest.TestCase):
    """Test cases for isolated components"""
    
    def setUp(self):
        """Set up test environment before each test"""
        self.app = create_app()
        self.app.config.update({
            'TESTING': True,
            'WTF_CSRF_ENABLED': False,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'SECRET_KEY': 'test-key'
        })
        self.client = self.app.test_client()
        
        # Create application context and set up database
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Create a test user with unique email for this test run
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        self.test_email = f"test{random_suffix}@example.com"
        
        self.test_user = User(
            first_name='Test',
            last_name='User',
            email=self.test_email,
            role='member'
        )
        self.test_user.set_password('testpassword')
        db.session.add(self.test_user)
        db.session.commit()
    
    # Create a test user in the database
    def create_user(self, email="test@example.com", password="testpass123"):
        user = User(
            first_name="Test",
            last_name="User",
            email=email
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user
    
    # Gets the CSRF token from any page that renders a form 
    def get_csrf_token(self, route): 
        response = self.client.get(route)
        token = None
        if b'name="csrf_token"' in response.data:
            import re
            match = re.search(r'name="csrf_token" type="hidden" value="([^"]+)"', response.get_data(as_text=True))
            if match:
                token = match.group(1)
        return token
    
    # Log in a user via the test client
    def login(self, user, password="testpass123"):
        return self.client.post("/login", data={
            "email": user.email,
            "password": password
        }, follow_redirects=True)

    # Upload and register a test document for a user
    def add_document(self, user, document_name="Sample Doc", file="sample_file.pdf", document_type="General", practitioner_name="Dr. Smith", document_notes="Routine checkup"):
        os.makedirs("app/static/uploads", exist_ok=True)
        file_path = os.path.join("app/static/uploads", file)

        with open(file_path, "wb") as f:
            f.write(b"Dummy file content")

        doc = Document(
            user_id=user.id,
            file=file,
            document_name=document_name,
            document_type=document_type,
            document_notes=document_notes, 
            practitioner_name=practitioner_name,
            upload_date=datetime.utcnow()
        )
        db.session.add(doc)
        db.session.commit()
        return doc

    def tearDown(self):
        """Clean up after each test"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    # Helper method - Original from unit_test.py
    def add_student(self, id, password):
        """Helper method to add a student"""
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        email = f"student{id}_{random_suffix}@example.com"
        
        student = User(
            first_name='Student',
            last_name=str(id),
            email=email,
            role='member'
        )
        student.set_password(password)
        db.session.add(student)
        db.session.commit()
        return student
    
    # Helper method - From test_routes.py, AppointmentTestCase
    def login_session(self):
        """Helper method to log in a user"""
        return self.client.post("/login", data={
            "email": self.test_email,
            "password": "testpassword"
        }, follow_redirects=True)
    
    #
    # MODEL TESTS - From test_auth_unittest.py and test_models.py
    #
    
    # From test_auth_unittest.py
    def test_user_password_hashing(self):
        """Test that passwords are properly hashed and verified"""
        user = User(
            first_name='Hash',
            last_name='Test',
            email='hash_test@example.com'  # Changed to be unique
        )
        
        user.set_password('testpassword')
        self.assertNotEqual(user.password, 'testpassword')
        self.assertGreater(len(user.password), 20)
        
        # Password verification
        self.assertTrue(user.check_password('testpassword'))
        self.assertFalse(user.check_password('wrongpassword'))
    
    # From test_auth_unittest.py
    def test_user_reset_token_generation(self):
        """Test that reset tokens can be generated and verified"""
        user = User.query.filter_by(email=self.test_email).first()
        
        # Generate token
        token = user.get_reset_token()
        self.assertIsNotNone(token)
        
        # Verify token
        verified_user = User.verify_reset_token(token)
        self.assertEqual(verified_user.id, user.id)
        
        # Test invalid token
        invalid_user = User.verify_reset_token('invalid-token')
        self.assertIsNone(invalid_user)
    
    # From test_auth_unittest.py
    def test_user_creation(self):
        """Test creating a new user in the database"""
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        new_email = f"new{random_suffix}@example.com"
        
        new_user = User(
            first_name='New',
            last_name='User',
            email=new_email,
            role='member'
        )
        new_user.set_password('newpassword')
        db.session.add(new_user)
        db.session.commit()
        
        # Verify user exists in database
        user = User.query.filter_by(email=new_email).first()
        self.assertIsNotNone(user)
        self.assertEqual(user.first_name, 'New')
        self.assertEqual(user.last_name, 'User')
        self.assertTrue(user.check_password('newpassword'))
    
    # From test_models.py
    def test_appointment_creation(self):
        """Test creating a new appointment"""
        # Create test appointment
        appointment = Appointment(
            user_id=self.test_user.id,
            practitioner_type='GP',
            practitioner_name='Dr. Smith',
            appointment_date=date(2025, 1, 1),
            starting_time=time(10, 0),
            ending_time=time(10, 30),
            location='Clinic',
            appointment_type='Checkup',
            appointment_notes='Bring reports'
        )
        
        db.session.add(appointment)
        db.session.commit()
        
        # Retrieve and verify appointment
        saved_appt = Appointment.query.filter_by(practitioner_name='Dr. Smith').first()
        self.assertIsNotNone(saved_appt)
        self.assertEqual(saved_appt.location, 'Clinic')
        self.assertEqual(saved_appt.appointment_type, 'Checkup')
    
    # From test_models.py
    def test_document_creation(self):
        """Test creating a new document"""
        # Create test document
        document = Document(
            user_id=self.test_user.id,
            file='report.pdf',
            document_name='Test Report',
            upload_date=date(2025, 1, 1),
            document_type='Lab',
            document_notes='Blood test',
            practitioner_name='Dr. Adams'
        )
        
        db.session.add(document)
        db.session.commit()
        
        # Retrieve and verify document
        saved_doc = Document.query.filter_by(document_name='Test Report').first()
        self.assertIsNotNone(saved_doc)
        self.assertEqual(saved_doc.document_type, 'Lab')
        self.assertEqual(saved_doc.practitioner_name, 'Dr. Adams')
    
    #
    # ROUTE TESTS - From test_routes.py
    #
    
    # From test_routes.py, RegistrationTestCase
    def test_register_route(self):
        """Test registration route"""
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        new_email = f"newuser{random_suffix}@example.com"

        response = self.client.post("/register", data={
            "first_name": "New",
            "last_name": "User",
            "email": new_email,
            "password": "testpass123",
            "confirm_password": "testpass123"
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Account created successfully", response.data)

        # Verify user exists in database
        user = User.query.filter_by(email=new_email).first()
        self.assertIsNotNone(user)
        self.assertEqual(user.first_name, "New")
    
    # From test_routes.py, RegistrationTestCase
    def test_register_duplicate_email(self):
        """Test registration with duplicate email"""
        # First register a user
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        dup_email = f"dup{random_suffix}@example.com"
        
        # First registration
        self.client.post("/register", data={
            "first_name": "First",
            "last_name": "User",
            "email": dup_email,
            "password": "testpass123",
            "confirm_password": "testpass123"
        }, follow_redirects=True)

        # Try to register with the same email
        response = self.client.post("/register", data={
            "first_name": "Second",
            "last_name": "User",
            "email": dup_email,  # Same email
            "password": "testpass123",
            "confirm_password": "testpass123"
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"error checking email", response.data.lower())
    
    # From test_routes.py, AppointmentTestCase
    def test_add_appointment_route(self):
        """Test adding appointment through route"""
        # Login first
        self.login_session()

        today = datetime.today().date()
        tomorrow = today + timedelta(days=1)

        response = self.client.post("/appointment/add", data={
            "appointment_date": today.strftime('%Y-%m-%d'),
            "starting_time": "09:00",
            "ending_time": "10:00",
            "practitioner_name": "Dr. Smith",
            "practitioner_type": "General Practitioner (GP)",
            "location": "Test Clinic",
            "provider_number": "123456",
            "appointment_type": "General",
            "appointment_notes": "Unittest appointment.",
            "reminder": ["2 hours before", "1 day before"],
            "custom_reminder": tomorrow.strftime('%Y-%m-%d')
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Appointment successfully created", response.data)

        # Verify appointment was created
        appt = Appointment.query.filter_by(practitioner_name="Dr. Smith").first()
        self.assertIsNotNone(appt)
        self.assertEqual(appt.location, "Test Clinic")
        self.assertEqual(appt.reminder, "2 hours before,1 day before")
        self.assertEqual(appt.custom_reminder, tomorrow)

    # Test searching appointments by partial practitioner name returns correct results
    def test_appointment_search_by_practitioner(self):
        """Test searching appointments by practitioner name"""
        # Add two appointments with different practitioners
        appt1 = Appointment(
            user_id=self.test_user.id,
            practitioner_name="Dr. Jess",
            practitioner_type="GP",
            appointment_date=date(2025, 5, 28),
            starting_time=time(8, 0),
            ending_time=time(9, 0),
            location="Wellness Clinic",
            appointment_type="Checkup",
            appointment_notes="First visit"
        )
        appt2 = Appointment(
            user_id=self.test_user.id,
            practitioner_name="Dr. Sam",
            practitioner_type="Physio",
            appointment_date=date(2025, 6, 1),
            starting_time=time(10, 0),
            ending_time=time(10, 30),
            location="Care Centre",
            appointment_type="Follow-Up",
            appointment_notes="Post-treatment"
        )
        db.session.add_all([appt1, appt2])
        db.session.commit()

        self.login_session()
        response = self.client.get("/appointments?q=Jess", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Dr. Jess", response.data)
        self.assertNotIn(b"Dr. Sam", response.data)

    # Test sorting appointments in descending date order
    def test_appointment_sorting_order(self):
        """Test sorting appointments in descending order"""
        appt1 = Appointment(
            user_id=self.test_user.id,
            practitioner_name="Dr. A",
            practitioner_type="GP",
            appointment_date=date(2025, 5, 10),
            starting_time=time(9, 0),
            ending_time=time(10, 0),
            location="Clinic A",
            appointment_type="General",
            appointment_notes="Older"
        )
        appt2 = Appointment(
            user_id=self.test_user.id,
            practitioner_name="Dr. B",
            practitioner_type="GP",
            appointment_date=date(2025, 6, 10),
            starting_time=time(9, 0),
            ending_time=time(10, 0),
            location="Clinic B",
            appointment_type="General",
            appointment_notes="Newer"
        )
        db.session.add_all([appt1, appt2])
        db.session.commit()

        self.login_session()
        response = self.client.get("/appointments?order=desc", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        # Check that newer appointment appears first
        self.assertTrue(response.data.find(b"Dr. B") < response.data.find(b"Dr. A"))

    # Test clearing filters resets the appointment view
    def test_clear_appointment_filters(self):
        """Test clearing filters returns all appointments"""
        appt = Appointment(
            user_id=self.test_user.id,
            practitioner_name="Dr. Clear",
            practitioner_type="GP",
            appointment_date=date.today(),
            starting_time=time(10, 0),
            ending_time=time(10, 30),
            location="Clinic Clear",
            appointment_type="Checkup",
            appointment_notes="Test clear"
        )
        db.session.add(appt)
        db.session.commit()

        self.login_session()
        response = self.client.get("/appointments", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Dr. Clear", response.data)
    
    # Test downloading a document the user owns
    def test_document_download(self):
        """Test that a user can download their own document"""
        self.login_session()

        # Upload a mock document entry
        doc = Document(
            user_id=self.test_user.id,
            document_name="Download Test",
            file="sample_file.pdf",
            upload_date=date.today(),
            document_type="General",
            document_notes="Test doc",
            practitioner_name="Dr. Test"
        )
        db.session.add(doc)
        db.session.commit()

        # Manually ensure the dummy file exists in the upload directory
        filepath = os.path.join(self.app.config['UPLOAD_FOLDER'], doc.file)
        os.makedirs(self.app.config['UPLOAD_FOLDER'], exist_ok=True)
        with open(filepath, 'w') as f:
            f.write("Dummy content")

        # Perform the download
        response = self.client.get(f"/medical_document/download/{doc.id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Dummy content", response.data)

    # Test deleting a document the user owns
    def test_document_delete(self):
        """Test that a user can delete their own document"""
        self.login_session()

        doc = Document(
            user_id=self.test_user.id,
            document_name="Delete Test",
            file="delete_me.pdf",
            upload_date=date.today(),
            document_type="Lab",
            document_notes="To delete",
            practitioner_name="Dr. Delete"
        )
        db.session.add(doc)
        db.session.commit()

        # Perform the delete
        response = self.client.get(f"/medical_document/delete/{doc.id}", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"has been deleted", response.data)

        # Confirm deletion
        deleted_doc = Document.query.get(doc.id)
        self.assertIsNone(deleted_doc)

    # Test document search by practitioner name
    def test_document_search(self):
        """Test document search returns correct matches"""
        self.login_session()

        doc1 = Document(
            user_id=self.test_user.id,
            document_name="Lab Results",
            file="lab_results.pdf",  
            document_type="Lab",
            document_notes="Blood test",
            practitioner_name="Dr. Jess",
            upload_date=date.today()
        )
        doc2 = Document(
            user_id=self.test_user.id,
            document_name="Scan Report",
            file="scan_report.pdf",  
            document_type="Radiology",
            document_notes="Chest scan",
            practitioner_name="Dr. Sam",
            upload_date=date.today()
        )

        db.session.add_all([doc1, doc2])
        db.session.commit()

        # Search for Dr. Jess
        response = self.client.get("/medical_document?q=Jess", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Dr. Jess", response.data)
        self.assertNotIn(b"Dr. Sam", response.data)

    # Share documents internally between users
    def test_share_documents_internally(self):
        """Test sharing documents with another user"""
        user1 = self.create_user(email="sharer@example.com")
        user2 = self.create_user(email="receiver@example.com")
        self.login(user1)

        # Add a test document
        doc = self.add_document(user1, document_name="X-Ray", document_type="Imaging")

        # Share the document with user2
        response = self.client.post(
            "/medical_document/share_document",
            data={
                "document_ids": [str(doc.id)],
                "recipient_email": user2.email,
                "include_personal_summary": "on",
                "csrf_token": self.get_csrf_token("/documents/share")
            },
            follow_redirects=True
        )

        self.assertIn(b"Documents shared successfully!", response.data)

    # Download selected documents as a ZIP archive
    def test_download_documents_zip(self):
        """Test downloading selected documents as a ZIP archive"""
        user = self.create_user(email="zipuser@example.com")
        self.login(user)

        # Add a document
        doc = self.add_document(user, document_name="MRI Scan", file="sample_file.pdf")

        response = self.client.post(
            "/documents/export",
            data={
                "document_ids": [str(doc.id)],
                "include_personal_summary": "on",
                "csrf_token": self.get_csrf_token("/documents/share")
            },
            follow_redirects=True
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/zip")
        self.assertIn(b'PK', response.data[:2])  # ZIP file starts with "PK"

    # Search documents by name/type before sharing
    def test_search_documents_to_share(self):
        """Test document search for sharing functionality"""
        user = self.create_user(email="searcher@example.com")
        self.login(user)

        # Add documents
        self.add_document(user, document_name="Blood Test", document_type="Lab")
        self.add_document(user, document_name="X-Ray Result", document_type="Imaging")

        response = self.client.get("/documents/share/search?q=Blood", follow_redirects=True)

        self.assertIn(b"Blood Test", response.data)
        self.assertNotIn(b"X-Ray Result", response.data)

if __name__ == '__main__':
    unittest.main()


