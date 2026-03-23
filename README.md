# 🧞‍♂️ GastoGenie: AI-Powered Financial Planning System

**GastoGenie** is a high-performance, full-stack financial management application that transcends traditional expense tracking. By leveraging the power of **Google Gemini AI**, it provides users with a multimodal experience, predictive financial analysis, and strategic savings management.

---

## 🚀 Key Features

### 🔮 1. Genie Analysis (AI-Driven Predictions)
Utilizes Large Language Models (LLM) to perform deep analysis of user financial data:
- **Predictive Balancing**: Projects end-of-month cash flow based on real-time spending velocity.
- **"Gasto Hormiga" Detection**: Automatically identifies small, recurring leaks in the budget and calculates the potential annual savings if eliminated.
- **Strategic Advisory**: Generates personalized, motivational financial advice based on active savings goals.

### 📸 2. Multimodal Receipt Processing
- Integrated **OCR & IA Scan**: Users can upload photos or PDFs of receipts.
- **Auto-Categorization**: Gemini automatically detects if a document is a salary slip (Income) or a commercial receipt (Expense), extracting amounts, dates, and merchants with high precision.

### 📊 3. Interactive Financial Dashboard
- **Real-Time KPIs**: Instant visibility of Total Income, Fixed Expenses, and Real Disposable Balance.
- **Dynamic Charting**: Multi-colored Doughnut and Bar charts (using Chart.js) for category distribution and monthly income vs. expense comparisons.
- **Visual Budgeting**: Progress bars that dynamically change color as users approach or exceed category limits.

### 🏆 4. Savings Goals Management
- Dedicated system for defining and tracking long-term financial milestones.
- Real-time progress tracking with a one-click funding system.

---

## 🛠️ Technical Stack

### **Backend (Python / Flask)**
- **Framework**: Flask (RESTful API architecture).
- **Database**: SQLAlchemy (ORM) with SQLite/PostgreSQL support.
- **AI Integration**: Google Generative AI (Gemini 2.5 Flash) for multimodal analysis and natural language processing.
- **Security**: Secure file handling via Werkzeug and environment-based configuration (python-dotenv).

### **Frontend (Vue.js 3 / Vite)**
- **Framework**: Vue 3 (Composition API) for a reactive and modular UI.
- **Styling**: Vanilla CSS with custom design tokens for a premium "Glassmorphism" aesthetic.
- **Data Visualization**: Vue-chartjs & Chart.js for responsive, interactive datasets.
- **State Management**: Reactive refs and computed properties for real-time dashboard updates.

---

## 📂 Project Structure

```text
├── backend/
│   ├── app.py             # Core Flask application & API Endpoints
│   ├── uploads/           # Secure storage for scanned receipts
│   └── requirements.txt   # Backend dependencies
├── frontend/
│   ├── src/
│   │   ├── App.vue        # Main Application Logic & UI
│   │   ├── main.js        # Entry point
│   │   └── main.css       # Custom Design System
│   └── package.json       # Frontend dependencies
└── README.md              # Documentation
```

---

## ⚙️ Installation & Setup

### 1. Prerequisites
- Python 3.10+
- Node.js 16+
- Gemini API Key ([Get one here](https://aistudio.google.com/))

### 2. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
pip install -r requirements.txt
# Create .env file with:
# GEMINI_API_KEY=your_key_here
# DATABASE_URL=sqlite:///gastogenie.db
python app.py
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## 📧 Contact & Portfolio
This project was developed as a showcase of Full-Stack craftsmanship, AI integration, and user-centric design. 

**Developed with ❤️ by [Your Name/Jaiime7]**
