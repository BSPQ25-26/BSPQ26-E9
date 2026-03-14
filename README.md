# BSPQ26-E9
Repository for team BSPQ26-E9

# Wallabot: AI-Powered Microservices Marketplace

Wallabot is a multi-tier, distributed **RESTful microservice architecture** designed to provide a seamless buying and selling experience. The platform integrates advanced AI capabilities via "Wallabot," an intelligent agent that assists users with automated category suggestions and competitive price recommendations.

---

## Features

### **User Management & Authentication**

* **Secure Access**: Traditional registration and login using email and password with hashed storage for security.


* **Social Integration**: OAuth2 authentication flow supporting Google and Facebook accounts.


* **Identity**: Stateless authentication handled via JWT tokens with set expirations.


* **Trust System**: A post-transaction rating (1-5 stars) and review system to build community trust.



### **Inventory & Transaction Engine**

* **Product Lifecycle**: Full CRUD operations for sellers, including image uploads (JPEG/PNG) and quality specifications.


* **State Management**: Atomic transitions between `Available`, `Reserved`, and `Sold` states to ensure data integrity.


* **Virtual Wallet**: Integrated wallet system for adding funds and making secure, balance-validated purchases.



### **Wallabot (AI Agent)**

* 
**Smart Categorization**: Automatically suggests product categories in structured JSON format.


* **Price Recommendations**: Provides competitive pricing data utilizing the **TO BE DEFINED**.


* **Observability**: Uses **TO BE DEFINED** to trace AI reasoning, monitor decisions, and alert on invalid responses.



### **User Experience**

* **Reactive Frontend**: Built with **TO BE DEFINED** for an intuitive and responsive product listing interface.


* 
**Advanced Filtering**: Capability to filter the product catalog by state, category, price range, and item quality.



---

## Stack

| Component | Technology |
| --- | --- |

 |
|  **Backend** | FastAPI (Python) 

 |
| **Frontend** | TO BE DEFINED

 |
| **Database** | TO BE DEFINED 

 |
| **AI Monitoring** | TO BE DEFINED 

 |
| **External AI API** | TO BE DEFINED

 |
| **Containerization** | Docker & Docker Compose 

 |
| **CI/CD** | GitHub Actions 

 

---

## Development & Deployment

### **Containerization**

Each microservice is containerized using optimized **Dockerfiles**. You can spin up the entire local environment, including the database and services, using **Docker Compose**.

### **CI/CD Pipeline**

The project uses **GitHub Actions** to automate quality assurance. The pipeline:

1. Runs unit and integration tests.


2. Blocks merges if builds fail, ensuring continuous delivery of stable code.



---

## Product Backlog Highlights

The project is prioritized to ensure core functionality is delivered first:

* **High Priority (1-2)**: Email/Password Authentication, Basic Product Listings, and Containerization.


* **Medium Priority (3-5)**: Wallet Management, Image Uploads, and CI/CD Pipeline Setup.


* **AI & Social (6-9)**: Social Logins, AI Category/Price suggestions, and User Ratings.



---
