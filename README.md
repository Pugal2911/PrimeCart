# PrimeCart
### IoT-Enabled Smart E-Commerce Order Management System

## Project Overview
PrimeCart is a smart e-commerce web application that manages the complete order lifecycle from product purchase to delivery. The system integrates IoT-based RFID scanning and real-time communication to automate product tracking and order status updates.

The platform supports multiple user roles including **Admin, Customer, Seller, and Delivery Agent**, each with dedicated dashboards and role-based functionalities.

---

## Features
- Multi-role authentication system
- Product browsing and cart management
- Order lifecycle tracking (Processing → Shipped → Delivered)
- RFID-based product scanning
- Real-time order updates using Socket.IO
- Inventory management
- Delivery tracking system

---

## 🛠 Tech Stack

### Frontend
- HTML
- CSS
- JavaScript
- Bootstrap

### Backend
- Python
- Flask
- Flask-SocketIO

### Database
- MySQL

### IoT Integration
- RFID Tags
- ESP Module

---

## System Workflow
1. Customer browses products and places an order
2. Order status becomes **Processing**
3. Seller scans RFID tag to mark order as **Shipped**
4. Delivery agent scans RFID tag to mark order as **Delivered**

---

## Project Structure
PrimeCart/
│
├── static/ # CSS, JS, images
├── templates/ # HTML templates
├── app.py # Main Flask application
├── bc.py # Blockchain
├── create_admin.py # Creating the admin
├── requirements.txt 
└── README.md


---

## Security Features
- Password hashing using Werkzeug
- Session-based authentication
- Role-based access control

---

## Future Enhancements
- Online payment integration
- Email / SMS notifications
- Mobile application support
- Advanced analytics dashboard

---

## Author
**Sripugal D**
*Full Stack, Python Developer & Data Scientist*

GitHub: https://github.com/Pugal2911