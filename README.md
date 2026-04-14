# Employee Assistant AI

An AI-powered Employee Assistant System that helps with internal operations by handling employee queries, managing tasks, processing emails, analyzing logs, and automating notifications.

## Features

### 1. Natural Language Processing
- **Intent Recognition**: Understands what employees want to do
- **Entity Extraction**: Pulls out important information (dates, names, tasks)
- **Response Generation**: Creates human-like responses
- **Email Content Analysis**: Understands email content for automation

### 2. Task Management
- **Create Tasks**: Add tasks with natural language or through API
- **Assign Tasks**: Assign tasks to team members
- **Track Progress**: Monitor task status and completion
- **Priority Management**: Set and track task priorities
- **Due Date Tracking**: Monitor deadlines and overdue tasks

### 3. Email Processing
- **IMAP Integration**: Fetch emails from your email server
- **Content Analysis**: AI-powered email analysis
- **Task Creation**: Automatically create tasks from email action items
- **Auto-Reply**: Generate and send automatic responses
- **Email Summarization**: Get summaries of email batches

### 4. System Monitoring
- **Log Analysis**: Process system logs for insights
- **Health Monitoring**: Track system health and performance
- **Automated Alerts**: Send notifications based on rules

### 5. Notification System
- **Automated Notifications**: Send alerts and updates
- **Email Notifications**: Integrate with email system
- **Custom Triggers**: Set up custom notification rules

## How It Works

### High-Level Architecture

```
Employee Assistant AI
    |
    |-- FastAPI Backend (REST API)
    |   |-- Task Management API
    |   |-- Email Processing API
    |   |-- AI Processing Core
    |   |-- Database Layer (SQLAlchemy)
    |
    |-- AI Core
    |   |-- Natural Language Understanding
    |   |-- Intent Recognition
    |   |-- Entity Extraction
    |   |-- Response Generation
    |
    |-- Services
    |   |-- Email Service (IMAP/SMTP)
    |   |-- Task Manager
    |   |-- Notification Service
    |
    |-- Database
    |   |-- SQLite (default)
    |   |-- PostgreSQL/MySQL (optional)
```

### Workflow Example

1. **Employee Query**: "Create a task to review Q3 reports by Friday and assign it to John"
2. **AI Processing**: System analyzes the natural language input
3. **Intent Detection**: Identifies this as a "create_task" intent
4. **Entity Extraction**: Extracts:
   - Task: "review Q3 reports"
   - Due date: "Friday"
   - Assignee: "John"
5. **Task Creation**: Creates task in database with extracted information
6. **Confirmation**: Returns human-like response confirming task creation

## Installation

### Prerequisites
- Python 3.8+
- pip or poetry

### Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd employee-assistant-AI
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Install spaCy language model**
```bash
python -m spacy download en_core_web_sm
```

5. **Run the application**
```bash
python main.py
```

The application will start on `http://localhost:8000`

## Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Database Configuration
DATABASE_URL=sqlite:///./employee_assistant.db

# Email Configuration
EMAIL_HOST=imap.gmail.com
EMAIL_PORT=993
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587

# OpenAI API (for advanced AI processing)
OPENAI_API_KEY=your-openai-api-key

# Application Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
```

### Email Setup

For Gmail, you'll need to:
1. Enable 2-factor authentication
2. Create an app password
3. Use the app password in your `.env` file

## API Documentation

Once the application is running, visit `http://localhost:8000/docs` for interactive API documentation.

### Main API Endpoints

#### Task Management
- `POST /api/v1/tasks/` - Create a new task
- `POST /api/v1/tasks/from-text` - Create task from natural language
- `GET /api/v1/tasks/` - Get all tasks (with filtering)
- `GET /api/v1/tasks/{task_id}` - Get specific task
- `PUT /api/v1/tasks/{task_id}` - Update task
- `DELETE /api/v1/tasks/{task_id}` - Delete task
- `GET /api/v1/tasks/overdue/` - Get overdue tasks
- `GET /api/v1/tasks/statistics/` - Get task statistics

#### Email Processing
- `POST /api/v1/emails/fetch` - Fetch emails from server
- `POST /api/v1/emails/analyze` - Analyze email content
- `POST /api/v1/emails/send` - Send an email
- `GET /api/v1/emails/summary` - Get email summary
- `POST /api/v1/emails/auto-reply` - Generate and send auto-reply

## Usage Examples

### Creating Tasks with Natural Language

```bash
curl -X POST "http://localhost:8000/api/v1/tasks/from-text" \
  -H "Content-Type: application/json" \
  -d '"Create a task to review the Q3 financial reports by Friday and assign it to Sarah with high priority"'
```

### Fetching and Analyzing Emails

```bash
curl -X POST "http://localhost:8000/api/v1/emails/fetch" \
  -H "Content-Type: application/json" \
  -d '{
    "folder": "INBOX",
    "limit": 10,
    "since_days": 7
  }' \
  --data-binary @email_config.json
```

### Getting Task Statistics

```bash
curl -X GET "http://localhost:8000/api/v1/tasks/statistics/"
```

## Project Structure

```
employee-assistant-AI/
    |
    |-- app/
    |   |-- api/                 # API endpoints
    |   |   |-- tasks.py         # Task management API
    |   |   |-- emails.py        # Email processing API
    |   |   |-- __init__.py
    |   |
    |   |-- core/                # Core AI functionality
    |   |   |-- ai_processor.py  # Natural language processing
    |   |
    |   |-- models/              # Data models
    |   |   |-- task.py          # Task model and manager
    |   |
    |   |-- services/            # Business logic services
    |   |   |-- email_service.py # Email processing service
    |   |
    |   |-- database/            # Database configuration
    |   |   |-- database.py      # SQLAlchemy setup
    |   |
    |   |-- utils/               # Utility functions
    |   |-- __init__.py
    |
    |-- main.py                  # FastAPI application entry point
    |-- requirements.txt         # Python dependencies
    |-- .env.example            # Environment variables template
    |-- README.md               # This file
```

## Technology Stack

- **Backend**: FastAPI (Python web framework)
- **Database**: SQLAlchemy ORM with SQLite (default)
- **AI/NLP**: spaCy, NLTK, OpenAI API (optional)
- **Email**: IMAP/SMTP libraries
- **API Documentation**: FastAPI automatic docs (Swagger/OpenAPI)

## Development

### Running Tests
```bash
# Add test commands when implemented
python -m pytest tests/
```

### Code Style
This project follows PEP 8 style guidelines. Use tools like:
- `black` for code formatting
- `flake8` for linting
- `mypy` for type checking

### Adding New Features

1. **Create Models**: Define data models in `app/models/`
2. **Implement Services**: Add business logic in `app/services/`
3. **Create API Endpoints**: Add REST endpoints in `app/api/`
4. **Update Documentation**: Update README and API docs

## Security Considerations

- Store sensitive credentials in environment variables
- Use app passwords for email access (not regular passwords)
- Implement proper authentication in production
- Validate all input data
- Use HTTPS in production

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Check DATABASE_URL in .env file
   - Ensure database directory is writable

2. **Email Connection Failed**
   - Verify email credentials
   - Check if app password is enabled (Gmail)
   - Ensure IMAP is enabled in email settings

3. **AI Processing Not Working**
   - Check OpenAI API key if using advanced features
   - Ensure spaCy model is installed

### Logs

Check application logs for detailed error information. Logs are printed to console and can be configured to write to files.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is created for educational purposes. Please check the license file for details.

## Support

For questions and support:
- Check the API documentation at `/docs`
- Review the troubleshooting section
- Check the application logs for detailed error information

---

**Note**: This is a prototype system designed for demonstration. For production use, additional security, error handling, and scalability considerations should be implemented.
