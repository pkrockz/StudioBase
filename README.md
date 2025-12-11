# StudioBase

**StudioBase** is a comprehensive Internal Operating System for freelancers, agencies, and small studios to manage their entire business workflow from lead generation to invoicing.

## 🌟 Features

### Sales Pipeline Management
- **Lead Management**: Track and nurture potential clients through Cold, Warm, and Hot stages
- **Prospect Pipeline**: Move qualified leads through Discovery, Proposal, Negotiation, and Closing stages with probability tracking
- **Pipeline Value Tracking**: Real-time visualization of your total pipeline value

### Client & Project Management
- **Client Database**: Maintain detailed client information including contracts, billing terms, and status
- **Project Planning**: Create and manage projects with deadlines and status tracking
- **AI-Powered Task Generation**: Leverage Google's Gemini AI to automatically break down project descriptions into actionable tasks
- **Task Management**: Track tasks with status updates, time estimates, and progress monitoring
- **Progress Visualization**: Real-time project progress bars based on task completion

### Financial Management
- **Invoice Generation**: Create professional invoices with automatic numbering
- **Payment Tracking**: Monitor unpaid, overdue, and paid invoices
- **Due Date Management**: Track invoice due dates with overdue alerts
- **Auto-Archive**: Automatically remove clients once all invoices are paid

### Command Dashboard
- **Real-time Metrics**: View active projects, pipeline value, pending tasks, and overdue invoices at a glance
- **Urgent Leads Alert**: Quickly identify cold leads that need attention
- **Active Projects Progress**: Track all ongoing projects with visual progress indicators

### Authentication & Security
- **OAuth Integration**: Secure login with GitHub and Google accounts
- **User Isolation**: All data is user-specific and isolated
- **Session Management**: Secure session handling with Flask

## 🛠 Technology Stack

### Backend
- **Flask**: Python web framework
- **MongoDB**: NoSQL database for flexible data management
- **Flask-PyMongo**: MongoDB integration for Flask
- **Authlib**: OAuth 2.0 authentication library

### AI Integration
- **Google Gemini AI**: Advanced AI model for intelligent task generation

### Frontend
- **Bootstrap 5**: Responsive UI framework
- **Jinja2**: Template engine for dynamic HTML rendering

### Authentication Providers
- GitHub OAuth
- Google OAuth

## 📋 Prerequisites

- Python 3.7 or higher
- MongoDB database (local or cloud instance)
- GitHub OAuth App credentials
- Google OAuth App credentials
- Google Gemini API key

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/pkrockz/StudioBase.git
cd StudioBase
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
# Flask Configuration
FLASK_SECRET_KEY=your-secret-key-here

# MongoDB Configuration
MONGO_URI=mongodb://localhost:27017/studiobase
# Or use MongoDB Atlas: mongodb+srv://username:password@cluster.mongodb.net/studiobase

# GitHub OAuth
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Google Gemini AI
GEMINI_API_KEY=your-gemini-api-key
```

### 5. Configure OAuth Applications

#### GitHub OAuth Setup
1. Go to GitHub Settings → Developer settings → OAuth Apps
2. Create a new OAuth App
3. Set Authorization callback URL to: `http://localhost:5000/authorize/github`
4. Copy Client ID and Client Secret to your `.env` file

#### Google OAuth Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URI: `http://localhost:5000/authorize/google`
6. Copy Client ID and Client Secret to your `.env` file

#### Google Gemini API Setup
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create an API key
3. Add it to your `.env` file

### 6. Run the Application

```bash
python app.py
```

The application will be available at `http://localhost:5000`

## 📖 Usage Guide

### Getting Started

1. **Login**: Access the application and login using GitHub or Google OAuth
2. **Dashboard**: View your command dashboard with all key metrics

### Lead to Client Workflow

#### Step 1: Add a Lead
- Navigate to **Leads** section
- Add new lead with name, company, email, and source
- Leads start in "Cold" status

#### Step 2: Nurture and Convert to Prospect
- Update lead status through Cold → Warm → Hot stages
- Convert hot leads to **Prospects** when ready to propose

#### Step 3: Manage Prospects
- In **Prospects** section, track deals through sales stages
- Update stage: Discovery → Proposal Sent → Negotiating → Verbal Agreement
- Probability automatically adjusts based on stage
- Add expected deal value for pipeline tracking

#### Step 4: Convert to Client
- When deal closes, convert prospect to **Client**
- Contract value carries over from prospect deal value

### Project Management

#### Creating Projects
1. Go to **Projects** section
2. Select a client and add project details
3. Choose to use AI task generation or add tasks manually

#### Using AI Task Generation
- Enable "Use AI to generate tasks" when creating a project
- Gemini AI will analyze your project description
- Automatically creates 3-5 specific technical tasks with time estimates

#### Managing Tasks
- View all tasks in project detail page
- Toggle tasks between Pending and Done
- Edit task descriptions and time estimates
- Add new tasks manually as needed
- Track overall project progress

#### Completing Projects
- Mark project as completed when all work is done
- Automatically redirects to create invoice for the project

### Invoice Management

#### Creating Invoices
- Navigate to **Invoices** section
- Select client and project
- Enter amount and due date
- System generates unique invoice number automatically

#### Tracking Payments
- View all invoices with status indicators
- Mark invoices as paid when payment received
- System tracks overdue invoices automatically
- View detailed invoice information

## 📁 Project Structure

```
StudioBase/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (not in repo)
├── .gitignore            # Git ignore rules
└── templates/            # HTML templates
    ├── base.html         # Base template layout
    ├── login.html        # Login page
    ├── dashboard.html    # Command dashboard
    ├── leads.html        # Lead management
    ├── prospects.html    # Prospect pipeline
    ├── clients.html      # Client database
    ├── projects.html     # Project list
    ├── project_detail.html  # Project details & tasks
    ├── invoices.html     # Invoice management
    └── invoice_view.html # Invoice detail view
```

## 🗄 Database Schema

### Collections

- **users**: User accounts with OAuth information
- **leads**: Potential clients in early stages
- **prospects**: Qualified leads in active sales process
- **clients**: Converted prospects with active contracts
- **projects**: Client projects with status and deadlines
- **tasks**: Individual project tasks with time estimates
- **invoices**: Financial documents with payment tracking

## 🔐 Security Features

- OAuth 2.0 authentication (no password storage)
- Session-based authorization
- User data isolation (all queries filtered by user_id)
- Environment variable protection for sensitive keys
- HTTPS recommended for production deployment

## 🚀 Deployment Tips

### Production Considerations

1. **Set Debug to False**: Change `app.run(debug=False)` in production
2. **Use Production Server**: Deploy with Gunicorn or uWSGI instead of Flask development server
3. **Enable HTTPS**: Use SSL certificates for secure connections
4. **Update OAuth Callbacks**: Configure production URLs in OAuth apps
5. **Secure Environment Variables**: Use proper secrets management
6. **MongoDB Security**: Enable authentication and use connection strings with credentials
7. **Set Production Secret Key**: Generate a secure random secret key

### Example Production Run

```bash
gunicorn --bind 0.0.0.0:8000 app:app
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is available for use under standard open-source practices. Please check with the repository owner for specific licensing terms.

## 🐛 Troubleshooting

### Common Issues

**MongoDB Connection Error**
- Verify MongoDB is running: `mongod --version`
- Check MONGO_URI in `.env` file
- For MongoDB Atlas, ensure IP whitelist is configured

**OAuth Redirect Error**
- Verify callback URLs match exactly in OAuth app settings
- Check client IDs and secrets in `.env` file
- Ensure OAuth apps are not in development/testing mode restrictions

**AI Task Generation Not Working**
- Verify GEMINI_API_KEY is valid
- Check API quota limits
- Review console logs for AI response debugging

**Session Issues**
- Verify FLASK_SECRET_KEY is set
- Clear browser cookies and try again
- Check session configuration

## 📧 Support

For issues, questions, or suggestions, please open an issue on GitHub or contact the repository maintainer.

## 🎯 Roadmap

Future enhancements may include:
- Email notifications for overdue invoices
- Calendar integration for deadlines
- Time tracking functionality
- Team collaboration features
- Reporting and analytics dashboard
- Export capabilities (PDF invoices, CSV reports)
- Mobile responsive improvements
- Dark mode theme

---

**Made with ❤️ for freelancers and small studios**
