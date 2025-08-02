# Afro-Nyanka-Tours-backend

A FastAPI-based backend for the Afro Nyanka Tours booking platform. This API handles tour listings, bookings, and automated email notifications for both customers and administrators.

## Features

- **Tour Management**: Browse tours by country/region with detailed information
- **Booking System**: Simple booking process without user authentication
- **Email Notifications**: Automated confirmation emails for customers and admin notifications
- **PostgreSQL Database**: Robust data storage with Alembic migrations
- **Docker Support**: Containerized application for easy deployment
- **Google SMTP Integration**: Professional email delivery

## Tech Stack

- **FastAPI**: Modern, fast web framework for building APIs
- **PostgreSQL**: Robust relational database
- **SQLAlchemy**: Python SQL toolkit and ORM
- **Alembic**: Database migration tool
- **Docker & Docker Compose**: Containerization
- **Pydantic**: Data validation using Python type annotations
- **Jinja2**: Email template engine

## Project Structure

```
├── src/
│   ├── api/
│   │   └── routes/
│   │       ├── tours.py          # Tour-related endpoints
│   │       └── bookings.py       # Booking-related endpoints
│   ├── core/
│   │   └── config.py             # Application configuration
│   ├── crud/
│   │   └── crud.py               # Database operations
│   ├── database/
│   │   └── database.py           # Database connection setup
│   ├── models/
│   │   └── models.py             # SQLAlchemy models
│   ├── schemas/
│   │   └── schemas.py            # Pydantic schemas
│   ├── services/
│   │   └── email_service.py      # Email handling
│   └── main.py                   # FastAPI application
├── alembic/                      # Database migrations
├── docker-compose.yaml
├── DockerFile
├── requirements.txt
└── populate_data.py              # Script to populate predefined data
```

## API Endpoints

### Tours
- `GET /api/tours/` - Get all tours
- `GET /api/tours/{tour_id}` - Get specific tour
- `GET /api/tours/country/{country}` - Get tours by country
- `POST /api/tours/` - Create new tour (admin)
- `GET /api/tours/locations/` - Get all locations
- `POST /api/tours/locations/` - Create new location (admin)

### Bookings
- `POST /api/bookings/` - Create new booking
- `GET /api/bookings/{booking_id}` - Get booking by ID
- `GET /api/bookings/` - Get all bookings (admin)

## Setup Instructions

### Prerequisites
- Docker and Docker Compose
- Git

### 1. Clone the Repository
```bash
git clone <repository-url>
cd Afro-Nyanka-Tours-backend
```

### 2. Environment Configuration
```bash
cp .env.example .env
```

Edit `.env` file with your configuration:
```env
SMTP_USERNAME=your_gmail@gmail.com
SMTP_PASSWORD=your_app_password
ADMIN_EMAIL=admin@afro-nyanka-tours.com
DATABASE_URL=postgresql://afro_user:afro_password@localhost:5432/afro_tours_db
DEBUG=True
SECRET_KEY=your-secret-key-here-change-in-production
```

**Note**: For Gmail SMTP, you need to:
1. Enable 2-factor authentication on your Gmail account
2. Generate an App Password (not your regular password)
3. Use the App Password in the `SMTP_PASSWORD` field

### 3. Start the Application
```bash
docker-compose up --build
```

This will:
- Start PostgreSQL database
- Build and run the FastAPI application
- Make the API available at `http://localhost:8000`

### 4. Initialize Database
```bash
# Run database migrations
docker-compose exec web alembic upgrade head

# Populate with predefined tour data
docker-compose exec web python populate_data.py
```

### 5. Access the Application
- **API Documentation**: `http://localhost:8000/docs`
- **API**: `http://localhost:8000`
- **Health Check**: `http://localhost:8000/health`

## Development

### Running Locally (without Docker)
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
export DATABASE_URL="postgresql://afro_user:afro_password@localhost:5432/afro_tours_db"
export SMTP_USERNAME="your_gmail@gmail.com"
export SMTP_PASSWORD="your_app_password"
export ADMIN_EMAIL="admin@afro-nyanka-tours.com"

# Run database migrations
alembic upgrade head

# Populate predefined data
python populate_data.py

# Start the server
uvicorn src.main:app --reload
```

### Database Migrations
```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## Tour Data

The application comes with predefined tours based on `predefined_data.md`:

### Ghana Tours
1. **Accra City Tours** - Historical sites, museums, cultural centers
2. **Cape Coast Tours** - Slave trade history, castles, canopy walk
3. **Kumasi City Tour** - Ashanti Kingdom cultural sites
4. **Savannah Region Tour** - Mole National Park wildlife safari

### International Tours
5. **Togo Tours** - Voodoo culture experience
6. **Burkina Faso Tours** - Traditional West African culture
7. **East Africa Tours** - Kenya safari, Ethiopia cultural journey
8. **South Africa Tours** - Wine tours, cultural experiences, Lesotho adventures

## Email System

The system sends two types of emails upon booking:

1. **Customer Confirmation Email**: 
   - Booking details and reference number
   - Tour information
   - Next steps

2. **Admin Notification Email**:
   - Customer contact information
   - Complete booking details
   - Action required notification

## API Usage Examples

### Get All Tours
```bash
curl -X GET "http://localhost:8000/api/tours/"
```

### Create a Booking
```bash
curl -X POST "http://localhost:8000/api/bookings/" \
  -H "Content-Type: application/json" \
  -d '{
    "tour_id": 1,
    "customer_name": "John Doe",
    "customer_email": "john@example.com",
    "customer_age": 30,
    "customer_country": "USA",
    "preferred_date": "2024-06-15T00:00:00",
    "additional_services": "Airport pickup required"
  }'
```

### Get Tours by Country
```bash
curl -X GET "http://localhost:8000/api/tours/country/Ghana"
```

## Security Considerations

- **Production Environment**: 
  - Change default database credentials
  - Use strong secret keys
  - Enable HTTPS
  - Configure CORS properly
  - Use environment variables for sensitive data

- **Email Security**:
  - Use App Passwords for Gmail
  - Store credentials securely
  - Monitor email sending limits

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For support or questions, please contact the development team or create an issue in the repository.

## License

This project is licensed under the MIT License - see the LICENSE file for details.