# 🛍️ Noirette – E-Commerce Website

**Noirette** is a fully functional **E-Commerce web application** built with **Python (Django)**, designed to provide a smooth online shopping experience.  
It features secure payment integration via **Razorpay API**, **Google Authentication**, and a modern responsive design using **Bootstrap**.

---

## 🌐 Live Demo
🔗 [http://noirette.shop/](http://noirette.shop/)  
*(Currently offline for maintenance)*

---

## 🚀 Features
- 🏠 **Home Page** with featured products
- 🛒 Add to Cart & Wishlist
- 👤 **User Registration & Login** (Google Authentication)
- 💳 **Secure Online Payments** via Razorpay API
- 📦 Product Management (CRUD operations for admins)
- 📱 Mobile-Friendly Responsive Design (Bootstrap)
- 🗄️ PostgreSQL Database integration
- 🔍 Search and filter products
- 📜 Order history & tracking

---

## 🛠 Tech Stack

**Frontend:**
- HTML5
- CSS3
- Bootstrap 5

**Backend:**
- Python 3
- Django Framework

**Database:**
- PostgreSQL (psql)
- Django ORM

**Other Tools:**
- Razorpay API (Payments)
- Google Authentication
- AWS (Deployment)
- Git & GitHub (Version Control)

---

## ⚙️ Installation & Setup (For Developers)

Follow these steps to run **Noirette** locally:

# Clone the repository
git clone https://github.com/yourusername/noirette.git
cd noirette

# Create virtual environment
python -m venv env
source env/bin/activate   # Mac/Linux
env\Scripts\activate      # Windows

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver

Visit: http://127.0.0.1:8000

---

## 🎯 Learning Outcomes
While building **Noirette**, I learned:
- Integrating third-party APIs like Razorpay for secure payments
- Implementing Google Authentication in Django
- Managing a PostgreSQL database with Django ORM
- Designing a responsive and user-friendly UI with Bootstrap
- Deploying a Django application on AWS

---

## 🤝 Contributing
Suggestions and improvements are welcome!  
Feel free to fork this repository, make changes, and submit a pull request.

---

## 📜 License
This project is licensed under the **MIT License**.

---

**Author:** Joel Sunny  
📧 Email: [joelsunnyp@gmail.com](mailto:joelsunnyp@gmail.com)
