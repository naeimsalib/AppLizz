# Job Application Tracker (Applizz)

A comprehensive web application built with Flask and MongoDB to help job seekers track and manage their job applications effectively.

## Features

### Dashboard

- Visual representation of application statistics
- Interactive timeline chart showing application history
- Status distribution chart (doughnut chart)
- Weekly application metrics
- Success rate calculations
- Application velocity metrics
- Quick access to upcoming deadlines, interviews, and reminders

### Application Management

- Add new job applications with detailed information:
  - Company name
  - Position
  - Application status
  - Application date
  - Application URL
  - Deadlines
  - Notes
- Edit existing applications
- Delete applications
- Bulk delete all applications

### Status Tracking

Applications can be tracked in various states:

- Applied
- In Progress
- Interview
- Offer
- Rejected
- Withdrawn

### Interview Management

- Schedule interviews for applications
- Track different types of interviews
- Add interview notes
- Edit interview details
- Delete interviews
- Automatic status updates when interviews are added

### Reminder System

- Create reminders for applications
- Set reminder types:
  - Interview
  - Deadline
  - Follow Up
  - Other
- Mark reminders as completed
- Edit reminder details
- Delete reminders
- View all reminders for a specific application

### Document Management

- Upload and store documents for each application
- Support for various file types
- Secure file storage
- Delete documents when no longer needed

### Notes System

- Add detailed notes to applications
- Edit existing notes
- Delete notes
- Chronological tracking of all notes

### Email Integration

- Connect with email providers (Gmail, Yahoo)
- Automatic email scanning for job applications
- Smart suggestions for new applications
- Status update suggestions based on email content
- Email notification settings

## Technical Stack

### Backend

- Python Flask
- MongoDB for database
- Flask-Login for authentication
- PyMongo for MongoDB integration

### Frontend

- HTML/CSS with Tailwind CSS
- JavaScript
- Chart.js for data visualization
- AJAX for asynchronous updates

### Security Features

- CSRF protection
- Secure file uploads
- User authentication
- Protected routes

## Installation and Setup

1. Clone the repository:

```bash
git clone <repository-url>
cd job_app_tracker
```

2. Create a virtual environment and activate it:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Set up environment variables:

```bash
export MONGODB_URI="your_mongodb_uri"
export SECRET_KEY="your_secret_key"
export GOOGLE_CLIENT_ID="your_google_client_id"  # Optional for Gmail integration
export GOOGLE_CLIENT_SECRET="your_google_client_secret"  # Optional for Gmail integration
```

5. Initialize the database:

```bash
python init_db.py
```

6. Run the application:

```bash
flask run
```

## Usage Guide

### Getting Started

1. Register for an account or log in if you already have one
2. Navigate to the dashboard to see your application overview
3. Click "Add Application" to start tracking your first job application

### Managing Applications

1. From the dashboard, you can:

   - View all your applications
   - Filter applications by status
   - Sort applications by date
   - Access quick actions for each application

2. For each application, you can:
   - Add/edit application details
   - Schedule interviews
   - Set reminders
   - Upload documents
   - Add notes

### Using Reminders

1. Navigate to an application's detail page
2. Click on "Reminders" tab
3. Add a new reminder with:
   - Title
   - Type (Interview/Deadline/Follow Up/Other)
   - Date and time
   - Description
4. Manage reminders:
   - Mark as completed
   - Edit details
   - Delete reminders

### Interview Tracking

1. Go to the application's interview section
2. Add new interviews with:
   - Date and time
   - Interview type
   - Notes
3. Track interview status
4. Update interview details as needed

### Document Management

1. Access the documents section of an application
2. Upload relevant files
3. View uploaded documents
4. Delete documents when no longer needed

### Email Integration

1. Go to Settings
2. Connect your email account (Gmail/Yahoo)
3. Configure email scanning preferences
4. Review and accept/reject application suggestions

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Chart.js for data visualization
- Tailwind CSS for styling
- Flask community for the excellent web framework
- MongoDB team for the robust database solution
