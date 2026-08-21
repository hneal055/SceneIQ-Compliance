# 📖 SceneIQ - User Manual

> **Tax Incentive Intelligence for Film & TV Productions**  
> Complete guide to the SceneIQ platform

**Version:** 1.1.0  
**Last Updated:** February 3, 2026  
**Product Name:** SceneIQ

---

## 📚 Documentation Index

This user manual is organized into focused guides for easy navigation:

### **Getting Started**
- [Introduction](#introduction)
- [System Requirements](#system-requirements)
- [Installation & Setup](#installation--setup)
- [Quick Start](#quick-start)

### **User Guides**
- [Frontend Guide](./FRONTEND_GUIDE.md) - Complete UI walkthrough
- [Calculator Guide](./CALCULATOR_GUIDE.md) - Tax incentive calculations
- [Reports Guide](./REPORTS_GUIDE.md) - PDF & Excel exports

### **Developer Guides**
- [API Guide](./API_GUIDE.md) - RESTful API documentation
- [Data Management Guide](./DATA_MANAGEMENT_GUIDE.md) - CRUD operations

### **Support**
- [Troubleshooting Guide](./TROUBLESHOOTING_GUIDE.md) - Common issues
- [FAQ](./FAQ.md) - Frequently asked questions
- [Best Practices](./BEST_PRACTICES.md) - Tips and recommendations

---

## 🎬 Introduction

### **What is SceneIQ?**

SceneIQ is a comprehensive tax incentive calculation and compliance platform designed specifically for the global film and television production industry. It helps producers, line producers, and production accountants:

- **Compare tax incentives** across 32+ global jurisdictions
- **Calculate potential savings** with precision and compliance
- **Track productions** and manage budgets effectively
- **Generate professional reports** for stakeholders and investors
- **Ensure compliance** with jurisdiction-specific requirements

### **Key Features**

✅ **32 Global Jurisdictions** - USA, Canada, UK, Ireland, Australia, New Zealand, and more  
✅ **33 Incentive Programs** - State credits, federal rebates, provincial programs  
✅ **Multi-Currency Support** - Automatic currency conversion  
✅ **Stackable Credits** - Calculate base + bonus incentives  
✅ **Compliance Verification** - Automated requirement checking  
✅ **Professional Reports** - PDF and Excel exports  
✅ **Modern React UI** - Intuitive, responsive interface  
✅ **RESTful API** - Full programmatic access

### **Who Should Use SceneIQ?**

- **Production Managers** - Planning shooting locations
- **Line Producers** - Budgeting and cost analysis
- **Production Accountants** - Tax credit calculations and compliance
- **Developers** - API integration and automation
- **Investors** - ROI analysis and incentive maximization

---

## 💻 System Requirements

### **For Users (Frontend Only)**
- Modern web browser (Chrome 90+, Firefox 88+, Safari 14+, Edge 90+)
- Internet connection
- Screen resolution: 1280x720 minimum (responsive to mobile)

### **For Developers (Full Stack)**
- **Backend:** Python 3.12+
- **Frontend:** Node.js 20+, npm 10+
- **Database:** PostgreSQL 16+
- **Operating System:** Windows 10/11, macOS 12+, or Linux (Ubuntu 20.04+)

---

## 🚀 Installation & Setup

### **Option 1: Production Deployment**

Simply visit:
```
https://pilotforge.onrender.com
```

No installation required!

### **Option 2: Local Development - Full Stack**

**Linux/macOS:**
```bash
git clone https://github.com/hneal055/Tax_Incentive_Compliance_Platform.git
cd Tax_Incentive_Compliance_Platform
./start-fullstack.sh
```

**Windows:**
```powershell
git clone https://github.com/hneal055/Tax_Incentive_Compliance_Platform.git
cd Tax_Incentive_Compliance_Platform
.\(start-fullstack.ps1
```

**Access:**
- Frontend UI: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### **Option 3: Backend Only**

```bash
# Create virtual environment
python -m venv .venv

# Activate (Linux/macOS)
source .venv/bin/activate

# Activate (Windows)
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Generate Prisma client
python -m prisma generate

# Run migrations
python -m prisma migrate deploy

# Start server
python -m uvicorn src.main:app --reload
```

### **Option 4: Frontend Only**

```bash
cd frontend
npm install
npm run dev
```

**Note:** Requires backend to be running.

---

## ⚡ Quick Start

### **Your First Calculation (5 minutes)**

**Step 1: Create a Production**
1. Go to http://localhost:3000/productions
2. Click "Create New Production"
3. Fill in:
   - Title: "My Feature Film"
   - Type: Feature Film
   - Budget: $5,000,000
   - Jurisdiction: California
   - Start Date: June 1, 2026
4. Click "Create Production"

**Step 2: Calculate Tax Incentive**
1. Go to Calculator page
2. Select "My Feature Film"
3. Select "California"
4. Click "Calculate Tax Incentive"
5. View result: ~$1,000,000 (20%)

**Step 3: Compare Jurisdictions**
1. Click "Compare More"
2. Add Georgia and Louisiana
3. See which offers best savings

**Step 4: Generate Report**
1. Click "Generate Report"
2. Choose PDF or Excel
3. Share with stakeholders

**Congratulations!** You've completed your first tax incentive calculation.

---

## 📖 Detailed Documentation

For detailed information on each component, see the specialized guides:

### **[Frontend Guide](./FRONTEND_GUIDE.md)**
Complete walkthrough of the user interface including:
- Dashboard navigation
- Productions management
- Jurisdictions browser
- Calculator usage
- UI components and features

### **[Calculator Guide](./CALCULATOR_GUIDE.md)**
Tax incentive calculation features:
- Simple calculator
- Multi-jurisdiction comparison
- Compliance verification
- Stackable credits
- Scenario modeling
- Date-based rules

### **[Reports Guide](./REPORTS_GUIDE.md)**
Professional documentation:
- PDF comparison reports
- PDF compliance reports
- Excel workbooks
- Custom exports

### **[API Guide](./API_GUIDE.md)**
RESTful API documentation:
- Endpoints reference
- Request/response formats
- Authentication (future)
- Rate limits
- Examples

### **[Data Management Guide](./DATA_MANAGEMENT_GUIDE.md)**
CRUD operations:
- Jurisdictions API
- Incentive Rules API
- Productions API
- Filtering and pagination

### **[Troubleshooting Guide](./TROUBLESHOOTING_GUIDE.md)**
Common issues and solutions:
- Frontend issues
- API errors
- Performance problems
- Database issues

### **[FAQ](./FAQ.md)**
Frequently asked questions:
- General questions
- Technical questions
- Usage questions
- Pricing and licensing

### **[Best Practices](./BEST_PRACTICES.md)**
Tips and recommendations:
- Frontend development
- API usage
- Production planning
- Security

---

## 🔐 Security

- Use HTTPS in production
- Validate all inputs
- Keep dependencies updated
- Never commit secrets
- See [Best Practices](./BEST_PRACTICES.md) for details

---

## 🛠️ Technology Stack

**Frontend:**
- React 19
- TypeScript 5.9
- React Router 7
- Tailwind CSS 4
- Vite 7

**Backend:**
- Python 3.12
- FastAPI 0.115
- Prisma ORM
- PostgreSQL 16
- Pydantic

**Reports:**
- ReportLab (PDF)
- OpenPyXL (Excel)

---

## 📊 Current Statistics

- **32** Global Jurisdictions
- **33** Incentive Programs
- **6** Calculator Endpoints
- **100%** API Coverage
- **100%** TypeScript Coverage

---

## 🗺️ Roadmap

### **Q1 2026**
- ✅ Enhanced UI with filtering
- ✅ Scenario modeling
- 🔄 User authentication (in progress)
- 📅 Saved calculations

### **Q2 2026**
- 📅 Email notifications
- 📅 Multi-currency expansion
- 📅 Mobile app
- 📅 Collaboration features

### **Q3 2026**
- 📅 AI-powered recommendations
- 📅 Budget optimization
- 📅 Real-time collaboration
- 📅 Expense tracking

### **Q4 2026**
- 📅 Advanced analytics
- 📅 Custom report templates
- 📅 GraphQL API
- 📅 Enterprise features

---

## 🤝 Contributing

We welcome contributions! Please see:
- [Contributing Guidelines](../CONTRIBUTING.md)
- [Code of Conduct](../CODE_OF_CONDUCT.md)
- [Development Setup](../README.md)

---

## 📞 Support

**Documentation:**
- User Manual (this document)
- [API Reference](http://localhost:8000/docs)
- [Project Summary](../PROJECT_SUMMARY.md)

**GitHub:**
- Repository: https://github.com/hneal055/Tax_Incentive_Compliance_Platform
- Issues: https://github.com/hneal055/Tax_Incentive_Compliance_Platform/issues
- Discussions: https://github.com/hneal055/Tax_Incentive_Compliance_Platform/discussions

**Community:**
- Report bugs via GitHub Issues
- Ask questions in Discussions
- Submit feature requests

---

## 📄 License

**Proprietary and Confidential** - Copyright (c) 2026 SceneIQ. All Rights Reserved. See [LICENSE](../LICENSE) for full terms and restrictions.

---

## 🙏 Acknowledgments

- FastAPI framework
- React ecosystem
- Prisma ORM
- PostgreSQL
- All contributors and users

---

**Thank you for using SceneIQ!**

*Making tax incentives simple for film & TV productions worldwide.*

---

**Document Version:** 1.1.0  
**Last Updated:** February 3, 2026  
**Next Review:** May 3, 2026