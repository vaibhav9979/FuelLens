# FuelLens – Smart CNG Compliance & Fuel Station Intelligence Platform

FuelLens is a comprehensive, production-ready web application that ensures CNG tank safety compliance, improves fuel station efficiency, and provides real-time insights to vehicle owners, fuel station operators, and administrators.

## Features

- **Authentication & User Management**: Secure login/signup for vehicle owners, operators, and admins
- **Vehicle Registration & Compliance System**: Track CNG compliance status, expiry dates, and compliance history
- **Camera-Based Number Plate Detection**: OCR-based vehicle number plate recognition
- **QR Code Compliance Verification**: Generate and scan QR codes for instant compliance checks
- **Fuel Station Operator Dashboard**: Tools for compliance verification and record keeping
- **Smart Compliance Dashboard**: Real-time compliance status for vehicle owners
- **Auto Reminder & Alert System**: Automated notifications for compliance expiry
- **Nearby CNG Fuel Stations**: Location-based station finder with live load information
- **Live Fuel Station Load System**: Real-time station load tracking
- **Digital Vehicle Document Locker**: Secure storage for vehicle documents
- **Compliance History & Proof**: Complete compliance timeline and export capabilities
- **Fuel Station Rating System**: User rating and review system
- **Admin Dashboard**: Comprehensive management and reporting tools

## Technology Stack

- **Backend**: Python Flask with advanced security features
- **Database**: PostgreSQL (production) / SQLite (development)
- **Frontend**: HTML, CSS, JavaScript with Bootstrap
- **OCR**: Tesseract for number plate recognition
- **QR Codes**: QR code generation and scanning
- **Geolocation**: Geopy for location services
- **Scheduling**: APScheduler for automated tasks
- **Caching**: Redis for session and data caching
- **Background Jobs**: Celery for async processing
- **Security**: Advanced authentication, rate limiting, and encryption

## Production Architecture

- **Database**: PostgreSQL with connection pooling and read replicas
- **Caching**: Redis for sessions and frequently accessed data
- **Load Balancing**: Nginx reverse proxy with SSL termination
- **Application**: Gunicorn WSGI server with multiple workers
- **Background Processing**: Celery with Redis broker
- **Monitoring**: Structured logging with JSON format
- **Security**: Rate limiting, input validation, and threat detection

## Installation

### Development Setup

1. Clone the repository
2. Install Python dependencies:
   ```bash
   pip install -r requirements/development.txt
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. Run database migrations:
   ```bash
   flask db upgrade
   ```

5. Run the application:
   ```bash
   python run.py
   ```

### Production Deployment

1. Use Docker Compose for containerized deployment:
   ```bash
   docker-compose up -d
   ```

2. Or deploy manually with Gunicorn:
   ```bash
   gunicorn --config gunicorn.conf.py run:app
   ```

3. Set up Nginx reverse proxy with SSL

## Configuration

### Environment Variables

- `SECRET_KEY`: Application secret key (required)
- `DATABASE_URL`: Database connection string
- `REDIS_URL`: Redis connection string
- `MAIL_SERVER`: SMTP server for email notifications
- `MAIL_USERNAME`/`MAIL_PASSWORD`: Email credentials
- `ENCRYPTION_KEY`: Key for data encryption
- `TESSERACT_CMD`: Path to Tesseract OCR executable

## Default Credentials

- **Admin**: admin@fuellens.com / admin123

## Project Structure

```
├── app/
│   ├── __init__.py          # Flask app initialization
│   ├── models/              # Database models
│   │   ├── __init__.py      # Model imports
│   │   ├── user.py          # User model
│   │   ├── vehicle.py       # Vehicle model
│   │   ├── station.py       # Station model
│   │   ├── compliance.py    # Compliance records
│   │   ├── document.py      # Document management
│   │   ├── notification.py  # Notification system
│   │   ├── qr_code.py       # QR code management
│   │   ├── rating.py        # Rating system
│   │   └── security_log.py  # Security logging
│   ├── controllers/         # Route handlers
│   │   ├── auth.py          # Authentication
│   │   ├── user.py          # User dashboard
│   │   ├── operator.py      # Operator dashboard
│   │   ├── admin.py         # Admin dashboard
│   │   ├── main.py          # Main routes
│   │   └── stations.py      # Station routes
│   ├── services/            # Business logic
│   │   ├── __init__.py      # Service imports
│   │   ├── security.py      # Security services
│   │   ├── compliance.py    # Compliance services
│   │   └── notifications.py # Notification services
│   ├── utils/               # Utility functions
│   │   ├── __init__.py      # Utility imports
│   │   ├── helpers.py       # Helper functions
│   │   ├── security.py      # Security utilities
│   │   ├── security_middleware.py # Security middleware
│   │   ├── logging_config.py # Logging configuration
│   │   ├── error_handler.py # Error handling
│   │   ├── plate_detector.py # OCR functionality
│   │   ├── qr_generator.py  # QR code generation
│   │   ├── reminder_scheduler.py # Scheduler
│   │   ├── location_service.py # Location services
│   │   └── reporting.py     # Reporting utilities
│   ├── static/              # CSS, JS, images
│   │   ├── css/
│   │   ├── js/
│   │   ├── images/
│   │   └── uploads/
│   └── templates/           # HTML templates
│       ├── auth/
│       ├── user/
│       ├── operator/
│       ├── admin/
│       ├── errors/
│       └── shared/
├── config/                  # Configuration files
│   ├── __init__.py
│   ├── base.py              # Base configuration
│   ├── development.py       # Development config
│   ├── production.py        # Production config
│   └── testing.py           # Testing config
├── migrations/              # Database migrations
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── tests/                   # Test files
├── scripts/                 # Deployment scripts
├── docker/                  # Docker configurations
├── docs/                    # Documentation
├── logs/                    # Log files
├── requirements/
│   ├── base.txt             # Base dependencies
│   ├── development.txt      # Development dependencies
│   ├── production.txt       # Production dependencies
│   └── testing.txt          # Testing dependencies
├── alembic.ini              # Alembic configuration
├── gunicorn.conf.py         # Gunicorn configuration
├── Dockerfile               # Docker configuration
├── docker-compose.yml       # Docker Compose configuration
├── run.py                   # Application entry point
└── README.md
```

## Key Modules

- **Authentication**: Advanced security with rate limiting, account locking, and MFA-ready implementation
- **Vehicle Management**: Comprehensive vehicle registration and compliance tracking
- **Compliance System**: Advanced check recording with multiple verification methods
- **Security**: Rate limiting, input validation, threat detection, and audit logging
- **Background Processing**: Async OCR processing and reminder scheduling
- **Caching**: Redis-based caching for performance optimization
- **Monitoring**: Comprehensive logging and error tracking

## Security Features

- Advanced password policies with 12+ character requirements
- Account locking after 5 failed login attempts
- Rate limiting with sliding window algorithm
- Input sanitization and XSS prevention
- SQL injection prevention with SQLAlchemy ORM
- CSRF protection across all forms
- Secure session management with timeouts
- Data encryption for sensitive information
- Threat detection and security logging
- IP reputation checking

## Performance Optimizations

- Database connection pooling
- Redis caching for sessions and frequently accessed data
- Background job processing for heavy operations
- Optimized OCR processing with image enhancement
- Asset minification and CDN-ready static files
- Query optimization with proper indexing

## Monitoring & Logging

- Structured JSON logging for easy parsing
- Security event logging with severity levels
- Performance metrics collection
- Error tracking with detailed context
- Health check endpoints

## Deployment

### Production Environment

1. Database: PostgreSQL with connection pooling
2. Cache: Redis for sessions and data
3. Application Server: Gunicorn with multiple workers
4. Reverse Proxy: Nginx with SSL termination
5. Background Jobs: Celery with Redis broker
6. Monitoring: Structured logging to centralized system
7. Backup: Automated database backups

### Environment Configuration

- Development: SQLite, debug mode, detailed logging
- Staging: PostgreSQL, limited caching, moderate logging
- Production: PostgreSQL, full caching, security-focused logging

## Testing Strategy

- Unit tests for all business logic
- Integration tests for API endpoints
- Security tests for authentication and authorization
- Performance tests for critical paths
- End-to-end tests for user workflows

## License

This project is created for demonstration purposes.