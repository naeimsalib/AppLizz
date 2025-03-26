from datetime import datetime, timedelta
from job_app_tracker import create_app
from job_app_tracker.models.user import User
from job_app_tracker.models.job_application import JobApplication
import random

def add_sample_applications():
    app = create_app()
    with app.app_context():
        # Get the user by email
        user = User.get_by_email('naeimsalib@gmail.com')
        if not user:
            print("User not found")
            return

        # Sample companies and positions
        companies = [
            "Google", "Microsoft", "Amazon", "Meta", "Apple", "Netflix", "Stripe", 
            "LinkedIn", "Uber", "Airbnb", "Twitter", "Pinterest", "Adobe", "Salesforce",
            "Oracle", "IBM", "Intel", "NVIDIA", "AMD", "Qualcomm"
        ]
        
        positions = [
            "Software Engineer", "Full Stack Developer", "Frontend Developer", 
            "Backend Developer", "DevOps Engineer", "Data Engineer", "ML Engineer",
            "Product Manager", "Technical Lead", "Senior Software Engineer"
        ]

        # Generate applications over the past 6 months
        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)  # 6 months ago

        # Create a list of dates to distribute applications
        dates = []
        current_date = start_date
        while current_date <= end_date:
            dates.append(current_date)
            current_date += timedelta(days=1)

        # Add 50 applications with random dates
        for _ in range(50):
            # Random date between start and end
            date_applied = random.choice(dates)
            
            # Random company and position
            company = random.choice(companies)
            position = random.choice(positions)
            
            # Determine status based on date_applied
            days_since_applied = (end_date - date_applied).days
            
            if days_since_applied < 7:
                status = random.choice(['Applied', 'In Progress'])
            elif days_since_applied < 14:
                status = random.choice(['Applied', 'In Progress', 'Interview'])
            elif days_since_applied < 30:
                status = random.choice(['Interview', 'Offer', 'Rejected'])
            else:
                status = random.choice(['Offer', 'Rejected', 'Withdrawn'])

            # Create application
            application = {
                'user_id': str(user.id),
                'company': company,
                'position': position,
                'status': status,
                'date_applied': date_applied,
                'notes': f"Sample application for {position} position at {company}",
                'url': f"https://careers.{company.lower()}.com/jobs/{random.randint(1000, 9999)}",
                'deadline': date_applied + timedelta(days=random.randint(7, 30)) if random.random() > 0.5 else None,
                'created_at': datetime.utcnow()
            }

            # Add some random notes and interviews for older applications
            if days_since_applied > 14:
                application['notes_list'] = [
                    {
                        'content': f"Initial application submitted for {position}",
                        'created_at': date_applied
                    }
                ]
                
                if status in ['Interview', 'Offer']:
                    interview_date = date_applied + timedelta(days=random.randint(3, 14))
                    application['interviews'] = [{
                        'id': str(random.randint(1000, 9999)),
                        'date': interview_date,
                        'type': random.choice(['Phone', 'Technical', 'Behavioral', 'Final']),
                        'notes': f"Interview went well. Discussed {random.choice(['system design', 'algorithms', 'past experience', 'team fit'])}"
                    }]

            # Add salary info for some applications
            if random.random() > 0.5:
                application['salary_info'] = {
                    'range': f"${random.randint(80, 200)}k - ${random.randint(200, 400)}k",
                    'currency': 'USD',
                    'type': random.choice(['Full-time', 'Contract', 'Internship'])
                }

            # Add some tags
            application['tags'] = random.sample([
                'Remote', 'Hybrid', 'On-site', 'Entry Level', 'Mid Level', 
                'Senior Level', 'Tech Stack', 'Benefits', '401k', 'Healthcare'
            ], random.randint(2, 5))

            # Insert into database
            JobApplication.create(application)

        print("Added 50 sample applications with past dates")

if __name__ == '__main__':
    add_sample_applications() 