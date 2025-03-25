# Applizz - Job Application Tracker

A clean, streamlined job application tracking system built with Flask and MongoDB.

## Features

- **User Management**: Register, login, and user profile management
- **Application Tracking**: Add, edit, and delete job applications with status management
- **Dashboard**: Visual statistics of your job hunt progress
- **Document Management**: Attach and manage documents for each application
- **Interview Tracking**: Schedule and manage interview processes
- **Notes System**: Keep detailed notes on each application

## Tech Stack

- **Backend**: Flask (Python)
- **Database**: MongoDB
- **Frontend**: HTML, Tailwind CSS, JavaScript
- **Authentication**: Flask-Login
- **Data Visualization**: Chart.js

## Deployment Instructions

### Local Development

1. Clone the repository

   ```
   git clone <repository-url>
   cd job_app_tracker
   ```

2. Create a virtual environment and install dependencies

   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Set up environment variables
   Create a `.env` file in the root directory with the following:

   ```
   FLASK_ENV=development
   SECRET_KEY=your_secret_key
   MONGODB_URI=mongodb://localhost:27017/job_app_tracker
   ```

4. Run the application
   ```
   python run.py
   ```
   The application will be available at http://localhost:3000

### Production Deployment

#### Deploying to Heroku

1. Create a Heroku account and install the Heroku CLI

2. Login to Heroku and create a new app

   ```
   heroku login
   heroku create your-app-name
   ```

3. Add MongoDB as an add-on or connect to your own MongoDB instance

   ```
   # Using MongoDB Atlas
   heroku config:set MONGODB_URI=your_mongodb_connection_string
   ```

4. Configure environment variables

   ```
   heroku config:set FLASK_ENV=production
   heroku config:set SECRET_KEY=your_secure_secret_key
   ```

5. Deploy the application
   ```
   git push heroku main
   ```

#### Deploying with Docker

1. Build the Docker image

   ```
   docker build -t applizz .
   ```

2. Run the container
   ```
   docker run -p 3000:3000 \
     -e FLASK_ENV=production \
     -e SECRET_KEY=your_secure_secret_key \
     -e MONGODB_URI=your_mongodb_connection_string \
     applizz
   ```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
