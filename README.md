# Job Application Tracker

A web application that helps users track their job applications by automatically processing their emails and organizing application status.

## Features

- Email Integration: Automatically tracks job applications from your email
- Application Status Tracking: Keep track of your application statuses
- User Authentication: Secure login and registration system
- Dashboard: View all your job applications in one place

## Tech Stack

- Python 3.8+
- Flask (Web Framework)
- PostgreSQL (Database)
- SQLAlchemy (ORM)
- Flask-Login (Authentication)
- Flask-Mail (Email Integration)

## Setup

1. Clone the repository:

```bash
git clone <repository-url>
cd job_app_tracker
```

2. Create and activate virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Set up environment variables:
   Create a `.env` file in the root directory with the following variables:

```
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://localhost/job_app_tracker
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-specific-password
```

5. Initialize the database:

```bash
python init_db.py
```

6. Run the application:

```bash
python run.py
```

## Usage

1. Register an account at `/auth/register`
2. Configure your email settings in your profile
3. The application will automatically track job applications from configured email addresses
4. View and manage your applications on the dashboard

## Development

- Use `DevelopmentConfig` for local development
- Run tests with `python -m pytest`
- Follow PEP 8 style guide
- Use type hints for better code documentation

## Production Deployment

1. Set up proper PostgreSQL database
2. Configure production environment variables
3. Use `ProductionConfig`
4. Set up proper WSGI server (e.g., Gunicorn)
5. Configure proper email server settings

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
