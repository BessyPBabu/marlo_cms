# MARLO CMS

Live Application: https://marlo-cms-production.up.railway.app/

---

## Project Overview

**MARLO CMS** is a production-ready Content Management System designed to allow users to publish, manage, and interact with blog content efficiently.

The application is built using **Python Django** with **PostgreSQL** as the database. Media files are stored in **Cloudinary**, and the application is deployed using **Railway**, enabling a scalable and reliable production environment.

The system supports content publishing workflows, user engagement features, comment moderation, and administrator-level management capabilities.

This project demonstrates real-world backend architecture, REST API development, authentication security, and deployment practices expected in professional full-stack roles.

---

## Project Idea

The objective of MARLO CMS is to develop a scalable blogging platform where:

* Administrators can manage users, blog posts, and comments.
* Authors can publish articles with images and attachments.
* Users can browse blog posts and read full content.
* Users can interact with posts using comments and likes.
* The system tracks engagement metrics such as read counts.
* Media files are securely stored in cloud storage.
* The application is deployed in a production environment.

The project focuses on modular architecture, API-driven design, authentication security, and maintainable code structure.

---

## Technology Stack

### Backend

* Python
* Django
* Django REST Framework
* JWT Authentication

### Frontend

* Django Templates (HTML, CSS)

### Database

* PostgreSQL

### Cloud Services

* Cloudinary (Media Storage)

### Deployment

* Railway (Application Hosting)
* Gunicorn

### Development Tools

* Git
* GitHub
* Whitenoise

---

## Core Features

### User Features

* View all blog posts
* Read full blog post details
* Add comments to blog posts
* Like blog posts
* Post read count tracking

### Admin Features

* Manage users (Create, Read, Update, Delete)
* Manage blog posts (Create, Read, Update, Delete)
* Upload images and attachments for blog posts
* Moderate comments (approve/block)
* Monitor user engagement metrics

---

## Modules

### Module 1 – Database and API Development

* Designed relational schema using PostgreSQL
* Implemented REST APIs using Django REST Framework
* Secured APIs using JWT authentication
* Core entities include users, blog posts, comments, reactions, and read counts

---

### Module 2 – Authentication and User Management

* Login system for administrators and users
* JWT-based authentication
* CRUD operations for users
* Role-based access control implementation

---

### Module 3 – Frontend Templates

* Blog post list page template
* Blog post detail page template
* UI built using Django templating engine

---

### Module 4 – Blog Management and Media Storage

* CRUD functionality for blog posts
* Image and file upload support
* Cloudinary integration for storing media files
* Media URLs stored and retrieved from database

---

### Module 5 – Blog Display

* List view for displaying all blog posts
* Detailed view for reading complete blog content
* Dynamic retrieval of images from Cloudinary

---

### Module 6 – Engagement System

* Comment functionality for each blog post
* Like and Unlike system
* Read count tracking for posts
* Admin moderation panel for comment approval or blocking

---

## System Architecture

Client Browser
│
▼
Django Templates (Frontend UI)
│
▼
Django Views / REST APIs
│
├── JWT Authentication Layer
│
├── Business Logic Layer
│
▼
PostgreSQL Database
│
▼
Cloudinary (Media Storage)
│
▼
Railway Deployment (Gunicorn Server)

---

## Repository Name

marlo_cms
