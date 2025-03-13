from job_app_tracker.config.mongodb import mongo
from bson.objectid import ObjectId
from datetime import datetime

class Application:
    def __init__(self, app_data):
        self.id = str(app_data.get('_id', ''))
        self.user_id = app_data.get('user_id')
        self.company = app_data.get('company')
        self.position = app_data.get('position')
        self.status = app_data.get('status')
        self.date_applied = app_data.get('date_applied')
        self.url = app_data.get('url')
        self.deadline = app_data.get('deadline')
        self.company_logo = app_data.get('company_logo')
        self.notes = app_data.get('notes', '')
        
        # New fields for enhanced functionality
        self.notes_list = app_data.get('notes_list', [])
        self.documents = app_data.get('documents', [])
        self.contacts = app_data.get('contacts', [])
        self.interviews = app_data.get('interviews', [])
        self.salary_info = app_data.get('salary_info', {})
        self.created_at = app_data.get('created_at')
        self.updated_at = app_data.get('updated_at')
        self.source = app_data.get('source', 'manual')  # manual, email, etc.
        self.email_ids = app_data.get('email_ids', [])  # IDs of related emails
        self.tags = app_data.get('tags', [])
    
    @staticmethod
    def get_by_id(app_id, user_id=None):
        """Get application by ID, optionally filtering by user_id for security"""
        try:
            query = {'_id': ObjectId(app_id)}
            if user_id:
                query['user_id'] = str(user_id)
                
            app_data = mongo.db.applications.find_one(query)
            return Application(app_data) if app_data else None
        except:
            return None
    
    @staticmethod
    def get_all_for_user(user_id, filters=None, sort=None):
        """Get all applications for a user with optional filtering and sorting"""
        query = {'user_id': str(user_id)}
        
        # Apply additional filters if provided
        if filters:
            for key, value in filters.items():
                query[key] = value
        
        # Default sort by date applied descending
        sort_params = sort if sort else [('date_applied', -1)]
        
        apps_data = mongo.db.applications.find(query).sort(sort_params)
        return [Application(app) for app in apps_data]
    
    @staticmethod
    def create(app_data):
        """Create a new application"""
        # Add timestamps
        app_data['created_at'] = datetime.now()
        app_data['updated_at'] = datetime.now()
        
        # Initialize notes list if not present
        if 'notes' in app_data and app_data['notes'] and 'notes_list' not in app_data:
            app_data['notes_list'] = [{
                'content': app_data['notes'],
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }]
        
        result = mongo.db.applications.insert_one(app_data)
        app_data['_id'] = result.inserted_id
        return Application(app_data)
    
    def update(self, updates):
        """Update an application"""
        # Add updated timestamp
        updates['updated_at'] = datetime.now()
        
        # Handle notes updates
        if 'notes' in updates and updates['notes'] != self.notes:
            # If notes_list doesn't exist yet, create it
            if not self.notes_list:
                updates['notes_list'] = []
                
                # Add the old note if it exists
                if self.notes:
                    updates['notes_list'].append({
                        'content': self.notes,
                        'created_at': self.created_at or datetime.now(),
                        'updated_at': self.created_at or datetime.now()
                    })
            
            # Add the new note
            if updates['notes']:
                updates['notes_list'] = updates.get('notes_list', self.notes_list or [])
                updates['notes_list'].append({
                    'content': updates['notes'],
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                })
        
        mongo.db.applications.update_one(
            {'_id': ObjectId(self.id)},
            {'$set': updates}
        )
        
        # Update local attributes
        for key, value in updates.items():
            setattr(self, key, value)
        
        return self
    
    def add_note(self, content):
        """Add a note to the application"""
        note = {
            'id': str(ObjectId()),
            'content': content,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        mongo.db.applications.update_one(
            {'_id': ObjectId(self.id)},
            {
                '$push': {'notes_list': note},
                '$set': {
                    'notes': content,  # Update the main notes field too
                    'updated_at': datetime.now()
                }
            }
        )
        
        # Update local attributes
        if not self.notes_list:
            self.notes_list = []
        self.notes_list.append(note)
        self.notes = content
        self.updated_at = note['updated_at']
        
        return note
    
    def update_note(self, note_id, content):
        """Update a specific note"""
        mongo.db.applications.update_one(
            {'_id': ObjectId(self.id), 'notes_list.id': note_id},
            {
                '$set': {
                    'notes_list.$.content': content,
                    'notes_list.$.updated_at': datetime.now(),
                    'updated_at': datetime.now()
                }
            }
        )
        
        # Update local attributes
        for note in self.notes_list:
            if note['id'] == note_id:
                note['content'] = content
                note['updated_at'] = datetime.now()
                break
        
        # Update the main notes field with the most recent note
        if self.notes_list:
            self.notes = self.notes_list[-1]['content']
        
        self.updated_at = datetime.now()
        
        return True
    
    def delete_note(self, note_id):
        """Delete a specific note"""
        mongo.db.applications.update_one(
            {'_id': ObjectId(self.id)},
            {
                '$pull': {'notes_list': {'id': note_id}},
                '$set': {'updated_at': datetime.now()}
            }
        )
        
        # Update local attributes
        self.notes_list = [note for note in self.notes_list if note['id'] != note_id]
        
        # Update the main notes field with the most recent note
        if self.notes_list:
            self.notes = self.notes_list[-1]['content']
        else:
            self.notes = ''
        
        self.updated_at = datetime.now()
        
        return True
    
    def add_document(self, name, file_path, file_type, size):
        """Add a document to the application"""
        document = {
            'id': str(ObjectId()),
            'name': name,
            'file_path': file_path,
            'file_type': file_type,
            'size': size,
            'uploaded_at': datetime.now()
        }
        
        mongo.db.applications.update_one(
            {'_id': ObjectId(self.id)},
            {
                '$push': {'documents': document},
                '$set': {'updated_at': datetime.now()}
            }
        )
        
        # Update local attributes
        if not self.documents:
            self.documents = []
        self.documents.append(document)
        self.updated_at = document['uploaded_at']
        
        return document
    
    def delete_document(self, document_id):
        """Delete a document"""
        mongo.db.applications.update_one(
            {'_id': ObjectId(self.id)},
            {
                '$pull': {'documents': {'id': document_id}},
                '$set': {'updated_at': datetime.now()}
            }
        )
        
        # Update local attributes
        self.documents = [doc for doc in self.documents if doc['id'] != document_id]
        self.updated_at = datetime.now()
        
        return True
    
    def add_interview(self, date, interview_type, notes=None):
        """Add an interview to the application"""
        interview = {
            'id': str(ObjectId()),
            'date': date,
            'type': interview_type,
            'notes': notes,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        mongo.db.applications.update_one(
            {'_id': ObjectId(self.id)},
            {
                '$push': {'interviews': interview},
                '$set': {'updated_at': datetime.now()}
            }
        )
        
        # Update local attributes
        if not self.interviews:
            self.interviews = []
        self.interviews.append(interview)
        self.updated_at = interview['created_at']
        
        return interview
    
    def delete_interview(self, interview_id):
        """Delete an interview"""
        mongo.db.applications.update_one(
            {'_id': ObjectId(self.id)},
            {
                '$pull': {'interviews': {'id': interview_id}},
                '$set': {'updated_at': datetime.now()}
            }
        )
        
        # Update local attributes
        self.interviews = [i for i in self.interviews if i.get('id') != interview_id]
        self.updated_at = datetime.now()
        
        return True
    
    def delete(self):
        """Delete the application"""
        result = mongo.db.applications.delete_one({'_id': ObjectId(self.id)})
        return result.deleted_count > 0
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'company': self.company,
            'position': self.position,
            'status': self.status,
            'date_applied': self.date_applied,
            'url': self.url,
            'deadline': self.deadline,
            'company_logo': self.company_logo,
            'notes': self.notes,
            'notes_list': self.notes_list,
            'documents': self.documents,
            'contacts': self.contacts,
            'interviews': self.interviews,
            'salary_info': self.salary_info,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'source': self.source,
            'email_ids': self.email_ids,
            'tags': self.tags
        } 