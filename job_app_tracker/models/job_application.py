from datetime import datetime
from job_app_tracker.config.mongodb import mongo
from bson import ObjectId

class JobApplication:
    def __init__(self, data):
        self.id = str(data.get('_id', ''))
        self.user_id = data.get('user_id', '')
        self.company = data.get('company', '')
        self.position = data.get('position', '')
        self.status = data.get('status', 'Applied')
        self.date_applied = data.get('date_applied', datetime.now())
        self.url = data.get('url', '')
        self.deadline = data.get('deadline')
        self.notes = data.get('notes', '')
        self.notes_list = data.get('notes_list', [])
        self.interviews = data.get('interviews', [])
        self.salary_info = data.get('salary_info', {})
        self.tags = data.get('tags', [])
        self.created_at = data.get('created_at', datetime.utcnow())
        self.updated_at = data.get('updated_at', datetime.utcnow())

    @classmethod
    def create(cls, data):
        data['created_at'] = datetime.utcnow()
        data['updated_at'] = datetime.utcnow()
        result = mongo.db.applications.insert_one(data)
        data['_id'] = result.inserted_id
        return cls(data)

    @classmethod
    def get_by_id(cls, application_id, user_id):
        data = mongo.db.applications.find_one({
            '_id': ObjectId(application_id),
            'user_id': str(user_id)
        })
        return cls(data) if data else None

    def update(self, data):
        data['updated_at'] = datetime.utcnow()
        result = mongo.db.applications.update_one(
            {'_id': ObjectId(self.id)},
            {'$set': data}
        )
        if result.modified_count > 0:
            for key, value in data.items():
                setattr(self, key, value)
            return True
        return False

    def add_note(self, content):
        note = {
            'content': content,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        self.notes_list.append(note)
        return self.update({'notes_list': self.notes_list})

    def update_note(self, note_id, content):
        for note in self.notes_list:
            if str(note.get('id')) == str(note_id):
                note['content'] = content
                note['updated_at'] = datetime.utcnow()
                return self.update({'notes_list': self.notes_list})
        return False

    def delete_note(self, note_id):
        self.notes_list = [note for note in self.notes_list if str(note.get('id')) != str(note_id)]
        return self.update({'notes_list': self.notes_list})

    def add_interview(self, date, interview_type, notes):
        interview = {
            'id': str(ObjectId()),
            'date': date,
            'type': interview_type,
            'notes': notes,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        self.interviews.append(interview)
        return self.update({'interviews': self.interviews})

    def edit_interview(self, interview_id, date, interview_type, notes):
        for interview in self.interviews:
            if interview.get('id') == interview_id:
                interview.update({
                    'date': date,
                    'type': interview_type,
                    'notes': notes,
                    'updated_at': datetime.utcnow()
                })
                return self.update({'interviews': self.interviews})
        return False

    def delete_interview(self, interview_id):
        self.interviews = [i for i in self.interviews if i.get('id') != interview_id]
        return self.update({'interviews': self.interviews})

    def add_document(self, name, file_path, file_type, size):
        document = {
            'id': str(ObjectId()),
            'name': name,
            'file_path': file_path,
            'file_type': file_type,
            'size': size,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        if not hasattr(self, 'documents'):
            self.documents = []
        self.documents.append(document)
        return self.update({'documents': self.documents})

    def delete_document(self, document_id):
        if not hasattr(self, 'documents'):
            return False
        self.documents = [d for d in self.documents if d.get('id') != document_id]
        return self.update({'documents': self.documents}) 