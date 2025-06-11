# Chronic Pain Tracker

<p align="center">
  <img src="https://raw.githubusercontent.com/olalozyk/3403GroupProject/main/app/static/images/chronic-care-title.png" alt="Chronic Care Logo" height="80px">
</p>
A web-based application designed to help individuals with chronic pain manage medical appointments, documents, and reminders with ease. The application prioritizes simplicity, accessibility, and privacy, making it suitable for users of all ages, including caregivers.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Setup Instructions](#setup-instructions)
- [Team Members](#team-members)

---

## Overview

Chronic Pain Tracker is a Flask-based data analytics application that allows users to:

- Log appointments and view them in a calendar format
- Upload, categorize, and manage medical documents
- Get notified about upcoming appointments, expiring referrals, and insurance
- Share selected documents with medical providers or pharmacists

All data is stored privately per user, with secure authentication and controlled sharing options.

---

## Features

- **User Authentication**: Register and log in securely
- **Dashboard**: View upcoming appointments and alerts for expiring items
- **Appointments Manager**: Add, edit, delete and view past and upcoming medical appointments
- **Calendar View**: See all appointments and reminders in a month-based layout
- **Medical Document Manager**: Upload and manage test results, referrals, invoices, and prescriptions
- **Document Sharing**: Select and bundle documents to share externally
- **Insights & Analytics**: Visual charts showing appointment trends, top practitioners, and frequencies
- **Profile Settings** (optional): Change email, password, and delete account
- **Notifications**: Shows reminders for upcoming and custom appointments based on real-time logic
- **SocketIO Integration**: Real-time login and user connection events

---

## Tech Stack

| Category  | Tools/Libraries                             |
| --------- | ------------------------------------------- |
| Frontend  | HTML, CSS, Bootstrap, JavaScript, JQuery    |
| Backend   | Python, Flask                               |
| Charting  | Chart.js, ChartDataLabels                   |
| Database  | SQLite with SQLAlchemy ORM                  |
| Forms     | Flask-WTF, WTForms                          |
| Real-Time | Flask-SocketIO                              |
| Other     | AJAX, CSRF protection, Meta tag integration |

---

## Setup Instructions

1. **Clone the repository**

   ```bash
   git clone https://github.com/YOUR-TEAM/chronic-pain-tracker.git
   cd chronic-pain-tracker

   ```

2. **Create a virtual environment**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt

   ```
4. **Create A Folder for the Database**
   ```bash
   mkdir instance
   ```

5. **Run the app**

```bash
+ flask db upgrade  # Run database migrations (if using Flask-Migrate)
+ flask run

```

## Team Members

<table>
  <tr>
    <th>No.</th>
    <th>UWA ID</th>
    <th>Name</th>
    <th>GitHub Username</th>
  </tr>
  <tr>
    <td>1</td>
    <td>23032563</td>
    <td>Aleksandra Lozyk</td>
    <td>@olalozyk</td>
  </tr>
  <tr>
    <td>2</td>
    <td>23804104</td>
    <td>Siena Isaacs</td>
    <td>@enahen77</td>
  </tr>
  <tr>
    <td>3</td>
    <td>24250666</td>
    <td>Wei Shen Hong</td>
    <td>@weishen1113</td>
  </tr>
  <tr>
    <td>4</td>
    <td>23832333</td>
    <td>Dharun Somalingam</td>
    <td>@DharunSomalingam</td>
  </tr>
</table>
