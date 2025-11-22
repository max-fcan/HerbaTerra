# HerbaTerra

A dynamic Flask web application for herbal knowledge and natural remedies.

## Project Structure

```
HerbaTerra/
├── app/
│   ├── __init__.py           # Application factory
│   ├── routes.py             # Route blueprints
│   ├── templates/            # HTML templates
│   │   ├── base.html        # Base template
│   │   ├── index.html       # Home page
│   │   └── about.html       # About page
│   └── static/              # Static files
│       ├── css/
│       │   └── style.css    # Stylesheets
│       ├── js/
│       │   └── main.js      # JavaScript
│       └── images/          # Image assets
├── config/
│   └── config.py            # Configuration settings
├── run.py                    # Application entry point
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables
├── .flaskenv                 # Flask environment file
└── README.md                 # Project documentation
```

## Installation

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd HerbaTerra
   ```

2. Create a virtual environment:

   ```bash
   python -m venv venv
   venv\Scripts\activate  # On Windows
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:

   ```bash
   python run.py
   ```

5. Open your browser and navigate to `http://localhost:5000`

## Features

- Dynamic route handling with Flask blueprints
- Responsive HTML templates with Jinja2
- CSS styling with responsive design
- RESTful API endpoints
- Configuration management for different environments
- Static file serving (CSS, JavaScript, Images)

## Configuration

Configuration is managed in `config/config.py` with support for:

- Development
- Testing
- Production

Set environment variables in `.env` file.

## API Endpoints

- `GET /` - Home page

## Technologies Used

- Flask 2.3.3
- Python 3.x
- HTML5
- CSS3
- JavaScript
