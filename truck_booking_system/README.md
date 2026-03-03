# Transova - Truck Booking System

A professional Django-based truck booking system for logistics and transportation management.

## Features

### User Roles
- **Customer**: Book trucks, view booking history, make payments
- **Driver**: View assigned jobs, update job status, manage profile
- **Company**: Manage fleet (trucks & drivers), view company bookings, assign drivers
- **Admin**: Full system control, manage users, companies, pricing

### Core Features
- Real-time price calculation with distance-based pricing
- GPS coordinate support for accurate distance calculation
- Multiple truck types (Box Truck, Flatbed, Refrigerated, Tanker, etc.)
- Load type multipliers for different cargo types
- Payment processing (simulated)
- OTP-based email verification
- Role-based access control

## Project Structure

```
truck_booking_system/
├── accounts/          # User authentication & profiles
├── bookings/          # Booking management
│   ├── models.py      # Booking & Payment models
│   ├── views.py       # All booking views
│   ├── utils.py       # Utility functions
│   └── urls.py        # URL routing
├── fleet/             # Fleet management
│   ├── models.py      # Company, Truck, Driver models
│   ├── views.py       # Fleet management views
│   └── urls.py        # URL routing
├── pricing/           # Pricing configuration
├── config/            # Django settings
└── static/            # CSS, JS, images
```

## Setup & Installation

### Prerequisites
- Python 3.8+
- Django 4.0+

### Installation

1. **Clone the repository**
   ```bash
   cd truck_booking_system
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install django
   pip install python-decouple  # For environment variables
   ```

4. **Run migrations**
   ```bash
   python manage.py migrate
   ```

5. **Create superuser (admin)**
   ```bash
   python manage.py createsuperuser
   ```

6. **Run development server**
   ```bash
   python manage.py runserver
   ```

### Environment Variables

Copy `.env.example` to `.env` and configure:

```env
SECRET_KEY=your-secret-key
DEBUG=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

## Pricing Configuration

Pricing is centralized in `config/settings.py`:

```python
BASE_PRICE = 50          # Minimum booking charge (USD)
RATE_PER_KM = 10         # Admin booking rate per km
BASE_RATE_CUSTOMER = 2   # Customer booking rate per km
COMMISSION_RATE = 0.05    # 5% platform commission
```

## API Endpoints

### Public
- `/` - Home page
- `/register/` - User registration
- `/login/` - User login
- `/book/` - Create booking (customer)
- `/faq/` - FAQ page

### Customer
- `/customer-dashboard/` - Customer dashboard
- `/bookings/my-bookings/` - View bookings
- `/bookings/receipt/<id>/` - Booking receipt

### Driver
- `/driver-dashboard/` - Driver dashboard
- `/driver-profile/` - Driver profile
- `/driver/job/<id>/accept/` - Accept job
- `/driver/job/<id>/reject/` - Reject job

### Company
- `/fleet/dashboard/` - Company dashboard
- `/fleet/add-truck/` - Add truck
- `/fleet/add-driver/` - Add driver
- `/fleet/bookings/` - View bookings
- `/fleet/booking/<id>/assign-driver/` - Assign driver

### Admin
- `/admin-dashboard/` - Admin dashboard
- `/admin/users/` - Manage users
- `/admin/trucks/` - Manage trucks
- `/admin/companies/` - Manage companies
- `/admin/drivers/` - Manage drivers
- `/admin/load-types/` - Manage load types
- `/admin/stats/` - System statistics

## Database Indexes

The system includes optimized indexes for common queries:

- **Booking**: booking_date, status, truck, driver, user, created_at
- **Truck**: company, is_available
- **Driver**: user, company, is_available
- **Company**: is_approved

## Security Features

- Role-based access control
- OTP-based email verification
- CSRF protection
- Session security settings
- Password validation
- Input sanitization

## Customization

### Adding New Load Types

```python
# Via Django Admin or code
from pricing.models import LoadType

LoadType.objects.create(
    name="Heavy Machinery",
    price_multiplier=1.5
)
```

### Adding New Truck Types

```python
# In fleet/models.py Truck.TRUCK_TYPES
('new_type', 'New Truck Type'),
```

## License

This project is for educational and demonstration purposes.

## Support

For issues or questions, please contact the development team.

