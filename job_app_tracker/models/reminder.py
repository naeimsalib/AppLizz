from job_app_tracker.config.mongodb import mongo
from bson.objectid import ObjectId
from datetime import datetime, timedelta

class Reminder:
    def __init__(self, reminder_data):
        self.id = str(reminder_data.get('_id', ''))
        self.user_id = reminder_data.get('user_id')
        self.application_id = reminder_data.get('application_id')
        self.title = reminder_data.get('title')
        self.description = reminder_data.get('description', '')
        self.reminder_date = reminder_data.get('reminder_date')
        self.reminder_type = reminder_data.get('reminder_type')  # 'interview', 'deadline', 'follow_up', etc.
        self.status = reminder_data.get('status', 'pending')  # 'pending', 'completed', 'cancelled'
        self.created_at = reminder_data.get('created_at')
        self.updated_at = reminder_data.get('updated_at')
        self.notification_sent = reminder_data.get('notification_sent', False)

    @staticmethod
    def create(reminder_data):
        """Create a new reminder"""
        reminder_data['created_at'] = datetime.now()
        reminder_data['updated_at'] = datetime.now()
        result = mongo.db.reminders.insert_one(reminder_data)
        reminder_data['_id'] = result.inserted_id
        return Reminder(reminder_data)

    @staticmethod
    def get_by_id(reminder_id, user_id=None):
        """Get reminder by ID, optionally filtering by user_id for security"""
        try:
            query = {'_id': ObjectId(reminder_id)}
            if user_id:
                query['user_id'] = str(user_id)
            reminder_data = mongo.db.reminders.find_one(query)
            return Reminder(reminder_data) if reminder_data else None
        except:
            return None

    @staticmethod
    def get_upcoming_reminders(user_id, days=7):
        """Get upcoming reminders for a user within specified days"""
        now = datetime.now()
        query = {
            'user_id': str(user_id),
            'status': 'pending',
            'reminder_date': {
                '$gte': now,
                '$lte': now + timedelta(days=days)
            }
        }
        reminders = mongo.db.reminders.find(query).sort('reminder_date', 1)
        return [Reminder(reminder) for reminder in reminders]

    def update(self, update_data):
        """Update reminder details"""
        update_data['updated_at'] = datetime.now()
        result = mongo.db.reminders.update_one(
            {'_id': ObjectId(self.id)},
            {'$set': update_data}
        )
        if result.modified_count > 0:
            for key, value in update_data.items():
                setattr(self, key, value)
            return True
        return False

    def delete(self):
        """Delete the reminder"""
        result = mongo.db.reminders.delete_one({'_id': ObjectId(self.id)})
        return result.deleted_count > 0

    def mark_as_completed(self):
        """Mark reminder as completed"""
        return self.update({'status': 'completed'})

    def mark_as_cancelled(self):
        """Mark reminder as cancelled"""
        return self.update({'status': 'cancelled'})

    def mark_notification_sent(self):
        """Mark that notification has been sent for this reminder"""
        return self.update({'notification_sent': True}) 