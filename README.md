# Job Application Tracker

A web application built with Flask and MongoDB to help job seekers track their job applications efficiently.

## Features

- **User Authentication**

  - Secure registration and login system
  - Case-insensitive email handling
  - Password reset functionality

- **Application Management**

  - Track job applications with company, position, and status
  - Add application details including URLs and notes
  - Set application deadlines
  - Update application status (Applied, Interview, Offer, Rejected, Withdrawn)

- **Interview Tracking**

  - Add and manage multiple interviews per application
  - Track interview dates, types, and notes
  - Edit or delete interview details

- **Dashboard Analytics**
  - Visual representation of application statuses
  - Track application progress over time
  - Quick overview of upcoming interviews and deadlines

## Tech Stack

- **Backend**: Python Flask
- **Database**: MongoDB
- **Frontend**: HTML, TailwindCSS, JavaScript
- **Authentication**: Flask-Login
- **Password Hashing**: Werkzeug Security

## Setup Instructions

1. **Clone the Repository**

   ```bash
   git clone <repository-url>
   cd job_app_tracker
   ```

2. **Set Up Virtual Environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables**
   Create a `.env` file in the root directory with:

   ```
   MONGODB_URI=your_mongodb_connection_string
   SECRET_KEY=your_secret_key
   ```

5. **Run the Application**
   ```bash
   python run.py
   ```
   The application will be available at `http://localhost:3000`

## Usage

1. **Registration/Login**

   - Create an account using email and password
   - Login with your credentials

2. **Adding Applications**

   - Click "Add Application" on the dashboard
   - Fill in company details, position, and status
   - Optionally add URL and notes

3. **Managing Interviews**

   - Add interviews from the application details page
   - Track interview dates and types
   - Add notes for interview preparation

4. **Updating Status**
   - Update application status as you progress
   - Track your success rate through the dashboard

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Contact

For any queries or support, please open an issue in the repository.
